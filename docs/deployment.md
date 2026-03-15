# Deployment Guide

This project is currently deployed on Google Cloud with:

- Cloud Run backend
- Cloud SQL for PostgreSQL
- Artifact Registry for container images
- Firebase Hosting prepared for the frontend

## Current Production Status

As of March 14, 2026:

- Project ID: `card-wise-app`
- Region: `us-central1`
- Cloud Run service: `credit-wise-backend`
- Cloud SQL instance: `cardwise-db`
- Public backend URL: `https://credit-wise-backend-329719459408.us-central1.run.app`

## Production Backend Flow

The backend container startup sequence is:

1. Run Alembic migrations
2. Optionally run seed data when `RUN_SEED_ON_STARTUP=true`
3. Start `uvicorn` on the port provided by Cloud Run

Implementation lives in [backend/start.sh](/Users/sri/Downloads/credit_wise/backend/start.sh).

## Required Environment Variables

Backend deploys expect these values:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `AR_REPO`
- `CLOUD_RUN_SERVICE`
- `CLOUD_SQL_CONNECTION_NAME`
- `DATABASE_URL`

Optional:

- `RUN_SEED_ON_STARTUP=true`
  Use only for one-time catalog initialization.

## DATABASE_URL Format

For Cloud Run + Cloud SQL Unix socket connections:

```text
postgresql+psycopg2://USER:PASSWORD@/cardwise?host=/cloudsql/PROJECT:REGION:INSTANCE
```

If the password contains reserved characters like `@`, URL-encode them.
Example:

```text
cwdb@1 -> cwdb%401
```

Alembic’s runtime config is patched to safely handle URL-encoded passwords in [backend/alembic/env.py](/Users/sri/Downloads/credit_wise/backend/alembic/env.py).

## Standard Deploy

```bash
export GCP_PROJECT_ID=card-wise-app
export GCP_REGION=us-central1
export AR_REPO=credit-wise
export CLOUD_RUN_SERVICE=credit-wise-backend
export CLOUD_SQL_CONNECTION_NAME=card-wise-app:us-central1:cardwise-db
export DATABASE_URL='postgresql+psycopg2://appuser:YOUR_URL_ENCODED_PASSWORD@/cardwise?host=/cloudsql/card-wise-app:us-central1:cardwise-db'

./scripts/deploy_backend_gcp.sh
```

## One-Time Seed Deploy

Only use this when the Cloud SQL catalog is empty or when you intentionally want to refresh seed-managed catalog data.

```bash
export RUN_SEED_ON_STARTUP=true
./scripts/deploy_backend_gcp.sh
```

After the seed deploy succeeds, remove the flag by redeploying normally:

```bash
unset RUN_SEED_ON_STARTUP
./scripts/deploy_backend_gcp.sh
```

## Verification

Health check:

```bash
curl -s https://credit-wise-backend-329719459408.us-central1.run.app/health
```

Recommendation smoke test:

```bash
curl -s -X POST https://credit-wise-backend-329719459408.us-central1.run.app/recommend \
  -H "Content-Type: application/json" \
  -d '{"amount":100,"category":"DINING","country":"US","channel":"ONLINE"}'
```

## Frontend Hosting

Build the frontend for production:

```bash
export VITE_API_BASE_URL=https://credit-wise-backend-329719459408.us-central1.run.app
./scripts/build_frontend_firebase.sh
```

Firebase Hosting config lives in [firebase.json](/Users/sri/Downloads/credit_wise/firebase.json).
