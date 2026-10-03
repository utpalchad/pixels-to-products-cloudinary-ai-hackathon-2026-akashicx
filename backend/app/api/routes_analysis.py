import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import AnalysisResponse, VisionProvider
from app.services.vision_router import VisionRouter
from app.utils.files import read_validated_image
from app.utils.validation import clean_user_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/image", response_model=AnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    provider: VisionProvider = Form(VisionProvider.auto),
    description: str = Form(""),
):
    settings = get_settings()
    safe_description = clean_user_text(
        description,
        field_name="description",
        max_length=1000,
    )
    image_bytes, mime_type = await read_validated_image(
        file,
        settings.max_upload_mb,
        settings.max_image_pixels,
    )
    vision = VisionRouter(settings)

    try:
        provider_name, analysis = await vision.analyze(
            image_bytes,
            mime_type,
            provider=provider,
            user_description=safe_description,
        )
    except RuntimeError:
        logger.warning("Vision provider temporarily unavailable", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Vision analysis is temporarily unavailable.",
        )
    except Exception:
        logger.exception("Vision analysis failed")
        raise HTTPException(
            status_code=502,
            detail="Vision analysis failed.",
        )

    return AnalysisResponse(provider=provider_name, analysis=analysis)
