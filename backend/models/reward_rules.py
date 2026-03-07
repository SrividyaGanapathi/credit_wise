from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from data.database import Base
from typing import Optional


class RewardRule(Base):
    __tablename__ = "reward_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    channel: Mapped[str] = mapped_column(String, index=True, default="ANY")
    country: Mapped[str] = mapped_column(String, index=True, default="US")
    multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    flat_points: Mapped[int] = mapped_column(Integer, default=0)
    cap_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cap_period: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    txn_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    txn_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card = relationship("Card", back_populates="reward_rules")
