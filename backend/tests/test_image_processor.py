import io

import numpy as np
from PIL import Image

from app.services.image_processor import image_bytes_to_heightmap


def make_gradient() -> bytes:
    arr = np.tile(np.arange(32, dtype=np.uint8), (16, 1)) * 8
    image = Image.fromarray(arr, mode="L")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_relief_heightmap_has_physical_depth():
    heightmap = image_bytes_to_heightmap(
        make_gradient(),
        resolution=32,
        mode="relief",
        depth_mm=8.0,
        base_thickness_mm=1.5,
    )
    assert heightmap.ndim == 2
    assert heightmap.shape[1] == 32
    assert float(heightmap.min()) >= 1.5
    assert float(heightmap.max()) <= 9.5 + 1e-3


def test_lithophane_dark_pixels_are_thicker():
    heightmap = image_bytes_to_heightmap(
        make_gradient(),
        resolution=32,
        mode="lithophane",
        base_thickness_mm=0.8,
        max_thickness_mm=3.2,
    )
    assert float(heightmap[:, 0].mean()) > float(heightmap[:, -1].mean())
