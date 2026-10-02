import io

import httpx
import trimesh
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.models.schemas import JobResponse
from app.services.jobs import job_store
from app.services.threews import ThreeWSService

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _fetch_finished_glb(job_id: str) -> tuple[object, bytes]:
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")

    if record.status != "done" or not record.glb_url:
        raise HTTPException(status_code=409, detail="The full 3D model is not ready yet.")

    try:
        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
            response = await client.get(record.glb_url)
            response.raise_for_status()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not fetch the generated full 3D model: {exc}",
        ) from exc

    return record, response.content


def _glb_to_stl(glb_bytes: bytes) -> bytes:
    try:
        loaded = trimesh.load(
            io.BytesIO(glb_bytes),
            file_type="glb",
            force="mesh",
            process=True,
        )

        if isinstance(loaded, trimesh.Scene):
            # Fallback for GLBs that still load as a scene despite force="mesh".
            loaded = loaded.dump(concatenate=True)

        if not isinstance(loaded, trimesh.Trimesh):
            raise ValueError("Generated GLB does not contain convertible mesh geometry.")

        if loaded.vertices.size == 0 or loaded.faces.size == 0:
            raise ValueError("Generated GLB contains an empty mesh.")

        loaded.process(validate=True)
        loaded.remove_unreferenced_vertices()

        exported = loaded.export(file_type="stl")
        if isinstance(exported, str):
            exported = exported.encode("utf-8")

        return bytes(exported)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Full 3D STL conversion failed: {exc}",
        ) from exc


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")

    if (
        record.provider in {"three.ws", "three.ws-image"}
        and record.status not in {"done", "failed"}
        and record.remote_job_id
    ):
        try:
            service = ThreeWSService(get_settings())
            remote = await service.poll(record.remote_job_id)
            remote_status = remote.status.lower()

            if remote.glb_url or remote_status == "done":
                glb_url = str(remote.glb_url) if remote.glb_url else record.glb_url
                viewer_url = (
                    str(remote.viewer_url)
                    if remote.viewer_url
                    else (service.viewer_url_for(glb_url) if glb_url else None)
                )
                record = job_store.update(
                    job_id,
                    status="done",
                    progress=100,
                    glb_url=glb_url,
                    viewer_url=viewer_url,
                    error=None,
                ) or record
            elif remote_status in {"failed", "error"}:
                record = job_store.update(
                    job_id,
                    status="failed",
                    progress=100,
                    error="The external 3D provider reported a failure.",
                ) or record
            else:
                progress = max(record.progress, min(record.progress + 10, 90))
                record = job_store.update(
                    job_id,
                    status="processing",
                    progress=progress,
                    error=None,
                ) or record
        except Exception as exc:
            record = job_store.update(
                job_id,
                error=f"Temporary provider polling error: {exc}",
            ) or record

    return job_store.response(record)


@router.get("/{job_id}/download")
async def download_job_glb(job_id: str):
    _, glb_bytes = await _fetch_finished_glb(job_id)

    return Response(
        content=glb_bytes,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'attachment; filename="pixel-forge-full-3d-{job_id}.glb"'
        },
    )


@router.get("/{job_id}/download-stl")
async def download_job_stl(job_id: str):
    """Convert the completed full 3D GLB mesh to a texture-free STL."""
    _, glb_bytes = await _fetch_finished_glb(job_id)
    stl_bytes = _glb_to_stl(glb_bytes)

    return Response(
        content=stl_bytes,
        media_type="model/stl",
        headers={
            "Content-Disposition": f'attachment; filename="pixel-forge-full-3d-{job_id}.stl"'
        },
    )
