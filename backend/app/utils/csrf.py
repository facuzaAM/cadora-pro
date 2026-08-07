import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CSRFOriginMiddleware(BaseHTTPMiddleware):
    """Reject cross-site state-changing requests.

    The API trusts the ``cadora_access``/``cadora_refresh`` cookies (SameSite=None
    in production) as a fallback auth transport, so a cross-site request from a
    malicious page would carry them. Browsers always send the ``Origin`` header
    on non-GET requests, so we reject unsafe methods whose Origin is not one of
    the trusted frontends. Requests without an Origin (curl, Paddle webhook,
    server-to-server) are allowed.
    """

    def __init__(self, app, allowed_origins: list[str]):
        super().__init__(app)
        self.allowed_origins = {o.rstrip("/").lower() for o in allowed_origins}

    async def dispatch(self, request: Request, call_next):
        if request.method in _UNSAFE_METHODS:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/").lower() not in self.allowed_origins:
                logger.warning(
                    "CSRF: rechazada petición %s %s desde Origin no permitido %s",
                    request.method, request.url.path, origin,
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origen no permitido"},
                )
        return await call_next(request)
