"""Wires B.1-B.7 into a session: frames in, full TrackState history out.

This is the only place the analysis modules meet. Each of them stays pure and
independently testable; the sequencing lives here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

import numpy as np

from app import config
from app.analysis.filter import KalmanTWI
from app.analysis.signal import frame_quality, twi_raw
from app.analysis.strategy import PitCallController
from app.analysis.trend import TrendResult, classify_trend, compound_for, project_crossover
from app.analysis.weather import WeatherSnapshot, drying_rate_prior, fuse_rates
from app.schemas import (
    ClassProbabilities,
    Crossover,
    FrameQuality,
    Fusion,
    Recommendation,
    TrackState,
    Trend,
)

# (source frame index, seconds from clip start, RGB image)
FrameInput = tuple[int, float, np.ndarray]


def analyse_frames(
    *,
    session_id: str,
    frames: Sequence[FrameInput],
    probabilities: Sequence[dict[str, float]],
    weather: WeatherSnapshot | None,
    started_at: datetime | None = None,
) -> list[TrackState]:
    """Run the full temporal stack over an ordered batch of classified frames."""
    if len(frames) != len(probabilities):
        raise ValueError(f"{len(frames)} frames but {len(probabilities)} probability sets")

    base_time = started_at or datetime.now(timezone.utc)
    kalman = KalmanTWI()
    controller: PitCallController | None = None
    rate_prior = drying_rate_prior(weather) if weather is not None else 0.0

    times: list[float] = []
    filtered: list[float] = []
    qualities: list[float] = []
    states: list[TrackState] = []

    for (frame_index, t_s, image), probs in zip(frames, probabilities):
        quality = frame_quality(image, probs)
        dt_s = t_s - times[-1] if times else 1.0 / config.SAMPLE_FPS
        estimate = kalman.update(twi_raw(probs), dt_s=max(dt_s, 1e-6), quality=quality.score)

        # The filter is unbounded by construction; the index is not. Clamping here keeps
        # a transient overshoot from becoming an impossible reading on the wire.
        twi = float(np.clip(estimate.twi, 0.0, 100.0))
        times.append(t_s)
        filtered.append(twi)
        qualities.append(quality.score)

        visual_trend = classify_trend(times, filtered, kalman_rate_per_min=estimate.rate_per_min)

        # B.7: blend the visual rate with the physical prior by how much the recent
        # footage can be trusted. With no weather available the camera carries it alone.
        window_qualities = qualities[-_window_samples(times) :]
        visual_weight = float(np.mean(window_qualities)) if weather is not None else 1.0
        fused_rate = fuse_rates(
            rate_visual=visual_trend.rate_per_min, rate_prior=rate_prior, visual_weight=visual_weight
        )
        fused_trend = _with_rate(visual_trend, fused_rate)

        if controller is None:
            # Start from what the track actually is, not an arbitrary default.
            controller = PitCallController(initial=compound_for(twi))
        call = controller.update(twi)
        crossover = project_crossover(twi_now=twi, trend=fused_trend)

        states.append(
            TrackState(
                session_id=session_id,
                timestamp=base_time + timedelta(seconds=t_s),
                twi=twi,
                twi_raw=float(np.clip(twi_raw(probs), 0.0, 100.0)),
                probabilities=ClassProbabilities(**probs),
                dominant_class=max(probs, key=lambda name: probs[name]),
                trend=Trend(
                    direction=fused_trend.direction,
                    rate_per_min=fused_trend.rate_per_min,
                    r_squared=fused_trend.r_squared,
                    window_s=fused_trend.window_s,
                    sufficient_signal=fused_trend.sufficient_signal,
                ),
                crossover=None if crossover is None else Crossover(**vars(crossover)),
                recommendation=Recommendation(
                    current=call.current,
                    next=call.next,
                    state=call.state,
                    windows_held=call.windows_held,
                    windows_required=call.windows_required,
                    rationale=call.rationale,
                ),
                frame_quality=FrameQuality(
                    score=quality.score,
                    blur=quality.blur,
                    clipping=quality.clipping,
                    entropy=quality.entropy,
                ),
                fusion=Fusion(
                    visual_weight=visual_weight,
                    weather_weight=1.0 - visual_weight,
                    weather_rate_prior=rate_prior,
                ),
                frame_index=frame_index,
                thumbnail_url=None,  # written in Phase 7, when the timeline needs it
            )
        )

    return states


def _window_samples(times: Sequence[float]) -> int:
    """How many of the most recent samples fall inside the trend window."""
    cutoff = times[-1] - config.TREND_WINDOW_S
    return max(1, sum(1 for t in times if t >= cutoff))


def _with_rate(trend: TrendResult, rate_per_min: float) -> TrendResult:
    """Re-derive the direction after fusion — the blended rate may sit on the other side
    of the threshold from the visual one, and the label has to follow the number it shows."""
    if not trend.sufficient_signal:
        direction = "STABLE"
    elif rate_per_min < -config.TREND_RATE_THRESHOLD:
        direction = "DRYING"
    elif rate_per_min > config.TREND_RATE_THRESHOLD:
        direction = "WETTING"
    else:
        direction = "STABLE"

    return TrendResult(
        direction=direction,
        rate_per_min=rate_per_min,
        r_squared=trend.r_squared,
        window_s=trend.window_s,
        sufficient_signal=trend.sufficient_signal,
        slope_stderr_per_min=trend.slope_stderr_per_min,
    )
