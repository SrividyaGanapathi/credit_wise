from typing import List, Optional

from pydantic import BaseModel, Field


class TransactionIn(BaseModel):
    amount: float = Field(..., gt=0)
    category: str
    country: str = "United States of America"
    channel: str = "Online"
    user_id: Optional[int] = None


class CardRecommendationOut(BaseModel):
    card_id: int
    card_name: str
    score: float
    applied_rule_ids: List[int]
    reasons: List[str]


class RecommendDebugOut(BaseModel):
    applied_rule_ids: List[int]


class RecommendResponse(BaseModel):
    best_card: Optional[CardRecommendationOut] = None
    top_3: List[CardRecommendationOut]
    explanations: List[str]
    debug: RecommendDebugOut
