from pydantic import BaseModel


class CheckoutSessionRequest(BaseModel):
    price_id: str
    plan: str


class CheckoutSessionResponse(BaseModel):
    url: str


class BillingPortalResponse(BaseModel):
    url: str


class PlanResponse(BaseModel):
    name: str
    price: int
    conversions_limit: int
    storage_limit: int
    priority_processing: bool


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    conversions_used: int
    conversions_limit: int
    storage_used: int
    storage_limit: int
    priority_processing: bool
