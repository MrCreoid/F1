"""B.1 Track Wetness Index and B.2 frame quality. Per-frame, pure, no history.

Both take a single frame's evidence and return a number. Everything temporal lives
downstream — nothing in this module knows what happened a second ago.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

import cv2
import numpy as np

from app import config


def twi_raw(probabilities: Mapping[str, float]) -> float:
    """B.1 — Track Wetness Index, 0-100, from the whole distribution.

    Never argmax. Argmax discards the information that makes trend detection possible:
    60% wet / 40% damp is meaningfully different from 95% wet, and that difference *is*
    the drying signal. A weighted sum moves smoothly as probability mass shifts; a
    label jumps or sits still.
    """
    return 100.0 * sum(
        weight * probabilities[name]
        for name, weight in zip(config.CLASS_NAMES, config.TWI_CLASS_WEIGHTS)
    )


@dataclass(frozen=True)
class QualityMetrics:
    score: float  # combined, 0-1
    blur: float  # raw Laplacian variance, reported so the UI can show the actual number
    clipping: float  # fraction of pixels at 0 or 255
    entropy: float  # normalised Shannon entropy of the distribution, 0-1
    degraded: bool  # below config.QUALITY_FLAG_THRESHOLD


def _focus_score(gray: np.ndarray) -> tuple[float, float]:
    """Variance of the Laplacian: high for crisp edges, near zero for defocus or spray."""
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    return min(1.0, variance / config.BLUR_REFERENCE), variance


def _exposure_score(gray: np.ndarray) -> tuple[float, float]:
    """Glare off wet asphalt and tunnel exits both destroy the surface texture."""
    clipped = float(np.count_nonzero((gray == 0) | (gray == 255)) / gray.size)
    return max(0.0, 1.0 - clipped / config.CLIPPING_TOLERANCE), clipped


def _confidence_score(probabilities: Mapping[str, float]) -> tuple[float, float]:
    """1 - normalised entropy. A flat distribution means the model does not know."""
    values = [probabilities[name] for name in config.CLASS_NAMES]
    entropy = -sum(p * math.log(p) for p in values if p > 0.0)
    normalised = entropy / math.log(len(config.CLASS_NAMES))
    return max(0.0, 1.0 - normalised), normalised


def frame_quality(image: np.ndarray, probabilities: Mapping[str, float]) -> QualityMetrics:
    """B.2 — how much this frame should be trusted, in [0, 1].

    Weighted geometric mean rather than arithmetic: a frame that is sharp and correctly
    exposed but produces a coin-flip distribution is not a good frame, and averaging
    would hide that. Low scores are never dropped — they are flagged and downweighted,
    so the user can see *why* the system distrusts a moment.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image
    focus, blur_variance = _focus_score(gray)
    exposure, clipped = _exposure_score(gray)
    confidence, entropy = _confidence_score(probabilities)

    weights = config.QUALITY_WEIGHTS
    factors = (focus, exposure, confidence)
    # Geometric mean in log space, guarding log(0) — any zero factor zeroes the score,
    # which is the intended behaviour for a fully blown or fully defocused frame.
    if min(factors) <= 0.0:
        score = 0.0
    else:
        score = math.exp(sum(w * math.log(f) for w, f in zip(weights, factors)) / sum(weights))

    return QualityMetrics(
        score=score,
        blur=blur_variance,
        clipping=clipped,
        entropy=entropy,
        degraded=score < config.QUALITY_FLAG_THRESHOLD,
    )
