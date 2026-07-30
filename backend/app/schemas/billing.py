from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: str
    name: str
    price: int
    conversions_limit: int
    storage_limit: int
    priority_processing: bool
    paddle_price_id: str


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    conversions_used: int
    conversions_limit: int
    storage_used: int
    storage_limit: int
    priority_processing: bool


class PaddleConfigResponse(BaseModel):
    client_token: str
    environment: str
