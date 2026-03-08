.PHONY: install migrate seed run test

BACKEND_DIR ?= backend
PYTHON ?= python3
PIP ?= pip3

install:
	cd $(BACKEND_DIR) && $(PIP) install -r requirements.txt

migrate:
	cd $(BACKEND_DIR) && $(PYTHON) -m alembic upgrade head

seed:
	cd $(BACKEND_DIR) && $(PYTHON) -m data.seed

run:
	cd $(BACKEND_DIR) && $(PYTHON) -m uvicorn app:app --reload --port 8000

test:
	cd $(BACKEND_DIR) && $(PYTHON) -m pytest -q
