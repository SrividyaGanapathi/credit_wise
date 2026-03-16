from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.firebase_auth import AuthenticatedUser, get_current_user_optional
from data.session import get_db
from models.recommendation_events import RecommendationEvent
from schemas.events import RecommendationEventIn, RecommendationEventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/recommendation", response_model=RecommendationEventOut)
def log_recommendation_event(
    payload: RecommendationEventIn,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser | None = Depends(get_current_user_optional),
) -> RecommendationEventOut:
    event = RecommendationEvent(
        event_type=payload.event_type,
        request_id=payload.request_id,
        user_id=current_user.id if current_user is not None else None,
        auth_mode=payload.auth_mode,
        amount=payload.amount,
        category=payload.category,
        country=payload.country,
        channel=payload.channel,
        recommended_card_ids=payload.recommended_card_ids,
        selected_card_id=payload.selected_card_id,
        selected_rank=payload.selected_rank,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return RecommendationEventOut(
        id=event.id,
        event_type=event.event_type,
        request_id=event.request_id,
        user_id=event.user_id,
    )
