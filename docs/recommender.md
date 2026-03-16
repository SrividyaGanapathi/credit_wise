# Recommender Model

This document explains how the current Credit Wise recommender works.

Short version:

- it is a rule-based recommender, not a machine learning model
- card reward logic comes from the database
- the engine filters matching reward rules, computes estimated savings, and ranks the best cards
- the API returns the top 3 cards plus explanation metadata

## Current Model Type

Credit Wise currently uses a deterministic rules engine.

There is no trained recommendation model, embedding model, or collaborative filtering system in the current version. The recommendation behavior is driven by:

- `cards`
- `reward_rules`
- optional `user_cards`
- optional `spend_tracker`

That choice is intentional at this stage because:

- reward logic is structured and explainable
- early product behavior should be easy to debug
- adding or changing a card is data entry, not code changes

## Inputs

The main runtime input to the recommender is the request body for `POST /recommend`:

- `amount`
- `category`
- `country`
- `channel`
- optional `user_id`

In the hosted app today, recommendation requests usually come from:

- anonymous users
- authenticated Firebase users

The backend may also use the authenticated app user identity to decide whether wallet filtering should apply.

## Data Used

The recommender pulls from these tables:

- `cards`
  - issuer, product name, network, annual fee, FX fee, active state
- `reward_rules`
  - category, country, channel, multiplier, flat points, cap fields, priority, transaction bounds
- `user_cards`
  - used when recommendations should be filtered to a user wallet
- `spend_tracker`
  - used only when cap-aware behavior is enabled in the backend flow

## Normalization

Before ranking, the service normalizes the request:

- category aliases such as `restaurants` become `DINING`
- channel aliases such as `in store` become `ANY`
- country aliases such as `United States of America` become `US`
- unknown category or channel values fall back to `OTHER`

This keeps the request format forgiving while still matching structured DB rules.

## Rule Matching

The service joins `reward_rules` with `cards` and keeps rows that satisfy all of the following:

- card is active
- reward rule is active
- category matches the normalized category or `OTHER`
- channel matches the normalized channel or a fallback like `ANY`
- country matches the normalized country or `ANY`
- transaction amount is within optional `txn_min` and `txn_max`

If a wallet filter is active, only the user’s active cards are considered.

If no reward rule matches, the service falls back to a simple base-rate ranking over active cards.

## Savings Calculation

The current output is designed for human readability.

For each candidate rule:

1. Compute reward units from:
   - `amount * multiplier`
   - optional base-rate fallback when cap logic reduces bonus eligibility
   - optional flat points
2. Convert reward units to estimated dollar savings by dividing by `100`
3. Subtract estimated FX fees when the purchase is outside the US and the card has a non-zero `fx_fee_bps`

The result is returned as:

- `net_value`

In the UI, `net_value` is shown as estimated dollar savings.

Example:

- a `$80` transaction on a `5x` rule gives `400` reward units
- `400 / 100 = $4.00`
- if FX fee impact is `$0.60`, then `net_value = $3.40`

## Score Calculation

The service also returns:

- `score`

This is a normalized score out of `10`.

How it works:

- the top ranked card in the current result set gets `10.0`
- other cards are scaled relative to that best card using their internal ranking value
- if all ranking values are non-positive, the score falls back to `0.0`

Important distinction:

- `net_value` is the estimated dollar savings
- `score` is a relative fit score for comparing cards in the current recommendation set

So:

- `net_value` answers: “How much value do I save?”
- `score` answers: “How strong is this card relative to the best option right now?”

## Ranking Logic

For each card, the engine keeps only the single best matching rule candidate.

Tie-breaking is:

1. higher `net_value`
2. lower `priority` value in the rule table
3. lower `card_id`

After that, the cards are sorted descending by ranking value and truncated to the top 3.

## Explainability Fields

Each returned card includes:

- `card_id`
- `card_name`
- `score`
- `net_value`
- `applied_rule_ids`
- `reasons`
- `warnings`

The full response also includes:

- `best_card`
- `top_3`
- `explanations`
- `debug.applied_rule_ids`

These fields are what make the recommender explainable rather than a black box.

## Wallet Behavior

The backend supports two recommendation modes:

- catalog mode
  - rank from the full active card set
- wallet mode
  - rank only cards attached to the user

Right now the product UI is focused on catalog-style recommendation. Wallet-specific filtering can be surfaced more prominently later.

Anonymous users are currently treated like this:

- they can authenticate and get an app identity
- recommendations still use the full card catalog
- they are not blocked by an empty wallet

## Cap Tracking

The backend still contains cap-aware logic and usage logging, but the product UI currently hides that feature.

That means:

- `reward_rules` can still contain cap fields
- `spend_tracker` can still be used by the backend
- cap-related warnings can still appear if the relevant path is active

This was deferred in the UI intentionally until real user behavior and usage data justify surfacing it again.

## Current Limitations

- reward value assumes a simple `points -> dollars` conversion of `100 units = $1`
- annual fees are not amortized into the current transaction recommendation
- welcome bonuses, transfer partners, lounge access, and non-transaction perks are not modeled
- the score is relative within the current result set, not a global card quality metric
- the engine is rules-based, so it does not learn from user behavior yet

## Future Model Improvements

Likely future improvements include:

- bring cap tracking back into the product once user activity is meaningful
- add wallet-aware recommendation mode to the main UI
- support better reward valuation by issuer/program instead of one global conversion
- factor annual fee and benefit offsets into longer-horizon value estimates
- add user preference weighting such as simplicity vs. max return
- add offline evaluation and integration tests against production-like Postgres data
- evolve from a pure rules engine into a hybrid system if real usage data supports it

## Code References

- recommender service: [backend/services/recommendation_service.py](/Users/sri/Downloads/credit_wise/backend/services/recommendation_service.py)
- response schema: [backend/schemas/recommendation.py](/Users/sri/Downloads/credit_wise/backend/schemas/recommendation.py)
- recommendation route: [backend/api/recommendations.py](/Users/sri/Downloads/credit_wise/backend/api/recommendations.py)
