# Credit Wise

Credit Wise is a full-stack credit card recommendation app. It ranks the best card for a purchase using DB-driven reward rules and explains why a card was chosen.

The app is live on Google Cloud:

- Frontend: `https://card-wise-app.web.app`
- Backend: `https://credit-wise-backend-329719459408.us-central1.run.app`

To learn how the recommender model works, see [docs/recommender.md](/Users/sri/Downloads/credit_wise/docs/recommender.md).

## What It Does

- Recommends the best card for a purchase amount, category, country, and channel
- Uses Postgres-backed `cards` and `reward_rules` data instead of hardcoded card logic
- Returns explainable results with estimated dollar savings, a 10-point card score, `applied_rule_ids`, and warnings
- Supports authenticated and guest access with Firebase Auth
- Supports wallet-based recommendations for signed-in users, plus full-catalog browsing for guests or first-time users
- Captures recommendation impressions and card selections for future model and product analysis

## Current Features

- FastAPI backend with SQLAlchemy and Alembic
- PostgreSQL locally via Docker Compose and in production via Cloud SQL
- Recommendation engine with category, channel, and country rule matching
- FX fee handling and top-3 ranked results
- Explainable recommendation output
- Estimated savings in dollars plus a normalized 10-point score
- Google sign-in, email/password auth, and guest mode
- New-user wallet onboarding with card search, issuer grouping, and add-to-wallet flow
- Recommendation mode toggle between `My Wallet` and `Full Catalog`
- Recommendation analytics events for impressions and selections
- React + Vite frontend deployed on Firebase Hosting
- Backend deployed on Cloud Run
- CORS configured for local dev and hosted frontend origins
- GitHub Actions CI for backend tests and frontend build

## Architecture

```text
                           End-to-end runtime architecture

┌──────────────────────┐
│ User Browser         │
│ card-wise-app.web.app│
└──────────┬───────────┘
           │ loads SPA
           v
┌──────────────────────────────────────┐
│ Firebase Hosting                     │
│ React + Vite frontend                │
│ - sign-in UI                         │
│ - wallet onboarding                  │
│ - recommend form                     │
│ - result dashboard                   │
└───────┬───────────────────────┬──────┘
        │                       │
        │ Auth flows            │ HTTPS API calls with bearer token
        v                       v
┌───────────────────┐     ┌──────────────────────────────────────────┐
│ Firebase Auth     │     │ Cloud Run: FastAPI backend              │
│ Google, email,    │     │ Routes                                  │
│ and anonymous     │     │ - GET /health                           │
│ issues ID token   │     │ - GET /auth/me                          │
└─────────┬─────────┘     │ - GET /cards                            │
          │ ID token      │ - GET /users/me/cards                   │
          └──────────────>│ - POST /users/me/cards                  │
                          │ - POST /events/recommendation           │
                          │ - POST /recommend                       │
                          │ - POST /usage/log                       │
                          ├──────────────────────────────────────────┤
                          │ Backend modules                         │
                          │ - CORS + request handling               │
                          │ - Firebase token verification           │
                          │ - recommendation service                │
                          │ - event logging                         │
                          │ - SQLAlchemy ORM                        │
                          └──────────────────┬───────────────────────┘
                                             │ SQL
                                             v
                          ┌──────────────────────────────────────────┐
                          │ Cloud SQL Postgres                       │
                          │ - users                                  │
                          │ - cards                                  │
                          │ - reward_rules                           │
                          │ - user_cards                             │
                          │ - spend_tracker                          │
                          │ - recommendation_events                  │
                          └──────────────────────────────────────────┘
```

Request flow:

- The browser loads the React app from Firebase Hosting.
- Users authenticate with Firebase Auth and receive an ID token.
- The frontend sends the ID token to FastAPI as a bearer token when user-specific features are active.
- FastAPI verifies the token, maps it to an app user, and serves wallet and analytics endpoints.
- Recommendation requests can run in either full-catalog mode or wallet mode.
- Recommendation and selection events are written to Cloud SQL for future analysis.

Primary tables:

- `users`
- `cards`
- `reward_rules`
- `user_cards`
- `spend_tracker`
- `recommendation_events`

## Tech Stack

- Frontend: React, Vite, Firebase Auth
- Backend: FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL
- Local infra: Docker Compose
- Cloud: Firebase Hosting, Cloud Run, Cloud SQL, Artifact Registry

## API Snapshot

- `GET /health` returns a simple health check
- `GET /auth/me` verifies a Firebase bearer token and returns the current app user
- `GET /cards` returns the active card catalog used by wallet onboarding
- `GET /users/me/cards` returns the signed-in user wallet
- `POST /users/me/cards` adds a card to the signed-in user wallet
- `POST /events/recommendation` logs recommendation impressions and card selections
- `POST /recommend` returns `best_card`, `top_3`, `explanations`, and applied rule metadata

Recommendation responses include:

- `net_value` as estimated dollar savings
- `score` as a normalized score out of `10`
- `applied_rule_ids`
- `warnings`
- optional `recommendation_mode` in the request body: `catalog` or `wallet`

## Local Development

### Backend

From the repo root:

```bash
docker compose up -d db
cp .env.example .env
cd backend
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m data.seed
python3 -m uvicorn app:app --reload --port 8000
```

Health check:

```bash
curl -s http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`

## Environment

Key variables are documented in [`.env.example`](/Users/sri/Downloads/credit_wise/.env.example).

Important values:

- `DATABASE_URL`
- `APP_HOST`
- `PORT`
- `APP_PORT`
- `FIREBASE_PROJECT_ID`
- `CORS_ALLOWED_ORIGINS`
- `VITE_API_BASE_URL`
- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_APP_ID`
- `RUN_SEED_ON_STARTUP`

`RUN_SEED_ON_STARTUP` is for controlled one-time initialization only. It should not stay enabled in normal runtime.

## Database and Migrations

Alembic lives under `backend/`.

Run migrations:

```bash
cd backend
python3 -m alembic upgrade head
```

Create a new migration:

```bash
cd backend
python3 -m alembic revision --autogenerate -m "describe change"
python3 -m alembic upgrade head
```

Notable migrations:

- `553a5f31132d_initial_schema.py`
- `30c2a2716f7c_add_spend_tracker.py`
- `6589d6b4e8b1_add_firebase_uid_to_users.py`

## Deployment

### Backend

The backend container:

- reads `DATABASE_URL` from env
- runs Alembic migrations on startup
- can do a one-time seed when `RUN_SEED_ON_STARTUP=true`

Deploy with:

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
export GCP_REGION=us-central1
export AR_REPO=credit-wise
export CLOUD_RUN_SERVICE=credit-wise-backend
export CLOUD_SQL_CONNECTION_NAME=YOUR_PROJECT_ID:us-central1:YOUR_SQL_INSTANCE
export FIREBASE_PROJECT_ID=YOUR_PROJECT_ID
export DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@/cardwise?host=/cloudsql/YOUR_PROJECT_ID:us-central1:YOUR_SQL_INSTANCE'

./scripts/deploy_backend_gcp.sh
```

### Frontend

Build the frontend against the deployed backend:

```bash
export VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL
./scripts/build_frontend_firebase.sh
```

Then deploy with Firebase Hosting.

## Project Status

Implemented:

- data-driven recommendation engine
- explainable recommendation output
- guest, full-catalog, and wallet-based recommendation journeys
- new-user wallet onboarding and saved-card setup
- recommendation impression and selection logging
- Dockerized local stack
- Cloud Run + Cloud SQL production backend
- Firebase Hosting production frontend
- Firebase Auth-backed user flows, including guest mode

Next likely areas:

- reintroduce cap tracking and usage logging once real user data exists
- add richer wallet management such as remove/edit cards and starter wallet imports
- stronger integration testing against Postgres
- API gateway, analytics, and ops hardening

## Additional Docs

- Deployment runbook: [docs/deployment.md](/Users/sri/Downloads/credit_wise/docs/deployment.md)
