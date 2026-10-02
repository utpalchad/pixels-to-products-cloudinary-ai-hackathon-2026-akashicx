import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.config import get_settings
from app.models.schemas import JobResponse
from app.services.jobs import job_store
from app.services.threews import ThreeWSService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")

    if (
        record.provider == "three.ws"
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
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found.")
    if record.status != "done" or not record.glb_url:
        raise HTTPException(status_code=409, detail="The GLB is not ready yet.")

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(record.glb_url)
        response.raise_for_status()

    return Response(
        content=response.content,
        media_type="model/gltf-binary",
        headers={
            "Content-Disposition": f'attachment; filename="pixel-forge-full-3d-{job_id}.glb"'
        },
    )
