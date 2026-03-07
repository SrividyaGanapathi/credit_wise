from typing import Dict, List

from data.database import SessionLocal
from models.cards import Card
from models.reward_rules import RewardRule


CARD_SEED: List[Dict] = [
    {"key": "chase_sapphire_pref", "issuer": "Chase", "name": "Sapphire Preferred", "network": "Visa", "annual_fee": 95, "fx_fee_bps": 0, "is_active": True},
    {"key": "amex_gold", "issuer": "American Express", "name": "Gold", "network": "Amex", "annual_fee": 325, "fx_fee_bps": 0, "is_active": True},
    {"key": "citi_double_cash", "issuer": "Citi", "name": "Double Cash", "network": "Mastercard", "annual_fee": 0, "fx_fee_bps": 300, "is_active": True},
    {"key": "capital_one_venture_x", "issuer": "Capital One", "name": "Venture X", "network": "Visa", "annual_fee": 395, "fx_fee_bps": 0, "is_active": True},
    {"key": "discover_it_cash_back", "issuer": "Discover", "name": "it Cash Back", "network": "Discover", "annual_fee": 0, "fx_fee_bps": 0, "is_active": True},
    {"key": "wells_fargo_autograph", "issuer": "Wells Fargo", "name": "Autograph", "network": "Visa", "annual_fee": 0, "fx_fee_bps": 300, "is_active": True},
    {"key": "us_bank_altitude_go", "issuer": "U.S. Bank", "name": "Altitude Go", "network": "Visa", "annual_fee": 0, "fx_fee_bps": 300, "is_active": True},
    {"key": "boa_customized_cash", "issuer": "Bank of America", "name": "Customized Cash Rewards", "network": "Visa", "annual_fee": 0, "fx_fee_bps": 300, "is_active": True},
    {"key": "chase_freedom_unlimited", "issuer": "Chase", "name": "Freedom Unlimited", "network": "Visa", "annual_fee": 0, "fx_fee_bps": 300, "is_active": True},
    {"key": "amex_blue_cash_everyday", "issuer": "American Express", "name": "Blue Cash Everyday", "network": "Amex", "annual_fee": 0, "fx_fee_bps": 270, "is_active": True},
]


RULE_SEED: Dict[str, List[Dict]] = {
    "chase_sapphire_pref": [
        {"category": "TRAVEL", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 10, "is_active": True},
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 10, "is_active": True},
        {"category": "STREAMING", "channel": "ONLINE", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 20, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
    "amex_gold": [
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 4.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 10, "is_active": True},
        {"category": "GROCERY", "channel": "ANY", "country": "US", "multiplier": 4.0, "flat_points": 0, "cap_amount": 25000.0, "cap_period": "YEARLY", "txn_min": None, "txn_max": None, "priority": 10, "is_active": True},
        {"category": "TRAVEL", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 15, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
    "citi_double_cash": [
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 40, "is_active": True},
        {"category": "TRAVEL", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 40, "is_active": True},
        {"category": "GROCERY", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 40, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 90, "is_active": True},
    ],
    "capital_one_venture_x": [
        {"category": "TRAVEL", "channel": "PORTAL", "country": "US", "multiplier": 10.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 5, "is_active": True},
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 25, "is_active": True},
        {"category": "TRANSIT", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 25, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 90, "is_active": True},
    ],
    "discover_it_cash_back": [
        {"category": "GROCERY", "channel": "ANY", "country": "US", "multiplier": 5.0, "flat_points": 0, "cap_amount": 1500.0, "cap_period": "QUARTERLY", "txn_min": None, "txn_max": None, "priority": 8, "is_active": True},
        {"category": "GAS", "channel": "ANY", "country": "US", "multiplier": 5.0, "flat_points": 0, "cap_amount": 1500.0, "cap_period": "QUARTERLY", "txn_min": None, "txn_max": None, "priority": 8, "is_active": True},
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 60, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
    "wells_fargo_autograph": [
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 20, "is_active": True},
        {"category": "TRAVEL", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 20, "is_active": True},
        {"category": "GAS", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 20, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
    "us_bank_altitude_go": [
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 4.0, "flat_points": 0, "cap_amount": 2000.0, "cap_period": "QUARTERLY", "txn_min": None, "txn_max": None, "priority": 12, "is_active": True},
        {"category": "GROCERY", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 30, "is_active": True},
        {"category": "STREAMING", "channel": "ONLINE", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 30, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
    "boa_customized_cash": [
        {"category": "ONLINE_SHOPPING", "channel": "ONLINE", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": 2500.0, "cap_period": "QUARTERLY", "txn_min": None, "txn_max": None, "priority": 10, "is_active": True},
        {"category": "GAS", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": 2500.0, "cap_period": "QUARTERLY", "txn_min": None, "txn_max": None, "priority": 30, "is_active": True},
        {"category": "GROCERY", "channel": "ANY", "country": "US", "multiplier": 2.0, "flat_points": 0, "cap_amount": 2500.0, "cap_period": "QUARTERLY", "txn_min": None, "txn_max": None, "priority": 30, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
    "chase_freedom_unlimited": [
        {"category": "DINING", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 15, "is_active": True},
        {"category": "TRAVEL", "channel": "PORTAL", "country": "US", "multiplier": 5.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 10, "is_active": True},
        {"category": "DRUGSTORE", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 20, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.5, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 90, "is_active": True},
    ],
    "amex_blue_cash_everyday": [
        {"category": "GROCERY", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": 6000.0, "cap_period": "YEARLY", "txn_min": None, "txn_max": None, "priority": 15, "is_active": True},
        {"category": "GAS", "channel": "ANY", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 20, "is_active": True},
        {"category": "ONLINE_SHOPPING", "channel": "ONLINE", "country": "US", "multiplier": 3.0, "flat_points": 0, "cap_amount": 6000.0, "cap_period": "YEARLY", "txn_min": None, "txn_max": None, "priority": 15, "is_active": True},
        {"category": "OTHER", "channel": "ANY", "country": "US", "multiplier": 1.0, "flat_points": 0, "cap_amount": None, "cap_period": None, "txn_min": None, "txn_max": None, "priority": 100, "is_active": True},
    ],
}


def seed_cards_and_rules() -> None:
    session = SessionLocal()
    try:
        card_ids_by_key: Dict[str, int] = {}

        for card_data in CARD_SEED:
            card = (
                session.query(Card)
                .filter(Card.issuer == card_data["issuer"], Card.name == card_data["name"])
                .one_or_none()
            )

            if card is None:
                card = Card(
                    issuer=card_data["issuer"],
                    name=card_data["name"],
                    network=card_data["network"],
                    annual_fee=card_data["annual_fee"],
                    fx_fee_bps=card_data["fx_fee_bps"],
                    is_active=card_data["is_active"],
                )
                session.add(card)
                session.flush()
            else:
                card.network = card_data["network"]
                card.annual_fee = card_data["annual_fee"]
                card.fx_fee_bps = card_data["fx_fee_bps"]
                card.is_active = card_data["is_active"]

            card_ids_by_key[card_data["key"]] = card.id

        seeded_card_ids = list(card_ids_by_key.values())
        if seeded_card_ids:
            session.query(RewardRule).filter(RewardRule.card_id.in_(seeded_card_ids)).delete(
                synchronize_session=False
            )

        total_rules = 0
        for key, rules in RULE_SEED.items():
            card_id = card_ids_by_key[key]
            for rule in rules:
                session.add(
                    RewardRule(
                        card_id=card_id,
                        category=rule["category"],
                        channel=rule["channel"],
                        country=rule["country"],
                        multiplier=rule["multiplier"],
                        flat_points=rule["flat_points"],
                        cap_amount=rule["cap_amount"],
                        cap_period=rule["cap_period"],
                        txn_min=rule["txn_min"],
                        txn_max=rule["txn_max"],
                        priority=rule["priority"],
                        is_active=rule["is_active"],
                    )
                )
                total_rules += 1

        session.commit()
        print(f"Seed complete: {len(CARD_SEED)} cards, {total_rules} reward rules.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_cards_and_rules()
