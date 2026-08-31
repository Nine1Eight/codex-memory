.PHONY: bootstrap format lint typecheck test verify smoke migrate build dev down test-db-real

PYTHON ?= python3

bootstrap:
	@$(PYTHON) scripts/verify_bootstrap.py

format:
	@$(PYTHON) scripts/verify_bootstrap.py --format

lint:
	@$(PYTHON) scripts/verify_bootstrap.py --lint

typecheck:
	@$(PYTHON) scripts/verify_bootstrap.py --typecheck

test:
	@$(PYTHON) -m pytest -q

verify: format lint typecheck test

smoke:
	@$(PYTHON) scripts/smoke_test.py

migrate:
	@$(PYTHON) scripts/apply_migrations.py --mode sqlite

build:
	@printf '%s\n' "No build artifacts yet."

dev:
	@AGENTVIEW_DATABASE_PATH="$${AGENTVIEW_DATABASE_PATH:-$$HOME/.agentview.sqlite3}" $(PYTHON) -m uvicorn agentview_api.app:app --app-dir apps/api --reload

down:
	@printf '%s\n' "No services to stop in milestone 0."

test-db-real:
	@sh scripts/real_db_harness.sh
