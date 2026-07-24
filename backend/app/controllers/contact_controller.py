import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from starlette.status import HTTP_400_BAD_REQUEST

from app.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


@router.post("")
@limiter.limit("3/hour")
async def send_contact(request: Request, body: ContactRequest):
    """Receive a contact form submission and log it."""
    if not body.message.strip():
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El mensaje no puede estar vacío",
        )

    logger.info(
        "Contact form submission: name=%s email=%s subject=%s",
        body.name,
        body.email,
        body.subject,
    )
    logger.info("Contact message: %s", body.message[:500])

    return {"ok": True, "message": "Mensaje enviado correctamente"}
