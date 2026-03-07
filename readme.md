# Credit Wise

Credit Wise is a full-stack app that recommends the best credit card for a purchase.

## Roadmap

Current phase: **Phase 2 (Data-driven Core)**.

- Phase 0: Bootstrap repo and basic app shape.
- Phase 1: Local MVP with hardcoded recommendation path.
- Phase 2: Structured DB + rules engine + DB-driven `/recommend`.
- Phase 3: Realism and explainability (caps, spend tracking, richer outputs).
- Phase 4: Containerization and portable deployment.
- Phase 5: First GCP deploy (backend, DB, hosted frontend).
- Phase 6: Auth and user-specific secure access.
- Phase 7: API Gateway (keys, quotas, versioning).
- Phase 8: Analytics and operations (events, dashboards, alerts).

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

## Local Setup (Backend)

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

4. Seed starter card data
```bash
python -m data.seed
```

5. Run backend
```bash
uvicorn app:app --reload --port 8000
```

6. Health check
```bash
curl -s http://localhost:8000/health
```

## Migrations

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
  - `applied_rule_ids`
  - `reasons`
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
