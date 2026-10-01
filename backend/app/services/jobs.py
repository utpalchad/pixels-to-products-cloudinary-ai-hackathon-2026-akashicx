from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from uuid import uuid4

from app.models.schemas import JobResponse


@dataclass
class JobRecord:
    id: str
    status: str
    provider: str
    prompt: str = ""
    progress: int = 0
    remote_job_id: str | None = None
    glb_url: str | None = None
    viewer_url: str | None = None
    error: str | None = None


class JobStore:
    """Hackathon-friendly in-memory store. Replace with Redis/Postgres for production."""

    def __init__(self):
        self._jobs: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(
        self,
        *,
        provider: str,
        prompt: str = "",
        remote_job_id: str | None = None,
        status: str = "queued",
        glb_url: str | None = None,
        viewer_url: str | None = None,
    ) -> JobRecord:
        record = JobRecord(
            id=uuid4().hex,
            status=status,
            provider=provider,
            prompt=prompt,
            remote_job_id=remote_job_id,
            progress=100 if status == "done" else 5,
            glb_url=glb_url,
            viewer_url=viewer_url,
        )
        with self._lock:
            self._jobs[record.id] = record
        return record

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **changes) -> JobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return None
            for key, value in changes.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            return record

    @staticmethod
    def response(record: JobRecord) -> JobResponse:
        return JobResponse(
            id=record.id,
            status=record.status,
            provider=record.provider,
            prompt=record.prompt,
            progress=record.progress,
            glb_url=record.glb_url,
            viewer_url=record.viewer_url,
            error=record.error,
        )


job_store = JobStore()
