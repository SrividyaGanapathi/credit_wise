from datetime import date
from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.cards import Card
from models.reward_rules import RewardRule
from models.spend_tracker import SpendTracker
from models.user_cards import UserCard


CATEGORY_ALIASES = {
    "RESTAURANTS": "DINING",
    "RESTAURANT": "DINING",
    "FOOD": "DINING",
    "FLIGHTS": "TRAVEL",
    "HOTELS": "TRAVEL",
    "SUPERMARKET": "GROCERY",
    "GROCERIES": "GROCERY",
}

KNOWN_CATEGORIES = {
    "DINING",
    "TRAVEL",
    "GROCERY",
    "GAS",
    "TRANSIT",
    "STREAMING",
    "ONLINE_SHOPPING",
    "DRUGSTORE",
    "OTHER",
}

CHANNEL_ALIASES = {
    "INSTORE": "ANY",
    "IN_STORE": "ANY",
    "IN-STORE": "ANY",
}

KNOWN_CHANNELS = {
    "ANY",
    "ONLINE",
    "PORTAL",
    "OTHER",
}


def _normalize_category(raw: str) -> str:
    normalized = raw.strip().upper().replace(" ", "_")
    mapped = CATEGORY_ALIASES.get(normalized, normalized)
    if mapped not in KNOWN_CATEGORIES:
        return "OTHER"
    return mapped


def _normalize_channel(raw: str) -> str:
    normalized = raw.strip().upper().replace(" ", "_")
    mapped = CHANNEL_ALIASES.get(normalized, normalized)
    if mapped not in KNOWN_CHANNELS:
        return "OTHER"
    return mapped


def _normalize_country(raw: str) -> str:
    normalized = raw.strip().upper()
    if normalized in {"USA", "UNITED STATES", "UNITED STATES OF AMERICA"}:
        return "US"
    return normalized


def _fallback_cards(
    db: Session,
    amount: float,
    country: str,
    allowed_card_ids: Optional[List[int]],
    limit: int,
) -> List[Dict]:
    query = db.query(Card).filter(Card.is_active.is_(True))
    if allowed_card_ids is not None:
        query = query.filter(Card.id.in_(allowed_card_ids))

    cards = query.order_by(Card.annual_fee.asc(), Card.fx_fee_bps.asc(), Card.id.asc()).all()
    if not cards:
        return []

    final_limit = min(limit, len(cards))
    results = []
    for card in cards[:final_limit]:
        fx_fee_value = 0.0
        if country != "US" and card.fx_fee_bps > 0:
            fx_fee_value = amount * (float(card.fx_fee_bps) / 10000.0)

        results.append(
            {
                "card_id": card.id,
                "card_name": f"{card.issuer} {card.name}",
                "score": round(amount, 2),
                "net_value": round(amount - fx_fee_value, 2),
                "applied_rule_ids": [],
                "reasons": ["Fallback base-rate recommendation (no matching reward rule)."],
                "cap_remaining": None,
                "warnings": (
                    [f"Estimated FX fee impact: {card.fx_fee_bps} bps."] if fx_fee_value > 0 else []
                ),
            }
        )
    return results


def _period_start_for_cap(cap_period: Optional[str], today: date) -> date:
    if cap_period == "MONTHLY":
        return date(today.year, today.month, 1)
    if cap_period == "QUARTERLY":
        quarter_start_month = (((today.month - 1) // 3) * 3) + 1
        return date(today.year, quarter_start_month, 1)
    if cap_period == "YEARLY":
        return date(today.year, 1, 1)
    return today


def recommend_cards(
    db: Session,
    amount: float,
    category: str,
    channel: str,
    country: str,
    user_id: Optional[int] = None,
    limit: int = 3,
) -> List[Dict]:
    norm_category = _normalize_category(category)
    norm_channel = _normalize_channel(channel)
    norm_country = _normalize_country(country)

    allowed_card_ids: Optional[List[int]] = None
    if user_id is not None:
        rows = (
            db.query(UserCard.card_id)
            .filter(UserCard.user_id == user_id, UserCard.is_active.is_(True))
            .all()
        )
        allowed_card_ids = [row.card_id for row in rows]
        if not allowed_card_ids:
            return []

    query = (
        db.query(RewardRule, Card)
        .join(Card, Card.id == RewardRule.card_id)
        .filter(
            RewardRule.is_active.is_(True),
            Card.is_active.is_(True),
            RewardRule.category.in_([norm_category, "OTHER"]),
            or_(RewardRule.channel == norm_channel, RewardRule.channel.in_(["ANY", "OTHER"])),
            or_(RewardRule.country == norm_country, RewardRule.country == "ANY"),
            or_(RewardRule.txn_min.is_(None), RewardRule.txn_min <= amount),
            or_(RewardRule.txn_max.is_(None), RewardRule.txn_max >= amount),
        )
    )

    if allowed_card_ids is not None:
        query = query.filter(RewardRule.card_id.in_(allowed_card_ids))

    rows = query.all()
    if not rows:
        return _fallback_cards(
            db=db,
            amount=amount,
            country=norm_country,
            allowed_card_ids=allowed_card_ids,
            limit=limit,
        )

    best_by_card: Dict[int, Dict] = {}
    for rule, card in rows:
        warnings: List[str] = []
        cap_remaining: Optional[float] = None

        eligible_amount = amount
        base_rate_amount = 0.0

        if rule.cap_amount is not None:
            if user_id is None:
                warnings.append("Cap usage is unknown without user_id; assumes full cap availability.")
            else:
                period_start = _period_start_for_cap(rule.cap_period, date.today())
                usage = (
                    db.query(SpendTracker)
                    .filter(
                        SpendTracker.user_id == user_id,
                        SpendTracker.rule_id == rule.id,
                        SpendTracker.period_start == period_start,
                    )
                    .one_or_none()
                )
                spent_amount = float(usage.spent_amount) if usage else 0.0
                remaining_before = max(float(rule.cap_amount) - spent_amount, 0.0)
                eligible_amount = min(amount, remaining_before)
                base_rate_amount = amount - eligible_amount
                cap_remaining = round(max(remaining_before - eligible_amount, 0.0), 2)

                if remaining_before <= 0:
                    warnings.append("Reward cap exhausted for this period; applying base rate only.")
                elif eligible_amount < amount:
                    warnings.append("Only part of the transaction qualifies for bonus due to cap limits.")

        gross_score = (
            (eligible_amount * float(rule.multiplier))
            + (base_rate_amount * 1.0)
            + float(rule.flat_points or 0)
        )
        fx_fee_value = 0.0
        if norm_country != "US" and card.fx_fee_bps > 0:
            fx_fee_value = amount * (float(card.fx_fee_bps) / 10000.0)
            warnings.append(f"Estimated FX fee impact: {card.fx_fee_bps} bps.")

        net_value = gross_score - fx_fee_value
        reason = f"{rule.multiplier}x on {rule.category}"
        if rule.cap_amount:
            reason = f"{reason} (cap {rule.cap_amount:g}/{rule.cap_period})"

        current = best_by_card.get(card.id)
        candidate = {
            "card_id": card.id,
            "card_name": f"{card.issuer} {card.name}",
            "score": round(gross_score, 2),
            "net_value": round(net_value, 2),
            "applied_rule_ids": [rule.id],
            "reasons": [reason],
            "cap_remaining": cap_remaining,
            "warnings": warnings,
            "_priority": rule.priority,
        }

        if current is None:
            best_by_card[card.id] = candidate
            continue

        if candidate["net_value"] > current["net_value"]:
            best_by_card[card.id] = candidate
        elif (
            candidate["net_value"] == current["net_value"]
            and candidate["_priority"] < current["_priority"]
        ):
            best_by_card[card.id] = candidate

    ranked = sorted(best_by_card.values(), key=lambda x: (-x["net_value"], x["_priority"], x["card_id"]))
    final_limit = min(limit, len(ranked))

    results = []
    for row in ranked[:final_limit]:
        row.pop("_priority", None)
        results.append(row)
    return results
