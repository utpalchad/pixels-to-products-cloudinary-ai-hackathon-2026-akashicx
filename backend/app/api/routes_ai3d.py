from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import ImageAnalysis, JobResponse, VisionProvider
from app.services.jobs import job_store
from app.services.threews import ThreeWSService
from app.services.vision_router import VisionRouter
from app.utils.files import fetch_cloudinary_image, read_validated_image

router = APIRouter(prefix="/ai3d", tags=["ai-3d"])


def _parse_cloudinary_urls(raw: str) -> list[str]:
    if not raw.strip():
        return []
    normalized = raw.replace("\n", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _compile_single_object_prompt(analysis: ImageAnalysis) -> str:
    """Build a deterministic one-object prompt instead of trusting free-form wording."""
    features = ", ".join(analysis.important_features[:8]) or "preserve all visible distinctive features"
    materials = ", ".join(analysis.materials[:8]) or "match the visible materials and colors"
    unknown = ", ".join(analysis.unknown_geometry[:6]) or "unseen back and hidden surfaces"

    prompt = (
        f"Create EXACTLY ONE 3D asset representing ONE instance of {analysis.object}. "
        "SINGLE-OBJECT RULE: there must be one primary object only. "
        "Do not create a pair, set, collection, lineup, scene, or multiple copies. "
        "Ignore reflections, shadows, mirrors, labels, logos, printed images, repeated patterns, "
        "and background elements as possible extra objects. "
        "Keep the object isolated and centered, with no unrelated props or surrounding objects. "
        f"Overall shape: {analysis.overall_shape}. "
        f"Reference orientation: {analysis.orientation}. "
        f"Symmetry: {analysis.symmetry}. "
        f"Important visible features: {features}. "
        f"Materials and visible colors: {materials}. "
        "Preserve the reference object's visible proportions, silhouette, recognizable details, "
        "material appearance, and color placement as faithfully as possible. "
        "Generate a complete 360-degree version of this SAME object. "
        f"For hidden geometry such as {unknown}, infer only the minimum plausible continuation "
        "needed to complete the object and do not invent decorative structures. "
        f"Additional reconstruction guidance: {analysis.generation_prompt}. "
        "STRICT NEGATIVE CONSTRAINTS: no duplicate object, no second copy, no repeated instance, "
        "no group, no collection, no mirrored duplicate, no extra bottle, no extra cap, "
        "no extra handle, no floating part, no unrelated prop, no background object, "
        "no pedestal, no text as separate geometry, no broken topology, no distorted proportions. "
        f"Also avoid: {analysis.negative_prompt}"
    )

    return " ".join(prompt.split())[:1000]


@router.post("/generate", response_model=JobResponse)
async def generate_ai_3d(
    files: list[UploadFile] | None = File(None),
    cloudinary_urls: str = Form(""),
    vision_provider: VisionProvider = Form(VisionProvider.auto),
    description: str = Form(""),
    tier: str = Form("draft"),
    analyze_image: bool = Form(True),
):
    """Turn a reference image into a Gemini-guided full textured GLB.

    The free three.ws lane is text-to-3D, so Pixel Forge first uses the image
    to build a strict single-object geometry/material prompt and then sends
    that prompt to the textured GLB generator.
    """
    settings = get_settings()
    uploads = files or []
    cloudinary_refs = _parse_cloudinary_urls(cloudinary_urls)

    if not uploads and not cloudinary_refs:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one uploaded image or Cloudinary delivery URL.",
        )

    if len(uploads) + len(cloudinary_refs) > 6:
        raise HTTPException(status_code=422, detail="A maximum of 6 image views is supported.")

    if tier != "draft":
        raise HTTPException(
            status_code=422,
            detail="The current free full-3D mode supports the draft tier only.",
        )

    validated: list[tuple[bytes, str, str]] = []
    for upload in uploads:
        data, mime = await read_validated_image(upload, settings.max_upload_mb)
        validated.append((data, mime, upload.filename or "view"))

    for index, url in enumerate(cloudinary_refs):
        data, mime = await fetch_cloudinary_image(url, settings.max_upload_mb)
        validated.append((data, mime, f"cloudinary-{index + 1}"))

    generation_prompt = description.strip()

    if analyze_image:
        vision = VisionRouter(settings)
        try:
            _, analysis = await vision.analyze(
                validated[0][0],
                validated[0][1],
                provider=vision_provider,
                user_description=description,
            )
            generation_prompt = _compile_single_object_prompt(analysis)
        except Exception as exc:
            if not generation_prompt:
                raise HTTPException(
                    status_code=502,
                    detail=f"Image analysis failed and no description was supplied: {exc}",
                ) from exc

    if not generation_prompt:
        generation_prompt = (
            "Create EXACTLY ONE isolated, centered, complete 360-degree textured 3D object. "
            "No duplicates, no second copy, no collection, no background objects, and no props."
        )

    generation_prompt = " ".join(generation_prompt.split())[:1000]

    try:
        service = ThreeWSService(settings)
        submitted = await service.submit_text(generation_prompt)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Full 3D generation failed: {exc}") from exc

    remote_status = submitted.status.lower()
    if submitted.glb_url or remote_status == "done":
        status = "done"
    elif remote_status in {"failed", "error"}:
        status = "failed"
    else:
        status = "queued"

    record = job_store.create(
        provider="three.ws",
        prompt=generation_prompt,
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
        job_store.update(record.id, error="The 3D generator reported a failure.")

    return job_store.response(record)
