from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes_ai3d import router as ai3d_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_convert import router as convert_router
from app.api.routes_download import router as download_router
from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_source import router as source_router
from app.config import get_settings
from app.security import SecurityMiddleware

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Pixel Forge backend for image analysis, local image-to-mesh conversion, "
        "and optional AI-assisted image-to-3D generation."
    ),
    debug=False,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# Only the known Render host is accepted in production. This blocks Host-header
# attacks against absolute URL generation and proxy behavior.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_host_list,
)

# CORS is intentionally narrow. No credentials/cookies are accepted.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
    max_age=600,
)

# Added last so security headers also wrap CORS/host-denial responses.
app.add_middleware(SecurityMiddleware, settings=settings)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    # Avoid echoing attacker-controlled values back in validation errors.
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request parameters.",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


app.include_router(health_router)
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(convert_router, prefix="/api/v1")
app.include_router(download_router, prefix="/api/v1")
app.include_router(ai3d_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(source_router, prefix="/api/v1")


@app.get("/")
async def root():
    payload = {
        "name": settings.app_name,
        "status": "running",
        "api": "/api/v1",
    }
    if not settings.is_production:
        payload["docs"] = "/docs"
    return payload
