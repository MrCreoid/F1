"""The temporal reasoning layer — SPEC-ANALYSIS B.1-B.7.

The intelligence of this project lives here, above the classifier. CLIP says what the
surface looks like; these modules decide what it is doing and what to do about it.
"""

from app.analysis.filter import KalmanTWI
from app.analysis.pipeline import analyse_frames
from app.analysis.signal import frame_quality, twi_raw
from app.analysis.strategy import PitCallController
from app.analysis.trend import classify_trend, compound_for, project_crossover
from app.analysis.weather import drying_rate_prior, fuse_rates, get_weather

__all__ = [
    "KalmanTWI",
    "analyse_frames",
    "classify_trend",
    "compound_for",
    "drying_rate_prior",
    "frame_quality",
    "fuse_rates",
    "get_weather",
    "project_crossover",
    "twi_raw",
    "PitCallController",
]
