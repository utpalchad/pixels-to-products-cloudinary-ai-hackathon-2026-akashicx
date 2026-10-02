from __future__ import annotations

from urllib.parse import quote

import httpx

from app.config import Settings
from app.models.schemas import ThreeWSSubmitResponse


class ThreeWSService:
    """Client for three.ws' free, keyless textured GLB generation lane."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.threews_base_url.rstrip("/")

    @staticmethod
    def _parse(data: dict, *, fallback_job_id: str | None = None) -> ThreeWSSubmitResponse:
        glb_url = data.get("glbUrl") or data.get("glb_url")
        viewer_url = data.get("viewerUrl") or data.get("viewer_url")
        job_id = (
            data.get("job")
            or data.get("job_id")
            or data.get("creation_id")
            or fallback_job_id
        )
        status = str(data.get("status") or ("done" if glb_url else "pending"))

        return ThreeWSSubmitResponse(
            status=status,
            job_id=str(job_id) if job_id else None,
            glb_url=glb_url,
            viewer_url=viewer_url,
            raw=data,
        )

    async def submit_text(self, prompt: str) -> ThreeWSSubmitResponse:
        clean = " ".join(prompt.split()).strip()
        if len(clean) < 3:
            raise ValueError("A descriptive 3D prompt is required.")
        clean = clean[:1000]

        payload = {
            "prompt": clean,
            "format": "glb",
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.base_url}/api/3d/generate",
                json=payload,
            )
            if response.status_code == 429:
                retry_after = response.headers.get("retry-after", "later")
                raise RuntimeError(
                    f"Free 3D generation rate limit reached. Retry after {retry_after}."
                )
            response.raise_for_status()
            return self._parse(response.json())

    async def poll(self, remote_job_id: str) -> ThreeWSSubmitResponse:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.get(
                f"{self.base_url}/api/3d/generate",
                params={"job": remote_job_id},
            )
            if response.status_code == 429:
                retry_after = response.headers.get("retry-after", "later")
                raise RuntimeError(
                    f"Free 3D generation rate limit reached. Retry after {retry_after}."
                )
            response.raise_for_status()
            return self._parse(response.json(), fallback_job_id=remote_job_id)

    def viewer_url_for(self, glb_url: str) -> str:
        return f"{self.base_url}/viewer?src={quote(glb_url, safe='')}"
