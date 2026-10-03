import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(prefix="/download", tags=["downloads"])

GENERATED_FILE_PATTERN = re.compile(
    r"^pixel-forge-[0-9a-f]{32}\.(stl|glb)$"
)


@router.get("/{filename}")
async def download_generated_file(filename: str):
    settings = get_settings()

    safe_name = Path(filename).name
    if safe_name != filename or not GENERATED_FILE_PATTERN.fullmatch(safe_name):
        raise HTTPException(status_code=404, detail="Generated file not found.")

    path = (settings.output_path / safe_name).resolve()
    output_root = settings.output_path.resolve()

    if output_root not in path.parents:
        raise HTTPException(status_code=404, detail="Generated file not found.")

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Generated file not found.")

    media_type = "model/stl" if path.suffix.lower() == ".stl" else "model/gltf-binary"

    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=safe_name,
        headers={"Cache-Control": "private, no-store, max-age=0"},
    )
