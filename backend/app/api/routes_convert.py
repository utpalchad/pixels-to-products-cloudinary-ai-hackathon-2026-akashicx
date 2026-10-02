import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import ConversionMode, ConvertResponse, OutputFormat
from app.services.exporter import export_mesh
from app.services.image_processor import image_bytes_to_heightmap
from app.services.mesh_engine import heightmap_to_mesh
from app.utils.files import read_validated_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/convert", tags=["conversion"])


@router.post("/local", response_model=ConvertResponse)
async def convert_local(
    file: UploadFile = File(...),
    mode: ConversionMode = Form(ConversionMode.relief),
    output_format: OutputFormat = Form(OutputFormat.stl),
    width_mm: float = Form(100.0),
    depth_mm: float = Form(8.0),
    base_thickness_mm: float = Form(1.5),
    max_thickness_mm: float = Form(4.0),
    resolution: int = Form(128),
    smoothing: float = Form(15.0),
    invert: bool = Form(False),
):
    settings = get_settings()
    image_bytes, _ = await read_validated_image(file, settings.max_upload_mb)

    if not 10 <= width_mm <= 500:
        raise HTTPException(status_code=422, detail="width_mm must be between 10 and 500.")
    if not 16 <= resolution <= 256:
        raise HTTPException(status_code=422, detail="resolution must be between 16 and 256.")
    if not 0.1 <= base_thickness_mm <= 20:
        raise HTTPException(
            status_code=422,
            detail="base_thickness_mm must be between 0.1 and 20.",
        )
    if mode == ConversionMode.relief and not 0.1 <= depth_mm <= 50:
        raise HTTPException(status_code=422, detail="depth_mm must be between 0.1 and 50.")
    if mode == ConversionMode.lithophane and not (
        base_thickness_mm < max_thickness_mm <= 20
    ):
        raise HTTPException(
            status_code=422,
            detail="max_thickness_mm must be greater than base thickness and at most 20.",
        )

    try:
        heightmap = image_bytes_to_heightmap(
            image_bytes,
            resolution=resolution,
            mode=mode.value,
            depth_mm=depth_mm,
            base_thickness_mm=base_thickness_mm,
            max_thickness_mm=max_thickness_mm,
            invert=invert,
            smoothing=smoothing,
        )
        mesh, actual_width, actual_height = heightmap_to_mesh(
            heightmap,
            width_mm=width_mm,
        )
        _, file_url = export_mesh(
            mesh,
            output_format=output_format.value,
            settings=settings,
        )
    except Exception as exc:
        logger.exception("Mesh conversion failed")
        raise HTTPException(status_code=500, detail=f"Mesh conversion failed: {exc}") from exc

    return ConvertResponse(
        status="success",
        mode=mode,
        format=output_format,
        vertices=len(mesh.vertices),
        faces=len(mesh.faces),
        watertight=bool(mesh.is_watertight),
        width_mm=round(actual_width, 3),
        height_mm=round(actual_height, 3),
        file_url=file_url,
    )
