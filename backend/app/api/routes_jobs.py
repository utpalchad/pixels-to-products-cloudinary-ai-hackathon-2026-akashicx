import io
import logging
import re

import trimesh
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.models.schemas import JobResponse
from app.services.jobs import job_store
from app.services.threews import ThreeWSService
from app.utils.network import fetch_public_binary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])
JOB_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


def _validate_job_id(job_id: str) -> str:
    if not JOB_ID_PATTERN.fullmatch(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return job_id


async def _fetch_finished_glb(job_id: str) -> tuple[object, bytes]:
    job_id = _validate_job_id(job_id)
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")

    if record.status != "done" or not record.glb_url:
        raise HTTPException(status_code=409, detail="The full 3D model is not ready yet.")

    settings = get_settings()
    try:
        glb_bytes = await fetch_public_binary(
            record.glb_url,
            max_bytes=settings.max_model_bytes,
            timeout_seconds=180.0,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not fetch generated GLB job_id=%s", job_id)
        raise HTTPException(
            status_code=502,
            detail="Could not fetch the generated full 3D model.",
        )

    return record, glb_bytes


def _glb_to_stl(glb_bytes: bytes) -> bytes:
    try:
        loaded = trimesh.load(
            io.BytesIO(glb_bytes),
            file_type="glb",
            force="mesh",
            process=True,
        )

        if isinstance(loaded, trimesh.Scene):
            loaded = loaded.dump(concatenate=True)

        if not isinstance(loaded, trimesh.Trimesh):
            raise ValueError("GLB does not contain mesh geometry.")

        if loaded.vertices.size == 0 or loaded.faces.size == 0:
            raise ValueError("GLB contains an empty mesh.")

        loaded.process(validate=True)
        loaded.remove_unreferenced_vertices()

        exported = loaded.export(file_type="stl")
        if isinstance(exported, str):
            exported = exported.encode("utf-8")

        return bytes(exported)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Full 3D STL conversion failed")
        raise HTTPException(
            status_code=500,
            detail="Full 3D STL conversion failed.",
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job_id = _validate_job_id(job_id)
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

            if remote.glb_url:
                glb_url = str(remote.glb_url)
                viewer_url = (
                    str(remote.viewer_url)
                    if remote.viewer_url
                    else service.viewer_url_for(glb_url)
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
        except Exception:
            logger.warning(
                "Temporary provider polling failure job_id=%s",
                job_id,
                exc_info=True,
            )
            record = job_store.update(
                job_id,
                error="Temporary provider polling error.",
            ) or record

    return job_store.response(record)


@router.get("/{job_id}/download")
async def download_job_glb(job_id: str):
    _, glb_bytes = await _fetch_finished_glb(job_id)

    return Response(
        content=glb_bytes,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'attachment; filename="pixel-forge-full-3d-{job_id}.glb"',
            "Cache-Control": "private, no-store, max-age=0",
        },
    )


@router.get("/{job_id}/download-stl")
async def download_job_stl(job_id: str):
    _, glb_bytes = await _fetch_finished_glb(job_id)
    stl_bytes = _glb_to_stl(glb_bytes)

    return Response(
        content=stl_bytes,
        media_type="model/stl",
        headers={
            "Content-Disposition": f'attachment; filename="pixel-forge-full-3d-{job_id}.stl"',
            "Cache-Control": "private, no-store, max-age=0",
        },
    )
