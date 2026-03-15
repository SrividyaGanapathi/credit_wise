# Credit Wise

Credit Wise is a full-stack app that recommends the best credit card for a purchase.
It is now data-driven, containerized, and deployed on Google Cloud.

## Roadmap

Current phase: **Phase 5 complete; Phase 6 (auth) is next**.

- Phase 0: Bootstrap repo and basic app shape.
- Phase 1: Local MVP with hardcoded recommendation path.
- Phase 2: Structured DB + rules engine + DB-driven `/recommend`.
- Phase 3: Realism and explainability (caps, spend tracking, richer outputs).
- Phase 4: Containerization and portable deployment.
- Phase 5: First GCP deploy (backend, DB, hosted frontend).
- Phase 6: Auth and user-specific secure access.
- Phase 7: API Gateway (keys, quotas, versioning).
- Phase 8: Analytics and operations (events, dashboards, alerts).

## Current Status

Implemented:

- DB-driven recommendations from `cards` and `reward_rules`
- spend tracking and cap-aware ranking
- Dockerized backend and frontend
- Postgres via Docker Compose for local development
- Cloud SQL + Cloud Run production backend
- GitHub Actions CI for backend tests and frontend build

Current production backend:

- Cloud Run URL: `https://credit-wise-backend-329719459408.us-central1.run.app`
- Health check: passing
- Cloud SQL catalog: seeded

Current production frontend:

- Firebase Hosting URL: `https://card-wise-app.web.app`

Next:

- add real auth when public multi-user access is needed
- connect frontend login state to backend user-specific data

## Architecture

```text
+--------------------------+
| Firebase Hosting         |
| serves React + Vite UI   |
+--------------------------+
             |
             v
+--------------------------+         +-----------------------------+
| React Frontend           | <-----> | FastAPI on Cloud Run        |
| uses deployed API URL    |         | recommendation API          |
+--------------------------+         +-----------------------------+
                                                  |
                                                  v
                                   +-----------------------------+
                                   | Recommendation Service      |
                                   | rule match + scoring        |
                                   +-----------------------------+
                                                  |
                                                  v
                                   +-----------------------------+
                                   | Cloud SQL Postgres          |
                                   | cards, reward_rules, users, |
                                   | user_cards, spend_tracker   |
                                   +-----------------------------+
```

Notes:
- Structured DB is the source of truth for recommendations.
- production frontend runs on Firebase Hosting.
- production backend runs on Cloud Run and connects to Cloud SQL.

## Backend Data Model

Canonical structured schema:
- `users`
- `cards`
- `reward_rules`
- `user_cards`
- `spend_tracker`

Design intent:
- `cards` stores stable card metadata (issuer, name, fees, network)
- `reward_rules` stores earning logic (category/channel/country, multiplier, caps, priority)
- `spend_tracker` stores user spend by rule and period (`user_id`, `rule_id`, `period_start`, `spent_amount`) so cap-aware recommendations are possible
- this keeps recommendation behavior data-driven instead of hardcoded in Python

## Local Setup (Backend)

Canonical local backend path is Postgres + Alembic.

1. Start Postgres
```bash
docker compose up -d db
```

2. Optional: copy env defaults
```bash
cp .env.example .env
```

3. Install backend dependencies
```bash
cd backend
python3 -m pip install -r requirements.txt
```

4. Run migrations
```bash
python3 -m alembic upgrade head
```

5. Seed starter card data
```bash
python3 -m data.seed
```

6. Run backend
```bash
python3 -m uvicorn app:app --reload --port 8000
```

7. Health check
```bash
curl -s http://localhost:8000/health
```

## Local Setup (Frontend)

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open: `http://127.0.0.1:5173`

Frontend dev proxy can be changed with `VITE_API_PROXY_TARGET`.

## Docker Setup (Backend + Postgres)

At repo root:

```bash
docker compose up --build
```

Services:
- backend: `http://localhost:8000`
- frontend: `http://localhost:5173`
- postgres: `localhost:5432` (`postgres/postgres`, db `cardwise`)

Stop:
```bash
docker compose down
```

## Environment Variables

Shared defaults are documented in [`.env.example`](/Users/sri/Downloads/credit_wise/.env.example).

Key values:
- `DATABASE_URL`: backend database connection string
- `APP_HOST`: backend bind host
- `PORT`: backend listen port for container/cloud runtimes
- `APP_PORT`: local backend port fallback
- `VITE_API_BASE_URL`: frontend build-time API base URL
- `VITE_API_PROXY_TARGET`: frontend dev-server proxy target
- `RUN_SEED_ON_STARTUP`: optional one-time startup seed flag, intended for controlled initialization only

## Migrations

Alembic is configured under `backend/`:
- config: `backend/alembic.ini`
- environment: `backend/alembic/env.py`
- versions: `backend/alembic/versions/`

Run latest migration:
```bash
cd backend
python3 -m alembic upgrade head
```

Create a new migration after model changes:
```bash
cd backend
python3 -m alembic revision --autogenerate -m "describe change"
python3 -m alembic upgrade head
```

Current initial migration:
- `553a5f31132d_initial_schema.py`

Latest migration:
- `30c2a2716f7c_add_spend_tracker.py`

## API

### `GET /health`
Response:
```json
{"ok": true}
```

### `POST /recommend`
Current behavior is DB-driven from `cards` + `reward_rules`.
Response contract:
- `best_card` (top ranked card object, or `null` if none)
- `top_3` list with:
  - `card_id`
  - `card_name`
  - `score`
  - `net_value`
  - `applied_rule_ids`
  - `reasons`
  - `cap_remaining`
  - `warnings`
- `explanations` (flat list of reasoning strings)
- `debug.applied_rule_ids` (unique rule IDs used in ranking)
- if `user_id` is provided and user has only 2 active cards, return/rank 2

### `POST /users/{user_id}/cards`
Attach (or update) a card in a user's wallet.

Example:
```bash
curl -s -X POST http://localhost:8000/users/1/cards \
  -H "Content-Type: application/json" \
  -d '{"card_id":2,"nickname":"My Gold","is_active":true}'
```

### `POST /usage/log`
Logs user spend against a reward rule and period, then returns updated cap usage context.

Example:
```bash
curl -s -X POST http://localhost:8000/usage/log \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"rule_id":2,"amount":120,"period_start":"2026-03-01"}'
```

## Cloud Run Backend Deploy

This repo is now prepared for backend-only Cloud Run deployment. The backend container:
- uses `PORT` from the environment
- runs Alembic migrations on startup
- optionally seeds reference data when `RUN_SEED_ON_STARTUP=true`
- reads `DATABASE_URL` from env

Typical deployment flow:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com
gcloud auth application-default login
```

Create Artifact Registry once:

```bash
gcloud artifacts repositories create credit-wise \
  --repository-format=docker \
  --location=us-central1
```

Build and deploy from repo root with env vars:

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
export GCP_REGION=us-central1
export AR_REPO=credit-wise
export CLOUD_RUN_SERVICE=credit-wise-backend
export CLOUD_SQL_CONNECTION_NAME=YOUR_PROJECT_ID:us-central1:YOUR_SQL_INSTANCE
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@/cardwise?host=/cloudsql/YOUR_PROJECT_ID:us-central1:YOUR_SQL_INSTANCE'

./scripts/deploy_backend_gcp.sh
```

Notes:
- for Cloud Run, point `DATABASE_URL` at Cloud SQL Postgres or another reachable Postgres instance
- if the password contains `@` or similar reserved characters, URL-encode it
- only set `RUN_SEED_ON_STARTUP=true` for a controlled one-time seed deploy
- current production backend URL is `https://credit-wise-backend-329719459408.us-central1.run.app`

## Firebase Hosting Deploy

Set the frontend API base URL to the Cloud Run service URL and build:

```bash
export VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL
./scripts/build_frontend_firebase.sh
```

Then initialize your local Firebase project mapping once:

```bash
cp .firebaserc.example .firebaserc
```

Deploy:

```bash
npm install -g firebase-tools
firebase login
firebase deploy --only hosting
```

Current production frontend URL:

`https://card-wise-app.web.app`

## Additional Docs

- Google Cloud deployment runbook: [docs/deployment.md](/Users/sri/Downloads/credit_wise/docs/deployment.md)
