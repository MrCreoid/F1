"""Every tunable in the backend. No magic numbers anywhere else.

Each constant carries the reasoning for its value, because in six hours nobody
remembers why a threshold is 0.4. Environment overrides exist only where a demo might
need to change behaviour without a code edit.
"""

from __future__ import annotations

import os
from pathlib import Path

import torch

# ---------------------------------------------------------------- paths

BACKEND_ROOT = Path(__file__).resolve().parent.parent

# HF weights live here, never in the user's global ~/.cache. Local-first is deliberate:
# venue Wi-Fi will fail and rate limits during judging would be fatal.
CACHE_DIR = Path(os.getenv("WW_CACHE_DIR", BACKEND_ROOT / ".cache"))

# Everything the app writes at runtime. Overridable so tests never touch dev data.
DATA_DIR = Path(os.getenv("WW_DATA_DIR", BACKEND_ROOT / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"

# Per-frame thumbnails, one directory per session, served read-only at /media. This is
# also the substrate Phase 9's build_dataset.py extracts from — the frames are already
# decoded and downscaled here, so nothing has to re-open the video.
FRAMES_DIR = DATA_DIR / "frames"

# Bundled demo footage. Committed, not generated at runtime: the demo must not depend on
# anything being downloaded or produced on the night.
SAMPLES_DIR = BACKEND_ROOT / "samples"
DATABASE_URL = f"sqlite:///{DATA_DIR / 'whiplash.db'}"

# ---------------------------------------------------------------- model

# Pinned in CLAUDE.md. Never substitute; if it fails to resolve, report and stop.
MODEL_ID = os.getenv("WW_MODEL_ID", "openai/clip-vit-base-patch32")

# The four appearance classes. Ordering is load-bearing: it indexes the prompt tuple,
# the TWI weights (Phase 2), and every probability dict the API returns.
CLASS_NAMES: tuple[str, ...] = ("dry", "damp", "wet", "standing_water")

# Zero-shot prompts, one per class, same order. These are a tunable, not a constant —
# CLIP is sensitive to phrasing, and the README will show the accuracy delta from
# tuning them. "racetrack" rather than "road" anchors the domain; the descriptive
# clause after each noun is what separates damp from wet in embedding space.
PROMPTS: tuple[str, ...] = (
    "a dry asphalt racetrack surface",
    "a damp racetrack with a darkened surface",
    "a wet racetrack surface reflecting light",
    "a racetrack with standing water and visible spray",
)

# Frames per inference batch. 16 keeps peak memory small enough for an 8GB machine
# while still amortising the per-call overhead that dominates at batch size 1.
CLASSIFY_BATCH_SIZE = 16

# Warmup passes at startup. The first forward on mps pays lazy kernel compilation;
# three passes is enough for the timing to settle, measured in Step 0.3.
WARMUP_FRAMES = 3

# ---------------------------------------------------------------- extraction

# Analyses per second of footage. Track conditions change over tens of seconds, so 4fps
# is ample temporal resolution, and it cuts inference work ~7x versus every frame of
# 30fps source. Phase 2's Kalman filter assumes samples arrive at roughly this rate.
SAMPLE_FPS = 4.0

# Longest edge after downscale. CLIP sees 224px, so anything above this is thrown away
# by the processor — but 640 stays useful as a UI thumbnail and for the blur metric in
# Phase 2, which needs more detail than 224 to separate defocus from motion blur.
FRAME_MAX_EDGE = 640

# Hard ceiling per upload: 900 frames at 4fps is 3.75 minutes of footage, longer than
# any demo clip, and bounds worst-case memory and inference time.
MAX_FRAMES_PER_VIDEO = 900

# Upload size limit at the trust boundary. 200MB comfortably holds a few minutes of
# 1080p while refusing anything that would exhaust disk during judging.
MAX_UPLOAD_MB = 200

# Thumbnail width. The camera monitor is ~326 CSS px wide, so 480 stays sharp on a
# retina panel without storing the full 640 the analysis ran on. One size serves both
# the monitor and the timeline filmstrip — two sizes would double the writes to save
# bandwidth that does not exist over localhost.
THUMB_WIDTH = 480

# JPEG quality. 80 is the knee: visually indistinguishable from 95 at this size, and
# roughly a third of the bytes. ~30KB a frame, ~8MB for a 70s clip.
THUMB_QUALITY = 80

# ---------------------------------------------------------------- B.1 wetness index

# Per-class contribution to the Track Wetness Index, same order as CLASS_NAMES.
# Damp is 0.35 rather than 0.33 because a damp line is closer to grip-limited than the
# even spacing suggests; standing water pins the top of the scale at 1.0.
TWI_CLASS_WEIGHTS: tuple[float, ...] = (0.00, 0.35, 0.75, 1.00)

# ---------------------------------------------------------------- B.2 frame quality

# Laplacian variance of a sharp trackside frame. Anything at or above this scores full
# marks for focus; the metric saturates rather than rewarding noise.
BLUR_REFERENCE = 150.0

# Fraction of pixels at 0 or 255 that drives the exposure score to zero. Above ~15%
# clipped, the frame is glare or silhouette and its colour information is gone.
CLIPPING_TOLERANCE = 0.15

# Weights for the geometric mean of (focus, exposure, confidence). Geometric rather than
# arithmetic so one catastrophic factor cannot be averaged away by two good ones.
# Focus and confidence carry more than exposure: a slightly hot frame is still readable,
# an out-of-focus or genuinely ambiguous one is not.
QUALITY_WEIGHTS: tuple[float, float, float] = (0.40, 0.20, 0.40)

# Below this the UI flags the frame as degraded. It is still displayed and still
# analysed, just heavily downweighted — the user must see why the system distrusts it.
QUALITY_FLAG_THRESHOLD = 0.25

# ---------------------------------------------------------------- B.3 kalman

# Process noise spectral density for the constant-velocity model, TWI^2/s^3.
# Measured on a synthetic 10-point step under 3.0 TWI of Gaussian noise at SAMPLE_FPS:
#
#     Q       settle to +/-2  plateau noise std
#     0.005      4.75s            0.85
#     0.02       3.50s            0.86
#     0.05       3.00s            0.89   <- chosen
#     0.3        1.50s            1.06
#     1.0        1.00s            1.19
#
# Every value in that range clears the spec's ~15s target, so the binding constraint is
# noise, not speed. 0.05 sits where settling has stopped improving much but the filter
# still rejects 3 TWI of measurement noise down to 0.9 — responsive enough to watch on
# stage, quiet enough that the curve does not shimmer when nothing is happening.
KALMAN_PROCESS_NOISE = 0.05

# Measurement variance at perfect frame quality, TWI^2. CLIP's frame-to-frame scatter on
# static footage is roughly +/-5 TWI, and 5^2 = 25.
KALMAN_MEASUREMENT_VARIANCE = 25.0

# R scales as MEASUREMENT_VARIANCE / max(quality, floor). The floor caps how far a
# garbage frame can be distrusted — without it, quality 0 divides by zero.
KALMAN_QUALITY_FLOOR = 0.02

# ---------------------------------------------------------------- B.4 / B.5 trend

# Regression window. 45s at 4fps is 180 samples: long enough for a slope to emerge from
# noise, short enough that the trend still reflects the last minute of racing.
TREND_WINDOW_S = 45.0

# TWI/min beyond which the track is genuinely changing rather than shimmering.
TREND_RATE_THRESHOLD = 1.5

# Below this R^2 the slope is not supported by the data, whatever its value. This gate
# is what produces "STABLE — INSUFFICIENT SIGNAL" instead of a confident wrong answer.
TREND_R2_MIN = 0.4

# No projection further out than this. Half an hour is beyond any useful strategy call,
# and extrapolating a linear trend past it is fiction.
CROSSOVER_HORIZON_S = 1800.0

# 95% interval on the OLS slope, for the optimistic/pessimistic edges of the cone.
CROSSOVER_Z = 1.96

# ---------------------------------------------------------------- B.6 pit call

# Compound boundaries on the TWI scale.
COMPOUND_THRESHOLDS: tuple[float, float] = (25.0, 65.0)

# TWI points past a boundary before a change is even considered. Without this the call
# flickers between compounds whenever the index sits on a threshold.
HYSTERESIS_MARGIN = 6.0

# Consecutive analysis windows the margin must hold before the call fires. Three at
# SAMPLE_FPS is under a second of footage — enough to reject a spike, fast enough to
# watch happen on stage.
HYSTERESIS_WINDOWS = 3

# ---------------------------------------------------------------- B.7 weather

# Open-Meteo: free, no API key, so there is no secret to leak and no quota to exhaust
# mid-demo.
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Silverstone. Default only — the client passes real coordinates.
DEFAULT_LAT = 52.0786
DEFAULT_LON = -1.0169

# WW_OFFLINE=1 skips the network entirely and uses the bundled snapshot. Two jobs: it
# keeps the test suite off the internet, and it is the lever to pull when venue Wi-Fi is
# hanging rather than failing — a timeout still costs seconds, a flag costs nothing.
OFFLINE_MODE = os.getenv("WW_OFFLINE", "").strip().lower() in {"1", "true", "yes"}

# Conditions change on a scale of tens of minutes; 10 minutes of cache costs nothing.
WEATHER_CACHE_TTL_S = 600.0

# Per-attempt timeout and retry budget. Total worst case stays under ~10s so a dead
# network degrades to the bundled fallback quickly rather than hanging the request.
WEATHER_TIMEOUT_S = 4.0
WEATHER_RETRIES = 3
WEATHER_BACKOFF_S = 0.5

# Physical drying prior, TWI/min. Baseline is the drying rate of a wet track in still,
# cool, saturated air — nearly nothing. The multipliers below scale it.
DRYING_BASE_RATE = -0.8

# Additional TWI/min of drying at full evaporative forcing (hot, windy, dry, clear).
# Together with the baseline this spans roughly -0.8 to -5.5 TWI/min, which matches the
# order of magnitude of a real track transitioning over 10-20 minutes.
DRYING_FORCING_RATE = -4.7

# TWI/min of wetting per mm/h of rain. 3mm/h is heavy enough to standing-water a track
# inside a few minutes, and 3 * 4.0 = 12 TWI/min gets there.
WETTING_PER_MM_H = 4.0

# ---------------------------------------------------------------- B.8 dataset

# Where scripts/ works. Outside DATA_DIR because the dataset is a deliverable we curate
# and publish, not runtime state the app rewrites.
DATASET_DIR = Path(os.getenv("WW_DATASET_DIR", BACKEND_ROOT.parent / "data"))
SOURCES_DIR = DATASET_DIR / "sources"
BUILD_DIR = DATASET_DIR / "dataset"

# Wikimedia Commons. Their API returns HTTP 403 to a request with no User-Agent, and the
# failure looks like a network fault rather than a policy one — an hour lost the first
# time. The contact address is part of their published requirement, not decoration.
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_USER_AGENT = "WeatherWhiplash/0.1 (hackathon project; pratyushgarg527@gmail.com)"

# Machine-readable licence slugs we are willing to redistribute. Everything here permits
# commercial use and redistribution with attribution; anything not on this list is
# skipped and counted, never silently downgraded. NC and ND are absent deliberately —
# a dataset nobody may reuse is not worth publishing.
ALLOWED_LICENSES: tuple[str, ...] = (
    "cc0",
    "cc-by-1.0", "cc-by-2.0", "cc-by-2.5", "cc-by-3.0", "cc-by-4.0",
    "cc-by-sa-1.0", "cc-by-sa-2.0", "cc-by-sa-2.5", "cc-by-sa-3.0", "cc-by-sa-4.0",
    "pd", "publicdomain",
)

# Curated Commons categories, grouped by the condition each is *expected* to surface.
# These are hints for retrieval only — a category never becomes the label.
#
# Categories rather than free-text search, because Commons search matches the wording of
# a file's description page and not the picture. Measured on a 288-image run, only 36% of
# search results had a road word in the title at all: "wet racetrack" returned a
# passenger's window photographs of a Heathrow-to-LAX flight, and "standing water on
# road" returned a series of Norfolk water towers, matched on "Water" and "standing by".
# Categories are maintained by people and cost the reviewer far less time.
#
# Every name here was verified to contain files. Plausible-sounding ones that are empty —
# Category:Wet asphalt, Category:Tarmac, Category:Dry asphalt — are omitted, so do not
# add a category without checking it first.
SOURCE_CATEGORIES: dict[str, tuple[str, ...]] = {
    "dry": (
        "Category:Asphalt",
        "Category:Asphalt concrete",
        "Category:Road surfaces",
    ),
    "wet": (
        "Category:Wet roads",
        "Category:Wet streets",
        "Category:Reflections in puddles",
    ),
    "standing_water": (
        "Category:Puddles",
        "Category:Flooded roads",
        "Category:Aquaplaning",
    ),
}

# Free-text terms, used only where no category covers the condition. There is no
# "damp roads" category on Commons — damp is the state nobody photographs deliberately,
# which is also why zero-shot CLIP is worst at it and why the dataset is worth building.
SOURCE_QUERIES: dict[str, tuple[str, ...]] = {
    "damp": (
        "damp road surface",
        "drying road surface after rain",
        "drying line racetrack",
    ),
}

# Commons categories carry audio and video too: Category:Puddles holds pronunciation
# recordings of the word "puddle". Anything not in this set is skipped.
IMAGE_EXTENSIONS: tuple[str, ...] = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")

# Files to pull per category or query. 60 is the API's comfortable page size and, across
# the categories above, yields roughly 400 candidates — enough for a linear probe.
SOURCE_PAGE_SIZE = 60

# Long edge of the thumbnail we request from Commons. Matches FRAME_MAX_EDGE so a
# published image is exactly what the model was shown — a dataset whose images differ
# from the pipeline's input is a dataset that documents nothing.
SOURCE_IMAGE_EDGE = FRAME_MAX_EDGE

# Per-attempt timeout and retry budget for Commons, mirroring the weather client.
COMMONS_TIMEOUT_S = 20.0
COMMONS_RETRIES = 3
COMMONS_BACKOFF_S = 1.0

# Pause between downloads. Measured: 0.2s earns HTTP 429 part-way through a full run,
# because requesting a derivative size makes Commons generate the thumbnail rather than
# serve a cached file. 1.0s keeps a ~700-image run inside their limits; the run takes
# about fifteen minutes and is done once.
COMMONS_DELAY_S = 1.0

# A 429 is a rate limit, not a transient fault, so the ordinary backoff is far too
# impatient — retrying two seconds later earns another 429. Waiting this long instead
# turns a lost image into a slow one.
COMMONS_RATE_LIMIT_BACKOFF_S = 30.0

# Candidate frames below this quality never reach the labelling queue. Reviewing a
# blown-out frame costs the same two seconds as reviewing a good one and teaches the
# probe nothing, so the budget goes to frames a human can actually judge. Higher than
# the runtime flag threshold: the app must still *show* a bad frame, but the dataset
# has no reason to contain one.
DATASET_MIN_QUALITY = 0.35

# Hub repo ids. Overridable so a fork does not have to edit code to publish its own.
HF_DATASET_REPO = os.getenv("WW_HF_DATASET", "pratyushgarg/weather-whiplash-surfaces")
HF_MODEL_REPO = os.getenv("WW_HF_MODEL", "pratyushgarg/weather-whiplash-probe")

# ---------------------------------------------------------------- runtime


def resolve_device() -> str:
    """cuda → mps → cpu, with an escape hatch.

    WW_DEVICE=cpu is the mid-demo recovery lever: mps is the fast path here (18.5ms in
    Step 0.3) but is the least battle-tested torch backend, and some ops silently fall
    back to CPU. If output ever looks wrong, force cpu rather than debug on stage.
    """
    override = os.getenv("WW_DEVICE", "").strip().lower()
    if override:
        return override
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
