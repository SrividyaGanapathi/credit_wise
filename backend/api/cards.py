from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from data.session import get_db
from models.cards import Card

router = APIRouter(prefix="/cards", tags=["cards"])


@router.get("")
def list_cards(db: Session = Depends(get_db)):
    cards = (
        db.query(Card)
        .filter(Card.is_active.is_(True))
        .order_by(Card.issuer.asc(), Card.name.asc(), Card.id.asc())
        .all()
    )

    return [
        {
            "id": card.id,
            "issuer": card.issuer,
            "name": card.name,
            "network": card.network,
            "annual_fee": card.annual_fee,
            "fx_fee_bps": card.fx_fee_bps,
        }
        for card in cards
    ]
