"""Frame extraction via OpenCV. Video files and image sequences, one shape of output.

Images come out as RGB uint8 arrays — OpenCV is BGR internally, and getting that
conversion wrong would tint every frame blue, which CLIP would happily classify as wet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from app import config


@dataclass(frozen=True)
class ExtractedFrame:
    index: int  # index in the source, not in the sampled output
    t_s: float  # seconds from the start of the clip
    image: np.ndarray  # RGB uint8, longest edge <= config.FRAME_MAX_EDGE


@dataclass(frozen=True)
class Extraction:
    frames: list[ExtractedFrame]
    source_fps: float
    source_frame_count: int
    duration_s: float
    sample_step: int


def _downscale(image: np.ndarray, max_edge: int = config.FRAME_MAX_EDGE) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_edge:
        return image
    scale = max_edge / longest
    # INTER_AREA is the correct choice for shrinking; INTER_LINEAR aliases and would
    # add high-frequency noise to the Phase 2 blur metric.
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def extract_frames(
    path: Path | str,
    *,
    target_fps: float = config.SAMPLE_FPS,
    max_frames: int = config.MAX_FRAMES_PER_VIDEO,
) -> Extraction:
    """Sample a video down to roughly `target_fps`.

    Raises ValueError naming the file if it cannot be opened or contains no frames —
    the UI shows that message directly, so it has to identify what failed.
    """
    path = Path(path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Could not open video: {path.name}")

    try:
        source_fps = float(capture.get(cv2.CAP_PROP_FPS))
        # Some containers report 0 or NaN. Assume the sample rate rather than divide by
        # zero — a wrong-but-sane timebase beats a crash on a judge's phone clip.
        if not source_fps or not np.isfinite(source_fps):
            source_fps = config.SAMPLE_FPS
        sample_step = max(1, round(source_fps / target_fps))

        frames: list[ExtractedFrame] = []
        index = 0
        while len(frames) < max_frames:
            ok, bgr = capture.read()
            if not ok:
                break
            if index % sample_step == 0:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                frames.append(ExtractedFrame(index=index, t_s=index / source_fps, image=_downscale(rgb)))
            index += 1
    finally:
        capture.release()

    if not frames:
        raise ValueError(f"No readable frames in: {path.name}")

    return Extraction(
        frames=frames,
        source_fps=source_fps,
        source_frame_count=index,
        duration_s=index / source_fps,
        sample_step=sample_step,
    )


def load_image_sequence(paths: Sequence[Path | str]) -> list[ExtractedFrame]:
    """An ordered burst of stills. Timestamps assume they were shot at SAMPLE_FPS."""
    frames: list[ExtractedFrame] = []
    for i, path in enumerate(paths):
        path = Path(path)
        bgr = cv2.imread(str(path))
        if bgr is None:
            raise ValueError(f"Could not read image: {path.name}")
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        frames.append(ExtractedFrame(index=i, t_s=i / config.SAMPLE_FPS, image=_downscale(rgb)))
    return frames


def write_thumbnail(image: np.ndarray, path: Path) -> None:
    """Write one RGB frame as a JPEG for the UI to display.

    The image arrives RGB from extraction and cv2 writes BGR, so the conversion back is
    mandatory — skip it and every thumbnail is blue, which is exactly the tint the
    classifier calls wet.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    scale = config.THUMB_WIDTH / image.shape[1]
    small = (
        image
        if scale >= 1.0
        else cv2.resize(
            image,
            (config.THUMB_WIDTH, max(1, round(image.shape[0] * scale))),
            interpolation=cv2.INTER_AREA,
        )
    )
    cv2.imwrite(
        str(path),
        cv2.cvtColor(small, cv2.COLOR_RGB2BGR),
        [cv2.IMWRITE_JPEG_QUALITY, config.THUMB_QUALITY],
    )


def decode_image_bytes(data: bytes, name: str) -> np.ndarray:
    """Decode an uploaded image. Raises ValueError naming the file if it isn't one."""
    bgr = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Not a readable image: {name}")
    return _downscale(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
