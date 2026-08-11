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
