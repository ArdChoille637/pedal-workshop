PYTHON = python3.11
VENV = .venv
PIP = $(VENV)/bin/pip
UVICORN = $(VENV)/bin/uvicorn
ALEMBIC = $(VENV)/bin/alembic

.PHONY: setup dev-api dev-ui migrate migrate-new seed index-schematics build clean

# First-time setup: venv, deps, DB, seed, index
setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -r requirements.txt
	cd ui && npm install
	mkdir -p data/design_files
	cp -n .env.example .env 2>/dev/null || true
	$(VENV)/bin/python scripts/seed_db.py
	$(VENV)/bin/python scripts/index_schematics.py
	@echo ""
	@echo "Setup complete! Run 'make dev-api' and 'make dev-ui' in separate terminals."

# Run API dev server (port 8000, auto-reload)
dev-api:
	cd /Users/home/schematics/workshop && PYTHONPATH=. $(UVICORN) api.main:app --reload --host 127.0.0.1 --port 8000

# Run UI dev server (port 5173, proxies /api to 8000)
dev-ui:
	cd ui && npm run dev

# Database migrations
migrate:
	cd /Users/home/schematics/workshop && PYTHONPATH=. $(ALEMBIC) -c api/migrations/alembic.ini upgrade head

migrate-new:
	cd /Users/home/schematics/workshop && PYTHONPATH=. $(ALEMBIC) -c api/migrations/alembic.ini revision --autogenerate -m "$(MSG)"

# Seed database with common components and suppliers
seed:
	cd /Users/home/schematics/workshop && PYTHONPATH=. $(VENV)/bin/python scripts/seed_db.py

# Re-index schematic library (run after adding new files)
index-schematics:
	cd /Users/home/schematics/workshop && PYTHONPATH=. $(VENV)/bin/python scripts/index_schematics.py

# Production build: bundle UI, serve from FastAPI
build:
	cd ui && npm run build
	@echo "UI built to ui/dist/. Run 'make dev-api' to serve both API and UI."

# Clean generated files
clean:
	rm -rf $(VENV) ui/node_modules ui/dist data/workshop.db __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
