from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.database import get_db
from app.schemas.billing import (
    BillingPortalResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    PlanResponse,
    SubscriptionResponse,
)
from app.services.plan_config import PLANS
from app.services.stripe_service import StripeService
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans():
    return [
        PlanResponse(
            name=p.name,
            price=p.price,
            conversions_limit=p.conversions_limit,
            storage_limit=p.storage_limit,
            priority_processing=p.priority_processing,
        )
        for p in PLANS.values()
    ]


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.plan not in PLANS:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Plan no válido")
    if request.plan == "free":
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="El plan Free no requiere pago")

    service = StripeService(db)
    try:
        url = await service.create_checkout_session(user, request.plan)
        return CheckoutSessionResponse(url=url)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/create-portal-session", response_model=BillingPortalResponse)
async def create_portal_session(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = StripeService(db)
    try:
        url = await service.create_portal_session(user)
        return BillingPortalResponse(url=url)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user=Depends(get_current_user),
):
    return SubscriptionResponse(
        plan=user.subscription_plan,
        status=user.subscription_status,
        conversions_used=user.conversions_used,
        conversions_limit=user.conversions_limit,
        storage_used=user.storage_used,
        storage_limit=user.storage_limit,
        priority_processing=user.priority_processing,
    )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Missing stripe-signature")

    try:
        await StripeService.handle_webhook(payload, sig_header)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    return {"status": "ok"}
