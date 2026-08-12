"""FastAPI application. The network boundary between the model and the browser.

The frontend never runs inference; it renders what this returns.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session as OrmSession

from app import config, db
from app.analysis.pipeline import analyse_frames
from app.analysis.weather import cache_age_s, drying_rate_prior, get_weather
from app.classifier import ZeroShotClassifier, dominant_class
from app.extraction import decode_image_bytes, extract_frames
from app.schemas import (
    FrameClassification,
    HealthResponse,
    SessionCreate,
    SessionDetail,
    SessionSummary,
    TrackState,
    VideoUploadResponse,
    WeatherResponse,
)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    classifier = ZeroShotClassifier.load()
    application.state.warmup_ms = classifier.warmup()
    application.state.classifier = classifier
    yield


app = FastAPI(title="Weather Whiplash", version="0.1.0", lifespan=lifespan)

# The Next.js dev server is a different origin. Locked to localhost — this never runs
# anywhere but the demo machine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> OrmSession:
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _load_session(session_id: str, database: OrmSession) -> db.Session:
    record = database.get(db.Session, session_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No session {session_id}")
    return record


def _to_classification(frame: db.Frame) -> FrameClassification:
    state = frame.state or {}
    return FrameClassification(
        frame_index=frame.frame_index,
        t_s=frame.t_s,
        probabilities=frame.probabilities,
        dominant_class=dominant_class(frame.probabilities),
        twi=state.get("twi"),
        quality_score=(state.get("frame_quality") or {}).get("score"),
    )


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    classifier: ZeroShotClassifier = app.state.classifier
    return HealthResponse(
        model_id=classifier.model_id,
        mode="zero-shot",
        device=classifier.device,
        warm=classifier.warm,
        weather_cache_age_s=cache_age_s(),
    )


@app.get("/api/weather", response_model=WeatherResponse)
def weather(lat: float = config.DEFAULT_LAT, lon: float = config.DEFAULT_LON) -> WeatherResponse:
    snapshot = get_weather(lat, lon)
    return WeatherResponse(
        **vars(snapshot),
        drying_rate_prior=drying_rate_prior(snapshot),
        cache_age_s=cache_age_s(),
    )


@app.post("/api/sessions", response_model=SessionSummary)
def create_session(body: SessionCreate, database: OrmSession = Depends(get_db)) -> SessionSummary:
    record = db.Session(name=body.name, source=body.source)
    database.add(record)
    database.commit()
    return SessionSummary(session_id=record.id, created_at=record.created_at, name=record.name)


@app.get("/api/sessions/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, database: OrmSession = Depends(get_db)) -> SessionDetail:
    record = _load_session(session_id, database)
    return SessionDetail(
        session_id=record.id,
        created_at=record.created_at,
        name=record.name,
        source=record.source,
        frames=[_to_classification(f) for f in record.frames],
        state=_latest_state(record),
    )


def _latest_state(record: db.Session) -> TrackState | None:
    """The most recent analysed frame is the session's current state."""
    for frame in reversed(record.frames):
        if frame.state is not None:
            return TrackState.model_validate(frame.state)
    return None


def _analyse_and_store(
    record: db.Session,
    database: OrmSession,
    frames: list[tuple[int, float, object]],
    probabilities: list[dict[str, float]],
) -> list[db.Frame]:
    """Run the temporal stack over a batch and persist a TrackState per frame.

    Each upload is analysed as its own run: the Kalman filter starts fresh rather than
    resuming from the session's stored history, because the earlier frames' images are
    gone by then and quality-weighted filtering needs them. Single-upload sessions —
    every demo path — are unaffected. Phase 4 holds a live filter per session and
    removes the limitation.
    """
    states = analyse_frames(
        session_id=record.id,
        frames=frames,
        probabilities=probabilities,
        weather=get_weather(),
    )
    stored = [
        db.Frame(
            session_id=record.id,
            frame_index=state.frame_index,
            t_s=t_s,
            probabilities=probs,
            state=state.model_dump(mode="json"),
        )
        for state, (_, t_s, _), probs in zip(states, frames, probabilities)
    ]
    database.add_all(stored)
    database.commit()
    return stored


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, database: OrmSession = Depends(get_db)) -> None:
    database.delete(_load_session(session_id, database))
    database.commit()


@app.post("/api/sessions/{session_id}/frames", response_model=list[FrameClassification])
async def upload_frames(
    session_id: str,
    files: list[UploadFile] = File(...),
    database: OrmSession = Depends(get_db),
) -> list[FrameClassification]:
    record = _load_session(session_id, database)
    start_index = len(record.frames)

    images = []
    for upload in files:
        try:
            images.append(decode_image_bytes(await upload.read(), upload.filename or "upload"))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    classifier: ZeroShotClassifier = app.state.classifier
    probabilities = classifier.classify(images)
    frames = [
        (start_index + offset, (start_index + offset) / config.SAMPLE_FPS, image)
        for offset, image in enumerate(images)
    ]
    stored = _analyse_and_store(record, database, frames, probabilities)
    return [_to_classification(f) for f in stored]


@app.post("/api/sessions/{session_id}/video", response_model=VideoUploadResponse)
async def upload_video(
    session_id: str,
    file: UploadFile = File(...),
    database: OrmSession = Depends(get_db),
) -> VideoUploadResponse:
    """Extract and classify synchronously. Phase 4 makes this a real background job."""
    record = _load_session(session_id, database)

    payload = await file.read()
    if len(payload) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Video exceeds {config.MAX_UPLOAD_MB}MB")

    job_id = str(uuid.uuid4())
    destination = config.UPLOAD_DIR / record.id
    destination.mkdir(parents=True, exist_ok=True)
    video_path = destination / f"{job_id}-{file.filename or 'clip.mp4'}"
    video_path.write_bytes(payload)

    try:
        extraction = extract_frames(video_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    classifier: ZeroShotClassifier = app.state.classifier
    probabilities = classifier.classify([f.image for f in extraction.frames])
    _analyse_and_store(
        record,
        database,
        [(f.index, f.t_s, f.image) for f in extraction.frames],
        probabilities,
    )

    return VideoUploadResponse(
        job_id=job_id,
        frame_count=len(extraction.frames),
        duration_s=extraction.duration_s,
    )
