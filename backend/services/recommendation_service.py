from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.cards import Card
from models.reward_rules import RewardRule
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
    db: Session, amount: float, allowed_card_ids: Optional[List[int]], limit: int
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
        results.append(
            {
                "card_id": card.id,
                "card_name": f"{card.issuer} {card.name}",
                "score": round(amount, 2),
                "applied_rule_ids": [],
                "reasons": ["Fallback base-rate recommendation (no matching reward rule)."],
            }
        )
    return results


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
        return _fallback_cards(db=db, amount=amount, allowed_card_ids=allowed_card_ids, limit=limit)

    best_by_card: Dict[int, Dict] = {}
    for rule, card in rows:
        score = (amount * float(rule.multiplier)) + float(rule.flat_points or 0)
        reason = f"{rule.multiplier}x on {rule.category}"
        if rule.cap_amount:
            reason = f"{reason} (cap {rule.cap_amount:g}/{rule.cap_period})"

        current = best_by_card.get(card.id)
        candidate = {
            "card_id": card.id,
            "card_name": f"{card.issuer} {card.name}",
            "score": round(score, 2),
            "applied_rule_ids": [rule.id],
            "reasons": [reason],
            "_priority": rule.priority,
        }

        if current is None:
            best_by_card[card.id] = candidate
            continue

        if candidate["score"] > current["score"]:
            best_by_card[card.id] = candidate
        elif candidate["score"] == current["score"] and candidate["_priority"] < current["_priority"]:
            best_by_card[card.id] = candidate

    ranked = sorted(best_by_card.values(), key=lambda x: (-x["score"], x["_priority"], x["card_id"]))
    final_limit = min(limit, len(ranked))

    results = []
    for row in ranked[:final_limit]:
        row.pop("_priority", None)
        results.append(row)
    return results
