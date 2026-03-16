from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class RecommendationEventIn(BaseModel):
    event_type: Literal["impression", "selection"]
    request_id: str = Field(..., min_length=1, max_length=128)
    auth_mode: str = "unauthenticated"
    amount: float = Field(..., gt=0)
    category: str
    country: str
    channel: str
    recommended_card_ids: List[int] = Field(default_factory=list)
    selected_card_id: Optional[int] = None
    selected_rank: Optional[int] = None

    @model_validator(mode="after")
    def validate_selection_fields(self):
        if self.event_type == "selection" and self.selected_card_id is None:
            raise ValueError("selected_card_id is required for selection events")
        return self


class RecommendationEventOut(BaseModel):
    id: int
    event_type: str
    request_id: str
    user_id: Optional[int] = None
