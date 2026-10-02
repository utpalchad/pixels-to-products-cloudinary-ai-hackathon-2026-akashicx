import io
from urllib.parse import urlparse

import trimesh
from fastapi.testclient import TestClient
from PIL import Image

from app.config import get_settings
from app.main import app
from app.models.schemas import ThreeWSSubmitResponse
from app.services.jobs import job_store
from app.services.threews import ThreeWSService
from app.api.routes_jobs import _glb_to_stl


client = TestClient(app)


def make_png() -> bytes:
    image = Image.new("RGB", (24, 18), color=(120, 180, 220))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_health_and_provider_routes():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    providers = client.get("/providers")
    assert providers.status_code == 200
    body = providers.json()
    assert any(item["name"] == "local" for item in body["vision"])
    assert any(item["name"] == "three.ws" for item in body["image_to_3d"])


def test_analysis_local_fallback_route():
    response = client.post(
        "/api/v1/analysis/image",
        files={"file": ("reference.png", make_png(), "image/png")},
        data={"provider": "local", "description": "small cup"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "local"
    assert body["analysis"]["object"] == "small cup"
    assert body["analysis"]["recommended_mode"] == "image_to_3d"


def test_relief_conversion_and_download(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "output_dir", str(tmp_path))

    response = client.post(
        "/api/v1/convert/local",
        files={"file": ("reference.png", make_png(), "image/png")},
        data={
            "mode": "relief",
            "output_format": "stl",
            "width_mm": "100",
            "depth_mm": "8",
            "base_thickness_mm": "1.5",
            "max_thickness_mm": "4",
            "resolution": "32",
            "smoothing": "10",
            "invert": "false",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["format"] == "stl"
    assert body["vertices"] > 0
    assert body["faces"] > 0
    assert body["watertight"] is True

    path = urlparse(body["download_url"]).path
    download = client.get(path)
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("model/stl")
    assert len(download.content) > 84


def test_multi_view_ai3d_submission_creates_pollable_job(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "output_dir", str(tmp_path))
    monkeypatch.setattr(settings, "public_base_url", "https://pixel-forge.example")

    async def fake_submit(self, image_urls, *, prompt="", tier="standard"):
        assert len(image_urls) == 2
        assert tier == "standard"
        return ThreeWSSubmitResponse(
            status="queued",
            job_id="remote-test-123",
        )

    monkeypatch.setattr(ThreeWSService, "submit_images", fake_submit)

    image = make_png()
    response = client.post(
        "/api/v1/ai3d/generate",
        files=[
            ("files", ("front.png", image, "image/png")),
            ("files", ("back.png", image, "image/png")),
        ],
        data={
            "tier": "standard",
            "description": "single cup",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["provider"] == "three.ws-image"
    assert body["id"]


def test_ai3d_rejects_more_than_six_views(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "output_dir", str(tmp_path))
    monkeypatch.setattr(settings, "public_base_url", "https://pixel-forge.example")

    image = make_png()
    files = [
        ("files", (f"view-{index}.png", image, "image/png"))
        for index in range(7)
    ]

    response = client.post(
        "/api/v1/ai3d/generate",
        files=files,
        data={"tier": "standard"},
    )
    assert response.status_code == 422


def test_done_without_glb_remains_pollable(monkeypatch):
    record = job_store.create(
        provider="three.ws-image",
        remote_job_id="remote-done-without-url",
        status="queued",
    )

    async def fake_poll(self, remote_job_id):
        return ThreeWSSubmitResponse(
            status="done",
            job_id=remote_job_id,
        )

    monkeypatch.setattr(ThreeWSService, "poll", fake_poll)

    response = client.get(f"/api/v1/jobs/{record.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processing"
    assert body["glb_url"] is None


def test_poll_marks_job_done_only_when_glb_exists(monkeypatch):
    record = job_store.create(
        provider="three.ws-image",
        remote_job_id="remote-with-url",
        status="queued",
    )

    async def fake_poll(self, remote_job_id):
        return ThreeWSSubmitResponse(
            status="done",
            job_id=remote_job_id,
            glb_url="https://example.com/model.glb",
        )

    monkeypatch.setattr(ThreeWSService, "poll", fake_poll)

    response = client.get(f"/api/v1/jobs/{record.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["glb_url"] == "https://example.com/model.glb"


def test_glb_to_stl_conversion():
    mesh = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    glb = mesh.export(file_type="glb")
    stl = _glb_to_stl(glb)

    assert isinstance(stl, bytes)
    assert len(stl) > 84
