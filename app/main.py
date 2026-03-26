import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_health import router as health_router
from app.auth.routes import router as auth_router
from app.api.routes_packages import router as packages_router
from app.api.routes_extraction import router as extraction_router
from app.api.routes_chat import router as chat_router
from app.config import settings

logger = logging.getLogger(__name__)

_INSECURE_JWT_SECRETS = {"change-me-in-production", "change-me-in-production-use-openssl-rand-hex-32", "secret"}


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    if settings.jwt_secret_key in _INSECURE_JWT_SECRETS or len(settings.jwt_secret_key) < 32:
        logger.warning(
            "SECURITY WARNING: jwt_secret_key is insecure (too short or default value). "
            "Set a strong random secret via JWT_SECRET_KEY env var."
        )
    yield


app = FastAPI(
    title="КОД-агент",
    description="AI-агент анализа кредитной обеспечительной документации",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(packages_router)
app.include_router(extraction_router)
app.include_router(chat_router)
