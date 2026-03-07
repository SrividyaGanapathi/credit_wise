from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from data.session import get_db
from models.cards import Card
from models.user_cards import UserCard
from models.users import User

router = APIRouter(prefix="/users", tags=["users"])


class AddUserCardRequest(BaseModel):
    card_id: int
    nickname: str = ""
    is_active: bool = True


@router.post("/{user_id}/cards")
def add_card_to_user(user_id: int, payload: AddUserCardRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    card = db.query(Card).filter(Card.id == payload.card_id, Card.is_active.is_(True)).one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail=f"Active card {payload.card_id} not found")

    user_card = (
        db.query(UserCard)
        .filter(UserCard.user_id == user_id, UserCard.card_id == payload.card_id)
        .one_or_none()
    )

    if user_card is None:
        user_card = UserCard(
            user_id=user_id,
            card_id=payload.card_id,
            nickname=payload.nickname,
            is_active=payload.is_active,
        )
        db.add(user_card)
    else:
        user_card.nickname = payload.nickname
        user_card.is_active = payload.is_active

    db.commit()
    db.refresh(user_card)

    return {
        "id": user_card.id,
        "user_id": user_card.user_id,
        "card_id": user_card.card_id,
        "nickname": user_card.nickname,
        "is_active": user_card.is_active,
    }
