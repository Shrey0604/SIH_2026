SHELL := /bin/bash
PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: install dev backend frontend test lint typecheck check seed reset clean

install:
	$(PYTHON) -m pip install -r backend/requirements.txt
	npm --prefix frontend install

dev:
	./scripts/dev.sh

backend:
	set -a; [[ ! -f .env ]] || source .env; set +a; $(PYTHON) -m uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000

frontend:
	set -a; [[ ! -f .env ]] || source .env; set +a; npm --prefix frontend run dev

test:
	PYTHONPATH=backend $(PYTHON) -m unittest discover -s backend/tests -v

lint:
	npm --prefix frontend run lint

typecheck:
	npm --prefix frontend run typecheck

check: test lint typecheck

seed:
	PYTHONPATH=backend $(PYTHON) -m app.scripts.seed

reset:
	curl --fail --silent --show-error -X POST http://localhost:8000/api/demo/reset

clean:
	$(PYTHON) -c "from pathlib import Path; p=Path('backend/data/nwis.db'); p.unlink(missing_ok=True)"
