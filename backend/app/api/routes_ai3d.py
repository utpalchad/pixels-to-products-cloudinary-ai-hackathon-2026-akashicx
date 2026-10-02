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

router = APIRouter(prefix="/ai3d", tags=["ai-3d"])


def _parse_cloudinary_urls(raw: str) -> list[str]:
    if not raw.strip():
        return []
    normalized = raw.replace("\n", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


@router.post("/generate", response_model=JobResponse)
async def generate_ai_3d(
    files: list[UploadFile] | None = File(None),
    cloudinary_urls: str = Form(""),
    vision_provider: VisionProvider = Form(VisionProvider.auto),
    description: str = Form(""),
    tier: str = Form("standard"),
    analyze_image: bool = Form(False),
):
    """Reconstruct a textured GLB directly from 1-6 reference photos.

    Cloudinary URLs are sent directly to three.ws image-to-3D. Local uploads
    are temporarily exposed through Pixel Forge's public /files route so the
    reconstruction provider can fetch them. Gemini is intentionally not used
    as an intermediate representation for geometry.
    """
    settings = get_settings()
    uploads = files or []
    cloudinary_refs = _parse_cloudinary_urls(cloudinary_urls)

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
            detail="Use draft or standard for Pixel Forge direct photo reconstruction.",
        )

    source_urls: list[str] = []

    # Validate every Cloudinary transform before handing it to the 3D provider.
    for url in cloudinary_refs:
        await fetch_cloudinary_image(url, settings.max_upload_mb)
        source_urls.append(url)

    # Local fallback: validate and serve the upload from our public backend.
    for upload in uploads:
        data, mime = await read_validated_image(upload, settings.max_upload_mb)

        if settings.public_base_url.startswith(("http://localhost", "http://127.0.0.1")):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Direct 3D reconstruction from local uploads needs a public backend URL. "
                    "Use Cloudinary upload in local development."
                ),
            )

        source_urls.append(save_public_source_image(data, mime, settings))

    guidance = " ".join(description.split()).strip()[:1000]

    try:
        service = ThreeWSService(settings)
        submitted = await service.submit_images(
            source_urls,
            prompt=guidance,
            tier=tier,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Direct image-to-3D generation failed: {exc}",
        ) from exc

    if not submitted.glb_url and not submitted.job_id:
        raise HTTPException(
            status_code=502,
            detail="3D provider returned neither a model URL nor a pollable job id.",
        )

    remote_status = submitted.status.lower()
    if submitted.glb_url:
        status = "done"
    elif remote_status in {"failed", "error"}:
        status = "failed"
    else:
        # Some providers can briefly report a terminal-looking status before
        # the model URL is published. Keep the job pollable until a GLB exists.
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
            error="The direct image reconstruction provider reported a failure.",
        )

    return job_store.response(record)
