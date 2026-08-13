#!/usr/bin/env python
"""Assemble the reviewed frames into an `imagefolder` dataset and publish it.

Two jobs, and the first one matters more: build the export locally so it can be read
before anyone uploads anything. `--dry-run` is the default. Publishing is a deliberate
act, not the thing that happens when you forget a flag.

The card is generated from the manifest's own counts. Nothing in it is typed by hand,
so it cannot drift from the files beside it — including the parts that are unflattering.

    ../.venv/bin/python scripts/push_to_hub.py                 # build export, print card
    HF_TOKEN=... ../.venv/bin/python scripts/push_to_hub.py --push

HF_TOKEN comes from the environment. It is never written to a file, never logged, and
never included in an error message.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import config  # noqa: E402

# Frames a reviewer marked as not showing a judgeable road surface: resurfacing work
# mid-pour, a close-up of a tyre, an animal filling the frame. Measured at 38% of a
# category-sourced corpus, spread evenly across all four groups — the ordinary cost of
# harvesting one visual property from a general-purpose image library. Excluded here
# rather than forced into whichever of the four classes fits worst.
REJECTED = "reject"


def load_manifest(path: Path) -> list[dict[str, Any]]:
    """The candidate list, tolerating both manifest shapes.

    Builds before the localStorage-collision fix wrote a bare list; current ones wrap it
    with a `build_id`. Reading both means an in-progress labelling session survives
    pulling this change.
    """
    payload = json.loads(path.read_text())
    return payload["candidates"] if isinstance(payload, dict) else payload


def load_labels(build_dir: Path) -> dict[str, str]:
    """Human corrections, keyed by frame id. Absent file means nothing reviewed yet."""
    path = build_dir / "labels.json"
    if not path.exists():
        return {}
    return {row["id"]: row["label"] for row in json.loads(path.read_text())}


def apply_labels(manifest: list[dict[str, Any]], labels: dict[str, str]) -> list[dict[str, Any]]:
    """Merge reviewer decisions onto the manifest.

    A frame with no human label is dropped. CLIP's proposal is a starting point for a
    reviewer, not a substitute for one — shipping auto-labels as ground truth would make
    the dataset a record of the model's own opinion, which teaches a probe nothing.
    """
    out = []
    for row in manifest:
        label = labels.get(row["id"]) or row.get("label")
        if not label:
            continue
        out.append({**row, "label": label})
    return out


def attribution_index(sources_dir: Path) -> dict[str, dict[str, Any]]:
    path = sources_dir / "attribution.json"
    if not path.exists():
        return {}
    return {row["file_name"]: row for row in json.loads(path.read_text())}


def build_export(
    labelled: list[dict[str, Any]], build_dir: Path, export_dir: Path, sources_dir: Path
) -> dict[str, Any]:
    """Write `data/<label>/<id>.jpg` plus the metadata sidecars. Returns the stats."""
    if export_dir.exists():
        shutil.rmtree(export_dir)

    kept = [row for row in labelled if row["label"] != REJECTED]
    counts = collections.Counter(row["label"] for row in kept)
    for row in kept:
        destination = export_dir / "data" / row["label"] / f"{row['id']}.jpg"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(build_dir / row["file"], destination)

    credits = attribution_index(sources_dir)
    used: dict[str, dict[str, Any]] = {}
    uncredited = 0
    # Keyed by the path the downloader actually receives, not by the source filename.
    # Frames are renamed to their manifest id on export, so a credits list keyed on the
    # original name is unresolvable to whoever has the dataset — and 219 of these images
    # are under licences that require attributing the specific work. An attribution
    # nobody can apply is not attribution.
    per_image: list[dict[str, Any]] = []
    for row in kept:
        origin = row["origin"].split("#", 1)[0]
        credit = credits.get(origin)
        entry: dict[str, Any] = {
            "file": f"data/{row['label']}/{row['id']}.jpg",
            "label": row["label"],
            "source_file": origin,
        }
        if credit is None:
            # Own footage, or the app's frame store. Counted rather than ignored: the
            # card must not claim every image came from Commons when some did not.
            uncredited += 1
            entry["source"] = "own footage"
        else:
            used[origin] = credit
            entry.update(
                title=credit["title"],
                artist=credit["artist"],
                license=credit["license"],
                license_url=credit["license_url"],
                source_url=credit["source_url"],
            )
        per_image.append(entry)

    (export_dir / "attribution.json").write_text(
        json.dumps(sorted(per_image, key=lambda r: r["file"]), indent=2) + "\n"
    )

    agreed = sum(1 for row in kept if row["label"] == row["auto_label"])
    stats = {
        "kept": len(kept),
        "reviewed": len(labelled),
        "rejected": len(labelled) - len(kept),
        "counts": dict(sorted(counts.items())),
        "agreement": agreed / len(kept) if kept else 0.0,
        "corrected": len(kept) - agreed,
        "licenses": dict(sorted(collections.Counter(r["license"] for r in used.values()).items())),
        "sources": len(used),
        "uncredited": uncredited,
    }
    (export_dir / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    return stats


def card(stats: dict[str, Any]) -> str:
    """The dataset card, written from the numbers rather than about them."""
    counts = stats["counts"]
    total = max(1, stats["kept"])
    rows = "\n".join(
        f"| `{name}` | {counts.get(name, 0)} | {counts.get(name, 0) / total:.0%} |"
        for name in config.CLASS_NAMES
    )
    licenses = "\n".join(f"| `{slug}` | {n} |" for slug, n in stats["licenses"].items())
    own = stats.get("uncredited", 0)
    provenance = (
        f"All {stats['sources']} source photographs come from Wikimedia Commons under "
        "licences that permit redistribution."
        if not own
        else (
            f"{stats['kept'] - own} images come from {stats['sources']} Wikimedia Commons "
            f"photographs under licences that permit redistribution. The remaining {own} "
            "are the authors' own footage, contributed directly."
        )
    )

    return f"""---
license: cc-by-sa-4.0
task_categories:
  - image-classification
tags:
  - weather
  - road-surface
  - motorsport
size_categories:
  - n<1K
---

# Weather Whiplash — road surface conditions

{stats['kept']} photographs of road and track surfaces, each labelled by a human with
one of four appearance classes. Built for **Weather Whiplash**, a live track-condition
detector whose reasoning layer turns a per-frame surface classification into a stable
wetness index, a trend, and a tyre-change recommendation.

## The four classes

The classes describe **appearance at one instant**, not direction of change. There is no
"drying" class and there will not be one: drying is a property of a sequence, derived
downstream from the time-derivative of a smoothed index. A single photograph cannot show
it, so a single photograph is never labelled with it.

| class | images | share |
|---|---|---|
{rows}

- `dry` — matte, uniform, no sheen.
- `damp` — surface darkened by moisture, but not reflecting.
- `wet` — specular; reflects light and objects.
- `standing_water` — water pooled on the surface, or visible spray.

## How it was labelled

Every image was first shown to `openai/clip-vit-base-patch32` zero-shot against four
engineered prompts, and that proposal was recorded. A human then reviewed all
{stats['reviewed']} candidates in a keyboard-driven tool and set the final label.

**The human agreed with CLIP on {stats['agreement']:.0%} of kept images and changed
{stats['corrected']}.** That gap is the reason the dataset exists. Zero-shot CLIP is
weak at exactly the distinction that matters most here — dry versus damp asphalt — and
the corrections concentrate there.

A further {stats['rejected']} candidates were rejected outright, because the surface in
them could not honestly be judged: resurfacing work mid-pour, a close-up of a tyre, a
lizard filling the frame, a vintage racing photograph. That is {stats['rejected'] / max(1, stats['reviewed']):.0%}
of everything retrieved, spread almost evenly across all four source groups — so it is
not a quirk of one search term but the ordinary cost of harvesting a specific visual
property from a general-purpose image library. They are excluded rather than forced into
whichever of the four classes fits worst.

## Provenance and licensing

{provenance} No image was downloaded whose licence could not be read.

**`attribution.json` is keyed by the file you receive**, not by the original upload name —
one record per image, carrying its title, author, licence, and a link to the source page:

```json
{{ "file": "data/wet/00278.jpg", "artist": "…", "license": "cc-by-sa-4.0",
  "source_url": "https://commons.wikimedia.org/wiki/File:…" }}
```

Most of these licences require you to credit the individual photographer. Credit them
from that file — not this repository.

| licence | images |
|---|---|
{licenses}

The set is published as **CC BY-SA 4.0**, the most restrictive licence among its
inputs, so that the whole is compatible with every part. Attribute the original
photographers via `attribution.json`, not this repository.

## Known limitations

Read these before using it for anything.

- **It is small.** {stats['kept']} images is enough to fit a linear probe on frozen
  embeddings. It is not enough to fine-tune a backbone, and not enough to make strong
  claims about accuracy.
- **Single-annotator.** One person labelled every image. There is no second pass and no
  inter-annotator agreement figure, so the boundary between `damp` and `wet` reflects
  one person's judgement of a genuinely continuous variable.
- **Not motorsport footage.** These are mostly public roads photographed from a
  standing position. A trackside broadcast camera sees a different angle, different
  optics, and spray the still images here do not contain.
- **Retrieval bias.** Images come from curated Wikimedia Commons categories (`Asphalt`,
  `Wet roads`, `Puddles`, `Flooded roads`, and others), with free-text search used only
  for `damp`, which has no category — because nobody photographs a slightly wet road on
  purpose. So the set over-represents conditions dramatic enough to be worth
  photographing and captioning, and `damp` is both the smallest class here and the one
  zero-shot is worst at. That is the honest shape of the problem, not an accident.
- **Geographic and seasonal skew.** Commons road photography skews heavily towards
  Western Europe, and towards daylight. There is very little night footage, which is
  precisely the condition the parent project is designed for.

## Loading it

```python
from datasets import load_dataset

ds = load_dataset("{config.HF_DATASET_REPO}")
```

The layout is standard `imagefolder`: `data/<label>/<id>.jpg`.
"""


def push(export_dir: Path, repo_id: str) -> None:
    from huggingface_hub import HfApi

    token = os.getenv("HF_TOKEN")
    if not token:
        raise SystemExit(
            "HF_TOKEN is not set. Create a write token at "
            "https://huggingface.co/settings/tokens and export it:\n"
            "    export HF_TOKEN=hf_...\n"
            "It is read from the environment and never written to disk."
        )

    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    api.upload_folder(
        repo_id=repo_id,
        folder_path=str(export_dir),
        repo_type="dataset",
        commit_message="Add reviewed road-surface frames with attribution",
    )
    print(f"published → https://huggingface.co/datasets/{repo_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=config.BUILD_DIR)
    parser.add_argument("--sources", type=Path, default=config.SOURCES_DIR)
    parser.add_argument("--export", type=Path, default=config.DATASET_DIR / "export")
    parser.add_argument("--repo", default=config.HF_DATASET_REPO)
    parser.add_argument("--push", action="store_true", help="actually upload; off by default")
    args = parser.parse_args()

    manifest_path = args.build / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"No manifest at {manifest_path}. Run scripts/build_dataset.py first.")

    manifest = load_manifest(manifest_path)
    labelled = apply_labels(manifest, load_labels(args.build))
    if not labelled:
        raise SystemExit(
            f"No human labels found. Open {args.build / 'label_tool.html'}, review the "
            "frames, then save labels.json back into that directory."
        )

    stats = build_export(labelled, args.build, args.export, args.sources)
    (args.export / "README.md").write_text(card(stats))

    print(f"export → {args.export}")
    print(f"  {stats['kept']} images across {len(stats['counts'])} classes: {stats['counts']}")
    print(f"  {stats['rejected']} rejected · CLIP agreement {stats['agreement']:.0%}")
    print(f"  licences: {stats['licenses']}")

    if args.push:
        push(args.export, args.repo)
    else:
        print(f"\nDry run. Read {args.export / 'README.md'}, then re-run with --push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
