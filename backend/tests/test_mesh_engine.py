import numpy as np

from app.services.mesh_engine import heightmap_to_mesh


def test_mesh_is_closed_and_watertight():
    heightmap = np.full((12, 16), 2.5, dtype=np.float32)
    mesh, width_mm, height_mm = heightmap_to_mesh(heightmap, width_mm=100)

    assert width_mm == 100
    assert height_mm > 0
    assert len(mesh.vertices) > 0
    assert len(mesh.faces) > 0
    assert mesh.is_watertight
    assert mesh.volume > 0
