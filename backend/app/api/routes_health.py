from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import ProviderStatus, ProvidersResponse

router = APIRouter(tags=["system"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "pixel-forge-api"}


@router.get("/providers", response_model=ProvidersResponse)
async def providers():
    settings = get_settings()
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
                note=(
                    "Pixel Forge accepts Cloudinary delivery URLs from the browser Upload Widget. "
                    "No Cloudinary API secret is stored on the backend."
                ),
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
