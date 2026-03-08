from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from data.session import get_db
from models.reward_rules import RewardRule
from models.spend_tracker import SpendTracker
from models.users import User
from schemas.usage import UsageLogIn, UsageLogOut

router = APIRouter(prefix="/usage", tags=["usage"])


def _default_period_start(cap_period: Optional[str], today: date) -> date:
    if cap_period == "MONTHLY":
        return date(today.year, today.month, 1)
    if cap_period == "QUARTERLY":
        quarter_start_month = (((today.month - 1) // 3) * 3) + 1
        return date(today.year, quarter_start_month, 1)
    if cap_period == "YEARLY":
        return date(today.year, 1, 1)
    return today


@router.post("/log", response_model=UsageLogOut)
def log_usage(payload: UsageLogIn, db: Session = Depends(get_db)) -> UsageLogOut:
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {payload.user_id} not found")

    rule = db.query(RewardRule).filter(RewardRule.id == payload.rule_id).one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Reward rule {payload.rule_id} not found")

    period_start = payload.period_start or _default_period_start(rule.cap_period, date.today())

    usage = (
        db.query(SpendTracker)
        .filter(
            SpendTracker.user_id == payload.user_id,
            SpendTracker.rule_id == payload.rule_id,
            SpendTracker.period_start == period_start,
        )
        .one_or_none()
    )

    if usage is None:
        usage = SpendTracker(
            user_id=payload.user_id,
            rule_id=payload.rule_id,
            period_start=period_start,
            spent_amount=payload.amount,
        )
        db.add(usage)
    else:
        usage.spent_amount = float(usage.spent_amount) + float(payload.amount)

    db.commit()
    db.refresh(usage)

    cap_amount = float(rule.cap_amount) if rule.cap_amount is not None else None
    cap_remaining = None
    if cap_amount is not None:
        cap_remaining = round(max(cap_amount - float(usage.spent_amount), 0.0), 2)

    return UsageLogOut(
        id=usage.id,
        user_id=usage.user_id,
        rule_id=usage.rule_id,
        period_start=usage.period_start,
        spent_amount=round(float(usage.spent_amount), 2),
        cap_amount=cap_amount,
        cap_remaining=cap_remaining,
    )
