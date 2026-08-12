"""Pydantic v2 models. The wire contract from docs/SPEC-API.md, verbatim.

TrackState and its children are defined in full here even though Phase 1 only populates
`probabilities`. Defining the contract before either side is written is the point: the
TypeScript client is generated from this, and the UI never computes analysis itself.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AppearanceClass = Literal["dry", "damp", "wet", "standing_water"]
TrendDirection = Literal["DRYING", "WETTING", "STABLE"]
Compound = Literal["SLICK", "INTERMEDIATE", "FULL_WET"]
CallState = Literal["HOLD", "ARMING", "BOX"]


class ClassProbabilities(BaseModel):
    """A full distribution, never an argmax — the spread is the drying signal."""

    dry: float = Field(ge=0.0, le=1.0)
    damp: float = Field(ge=0.0, le=1.0)
    wet: float = Field(ge=0.0, le=1.0)
    standing_water: float = Field(ge=0.0, le=1.0)


class Trend(BaseModel):
    direction: TrendDirection
    rate_per_min: float
    r_squared: float = Field(ge=0.0, le=1.0)
    window_s: float
    sufficient_signal: bool


class Crossover(BaseModel):
    """Null on the wire whenever any gate in SPEC-ANALYSIS B.5 fails. Never fabricated."""

    target_compound: Compound
    threshold: float
    eta_s: float
    eta_optimistic_s: float
    eta_pessimistic_s: float


class Recommendation(BaseModel):
    current: Compound
    next: Compound | None
    state: CallState
    windows_held: int = Field(ge=0)
    windows_required: int = Field(gt=0)
    rationale: str


class FrameQuality(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    blur: float
    clipping: float = Field(ge=0.0, le=1.0)
    entropy: float = Field(ge=0.0, le=1.0)


class Fusion(BaseModel):
    visual_weight: float = Field(ge=0.0, le=1.0)
    weather_weight: float = Field(ge=0.0, le=1.0)
    weather_rate_prior: float


class TrackState(BaseModel):
    """The single object the whole UI renders from."""

    session_id: str
    timestamp: datetime
    twi: float = Field(ge=0.0, le=100.0)
    twi_raw: float = Field(ge=0.0, le=100.0)
    probabilities: ClassProbabilities
    dominant_class: AppearanceClass
    trend: Trend
    crossover: Crossover | None
    recommendation: Recommendation
    frame_quality: FrameQuality
    fusion: Fusion
    frame_index: int
    thumbnail_url: str | None


class FrameClassification(BaseModel):
    """One analysed frame — the history the timeline and the projection chart plot.

    `twi` and `quality_score` are null only for frames stored before the analysis layer
    existed; every frame written since Phase 2 carries them.
    """

    frame_index: int
    t_s: float
    probabilities: ClassProbabilities
    dominant_class: AppearanceClass
    twi: float | None = None
    quality_score: float | None = None


class SessionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source: str | None = Field(default=None, max_length=200)


class SessionSummary(BaseModel):
    session_id: str
    created_at: datetime
    name: str


class SessionDetail(SessionSummary):
    source: str | None
    frames: list[FrameClassification]
    state: TrackState | None


class VideoUploadResponse(BaseModel):
    job_id: str
    frame_count: int
    duration_s: float


class Sample(BaseModel):
    """Bundled demo footage. `story` is what a judge should watch for."""

    id: str
    name: str
    story: str
    duration_s: float


class WeatherResponse(BaseModel):
    """Normalised conditions plus the drying prior derived from them (B.7)."""

    temperature_c: float
    wind_speed_kmh: float
    relative_humidity: float = Field(ge=0.0, le=1.0)
    cloud_cover: float = Field(ge=0.0, le=1.0)
    precipitation_mm_h: float
    source: Literal["open-meteo", "offline-fallback"]
    drying_rate_prior: float
    cache_age_s: float | None


class HealthResponse(BaseModel):
    model_id: str
    mode: Literal["zero-shot", "probe"]
    device: str
    warm: bool
    weather_cache_age_s: float | None
    # Measured on the last warmup pass, so the UI reports this machine's real per-frame
    # cost rather than a number from the README. Null only if warmup has not run.
    warmup_ms: float | None = None
