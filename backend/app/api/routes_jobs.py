from fastapi import APIRouter, HTTPException

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
                ) or record
            elif remote_status == "failed":
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
                ) or record
        except Exception as exc:
            # Keep the job pollable if the provider has a transient error.
            record = job_store.update(
                job_id,
                error=f"Temporary provider polling error: {exc}",
            ) or record

    return job_store.response(record)
