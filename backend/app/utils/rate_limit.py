from collections.abc import Callable
from typing import TypeVar

from fastapi import Request
from slowapi import Limiter

from app.config import settings

F = TypeVar("F", bound=Callable)


def _get_client_ip(request: Request) -> str:
    """Return the real client IP.

    Uvicorn resolves the true client from trusted proxies via
    ``--proxy-headers``/``--forwarded-allow-ips`` (see entrypoint.sh), so
    ``request.client.host`` is already the real IP. Reading the raw
    ``X-Forwarded-For`` header directly is unsafe: clients can spoof it.
    """
    return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=_get_client_ip, default_limits=["30/minute"])


def rate_limit(limit: str) -> Callable[[F], F]:
    """Apply a slowapi limit, or no-op when rate limiting is disabled.

    Without this wrapper the ``@limiter.limit`` decorators keep enforcing
    even when ``RATE_LIMIT_ENABLED=false``, and the app returns a 500
    (the RateLimitExceeded handler is only registered when enabled).
    """
    if settings.RATE_LIMIT_ENABLED:
        return limiter.limit(limit)
    return lambda func: func
