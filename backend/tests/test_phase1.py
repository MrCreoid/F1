"""Phase 1 proof: frame extraction, the classifier interface, and the HTTP surface.

The classifier tests deliberately do not assert *which* class wins on a given image —
zero-shot dry-vs-damp is known-weak (docs/STATE.md) and an accuracy assertion here would
be a flaky test dressed up as a guarantee. They assert the interface contract instead:
a valid distribution, determinism, batch-invariance, and numerical agreement with
CLIP's own single-shot path.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import config
from app.classifier import ZeroShotClassifier
from app.extraction import extract_frames, load_image_sequence
from app.main import app


# ---------------------------------------------------------------- fixtures


def write_video(path: Path, *, n_frames: int = 60, fps: float = 30.0, size: tuple[int, int] = (320, 240)) -> Path:
    """Synthetic clip: a horizontal brightness ramp over time, so frames differ."""
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    assert writer.isOpened(), "cv2 could not open an mp4v writer"
    for i in range(n_frames):
        frame = np.full((size[1], size[0], 3), int(255 * i / max(1, n_frames - 1)), dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def jpeg_bytes(color: tuple[int, int, int] = (90, 90, 95), size: tuple[int, int] = (320, 240)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Real app with real lifespan — this loads and warms the actual CLIP weights once."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def clf(client: TestClient) -> ZeroShotClassifier:
    return app.state.classifier


# ---------------------------------------------------------------- extraction


def test_extract_frames_samples_at_the_configured_rate(tmp_path: Path) -> None:
    video = write_video(tmp_path / "ramp.mp4", n_frames=60, fps=30.0)

    result = extract_frames(video, target_fps=4.0)

    assert result.source_fps == pytest.approx(30.0, abs=0.1)
    assert result.sample_step == 8  # 30fps / 4fps target, rounded
    assert len(result.frames) == math.ceil(result.source_frame_count / result.sample_step)
    assert [f.index for f in result.frames] == list(range(0, result.source_frame_count, 8))


def test_extract_frames_reports_wall_clock_timestamps(tmp_path: Path) -> None:
    video = write_video(tmp_path / "ramp.mp4", n_frames=60, fps=30.0)

    result = extract_frames(video, target_fps=4.0)

    assert result.duration_s == pytest.approx(2.0, abs=0.1)
    assert result.frames[0].t_s == pytest.approx(0.0, abs=1e-6)
    assert result.frames[1].t_s == pytest.approx(8 / 30.0, abs=1e-3)
    assert [f.t_s for f in result.frames] == sorted(f.t_s for f in result.frames)


def test_extract_frames_honours_the_frame_cap(tmp_path: Path) -> None:
    video = write_video(tmp_path / "long.mp4", n_frames=200, fps=30.0)

    result = extract_frames(video, target_fps=30.0, max_frames=5)

    assert len(result.frames) == 5


def test_extract_frames_downscales_to_the_configured_long_edge(tmp_path: Path) -> None:
    video = write_video(tmp_path / "big.mp4", n_frames=4, fps=30.0, size=(1920, 1080))

    result = extract_frames(video, target_fps=30.0)

    height, width = result.frames[0].image.shape[:2]
    assert max(width, height) == config.FRAME_MAX_EDGE
    assert width / height == pytest.approx(1920 / 1080, abs=0.01)


def test_extract_frames_names_the_file_it_could_not_open(tmp_path: Path) -> None:
    missing = tmp_path / "not-here.mp4"

    with pytest.raises(ValueError) as excinfo:
        extract_frames(missing, target_fps=4.0)

    assert "not-here.mp4" in str(excinfo.value)


def test_extract_frames_rejects_a_file_that_is_not_video(tmp_path: Path) -> None:
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"this is not an mp4")

    with pytest.raises(ValueError):
        extract_frames(junk, target_fps=4.0)


def test_load_image_sequence_preserves_order_and_downscales(tmp_path: Path) -> None:
    paths = []
    for i, color in enumerate([(10, 10, 10), (120, 120, 120), (240, 240, 240)]):
        p = tmp_path / f"{i}.jpg"
        Image.new("RGB", (1600, 900), color).save(p)
        paths.append(p)

    frames = load_image_sequence(paths)

    assert [f.index for f in frames] == [0, 1, 2]
    assert max(frames[0].image.shape[:2]) == config.FRAME_MAX_EDGE
    assert frames[0].image[0, 0, 0] < frames[2].image[0, 0, 0]  # RGB order, ascending brightness


# ---------------------------------------------------------------- classifier


def test_classify_returns_a_probability_distribution_over_the_four_classes(clf: ZeroShotClassifier) -> None:
    probs = clf.classify([Image.new("RGB", (320, 240), (70, 70, 74))])[0]

    assert list(probs) == list(config.CLASS_NAMES)
    assert all(0.0 <= p <= 1.0 for p in probs.values())
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-5)


def test_classify_is_deterministic(clf: ZeroShotClassifier) -> None:
    image = Image.new("RGB", (320, 240), (70, 70, 74))

    first = clf.classify([image])[0]
    second = clf.classify([image])[0]

    assert first == pytest.approx(second, abs=1e-6)


def test_classify_batches_without_changing_per_image_results(clf: ZeroShotClassifier) -> None:
    a = Image.new("RGB", (320, 240), (30, 30, 34))
    b = Image.new("RGB", (320, 240), (200, 200, 195))

    batched = clf.classify([a, b])
    singly = [clf.classify([a])[0], clf.classify([b])[0]]

    for got, want in zip(batched, singly):
        assert got == pytest.approx(want, abs=1e-5)


def test_classify_matches_clips_own_single_shot_path(clf: ZeroShotClassifier) -> None:
    """Guards the Phase 1 rewrite: precomputed text embeddings must not shift calibration.

    Phase 0 measured latency with processor(text=..., images=...) in one call. Phase 1
    caches the text embeddings and does the logit_scale softmax by hand. If those two
    disagree, every downstream TWI is silently miscalibrated.
    """
    from transformers import CLIPModel, CLIPProcessor

    image = Image.new("RGB", (320, 240), (70, 70, 74))
    model = CLIPModel.from_pretrained(config.MODEL_ID, cache_dir=str(config.CACHE_DIR)).eval()
    processor = CLIPProcessor.from_pretrained(config.MODEL_ID, cache_dir=str(config.CACHE_DIR))
    inputs = processor(text=list(config.PROMPTS), images=image, return_tensors="pt", padding=True)
    import torch

    with torch.no_grad():
        reference = model(**inputs).logits_per_image.softmax(dim=1)[0].tolist()

    got = clf.classify([image])[0]

    assert list(got.values()) == pytest.approx(reference, abs=1e-3)


def test_warmup_reports_a_real_per_frame_measurement(clf: ZeroShotClassifier) -> None:
    ms = clf.warmup()

    assert ms > 0.0
    assert clf.warm is True


# ---------------------------------------------------------------- http surface


def test_health_reports_the_pinned_model_and_resolved_device(client: TestClient) -> None:
    body = client.get("/api/health").json()

    assert body["model_id"] == "openai/clip-vit-base-patch32"
    assert body["device"] in {"cuda", "mps", "cpu"}
    assert body["mode"] == "zero-shot"
    assert body["warm"] is True
    assert body["weather_cache_age_s"] is None  # no weather layer until Phase 2


def test_session_lifecycle_create_read_delete(client: TestClient) -> None:
    created = client.post("/api/sessions", json={"name": "Spa FP2"}).json()

    fetched = client.get(f"/api/sessions/{created['session_id']}").json()
    assert fetched["name"] == "Spa FP2"
    assert fetched["frames"] == []
    assert fetched["state"] is None

    assert client.delete(f"/api/sessions/{created['session_id']}").status_code == 204
    assert client.get(f"/api/sessions/{created['session_id']}").status_code == 404


def test_unknown_session_is_a_404_not_a_500(client: TestClient) -> None:
    assert client.get("/api/sessions/does-not-exist").status_code == 404


def test_frames_upload_classifies_every_image_and_persists_them(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"name": "frames"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/frames",
        files=[
            ("files", ("a.jpg", jpeg_bytes((40, 40, 44)), "image/jpeg")),
            ("files", ("b.jpg", jpeg_bytes((210, 210, 205)), "image/jpeg")),
        ],
    )

    assert response.status_code == 200
    results = response.json()
    assert [r["frame_index"] for r in results] == [0, 1]
    assert sum(results[0]["probabilities"].values()) == pytest.approx(1.0, abs=1e-5)

    history = client.get(f"/api/sessions/{session_id}").json()["frames"]
    assert len(history) == 2


def test_frames_upload_rejects_a_file_that_is_not_an_image(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"name": "bad-frames"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/frames",
        files=[("files", ("notes.txt", b"not an image", "text/plain"))],
    )

    assert response.status_code == 400
    assert "notes.txt" in response.json()["detail"]


def test_video_upload_reports_extraction_counts(client: TestClient, tmp_path: Path) -> None:
    session_id = client.post("/api/sessions", json={"name": "video"}).json()["session_id"]
    video = write_video(tmp_path / "clip.mp4", n_frames=60, fps=30.0)

    response = client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("clip.mp4", video.read_bytes(), "video/mp4"))],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["frame_count"] == 8  # 60 frames @30fps sampled at 4fps
    assert body["duration_s"] == pytest.approx(2.0, abs=0.1)
    assert body["job_id"]


def test_video_upload_rejects_an_unreadable_file(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"name": "bad-video"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("broken.mp4", b"definitely not a video", "video/mp4"))],
    )

    assert response.status_code == 400
