# Credit Wise

Credit Wise is a full-stack app that recommends the best credit card for a purchase.

## Roadmap

Current phase: **Phase 3 (Realism + Explainability) - Step 2 complete**.

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
- `spend_tracker`

Design intent:
- `cards` stores stable card metadata (issuer, name, fees, network)
- `reward_rules` stores earning logic (category/channel/country, multiplier, caps, priority)
- `spend_tracker` stores user spend by rule and period (`user_id`, `rule_id`, `period_start`, `spent_amount`) so cap-aware recommendations are possible
- this keeps recommendation behavior data-driven instead of hardcoded in Python

## Product Improvement: Spend Tracking

Why this matters:
- reward programs often have monthly/quarterly/yearly caps
- static rules can over-recommend cards after caps are already consumed
- spend tracking enables user-specific, realistic recommendations and clearer explanations

Business impact:
- better recommendation accuracy after real usage
- improved trust via explainable outcomes (`cap remaining`, cap warnings)
- foundation for true Phase 3 ranking (`net value`, not just raw multiplier)

## Local Setup (Backend)

1. Install backend dependencies
```bash
cd backend
python3 -m pip install -r requirements.txt
```

2. Run migrations
```bash
python3 -m alembic upgrade head
```

3. Seed starter card data
```bash
python3 -m data.seed
```

4. Run backend
```bash
python3 -m uvicorn app:app --reload --port 8000
```

5. Health check
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

## Next Step

Phase 3 Step 3:
- add a frontend workflow to log usage (`/usage/log`) before recommendation
- show richer explanation blocks in UI (cap consumed, FX impact, rule match)
- add tests for multi-period usage rollover (monthly/quarterly/yearly)
