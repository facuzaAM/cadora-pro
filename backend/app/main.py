from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.controllers.auth_controller import router as auth_router
from app.controllers.billing_controller import router as billing_router
from app.controllers.cad_controller import router as cad_router
from app.controllers.contact_controller import router as contact_router
from app.controllers.demo_controller import router as demo_router
from app.controllers.detection_controller import router as detection_router
from app.controllers.document_controller import router as document_router
from app.controllers.project_controller import router as project_router
from app.database import Base, engine
from app.utils.logging import setup_logging
from app.utils.rate_limit import limiter

if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.2,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description="API para detección de ventanas en planos arquitectónicos y exportación a CAD.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    contact={
        "name": "Cadora Team",
        "url": "https://cadora.pro",
        "email": "hello@cadora.pro",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

trusted_hosts = [h.strip() for h in settings.TRUSTED_HOSTS.split(",") if h.strip()]
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts + settings.CORS_ORIGINS,
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(project_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(document_router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(detection_router, prefix="/api/v1/detection", tags=["detection"])
app.include_router(cad_router, prefix="/api/v1/cad", tags=["cad"])
app.include_router(billing_router, prefix="/api/v1/billing", tags=["billing"])
app.include_router(demo_router, prefix="/api/v1/demo", tags=["demo"])
app.include_router(contact_router, prefix="/api/v1/contact", tags=["contact"])


@app.get("/api/v1/health", tags=["health"])
async def health():
    from sqlalchemy import text

    from app.database import async_session_factory

    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db_ok else "disconnected",
    }
