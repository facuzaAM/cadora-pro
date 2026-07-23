from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.status import HTTP_400_BAD_REQUEST

from app.config import settings
from app.schemas.billing import (
    PaddleConfigResponse,
    PlanResponse,
    SubscriptionResponse,
)
from app.services.paddle_service import PaddleService
from app.services.plan_config import PLANS
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


@router.get("/config", response_model=PaddleConfigResponse)
async def get_paddle_config():
    return PaddleConfigResponse(
        client_token=settings.PADDLE_CLIENT_TOKEN,
        environment=settings.PADDLE_ENVIRONMENT,
    )


@router.post("/webhook")
async def paddle_webhook(request: Request):
    payload = await request.body()
    paddle_signature = request.headers.get("paddle-signature", "")

    if not paddle_signature:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Missing paddle-signature",
        )

    try:
        await PaddleService.handle_webhook(payload, paddle_signature)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))

    return {"status": "ok"}
