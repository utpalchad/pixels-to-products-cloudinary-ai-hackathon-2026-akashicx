from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageFilter


def image_bytes_to_heightmap(
    image_bytes: bytes,
    *,
    resolution: int = 128,
    mode: str = "relief",
    depth_mm: float = 8.0,
    base_thickness_mm: float = 1.5,
    max_thickness_mm: float = 4.0,
    invert: bool = False,
    smoothing: float = 0.0,
) -> np.ndarray:
    """Convert image bytes to a physical Z-height map in millimetres."""
    resolution = max(16, min(int(resolution), 256))

    image = Image.open(io.BytesIO(image_bytes)).convert("L")
    width, height = image.size
    aspect = height / max(width, 1)

    out_width = resolution
    out_height = max(16, min(256, round(resolution * aspect)))
    image = image.resize((out_width, out_height), Image.Resampling.LANCZOS)

    if smoothing > 0:
        radius = max(0.0, min(float(smoothing), 100.0)) / 25.0
        image = image.filter(ImageFilter.GaussianBlur(radius=radius))

    values = np.asarray(image, dtype=np.float32) / 255.0

    if invert:
        values = 1.0 - values

    if mode == "lithophane":
        # Dark areas are normally thicker in a lithophane.
        if not invert:
            values = 1.0 - values
        span = max(max_thickness_mm - base_thickness_mm, 0.1)
        z = base_thickness_mm + values * span
    else:
        z = base_thickness_mm + values * max(depth_mm, 0.1)

    return z.astype(np.float32)
