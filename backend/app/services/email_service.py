"""Email service for sending password reset codes and notifications.

In development, emails are logged instead of sent.
Configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD in .env for production.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    if settings.ENVIRONMENT != "production" or not settings.SMTP_HOST:
        logger.info(
            "📧 [DEV EMAIL] To: %s | Subject: %s | Body:\n%s",
            to, subject, html_body,
        )
        return True

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            if settings.SMTP_PORT == 587:
                server.starttls()
                server.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to)
        return False


def send_reset_code(email: str, code: str, name: str) -> bool:
    subject = "Cadora — Código de recuperación de contraseña"
    html_body = _build_reset_email(name, code)  # noqa: E501
    return send_email(email, subject, html_body)


def _build_reset_email(name: str, code: str) -> str:
    return (
        '<div style="font-family:Arial,sans-serif;max-width:480px;'
        'margin:0 auto;padding:24px;">'
        '<h2 style="color:#1a1a1a;margin-bottom:16px;">'
        "Recuperar contraseña</h2>"
        '<p style="color:#555;line-height:1.6;">'
        f"Hola {name}, "
        "recibimos una solicitud para restablecer "
        "tu contraseña en Cadora.</p>"
        '<div style="background:#f4f4f5;border-radius:8px;'
        'padding:20px;text-align:center;margin:24px 0;">'
        '<p style="color:#555;margin:0 0 8px 0;font-size:14px;">'
        "Tu código de verificación es:</p>"
        '<p style="font-size:32px;font-weight:bold;'
        'letter-spacing:8px;color:#1a1a1a;margin:0;">'
        f"{code}</p></div>"
        '<p style="color:#555;line-height:1.6;font-size:14px;">'
        "Este código expira en <strong>15 minutos</strong>. "
        "Si no solicitaste este cambio, "
        "podés ignorar este email.</p>"
        '<hr style="border:none;'
        'border-top:1px solid #e5e5e5;margin:24px 0;" />'
        '<p style="color:#999;font-size:12px;'
        'text-align:center;">Cadora — cadora.pro</p>'
        "</div>"
    )
