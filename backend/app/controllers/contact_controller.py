import asyncio
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from starlette.status import HTTP_400_BAD_REQUEST

from app.core.config import settings
from app.services.email_service import send_email
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
    """Receive a contact form submission and forward it via email."""
    if not body.message.strip():
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El mensaje no puede estar vacío",
        )

    html = (
        f"<h2>Nuevo mensaje de contacto</h2>"
        f"<p><strong>Nombre:</strong> {body.name}</p>"
        f"<p><strong>Email:</strong> {body.email}</p>"
        f"<p><strong>Asunto:</strong> {body.subject}</p>"
        f"<hr><p>{body.message}</p>"
    )
    sent = await asyncio.to_thread(
        send_email, settings.EMAIL_FROM, f"Contacto: {body.subject}", html,
    )

    if sent:
        logger.info("Contact form forwarded: %s <%s>", body.name, body.email)
        return {"ok": True, "message": "Mensaje enviado correctamente"}
    logger.warning("Contact form received but email delivery failed: %s", body.subject)
    raise HTTPException(
        status_code=500,
        detail="No pudimos enviar tu mensaje. Intentá de nuevo más tarde.",
    )
