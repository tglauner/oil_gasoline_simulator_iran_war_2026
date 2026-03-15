PYTHON ?= python3

.PHONY: frontend-install frontend-dev frontend-build backend-venv backend-dev backend-test bootstrap

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

backend-venv:
	cd backend && $(PYTHON) -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

backend-dev:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

backend-test:
	cd backend && . .venv/bin/activate && pytest

bootstrap:
	sh scripts/bootstrap_local.sh
