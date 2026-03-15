from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class UsageLogIn(BaseModel):
    user_id: Optional[int] = None
    rule_id: int
    amount: float = Field(..., gt=0)
    period_start: Optional[date] = None


class UsageLogOut(BaseModel):
    id: int
    user_id: int
    rule_id: int
    period_start: date
    spent_amount: float
    cap_amount: Optional[float] = None
    cap_remaining: Optional[float] = None
