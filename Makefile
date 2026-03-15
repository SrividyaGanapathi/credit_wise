.PHONY: install migrate seed run test frontend-build docker-up docker-down docker-logs gcp-backend-deploy firebase-build

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

frontend-build:
	cd frontend && npm ci && npm run build

gcp-backend-deploy:
	./scripts/deploy_backend_gcp.sh

firebase-build:
	./scripts/build_frontend_firebase.sh

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend db frontend
