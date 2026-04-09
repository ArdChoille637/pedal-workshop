# Pedal Workshop

Inventory, build management, and prototyping tool for boutique guitar/bass pedals and stomp boxes.

## Tech Stack
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy + SQLite (WAL mode)
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS + TanStack Table/Query
- **Migrations**: Alembic
- **Supplier Polling**: APScheduler (in-process background scheduler)

## Project Structure
- `api/` - FastAPI backend (models, schemas, routers, services, suppliers)
- `ui/` - React frontend (pages, components, hooks)
- `data/` - SQLite database and uploaded design files (gitignored)
- `seeds/` - Seed data (components, suppliers, sample project)
- `scripts/` - CLI scripts (seed_db.py, index_schematics.py)
- Parent directory (`../`) contains 24 folders of schematic reference files (untouched)

## Key Commands
```bash
make setup          # First-time: venv, deps, DB, seed, index
make dev-api        # API server on :8000 (auto-reload)
make dev-ui         # UI dev server on :5173 (proxies /api)
make migrate        # Run Alembic migrations
make seed           # Re-seed database
make index-schematics  # Re-index schematic library
```

## Architecture Notes
- All API routes are under `/api/` prefix
- Build analyzer (`api/services/build_analyzer.py`) is the core feature: classifies projects into Ready/ARNA 1-3/ARNA 4+ tiers based on BOM vs inventory
- Supplier adapters in `api/suppliers/` follow a protocol (`base.py`). Most are stubs pending implementation.
- Frontend uses React Query for data fetching, proxies `/api` to FastAPI in dev mode
- SQLite with WAL mode, foreign keys enforced via PRAGMA on connect
