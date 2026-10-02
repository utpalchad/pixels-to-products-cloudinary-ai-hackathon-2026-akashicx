import asyncio
import io
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import Settings

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MIME_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
CLOUDINARY_PENDING_CODES = {420, 423}
CLOUDINARY_MAX_ATTEMPTS = 15


def _validate_image_bytes(data: bytes, mime_type: str, max_upload_mb: int) -> tuple[bytes, str]:
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only JPG, PNG, and WebP images are supported.",
        )

    if not data:
        raise HTTPException(status_code=400, detail="Image is empty.")

    max_bytes = max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image exceeds the {max_upload_mb} MB upload limit.",
        )

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image file.") from exc

    return data, mime_type


async def read_validated_image(upload: UploadFile, max_upload_mb: int) -> tuple[bytes, str]:
    data = await upload.read()
    return _validate_image_bytes(
        data,
        upload.content_type or "application/octet-stream",
        max_upload_mb,
    )


async def fetch_cloudinary_image(url: str, max_upload_mb: int) -> tuple[bytes, str]:
    """Fetch an image only from Cloudinary's public delivery host.

    AI transformations may return 420/423 while Cloudinary creates the
    derived asset, so retry briefly before treating the request as failed.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
        raise HTTPException(
            status_code=422,
            detail="Cloudinary URL must use https://res.cloudinary.com/...",
        )

    max_bytes = max_upload_mb * 1024 * 1024
    response: httpx.Response | None = None

    async with httpx.AsyncClient(
        timeout=45.0,
        follow_redirects=False,
        headers={"User-Agent": "Pixel-Forge/1.0"},
    ) as client:
        for attempt in range(CLOUDINARY_MAX_ATTEMPTS):
            response = await client.get(url)
            if response.status_code not in CLOUDINARY_PENDING_CODES:
                break
            await asyncio.sleep(min(1.5 + attempt * 0.5, 5.0))

    if response is None or response.status_code != 200:
        status = response.status_code if response is not None else "unknown"
        raise HTTPException(
            status_code=422,
            detail=f"Could not fetch Cloudinary asset ({status}).",
        )

    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Cloudinary asset exceeds the {max_upload_mb} MB limit.",
        )

    mime_type = response.headers.get("content-type", "").split(";")[0].strip()
    return _validate_image_bytes(response.content, mime_type, max_upload_mb)


def save_public_source_image(
    data: bytes,
    mime_type: str,
    settings: Settings,
) -> str:
    """Persist a reference image under /files so external 3D providers can fetch it."""
    ext = MIME_EXTENSIONS.get(mime_type, ".jpg")
    source_dir: Path = settings.output_path / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)

    filename = f"source-{uuid4().hex}{ext}"
    path = source_dir / filename
    path.write_bytes(data)

    base = settings.public_base_url.rstrip("/")
    return f"{base}/files/sources/{filename}"
