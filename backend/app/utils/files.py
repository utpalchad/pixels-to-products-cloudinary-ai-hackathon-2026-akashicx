from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import time
import warnings
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
READ_CHUNK_BYTES = 1024 * 1024


def _validate_image_bytes(
    data: bytes,
    mime_type: str,
    max_upload_mb: int,
    max_image_pixels: int = 25_000_000,
) -> tuple[bytes, str]:
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
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                width, height = image.size

                if width <= 0 or height <= 0 or width * height > max_image_pixels:
                    raise HTTPException(
                        status_code=413,
                        detail="Image dimensions exceed the safe processing limit.",
                    )

                if getattr(image, "n_frames", 1) > 1:
                    raise HTTPException(
                        status_code=415,
                        detail="Animated images are not supported.",
                    )

                image.verify()
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(
            status_code=413,
            detail="Image dimensions exceed the safe processing limit.",
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image file.") from exc

    return data, mime_type


async def read_validated_image(
    upload: UploadFile,
    max_upload_mb: int,
    max_image_pixels: int = 25_000_000,
) -> tuple[bytes, str]:
    """Read uploads incrementally so oversized files are rejected early."""

    max_bytes = max_upload_mb * 1024 * 1024
    buffer = bytearray()

    while True:
        chunk = await upload.read(READ_CHUNK_BYTES)
        if not chunk:
            break

        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Image exceeds the {max_upload_mb} MB upload limit.",
            )

    return _validate_image_bytes(
        bytes(buffer),
        upload.content_type or "application/octet-stream",
        max_upload_mb,
        max_image_pixels,
    )


async def fetch_cloudinary_image(
    url: str,
    max_upload_mb: int,
    max_image_pixels: int = 25_000_000,
) -> tuple[bytes, str]:
    """Fetch only Cloudinary HTTPS delivery URLs with strict size limits."""

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "res.cloudinary.com":
        raise HTTPException(
            status_code=422,
            detail="Cloudinary URL must use https://res.cloudinary.com/...",
        )

    if len(url) > 4096:
        raise HTTPException(status_code=422, detail="Cloudinary URL is too long.")

    max_bytes = max_upload_mb * 1024 * 1024
    last_status: int | None = None

    async with httpx.AsyncClient(
        timeout=45.0,
        follow_redirects=False,
        headers={"User-Agent": "Pixel-Forge/1.0"},
    ) as client:
        for attempt in range(CLOUDINARY_MAX_ATTEMPTS):
            async with client.stream("GET", url) as response:
                last_status = response.status_code

                if response.status_code in CLOUDINARY_PENDING_CODES:
                    pass
                elif response.status_code != 200:
                    break
                else:
                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            if int(content_length) > max_bytes:
                                raise HTTPException(
                                    status_code=413,
                                    detail=(
                                        f"Cloudinary asset exceeds the "
                                        f"{max_upload_mb} MB limit."
                                    ),
                                )
                        except ValueError:
                            pass

                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > max_bytes:
                            raise HTTPException(
                                status_code=413,
                                detail=(
                                    f"Cloudinary asset exceeds the "
                                    f"{max_upload_mb} MB limit."
                                ),
                            )

                    mime_type = (
                        response.headers.get("content-type", "")
                        .split(";")[0]
                        .strip()
                    )
                    return _validate_image_bytes(
                        bytes(data),
                        mime_type,
                        max_upload_mb,
                        max_image_pixels,
                    )

            if last_status in CLOUDINARY_PENDING_CODES:
                await asyncio.sleep(min(1.5 + attempt * 0.5, 5.0))
                continue

            break

    raise HTTPException(
        status_code=422,
        detail=f"Could not fetch Cloudinary asset ({last_status or 'unknown'}).",
    )


def _source_signature(filename: str, expires: int, settings: Settings) -> str:
    message = f"{filename}:{expires}".encode("utf-8")
    return hmac.new(
        settings.source_signing_secret.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def verify_source_signature(
    filename: str,
    expires: int,
    signature: str,
    settings: Settings,
) -> bool:
    expected = _source_signature(filename, expires, settings)
    return hmac.compare_digest(expected, signature)


def _cleanup_expired_sources(settings: Settings) -> None:
    cutoff = time.time() - (settings.source_url_ttl_seconds * 2)

    for path in settings.source_path.glob("source-*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError:
            continue


def save_public_source_image(
    data: bytes,
    mime_type: str,
    settings: Settings,
) -> str:
    """Save a private reference and return a short-lived signed fetch URL."""

    ext = MIME_EXTENSIONS.get(mime_type)
    if ext is None:
        raise HTTPException(status_code=415, detail="Unsupported image type.")

    _cleanup_expired_sources(settings)

    filename = f"source-{uuid4().hex}{ext}"
    path = settings.source_path / filename
    path.write_bytes(data)

    expires = int(time.time()) + settings.source_url_ttl_seconds
    signature = _source_signature(filename, expires, settings)
    base = settings.public_base_url.rstrip("/")

    return (
        f"{base}/api/v1/source/{filename}"
        f"?expires={expires}&sig={signature}"
    )
