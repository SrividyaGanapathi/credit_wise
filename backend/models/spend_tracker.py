from datetime import date

from sqlalchemy import Date, DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from data.database import Base


class SpendTracker(Base):
    __tablename__ = "spend_tracker"
    __table_args__ = (
        UniqueConstraint("user_id", "rule_id", "period_start", name="uq_spend_tracker_user_rule_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("reward_rules.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    spent_amount: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
