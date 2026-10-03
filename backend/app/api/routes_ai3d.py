import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import JobResponse, VisionProvider
from app.services.jobs import job_store
from app.services.threews import ThreeWSService
from app.utils.files import (
    fetch_cloudinary_image,
    read_validated_image,
    save_public_source_image,
)
from app.utils.validation import clean_user_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai3d", tags=["ai-3d"])


def _parse_cloudinary_urls(raw: str) -> list[str]:
    if len(raw) > 25_000:
        raise HTTPException(status_code=422, detail="Cloudinary URL list is too long.")

    if not raw.strip():
        return []

    normalized = raw.replace("\n", ",")
    urls = [part.strip() for part in normalized.split(",") if part.strip()]

    if len(urls) > 6:
        raise HTTPException(
            status_code=422,
            detail="A maximum of 6 image views is supported.",
        )

    return urls


@router.post("/generate", response_model=JobResponse)
async def generate_ai_3d(
    files: list[UploadFile] | None = File(None),
    cloudinary_urls: str = Form(""),
    vision_provider: VisionProvider = Form(VisionProvider.auto),
    description: str = Form(""),
    tier: str = Form("standard"),
    analyze_image: bool = Form(False),
):
    """Reconstruct a textured GLB directly from 1-6 validated reference photos."""

    settings = get_settings()
    uploads = files or []
    cloudinary_refs = _parse_cloudinary_urls(cloudinary_urls)

    # Accepted for backwards compatibility with the current frontend. They do
    # not influence the direct geometry pipeline.
    _ = vision_provider, analyze_image

    if not uploads and not cloudinary_refs:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one uploaded image or Cloudinary delivery URL.",
        )

    total_views = len(uploads) + len(cloudinary_refs)
    if total_views > 6:
        raise HTTPException(
            status_code=422,
            detail="A maximum of 6 image views is supported.",
        )

    if tier not in {"draft", "standard"}:
        raise HTTPException(
            status_code=422,
            detail="Use draft or standard for direct photo reconstruction.",
        )

    safe_description = clean_user_text(
        description,
        field_name="description",
        max_length=1000,
    )

    source_urls: list[str] = []

    for url in cloudinary_refs:
        await fetch_cloudinary_image(
            url,
            settings.max_upload_mb,
            settings.max_image_pixels,
        )
        source_urls.append(url)

    for upload in uploads:
        data, mime = await read_validated_image(
            upload,
            settings.max_upload_mb,
            settings.max_image_pixels,
        )

        if settings.public_base_url.startswith(("http://localhost", "http://127.0.0.1")):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Direct 3D reconstruction from local uploads needs a public backend URL. "
                    "Use Cloudinary upload in local development."
                ),
            )

        source_urls.append(save_public_source_image(data, mime, settings))

    guidance = " ".join(safe_description.split()).strip()[:1000]

    try:
        service = ThreeWSService(settings)
        submitted = await service.submit_images(
            source_urls,
            prompt=guidance,
            tier=tier,
        )
    except Exception:
        logger.exception("Direct image-to-3D submission failed")
        raise HTTPException(
            status_code=502,
            detail="Direct image-to-3D generation is temporarily unavailable.",
        )

    if not submitted.glb_url and not submitted.job_id:
        logger.error("3D provider returned an untrackable response")
        raise HTTPException(
            status_code=502,
            detail="3D provider returned an invalid job response.",
        )

    remote_status = submitted.status.lower()
    if submitted.glb_url:
        status = "done"
    elif remote_status in {"failed", "error"}:
        status = "failed"
    else:
        status = "queued"

    prompt_record = (
        guidance
        if guidance
        else f"Direct image reconstruction from {len(source_urls)} reference view(s)."
    )

    record = job_store.create(
        provider="three.ws-image",
        prompt=prompt_record,
        remote_job_id=submitted.job_id,
        status=status,
        glb_url=str(submitted.glb_url) if submitted.glb_url else None,
        viewer_url=(
            str(submitted.viewer_url)
            if submitted.viewer_url
            else (
                service.viewer_url_for(str(submitted.glb_url))
                if submitted.glb_url
                else None
            )
        ),
    )

    if status == "failed":
        job_store.update(
            record.id,
            error="The external 3D provider reported a failure.",
        )

    return job_store.response(record)
