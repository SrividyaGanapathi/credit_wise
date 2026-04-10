from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.firebase_auth import AuthenticatedUser, get_current_user
from data.session import get_db
from models.cards import Card
from models.user_cards import UserCard

router = APIRouter(prefix="/users", tags=["users"])


class AddUserCardRequest(BaseModel):
    card_id: int
    nickname: str = ""
    is_active: bool = True


@router.get("/me/cards")
def list_my_cards(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    rows = (
        db.query(UserCard, Card)
        .join(Card, Card.id == UserCard.card_id)
        .filter(UserCard.user_id == current_user.id)
        .order_by(UserCard.id.asc())
        .all()
    )

    return [
        {
            "id": user_card.id,
            "user_id": user_card.user_id,
            "card_id": user_card.card_id,
            "nickname": user_card.nickname,
            "is_active": user_card.is_active,
            "card_name": f"{card.issuer} {card.name}",
            "network": card.network,
        }
        for user_card, card in rows
    ]


@router.post("/me/cards")
def add_card_to_user(
    payload: AddUserCardRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    card = db.query(Card).filter(Card.id == payload.card_id, Card.is_active.is_(True)).one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail=f"Active card {payload.card_id} not found")

    user_card = (
        db.query(UserCard)
        .filter(UserCard.user_id == current_user.id, UserCard.card_id == payload.card_id)
        .one_or_none()
    )

    if user_card is None:
        user_card = UserCard(
            user_id=current_user.id,
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


@router.delete("/me/cards/{user_card_id}", status_code=204)
def remove_card_from_user(
    user_card_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    user_card = (
        db.query(UserCard)
        .filter(UserCard.id == user_card_id, UserCard.user_id == current_user.id)
        .one_or_none()
    )
    if user_card is None:
        raise HTTPException(status_code=404, detail=f"User card {user_card_id} not found")

    db.delete(user_card)
    db.commit()
