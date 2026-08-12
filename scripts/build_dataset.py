#!/usr/bin/env python
"""Turn a pile of source images into a reviewable labelling queue.

Source-agnostic on purpose: point it at the Commons download, at the app's own frame
store, or at a directory of your own footage — stills and video both. Whatever the
input, the output is one flat set of candidate frames plus a manifest.

CLIP proposes a label for every frame. That proposal is recorded as `auto_label` and
never overwritten, so the published card can state exactly how many frames a human
changed. `label` starts null. A frame nobody has looked at is not a labelled frame, and
counting it as one would be the quiet lie that makes a dataset worthless.

    ../.venv/bin/python scripts/build_dataset.py
    ../.venv/bin/python scripts/build_dataset.py --source backend/data/frames --limit 400
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from app import config  # noqa: E402
from app.analysis.signal import frame_quality  # noqa: E402
from app.classifier import ZeroShotClassifier  # noqa: E402
from app.extraction import extract_frames, write_thumbnail  # noqa: E402

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


@dataclass
class Candidate:
    """One frame awaiting review."""

    id: str
    file: str  # relative to the manifest, so the labelling page can just load it
    origin: str  # the source file this came from
    auto_label: str  # CLIP's proposal, never overwritten
    auto_confidence: float
    probabilities: dict[str, float]
    quality: float
    query_hint: str | None  # what the search expected; never treated as truth
    label: str | None  # set by a human, and only by a human


def _read_rgb(path: Path) -> np.ndarray | None:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if bgr is None else cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def collect(source: Path) -> list[tuple[str, np.ndarray, str | None]]:
    """Every readable frame under `source`, as (origin, RGB image, query hint).

    Videos are sampled through the app's own extractor, so a frame that reaches the
    dataset is identical to a frame that reaches the classifier at runtime.
    """
    hints: dict[str, str] = {}
    attribution = source / "attribution.json"
    # A directory with an attribution file is a fetched corpus, and everything in it is
    # expected to be accounted for. A directory without one is own footage, where there
    # is nobody to credit. The distinction decides how an unlisted file is treated.
    fetched = attribution.exists()
    if fetched:
        hints = {
            record["file_name"]: record["query_hint"]
            for record in json.loads(attribution.read_text())
        }

    found: list[tuple[str, np.ndarray, str | None]] = []
    orphans: list[str] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            if fetched and path.name not in hints:
                # Left behind by an interrupted fetch: on disk, but with no licence
                # recorded. Indistinguishable from unlicensed content, so it does not
                # get to enter a dataset we intend to publish.
                orphans.append(path.name)
                continue
            image = _read_rgb(path)
            if image is not None:
                found.append((path.name, image, hints.get(path.name)))
        elif suffix in VIDEO_SUFFIXES:
            try:
                extraction = extract_frames(path)
            except ValueError as exc:
                print(f"  skip {path.name}: {exc}")
                continue
            # A clip contributes a spread of moments, not 300 near-identical ones.
            step = max(1, len(extraction.frames) // 24)
            for frame in extraction.frames[::step]:
                found.append((f"{path.name}#{frame.index}", frame.image, hints.get(path.name)))

    if orphans:
        print(
            f"  {len(orphans)} images skipped: on disk with no attribution record.\n"
            f"  Re-run scripts/fetch_sources.py to record them, or delete them."
        )
    return found


def build(source: Path, out: Path, limit: int | None) -> list[Candidate]:
    frames = collect(source)
    if not frames:
        raise SystemExit(f"No readable images or video under {source}")
    if limit:
        frames = frames[:limit]
    print(f"{len(frames)} candidate frames from {source}")

    classifier = ZeroShotClassifier.load()
    print(f"classifying on {classifier.device} …")
    probabilities = classifier.classify([image for _, image, _ in frames])

    images_dir = out / "images"
    if images_dir.exists():
        shutil.rmtree(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[Candidate] = []
    dropped = 0
    for index, ((origin, image, hint), probs) in enumerate(zip(frames, probabilities)):
        quality = frame_quality(image, probs)
        if quality.score < config.DATASET_MIN_QUALITY:
            # Reviewing a blown-out frame costs the same as reviewing a good one and
            # teaches the probe nothing. The runtime still shows bad frames; the
            # dataset has no reason to contain them.
            dropped += 1
            continue

        identifier = f"{index:05d}"
        write_thumbnail(image, images_dir / f"{identifier}.jpg")
        top = max(probs, key=lambda name: probs[name])
        candidates.append(
            Candidate(
                id=identifier,
                file=f"images/{identifier}.jpg",
                origin=origin,
                auto_label=top,
                auto_confidence=round(probs[top], 4),
                probabilities={k: round(v, 4) for k, v in probs.items()},
                quality=round(quality.score, 4),
                query_hint=hint,
                label=None,
            )
        )

    (out / "manifest.json").write_text(
        json.dumps([asdict(c) for c in candidates], indent=2) + "\n"
    )
    # The labelling page is opened straight off disk, and a browser will not fetch a
    # sibling JSON over file://. A script tag will, so the manifest ships as both.
    (out / "manifest.js").write_text(
        "window.MANIFEST = " + json.dumps([asdict(c) for c in candidates]) + ";\n"
    )

    print(f"{len(candidates)} queued · {dropped} dropped below quality {config.DATASET_MIN_QUALITY}")
    print(f"manifest → {out / 'manifest.json'}")
    print(f"\nNow label them:  open {out / 'label_tool.html'}")
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=config.SOURCES_DIR)
    parser.add_argument("--out", type=Path, default=config.BUILD_DIR)
    parser.add_argument("--limit", type=int, default=None, help="cap candidates, for a quick pass")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    build(args.source, args.out, args.limit)

    tool = Path(__file__).resolve().parent / "label_tool.html"
    if tool.exists():
        shutil.copy(tool, args.out / "label_tool.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
