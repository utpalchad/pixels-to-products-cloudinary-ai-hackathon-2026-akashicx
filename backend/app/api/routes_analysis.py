from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import AnalysisResponse, VisionProvider
from app.services.vision_router import VisionRouter
from app.utils.files import read_validated_image

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/image", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    provider: VisionProvider = Form(VisionProvider.auto),
    description: str = Form(""),
):
    settings = get_settings()
    image_bytes, mime_type = await read_validated_image(file, settings.max_upload_mb)
    vision = VisionRouter(settings)

    try:
        provider_name, analysis = await vision.analyze(
            image_bytes,
            mime_type,
            provider=provider,
            user_description=description,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Vision analysis failed: {exc}") from exc

    return AnalysisResponse(provider=provider_name, analysis=analysis)
