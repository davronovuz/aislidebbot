from pydantic import BaseModel
from datetime import datetime


class UserInfo(BaseModel):
    telegram_id: int
    username: str | None
    first_name: str | None
    balance: float
    free_presentations: int
    total_spent: float
    total_deposited: float
    member_since: str
    price_per_slide: float
    price_per_page: float
    subscription: "SubscriptionInfo | None" = None

    model_config = {"from_attributes": True}


class SubscriptionInfo(BaseModel):
    plan_name: str
    max_presentations: int
    presentations_used: int
    max_courseworks: int
    courseworks_used: int
    max_slides: int
    expires_at: datetime | None
    is_active: bool


class TransactionOut(BaseModel):
    id: int
    transaction_type: str
    amount: float
    description: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
