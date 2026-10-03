from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import get_settings
from app.utils.files import verify_source_signature

router = APIRouter(prefix="/source", tags=["internal-source"])

SOURCE_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@router.get("/{filename}", include_in_schema=False)
async def get_signed_source(
    filename: str,
    expires: int = Query(...),
    sig: str = Query(..., min_length=64, max_length=64),
):
    settings = get_settings()

    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    now = int(time.time())
    if expires < now:
        raise HTTPException(status_code=410, detail="Source URL expired.")

    # Refuse signatures with absurdly long lifetimes even if they were somehow
    # generated with the secret.
    if expires > now + settings.source_url_ttl_seconds + 120:
        raise HTTPException(status_code=403, detail="Invalid source URL.")

    if not verify_source_signature(safe_name, expires, sig, settings):
        raise HTTPException(status_code=403, detail="Invalid source URL.")

    path = settings.source_path / safe_name
    media_type = SOURCE_MEDIA_TYPES.get(path.suffix.lower())

    if media_type is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Source image not found.")

    return FileResponse(
        path=str(path),
        media_type=media_type,
        headers={"Cache-Control": "private, no-store, max-age=0"},
    )
