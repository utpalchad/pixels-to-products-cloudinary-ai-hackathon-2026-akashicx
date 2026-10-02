from __future__ import annotations

import asyncio

from google import genai
from google.genai import types

from app.config import Settings
from app.models.schemas import ImageAnalysis


SYSTEM_PROMPT = """You are Pixel Forge's strict 3D reconstruction analyst.

Analyze the reference image as a SINGLE-OBJECT reconstruction task.

PRIMARY GOAL:
Identify the one dominant physical foreground object that the user most likely wants reconstructed.
Unless the image clearly contains an intentional multi-object product set, assume the desired output is EXACTLY ONE instance of the main object.

OBJECT-COUNT RULES:
- Do not treat reflections, shadows, mirrored appearances, labels, logos, printed photos, packaging graphics, or background objects as additional instances.
- Do not turn repeated visual patterns into repeated physical objects.
- Do not describe a collection, lineup, pair, bundle, or scene when the reference is a single product/object photo.
- If the same object appears more than once because of a reflection or visual duplication, describe only one real object.
- Never invent extra copies of the primary object.

GEOMETRY RULES:
- Focus on the primary object's shape, proportions, silhouette, orientation, symmetry, visible parts, materials, colors, and surface details.
- Preserve the visible proportions and distinctive features faithfully.
- Treat the image as the source of truth.
- Do not invent hidden geometry as fact. Put uncertain or occluded geometry in unknown_geometry.
- Hidden/back surfaces should be completed conservatively and consistently with the visible geometry.
- Keep the result as one isolated 3D asset, not a scene.

GENERATION PROMPT RULES:
- generation_prompt must explicitly request EXACTLY ONE instance of the primary object.
- It must say the asset is isolated, centered, and contains no duplicate copies or unrelated props.
- It must preserve visible colors, materials, proportions, and recognizable features.
- It must request a complete 360-degree object while conservatively inferring unseen surfaces.
- Avoid scene-building language.

NEGATIVE PROMPT RULES:
Strongly forbid:
multiple objects, duplicate copies, extra instances, groups, collections, mirrored duplicates,
extra bottles, extra caps, extra handles, floating parts, unrelated props, background objects,
pedestals, text as separate geometry, broken topology, distorted proportions, and artifacts.

Return valid JSON only using the provided schema.
"""


class GeminiVisionService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.gemini_api_key)

    async def analyze(
        self,
        image_bytes: bytes,
        mime_type: str,
        *,
        user_description: str = "",
    ) -> ImageAnalysis:
        if not self.enabled:
            raise RuntimeError("Gemini is not configured.")

        client = genai.Client(api_key=self.settings.gemini_api_key)
        prompt = SYSTEM_PROMPT
        if user_description.strip():
            prompt += (
                "\nUSER GUIDANCE:\n"
                "Use this only to clarify the identity or desired appearance of the same single "
                "primary object. Do not use it as permission to create additional objects.\n"
                f"{user_description.strip()}"
            )

        def _call():
            return client.models.generate_content(
                model=self.settings.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ImageAnalysis,
                    temperature=0.0,
                ),
            )

        response = await asyncio.to_thread(_call)
        if not response.text:
            raise RuntimeError("Gemini returned an empty analysis.")

        return ImageAnalysis.model_validate_json(response.text)
