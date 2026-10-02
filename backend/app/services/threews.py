from __future__ import annotations

from urllib.parse import quote

import httpx

from app.config import Settings
from app.models.schemas import ThreeWSSubmitResponse


class ThreeWSService:
    """Client for three.ws direct image-to-3D and multi-view reconstruction."""

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
        status = str(data.get("status") or ("done" if glb_url else "queued"))

        return ThreeWSSubmitResponse(
            status=status,
            job_id=str(job_id) if job_id else None,
            glb_url=glb_url,
            viewer_url=viewer_url,
            raw=data,
        )

    async def submit_images(
        self,
        image_urls: list[str],
        *,
        prompt: str = "",
        tier: str = "standard",
    ) -> ThreeWSSubmitResponse:
        if not 1 <= len(image_urls) <= 6:
            raise ValueError("Direct image reconstruction accepts between 1 and 6 views.")

        if tier not in {"draft", "standard"}:
            raise ValueError("Pixel Forge free direct reconstruction supports draft or standard.")

        payload: dict = {
            "image_urls": image_urls,
            "tier": tier,
        }

        clean_prompt = " ".join(prompt.split()).strip()
        if clean_prompt:
            payload["prompt"] = clean_prompt[:1000]

        async with httpx.AsyncClient(timeout=240.0) as client:
            response = await client.post(
                f"{self.base_url}/api/forge",
                json=payload,
                headers={"x-forge-client": "pixel-forge"},
            )

            if response.status_code == 429:
                retry_after = response.headers.get("retry-after", "later")
                raise RuntimeError(
                    f"3D generation rate limit reached. Retry after {retry_after}."
                )

            if response.status_code == 402:
                raise RuntimeError(
                    "The selected three.ws reconstruction lane requires payment or access. "
                    "Try the free standard lane again later."
                )

            response.raise_for_status()
            return self._parse(response.json())

    async def poll(self, remote_job_id: str) -> ThreeWSSubmitResponse:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self.base_url}/api/forge",
                params={"job": remote_job_id},
                headers={"x-forge-client": "pixel-forge"},
            )

            if response.status_code == 429:
                retry_after = response.headers.get("retry-after", "later")
                raise RuntimeError(
                    f"3D generation rate limit reached. Retry after {retry_after}."
                )

            response.raise_for_status()
            return self._parse(response.json(), fallback_job_id=remote_job_id)

    def viewer_url_for(self, glb_url: str) -> str:
        return f"{self.base_url}/viewer?src={quote(glb_url, safe='')}"
