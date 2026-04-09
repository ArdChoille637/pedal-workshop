from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import builds, components, dashboard, design_files, projects, schematics, suppliers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: launch background scheduler if supplier polling is configured
    from api.tasks.scheduler import start_scheduler, stop_scheduler
    scheduler = start_scheduler()
    yield
    # Shutdown
    stop_scheduler(scheduler)


app = FastAPI(
    title="Pedal Workshop",
    description="Inventory, build management, and prototyping tool for boutique guitar pedals",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(components.router)
app.include_router(projects.router)
app.include_router(builds.router)
app.include_router(dashboard.router)
app.include_router(suppliers.router)
app.include_router(schematics.router)
app.include_router(design_files.router)

# Serve built frontend in production (if ui/dist exists)
ui_dist = Path(__file__).resolve().parent.parent / "ui" / "dist"
if ui_dist.is_dir():
    app.mount("/", StaticFiles(directory=str(ui_dist), html=True), name="ui")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "pedal-workshop"}
