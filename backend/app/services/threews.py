from __future__ import annotations

from urllib.parse import quote

import httpx

from app.config import Settings
from app.models.schemas import ThreeWSSubmitResponse


class ThreeWSService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.threews_base_url.rstrip("/")

    async def submit(
        self,
        image_urls: list[str],
        *,
        prompt: str = "",
        tier: str | None = None,
    ) -> ThreeWSSubmitResponse:
        if not 1 <= len(image_urls) <= 6:
            raise ValueError("three.ws accepts between 1 and 6 image views.")

        payload: dict = {
            "image_urls": image_urls,
            "tier": tier or self.settings.threews_default_tier,
        }
        if prompt.strip():
            payload["prompt"] = prompt.strip()

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{self.base_url}/api/forge", json=payload)
            response.raise_for_status()
            data = response.json()

        glb_url = data.get("glb_url") or data.get("glbUrl")
        viewer_url = data.get("viewer_url") or data.get("viewerUrl")
        status = data.get("status") or ("done" if glb_url else "queued")

        return ThreeWSSubmitResponse(
            status=status,
            job_id=data.get("job_id"),
            glb_url=glb_url,
            viewer_url=viewer_url,
            raw=data,
        )

    async def poll(self, remote_job_id: str) -> ThreeWSSubmitResponse:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.get(
                f"{self.base_url}/api/forge",
                params={"job": remote_job_id},
            )
            response.raise_for_status()
            data = response.json()

        glb_url = data.get("glb_url") or data.get("glbUrl")
        viewer_url = data.get("viewer_url") or data.get("viewerUrl")
        status = data.get("status") or ("done" if glb_url else "processing")

        return ThreeWSSubmitResponse(
            status=status,
            job_id=data.get("job_id") or remote_job_id,
            glb_url=glb_url,
            viewer_url=viewer_url,
            raw=data,
        )

    def viewer_url_for(self, glb_url: str) -> str:
        return f"{self.base_url}/viewer?src={quote(glb_url, safe='')}"
