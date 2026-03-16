from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.firebase_auth import AuthenticatedUser, get_current_user_optional
from data.session import get_db
from schemas.recommendation import RecommendDebugOut, RecommendResponse, TransactionIn
from services.recommendation_service import recommend_cards

router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    txn: TransactionIn,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> RecommendResponse:
    resolved_user_id = txn.user_id
    if current_user is not None and not current_user.is_anonymous:
        resolved_user_id = current_user.id

    top_cards = recommend_cards(
        db=db,
        amount=txn.amount,
        category=txn.category,
        channel=txn.channel,
        country=txn.country,
        user_id=resolved_user_id,
        limit=3,
    )
    best_card = top_cards[0] if top_cards else None
    explanations = []
    applied_rule_ids = []
    for card in top_cards:
        reasons = ", ".join(card["reasons"]) if card["reasons"] else "No rule reason available"
        explanations.append(
            f"{card['card_name']}: estimated savings=${card['net_value']:.2f}, score={card['score']}/10. {reasons}"
        )
        if card.get("cap_remaining") is not None:
            explanations.append(f"{card['card_name']}: cap remaining {card['cap_remaining']}.")
        for warning in card.get("warnings", []):
            explanations.append(f"{card['card_name']}: {warning}")
        applied_rule_ids.extend(card["applied_rule_ids"])

    return RecommendResponse(
        best_card=best_card,
        top_3=top_cards,
        explanations=explanations,
        debug=RecommendDebugOut(applied_rule_ids=sorted(set(applied_rule_ids))),
    )
