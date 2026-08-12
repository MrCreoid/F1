"""B.3 — adaptive smoothing with a 1D constant-velocity Kalman filter.

Not a rolling average. A rolling average lags by half its window exactly when
responsiveness matters, and it has no notion of how much to trust each sample. This
filter gets both: measurement noise scales inversely with frame quality, so a blurry
low-confidence frame barely moves the estimate while a crisp one moves it hard.

The velocity term is the reason for the whole design — it gives trend for free, as a
derivative of the state rather than as a predicted class.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app import config


@dataclass(frozen=True)
class FilterState:
    twi: float
    rate_per_min: float  # NOT per second — every consumer of this reports per minute
    variance: float  # estimate variance of the TWI component, for reference


class KalmanTWI:
    """State is [twi, twi_rate_per_second]. Rate is exposed per minute only."""

    def __init__(
        self,
        *,
        process_noise: float = config.KALMAN_PROCESS_NOISE,
        measurement_variance: float = config.KALMAN_MEASUREMENT_VARIANCE,
        quality_floor: float = config.KALMAN_QUALITY_FLOOR,
    ) -> None:
        self._q = process_noise
        self._r_base = measurement_variance
        self._quality_floor = quality_floor
        self._x = np.zeros(2, dtype=float)
        # Large initial uncertainty so the first measurement dominates rather than
        # being dragged towards the arbitrary zero the filter starts at.
        self._p = np.diag([1e4, 1e2])
        self._initialised = False

    @property
    def twi(self) -> float:
        return float(self._x[0])

    @property
    def rate_per_min(self) -> float:
        return float(self._x[1]) * 60.0

    def update(self, measurement: float, *, dt_s: float, quality: float) -> FilterState:
        if not self._initialised:
            # Seed at the first observation instead of predicting from zero.
            self._x = np.array([measurement, 0.0], dtype=float)
            self._initialised = True
            return FilterState(twi=self.twi, rate_per_min=self.rate_per_min, variance=float(self._p[0, 0]))

        # --- predict: constant velocity over dt
        f = np.array([[1.0, dt_s], [0.0, 1.0]])
        # Continuous white-noise acceleration model. The dt^3/dt^2/dt structure is what
        # keeps position and velocity uncertainty correctly correlated across sample rates.
        q = self._q * np.array(
            [[dt_s**3 / 3.0, dt_s**2 / 2.0],
             [dt_s**2 / 2.0, dt_s]]
        )
        self._x = f @ self._x
        self._p = f @ self._p @ f.T + q

        # --- update: we measure TWI only, so H = [1, 0] and the algebra collapses to
        # indexing. R scales inversely with frame quality: that is the whole adaptive
        # part of "adaptive smoothing".
        r = self._r_base / max(quality, self._quality_floor)
        innovation = measurement - self._x[0]
        s = self._p[0, 0] + r
        gain = self._p[:, 0] / s
        self._x = self._x + gain * innovation
        self._p = self._p - np.outer(gain, self._p[0, :])

        return FilterState(twi=self.twi, rate_per_min=self.rate_per_min, variance=float(self._p[0, 0]))
