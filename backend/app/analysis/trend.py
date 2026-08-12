"""B.4 trend classification and B.5 crossover projection.

Trend is *derived* here, from the time-derivative of the smoothed index. It is never a
predicted class. Appearance ("wet") and trend ("drying") are different axes, and this
module is the entire reason the architecture keeps them apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np

from app import config

Compound = Literal["SLICK", "INTERMEDIATE", "FULL_WET"]
Direction = Literal["DRYING", "WETTING", "STABLE"]


@dataclass(frozen=True)
class TrendResult:
    direction: Direction
    rate_per_min: float
    r_squared: float
    window_s: float
    sufficient_signal: bool
    slope_stderr_per_min: float


@dataclass(frozen=True)
class CrossoverResult:
    target_compound: Compound
    threshold: float
    eta_s: float
    eta_optimistic_s: float
    eta_pessimistic_s: float


def compound_for(twi: float) -> Compound:
    """B.6's bands, needed here too so a projection can name what it is crossing into."""
    low, high = config.COMPOUND_THRESHOLDS
    if twi < low:
        return "SLICK"
    if twi < high:
        return "INTERMEDIATE"
    return "FULL_WET"


def classify_trend(
    times_s: Sequence[float],
    twi: Sequence[float],
    *,
    kalman_rate_per_min: float | None = None,
    window_s: float = config.TREND_WINDOW_S,
) -> TrendResult:
    """OLS over the recent window, cross-checked against the Kalman rate term.

    Two independent estimators of the same quantity. When they disagree about which way
    the track is going, the honest answer is that we do not know — so the trend is
    reported as STABLE with sufficient_signal False rather than picking a winner.
    """
    times = np.asarray(times_s, dtype=float)
    values = np.asarray(twi, dtype=float)

    recent = times >= (times[-1] - window_s)
    times, values = times[recent], values[recent]
    span_s = float(times[-1] - times[0]) if times.size > 1 else 0.0

    if times.size < 3 or np.ptp(times) == 0.0:
        return TrendResult("STABLE", 0.0, 0.0, span_s, False, 0.0)

    slope_per_s, intercept = np.polyfit(times, values, 1)
    predicted = slope_per_s * times + intercept
    ss_res = float(np.sum((values - predicted) ** 2))
    ss_tot = float(np.sum((values - values.mean()) ** 2))
    # A perfectly flat signal has no variance to explain. Calling that a perfect fit is
    # correct: the line explains everything there is, and the slope is zero anyway.
    r_squared = 1.0 if ss_tot == 0.0 else max(0.0, 1.0 - ss_res / ss_tot)

    # Standard error of the OLS slope — the width of the uncertainty cone comes from here.
    residual_variance = ss_res / (times.size - 2)
    stderr_per_s = float(np.sqrt(residual_variance / np.sum((times - times.mean()) ** 2)))

    rate_per_min = float(slope_per_s) * 60.0
    stderr_per_min = stderr_per_s * 60.0

    disagrees = (
        kalman_rate_per_min is not None
        and abs(kalman_rate_per_min) > config.TREND_RATE_THRESHOLD
        and abs(rate_per_min) > config.TREND_RATE_THRESHOLD
        and np.sign(kalman_rate_per_min) != np.sign(rate_per_min)
    )
    sufficient = r_squared >= config.TREND_R2_MIN and not disagrees

    if not sufficient:
        direction: Direction = "STABLE"
    elif rate_per_min < -config.TREND_RATE_THRESHOLD:
        direction = "DRYING"
    elif rate_per_min > config.TREND_RATE_THRESHOLD:
        direction = "WETTING"
    else:
        direction = "STABLE"

    return TrendResult(direction, rate_per_min, r_squared, span_s, sufficient, stderr_per_min)


def project_crossover(
    *,
    twi_now: float,
    trend: TrendResult,
    horizon_s: float = config.CROSSOVER_HORIZON_S,
) -> CrossoverResult | None:
    """B.5 — when the track crosses the next compound boundary, with an honest cone.

    Returns None whenever any gate fails, and the UI renders "NO RELIABLE PROJECTION"
    from that null. Never fabricate a number: this is the answer to "how confident is
    that?", and a made-up ETA loses the question.
    """
    if not trend.sufficient_signal or abs(trend.rate_per_min) <= config.TREND_RATE_THRESHOLD:
        return None

    low, high = config.COMPOUND_THRESHOLDS
    drying = trend.rate_per_min < 0.0
    candidates = [b for b in (low, high) if (b < twi_now if drying else b > twi_now)]
    if not candidates:
        return None  # already past the last boundary in the direction of travel

    threshold = max(candidates) if drying else min(candidates)
    # Name the band we are heading into, not the one we are leaving.
    target = compound_for(threshold - 1e-6) if drying else compound_for(threshold + 1e-6)

    eta_s = (threshold - twi_now) / trend.rate_per_min * 60.0
    if eta_s <= 0.0 or eta_s > horizon_s:
        return None

    # The cone: same crossing computed at the edges of the slope's 95% interval. A faster
    # rate arrives sooner. If the slow edge never reaches the threshold — the interval
    # spans zero, or flips sign — the pessimistic case is "not within the horizon".
    margin = config.CROSSOVER_Z * trend.slope_stderr_per_min
    fast_rate = trend.rate_per_min - margin if drying else trend.rate_per_min + margin
    slow_rate = trend.rate_per_min + margin if drying else trend.rate_per_min - margin

    eta_optimistic = (threshold - twi_now) / fast_rate * 60.0
    slow_eta = (threshold - twi_now) / slow_rate * 60.0 if slow_rate != 0.0 else float("inf")
    eta_pessimistic = horizon_s if slow_eta <= 0.0 or slow_eta > horizon_s else slow_eta

    return CrossoverResult(
        target_compound=target,
        threshold=threshold,
        eta_s=eta_s,
        eta_optimistic_s=max(0.0, eta_optimistic),
        eta_pessimistic_s=eta_pessimistic,
    )
