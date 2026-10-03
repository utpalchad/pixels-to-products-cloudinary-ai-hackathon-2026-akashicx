from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.models.schemas import ProviderStatus, ProvidersResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "pixel-forge-api"}


@router.get("/providers", response_model=ProvidersResponse)
async def providers():
    settings = get_settings()

    # Provider configuration details are useful during development but are
    # unnecessary reconnaissance data in production.
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found.")

    return ProvidersResponse(
        vision=[
            ProviderStatus(
                name="gemini",
                configured=bool(settings.gemini_api_key),
                note=f"model: {settings.gemini_model}",
            ),
            ProviderStatus(
                name="local",
                configured=True,
                note="Fallback prompt builder; no external AI.",
            ),
        ],
        image_to_3d=[
            ProviderStatus(
                name="cloudinary",
                configured=True,
                note="Browser-side Cloudinary delivery URLs are supported.",
            ),
            ProviderStatus(
                name="three.ws",
                configured=True,
                note="Optional full image-to-3D reconstruction provider.",
            ),
            ProviderStatus(
                name="pixel-forge-local",
                configured=True,
                note="Relief/lithophane STL and GLB engine.",
            ),
        ],
    )
