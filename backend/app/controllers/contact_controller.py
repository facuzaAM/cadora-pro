import asyncio
import html
import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from starlette.status import HTTP_400_BAD_REQUEST

from app.config import settings
from app.services.email_service import send_email
from app.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr = Field(..., max_length=254)
    subject: str = Field(..., min_length=1, max_length=150)
    message: str = Field(..., min_length=1, max_length=5000)


@router.post("")
@rate_limit(settings.RATE_LIMIT_CONTACT)
async def send_contact(request: Request, body: ContactRequest):
    """Receive a contact form submission and forward it via email."""
    if not body.message.strip():
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El mensaje no puede estar vacío",
        )

    html_body = (
        f"<h2>Nuevo mensaje de contacto</h2>"
        f"<p><strong>Nombre:</strong> {html.escape(body.name)}</p>"
        f"<p><strong>Email:</strong> {html.escape(str(body.email))}</p>"
        f"<p><strong>Asunto:</strong> {html.escape(body.subject)}</p>"
        f"<hr><p>{html.escape(body.message)}</p>"
    )
    sent = await asyncio.to_thread(
        send_email, settings.EMAIL_FROM, f"Contacto: {body.subject}", html_body,
    )

    if sent:
        logger.info("Contact form forwarded: %s <%s>", body.name, body.email)
        return {"ok": True, "message": "Mensaje enviado correctamente"}
    logger.warning("Contact form received but email delivery failed: %s", body.subject)
    raise HTTPException(
        status_code=500,
        detail="No pudimos enviar tu mensaje. Intentá de nuevo más tarde.",
    )
