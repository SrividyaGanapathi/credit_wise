from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data.session import get_db
from schemas.recommendation import RecommendDebugOut, RecommendResponse, TransactionIn
from services.recommendation_service import recommend_cards

router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(txn: TransactionIn, db: Session = Depends(get_db)) -> RecommendResponse:
    top_cards = recommend_cards(
        db=db,
        amount=txn.amount,
        category=txn.category,
        channel=txn.channel,
        country=txn.country,
        user_id=txn.user_id,
        limit=3,
    )
    best_card = top_cards[0] if top_cards else None
    explanations = []
    applied_rule_ids = []
    for card in top_cards:
        explanations.extend(card["reasons"])
        applied_rule_ids.extend(card["applied_rule_ids"])

    return RecommendResponse(
        best_card=best_card,
        top_3=top_cards,
        explanations=explanations,
        debug=RecommendDebugOut(applied_rule_ids=sorted(set(applied_rule_ids))),
    )
