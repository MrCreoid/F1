"""Phase 7 proof: the frame store.

The timeline and the camera monitor render images the backend wrote. What matters is
the round trip — a URL on the wire that actually resolves to a JPEG of the right frame —
so these tests follow the `thumbnail_url` the API returns rather than guessing at paths.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import config
from app.extraction import write_thumbnail
from app.main import app

from tests.test_phase1 import jpeg_bytes, write_video


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------- the writer


def test_write_thumbnail_downscales_to_the_configured_width(tmp_path: Path) -> None:
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)

    write_thumbnail(image, tmp_path / "nested" / "0.jpg")

    written = cv2.imread(str(tmp_path / "nested" / "0.jpg"))
    assert written is not None, "no file written"
    assert written.shape[1] == config.THUMB_WIDTH
    # 16:9 preserved, allowing a pixel of rounding.
    assert abs(written.shape[0] - config.THUMB_WIDTH * 1080 / 1920) <= 1


def test_write_thumbnail_does_not_upscale_a_small_frame(tmp_path: Path) -> None:
    write_thumbnail(np.zeros((90, 160, 3), dtype=np.uint8), tmp_path / "small.jpg")

    written = cv2.imread(str(tmp_path / "small.jpg"))
    assert written is not None
    assert written.shape[1] == 160


def test_write_thumbnail_preserves_channel_order(tmp_path: Path) -> None:
    """RGB in, RGB out. Getting this wrong tints every frame blue — the exact colour
    the classifier reads as wet, so the bug would look like a model failure."""
    red_rgb = np.zeros((90, 160, 3), dtype=np.uint8)
    red_rgb[:, :, 0] = 255

    write_thumbnail(red_rgb, tmp_path / "red.jpg")

    bgr = cv2.imread(str(tmp_path / "red.jpg"))
    assert bgr is not None
    blue, green, red = bgr[45, 80]
    assert red > 200 and blue < 60, f"channels swapped: BGR={(blue, green, red)}"


# ---------------------------------------------------------------- the round trip


def test_video_upload_writes_a_thumbnail_per_frame_and_serves_it(
    client: TestClient, tmp_path: Path
) -> None:
    session_id = client.post("/api/sessions", json={"name": "thumbs"}).json()["session_id"]
    video = write_video(tmp_path / "clip.mp4", n_frames=60, fps=30.0)

    client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("clip.mp4", video.read_bytes(), "video/mp4"))],
    )

    states = client.get(f"/api/sessions/{session_id}/states").json()
    assert states, "no states analysed"
    assert all(s["thumbnail_url"] for s in states), "a frame reached the wire with no image"

    for state in states:
        served = client.get(state["thumbnail_url"])
        assert served.status_code == 200, f"{state['thumbnail_url']} did not resolve"
        assert served.headers["content-type"] == "image/jpeg"
        decoded = cv2.imdecode(np.frombuffer(served.content, np.uint8), cv2.IMREAD_COLOR)
        assert decoded is not None, "served bytes are not a readable JPEG"


def test_frame_upload_also_populates_the_store(client: TestClient) -> None:
    """Both ingest paths go through _analyse_and_store, so both must produce images."""
    session_id = client.post("/api/sessions", json={"name": "stills"}).json()["session_id"]

    client.post(
        f"/api/sessions/{session_id}/frames",
        files=[("files", (f"{i}.jpg", jpeg_bytes(), "image/jpeg")) for i in range(3)],
    )

    states = client.get(f"/api/sessions/{session_id}/states").json()
    assert len(states) == 3
    assert all(client.get(s["thumbnail_url"]).status_code == 200 for s in states)


def test_deleting_a_session_removes_its_frames(client: TestClient, tmp_path: Path) -> None:
    """The frame store is outside the database, so the cascade cannot reach it."""
    session_id = client.post("/api/sessions", json={"name": "doomed"}).json()["session_id"]
    video = write_video(tmp_path / "doomed.mp4", n_frames=30, fps=30.0)
    client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("doomed.mp4", video.read_bytes(), "video/mp4"))],
    )
    assert (config.FRAMES_DIR / session_id).exists()

    assert client.delete(f"/api/sessions/{session_id}").status_code == 204

    assert not (config.FRAMES_DIR / session_id).exists()


def test_a_missing_frame_is_a_404_not_a_crash(client: TestClient) -> None:
    assert client.get("/media/no-such-session/0.jpg").status_code == 404
