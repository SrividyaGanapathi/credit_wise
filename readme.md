# Credit Wise

Credit Wise is a full-stack app that recommends the best credit card for a purchase.

Current status:
- Phase 0 complete
- Next: seed data and move `/recommend` from hardcoded logic to DB-driven ranking

## Architecture

```text
+---------------------+         +------------------------+
|  React + Vite UI    | <-----> |  FastAPI Backend API   |
+---------------------+         +------------------------+
                                         |
                                         v
                           +-----------------------------+
                           | Recommendation Service      |
                           | (rule match + scoring)      |
                           +-----------------------------+
                               |                   |
                               v                   v
                 +-------------------------+   +--------------------------+
                 | Structured DB           |   | Unstructured Vector DB   |
                 | cards, reward_rules,    |   | PDF/HTML chunks +        |
                 | users, user_cards       |   | embeddings (future phase)|
                 +-------------------------+   +--------------------------+
```

Notes:
- Structured DB is the source of truth for recommendations.
- Vector DB is support context for extraction and explainability, not direct truth.

## Product Phases

### Phase 0: Simplest Product Shape
- Bootstrapped repo and split backend/frontend.
- Goal: type purchase, get best card.

### Phase 1: Local-only MVP
- Built FastAPI and React flow end-to-end.
- `/recommend` works with hardcoded rules for demo speed.

### Phase 2: Data-driven Core
- Replace hardcoded logic with DB-driven rules.
- Add `cards` and `reward_rules`; manage schema with Alembic.
- Goal: adding a card/rule should be data entry, not code changes.

### Phase 3: Realism and Explainability
- Add caps, spend tracking, and richer outputs.
- Return top recommendations with rule IDs, cap remaining, warnings, and score breakdowns.

### Phase 4: Containerization
- Dockerize backend for portable runtime.
- Goal: same image locally and in cloud.

### Phase 5: First GCP Deploy
- Deploy backend + managed DB + hosted frontend.
- Goal: shareable public URL.

### Phase 6: Auth
- Add Firebase Auth and backend token verification.
- Goal: secure per-user wallet and spend state.

### Phase 7: API Gateway
- Add API keys/quotas/versioned edge.
- Goal: production-style API control.

### Phase 8: Analytics and Operations
- Add usage/event pipelines, dashboards, and alerts.
- Goal: observability once traffic grows.

## Backend Data Model

Canonical structured schema:
- `users`
- `cards`
- `reward_rules`
- `user_cards`

Design intent:
- `cards` stores stable card metadata (issuer, name, fees, network)
- `reward_rules` stores earning logic (category/channel/country, multiplier, caps, priority)
- this keeps recommendation behavior data-driven instead of hardcoded in Python

## Local Setup

This project uses Conda environment `credit-wise-env` (not `.venv`).

1. Activate env
```bash
conda activate credit-wise-env
```

2. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

3. Run migrations
```bash
python -m alembic upgrade head
```

4. Run backend
```bash
uvicorn app:app --reload --port 8000
```

5. Health check
```bash
curl -s http://localhost:8000/health
```

## Migrations (Alembic)

Alembic is configured under `backend/`:
- config: `backend/alembic.ini`
- environment: `backend/alembic/env.py`
- versions: `backend/alembic/versions/`

Run latest migration:
```bash
conda activate credit-wise-env
cd backend
python -m alembic upgrade head
```

Create a new migration after model changes:
```bash
conda activate credit-wise-env
cd backend
python -m alembic revision --autogenerate -m "describe change"
python -m alembic upgrade head
```

Current initial migration:
- `553a5f31132d_initial_schema.py`

## API Endpoints (Current)

### `GET /health`
Response:
```json
{"ok": true}
```

### `POST /recommend`
Current behavior is still hardcoded (temporary).  
Target response contract for next step:
- `top_3` list with:
  - `card_id`
  - `card_name`
  - `score`
  - `applied_rule_ids`
  - `reasons`
- if user has only 2 cards, return/rank 2

## Frontend

Frontend stack:
- React
- TypeScript
- Vite
