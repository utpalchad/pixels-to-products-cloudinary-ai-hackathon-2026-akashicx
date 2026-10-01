from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import trimesh

from app.config import Settings


def export_mesh(
    mesh: trimesh.Trimesh,
    *,
    output_format: str,
    settings: Settings,
) -> tuple[Path, str]:
    if output_format not in {"stl", "glb"}:
        raise ValueError("output_format must be stl or glb")

    filename = f"pixel-forge-{uuid4().hex}.{output_format}"
    path = settings.output_path / filename

    mesh.export(path, file_type=output_format)

    base = settings.public_base_url.rstrip("/")
    public_url = f"{base}/files/{filename}" if base else f"/files/{filename}"
    return path, public_url
