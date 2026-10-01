from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class ConversionMode(str, Enum):
    relief = "relief"
    lithophane = "lithophane"


class OutputFormat(str, Enum):
    stl = "stl"
    glb = "glb"


class VisionProvider(str, Enum):
    auto = "auto"
    gemini = "gemini"
    local = "local"


class ImageAnalysis(BaseModel):
    object: str = Field(description="The main object or subject in the reference image.")
    orientation: str = Field(description="The visible camera/view orientation.")
    overall_shape: str = Field(description="Concise description of the object's overall 3D shape.")
    symmetry: str = Field(description="Observed or likely symmetry.")
    important_features: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    unknown_geometry: list[str] = Field(default_factory=list)
    generation_prompt: str = Field(description="A precise prompt suitable for an image-to-3D generator.")
    negative_prompt: str = Field(default="")
    recommended_mode: Literal["image_to_3d", "relief", "lithophane"] = "image_to_3d"


class AnalysisResponse(BaseModel):
    provider: str
    analysis: ImageAnalysis


class ConvertResponse(BaseModel):
    status: Literal["success"]
    mode: ConversionMode
    format: OutputFormat
    vertices: int
    faces: int
    watertight: bool
    width_mm: float
    height_mm: float
    file_url: str


class ProviderStatus(BaseModel):
    name: str
    configured: bool
    note: str | None = None


class ProvidersResponse(BaseModel):
    vision: list[ProviderStatus]
    image_to_3d: list[ProviderStatus]


class ThreeWSSubmitResponse(BaseModel):
    status: str
    job_id: str | None = None
    glb_url: HttpUrl | None = None
    viewer_url: HttpUrl | None = None
    raw: dict = Field(default_factory=dict)


class JobResponse(BaseModel):
    id: str
    status: Literal["queued", "processing", "done", "failed"]
    provider: str
    prompt: str = ""
    progress: int = 0
    glb_url: str | None = None
    viewer_url: str | None = None
    error: str | None = None
