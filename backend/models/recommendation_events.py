from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from data.database import Base


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    request_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    auth_mode: Mapped[str] = mapped_column(String, default="unauthenticated", index=True)
    amount: Mapped[float] = mapped_column()
    category: Mapped[str] = mapped_column(String, index=True)
    country: Mapped[str] = mapped_column(String, index=True)
    channel: Mapped[str] = mapped_column(String, index=True)
    recommended_card_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    selected_card_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cards.id"), nullable=True, index=True)
    selected_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
