from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes_ai3d import router as ai3d_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_convert import router as convert_router
from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Pixel Forge backend for image analysis, local image-to-mesh conversion, "
        "and optional AI-assisted image-to-3D generation."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(convert_router, prefix="/api/v1")
app.include_router(ai3d_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")

app.mount(
    "/files",
    StaticFiles(directory=str(settings.output_path)),
    name="files",
)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1",
    }
