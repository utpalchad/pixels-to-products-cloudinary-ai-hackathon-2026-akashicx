from __future__ import annotations

import numpy as np
import trimesh


def heightmap_to_mesh(
    heightmap: np.ndarray,
    *,
    width_mm: float = 100.0,
) -> tuple[trimesh.Trimesh, float, float]:
    """Create a closed, printable mesh from a 2D physical height map."""
    if heightmap.ndim != 2:
        raise ValueError("heightmap must be a 2D array")

    rows, cols = heightmap.shape
    if rows < 2 or cols < 2:
        raise ValueError("heightmap must contain at least 2x2 samples")

    width_mm = max(float(width_mm), 1.0)
    height_mm = width_mm * (rows - 1) / (cols - 1)

    xs = np.linspace(-width_mm / 2.0, width_mm / 2.0, cols, dtype=np.float32)
    ys = np.linspace(-height_mm / 2.0, height_mm / 2.0, rows, dtype=np.float32)
    xx, yy = np.meshgrid(xs, ys)

    top = np.column_stack((xx.ravel(), yy.ravel(), heightmap.ravel()))
    bottom = np.column_stack(
        (xx.ravel(), yy.ravel(), np.zeros(rows * cols, dtype=np.float32))
    )
    vertices = np.vstack((top, bottom))

    n = rows * cols
    r = np.arange(rows - 1)[:, None]
    c = np.arange(cols - 1)[None, :]
    a = (r * cols + c).ravel()
    b = a + 1
    c0 = a + cols
    d = c0 + 1

    top_faces = np.column_stack(
        (
            np.concatenate((a, b)),
            np.concatenate((c0, c0)),
            np.concatenate((b, d)),
        )
    )

    bottom_faces = np.column_stack(
        (
            np.concatenate((a + n, b + n)),
            np.concatenate((b + n, d + n)),
            np.concatenate((c0 + n, c0 + n)),
        )
    )

    wall_faces: list[list[int]] = []

    def connect_edge(edge: list[int]) -> None:
        for first, second in zip(edge[:-1], edge[1:]):
            wall_faces.append([first, second + n, second])
            wall_faces.append([first, first + n, second + n])

    connect_edge(list(range(cols)))
    connect_edge(list(range((rows - 1) * cols, rows * cols))[::-1])
    connect_edge([row * cols for row in range(rows)][::-1])
    connect_edge([row * cols + (cols - 1) for row in range(rows)])

    faces = np.vstack(
        (
            top_faces.astype(np.int64),
            bottom_faces.astype(np.int64),
            np.asarray(wall_faces, dtype=np.int64),
        )
    )

    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        process=True,
        validate=True,
    )
    try:
        mesh.fix_normals()
    except Exception:
        pass

    return mesh, width_mm, height_mm
