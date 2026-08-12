"""Phase 10 proof: the surfaces you only meet when something is wrong.

Startup, device selection and error copy. These are the paths nobody exercises until
they are on stage, which is exactly why they get tests rather than a read-through.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------- warmup


def test_health_reports_a_measured_per_frame_cost(client: TestClient) -> None:
    """The UI shows this number. It has to be this machine's, not a constant."""
    body = client.get("/api/health").json()

    assert body["warmup_ms"] is not None
    assert 0.0 < body["warmup_ms"] < 5000.0, "implausible warmup measurement"


def test_health_answers_before_any_session_exists(client: TestClient) -> None:
    """The frontend polls this on a cold start, before anything has been analysed."""
    assert client.get("/api/health").status_code == 200


# ---------------------------------------------------------------- device selection


def test_device_override_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """WW_DEVICE=cpu is the mid-demo recovery lever. If it does not work, there is no
    lever — and mps is the least battle-tested torch backend."""
    monkeypatch.setenv("WW_DEVICE", "cpu")

    assert config.resolve_device() == "cpu"


def test_device_falls_back_without_an_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """cuda → mps → cpu. Never assume the GPU path exists: the demo machine is a Mac."""
    monkeypatch.delenv("WW_DEVICE", raising=False)

    assert config.resolve_device() in {"cuda", "mps", "cpu"}


def test_an_empty_override_does_not_become_a_device_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """`export WW_DEVICE=` in a shell profile must not resolve to the empty string,
    which torch would reject with an error naming neither the cause nor the fix."""
    monkeypatch.setenv("WW_DEVICE", "   ")

    assert config.resolve_device() in {"cuda", "mps", "cpu"}


# ---------------------------------------------------------------- error copy


def test_a_missing_sample_names_the_path_and_a_command_that_exists(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """The old copy sent the user to scripts/build_samples.py, which was never
    committed. An instruction to run a file that does not exist is worse than none."""
    monkeypatch.setattr(config, "SAMPLES_DIR", tmp_path)
    session_id = client.post("/api/sessions", json={"name": "no-samples"}).json()["session_id"]

    response = client.post(f"/api/sessions/{session_id}/sample/drying")

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert "drying.mp4" in detail
    assert "build_samples" not in detail
    assert "git checkout" in detail


def test_an_unknown_sample_is_a_404_naming_it(client: TestClient) -> None:
    session_id = client.post("/api/sessions", json={"name": "unknown"}).json()["session_id"]

    response = client.post(f"/api/sessions/{session_id}/sample/monsoon")

    assert response.status_code == 404
    assert "monsoon" in response.json()["detail"]


def test_an_unreadable_upload_names_the_file(client: TestClient) -> None:
    """Errors name the failure and the fix, never 'Something went wrong'."""
    session_id = client.post("/api/sessions", json={"name": "bad"}).json()["session_id"]

    response = client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("judges-phone-clip.mp4", b"not a video", "video/mp4"))],
    )

    assert response.status_code == 400
    assert "judges-phone-clip.mp4" in response.json()["detail"]


# ---------------------------------------------------------------- upload limits


def test_an_oversized_upload_is_refused_without_being_held_in_memory(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard used to run after `await file.read()`, which made it decorative: a body
    large enough to matter exhausted memory before the 413 it was meant to produce."""
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 1)
    session_id = client.post("/api/sessions", json={"name": "oversize"}).json()["session_id"]
    oversized = b"\0" * (3 * 1024 * 1024)

    response = client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("huge.mp4", oversized, "video/mp4"))],
    )

    assert response.status_code == 413
    assert "1MB" in response.json()["detail"]


def test_a_refused_upload_leaves_no_partial_file(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A half-written file would be picked up by the extractor and fail confusingly."""
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 1)
    session_id = client.post("/api/sessions", json={"name": "partial"}).json()["session_id"]

    client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("huge.mp4", b"\0" * (3 * 1024 * 1024), "video/mp4"))],
    )

    assert list((config.UPLOAD_DIR / session_id).glob("*")) == []


def test_deleting_a_session_removes_its_upload_too(client: TestClient, tmp_path) -> None:
    """The upload is outside the database, like the frame store. Phase 7 cleaned up only
    the frame store, and data/uploads grew without bound."""
    from tests.test_phase1 import write_video

    session_id = client.post("/api/sessions", json={"name": "cleanup"}).json()["session_id"]
    video = write_video(tmp_path / "clip.mp4", n_frames=20, fps=30.0)
    client.post(
        f"/api/sessions/{session_id}/video",
        files=[("file", ("clip.mp4", video.read_bytes(), "video/mp4"))],
    )
    assert (config.UPLOAD_DIR / session_id).exists()

    client.delete(f"/api/sessions/{session_id}")

    assert not (config.UPLOAD_DIR / session_id).exists()


# ---------------------------------------------------------------- confidence floor


def test_a_flat_signal_is_no_evidence_not_perfect_confidence() -> None:
    """A frozen feed produces exactly this input. Returning R^2 1.0 would answer a dead
    camera with maximum confidence, and it was discontinuous: 0.001 of noise on the same
    signal scored 0.004."""
    from app.analysis.trend import classify_trend

    times = [i / 4 for i in range(180)]

    flat = classify_trend(times, [55.0] * 180, kalman_rate_per_min=0.0)

    assert flat.r_squared == 0.0
    assert flat.sufficient_signal is False
    assert flat.direction == "STABLE"


def test_a_flat_signal_and_a_nearly_flat_one_agree() -> None:
    """The discontinuity was the tell: the two must not land at opposite extremes."""
    import random

    from app.analysis.trend import classify_trend

    random.seed(0)
    times = [i / 4 for i in range(180)]

    flat = classify_trend(times, [55.0] * 180, kalman_rate_per_min=0.0)
    almost = classify_trend(
        times, [55.0 + random.gauss(0, 0.001) for _ in range(180)], kalman_rate_per_min=0.0
    )

    assert flat.sufficient_signal == almost.sufficient_signal is False
    assert abs(flat.r_squared - almost.r_squared) < 0.1


def test_a_real_trend_still_passes_the_gate() -> None:
    """The floor must not have made the whole gate unreachable."""
    from app.analysis.trend import classify_trend

    times = [i / 4 for i in range(180)]
    ramp = [80.0 - 0.05 * i for i in range(180)]

    trend = classify_trend(times, ramp, kalman_rate_per_min=-12.0)

    assert trend.sufficient_signal is True
    assert trend.direction == "DRYING"


# ---------------------------------------------------------------- offline


def test_weather_degrades_to_the_bundled_snapshot(client: TestClient) -> None:
    """Rule 4: the venue Wi-Fi will fail. The suite runs WW_OFFLINE=1, so this is the
    path a dead network takes — it must return conditions, not an error."""
    body = client.get("/api/weather").json()

    assert body["source"] == "offline-fallback"
    assert body["drying_rate_prior"] is not None
