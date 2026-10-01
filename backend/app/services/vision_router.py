from __future__ import annotations

from app.config import Settings
from app.models.schemas import ImageAnalysis, VisionProvider
from app.services.vision_gemini import GeminiVisionService


class VisionRouter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.gemini = GeminiVisionService(settings)

    def available(self) -> dict[str, bool]:
        return {
            "gemini": self.gemini.enabled,
            "local": True,
        }

    async def analyze(
        self,
        image_bytes: bytes,
        mime_type: str,
        *,
        provider: VisionProvider = VisionProvider.auto,
        user_description: str = "",
    ) -> tuple[str, ImageAnalysis]:
        if provider == VisionProvider.gemini:
            return "gemini", await self.gemini.analyze(
                image_bytes, mime_type, user_description=user_description
            )

        if provider == VisionProvider.local:
            return "local", self._local_fallback(user_description)

        if self.gemini.enabled:
            try:
                return "gemini", await self.gemini.analyze(
                    image_bytes, mime_type, user_description=user_description
                )
            except Exception:
                # Keep the app usable during quota/network/provider errors.
                return "local", self._local_fallback(user_description)

        return "local", self._local_fallback(user_description)

    @staticmethod
    def _local_fallback(user_description: str) -> ImageAnalysis:
        subject = user_description.strip() or "reference object"
        return ImageAnalysis(
            object=subject,
            orientation="unknown single-view orientation",
            overall_shape="derive the dominant silhouette and visible depth cues from the reference",
            symmetry="unknown",
            important_features=["preserve the visible silhouette", "preserve major proportions"],
            materials=[],
            unknown_geometry=["all surfaces hidden from the supplied view"],
            generation_prompt=(
                f"Create a coherent complete 3D model of {subject}. Preserve the visible "
                "silhouette, proportions, orientation, and major features from the reference. "
                "Complete unseen surfaces conservatively and keep the mesh clean and connected."
            ),
            negative_prompt=(
                "duplicate parts, floating geometry, broken topology, distorted proportions, "
                "unwanted text, extra limbs or components, disconnected fragments"
            ),
            recommended_mode="image_to_3d",
        )
