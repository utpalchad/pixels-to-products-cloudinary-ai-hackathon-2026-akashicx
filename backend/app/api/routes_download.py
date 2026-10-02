from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(prefix="/download", tags=["downloads"])

ALLOWED_EXPORT_EXTENSIONS = {".stl", ".glb"}


@router.get("/{filename}")
async def download_generated_file(filename: str):
    settings = get_settings()

    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    path = settings.output_path / safe_name
    if path.suffix.lower() not in ALLOWED_EXPORT_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported generated file type.")

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Generated file not found.")

    media_type = (
        "model/stl"
        if path.suffix.lower() == ".stl"
        else "model/gltf-binary"
    )
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=safe_name,
    )
