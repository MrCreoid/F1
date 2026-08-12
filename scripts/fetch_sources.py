#!/usr/bin/env python
"""Collect freely-licensed road-surface photographs from Wikimedia Commons.

Curated categories first, free text only where no category exists. Commons search
matches the wording of a description page rather than the picture: on a measured
288-image run only 36% of results had a road word in the title, and "wet racetrack"
returned a passenger's photographs out of an aeroplane window.

Retrieval only. Nothing here decides a label — the category or term that found an image
is recorded as a hint and never read again downstream. "Wet roads" holds plenty of
merely damp ones, and correcting exactly that is what the dataset is for.

Every image carries its licence, its author and its source page from the moment it lands
on disk, flushed after each source. An image whose licence we cannot read is skipped and
counted, never downloaded on the assumption that it is probably fine.

    .venv/bin/python scripts/fetch_sources.py

Re-running is cheap: anything already attributed on disk is left alone.
"""

from __future__ import annotations

import argparse
import http.client
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import config  # noqa: E402


@dataclass(frozen=True)
class SourceImage:
    """One downloaded photograph and everything needed to credit it."""

    file_name: str
    title: str
    license: str
    license_short: str
    license_url: str
    artist: str
    credit: str
    source_url: str
    query: str
    query_hint: str  # the class the query was expected to surface; never a label


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def strip_html(value: str) -> str:
    """Commons returns Artist and Credit as HTML fragments with links inside.

    A credit line has to survive being pasted into a plain-text card, so the markup goes
    and the text stays. Entities are decoded after tag removal, not before, or an
    escaped `&lt;b&gt;` would turn into a tag and then vanish.
    """
    import html

    return _WS.sub(" ", html.unescape(_TAG.sub(" ", value or ""))).strip()


def license_allowed(slug: str) -> bool:
    """True for licences we may redistribute. Unknown means no."""
    return (slug or "").strip().lower() in config.ALLOWED_LICENSES


def safe_name(title: str) -> str:
    """`File:Wet winding road.jpg` -> `wet_winding_road.jpg`, collision-free enough."""
    stem = title.split(":", 1)[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-").lower()
    return cleaned or "untitled.jpg"


def _get(url: str, *, binary: bool = False) -> Any:
    """One HTTP GET with the required User-Agent, a timeout, and backoff.

    Commons answers a request with no User-Agent with HTTP 403, which reads as a network
    fault rather than a policy one. The header is not optional.
    """
    request = urllib.request.Request(url, headers={"User-Agent": config.COMMONS_USER_AGENT})
    last: Exception | None = None
    for attempt in range(config.COMMONS_RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=config.COMMONS_TIMEOUT_S) as response:
                payload = response.read()
            return payload if binary else json.loads(payload)
        # OSError, not URLError. `http.client.RemoteDisconnected` — a server closing the
        # connection mid-run, which Commons does — is a ConnectionResetError and so an
        # OSError, but is *not* a URLError, and urllib does not wrap it. Catching the
        # narrower type let one dropped connection abort a forty-minute fetch.
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
            last = exc
            if attempt < config.COMMONS_RETRIES - 1:
                # A 429 is a rate limit, not a blip. Backing off two seconds just earns
                # another one, so it gets its own much longer wait.
                throttled = isinstance(exc, urllib.error.HTTPError) and exc.code == 429
                time.sleep(
                    config.COMMONS_RATE_LIMIT_BACKOFF_S
                    if throttled
                    else config.COMMONS_BACKOFF_S * (2**attempt)
                )
    raise RuntimeError(f"Commons request failed after {config.COMMONS_RETRIES} attempts: {last}")


def is_image(title: str) -> bool:
    """Commons categories carry sound and video too.

    Category:Puddles holds pronunciation recordings of the word "puddle". Passing one to
    an image decoder produces a confusing failure much further down.
    """
    return title.lower().endswith(config.IMAGE_EXTENSIONS)


def _query(**params: str) -> Iterator[dict[str, Any]]:
    """Run one API query and yield each page that carries imageinfo for an image."""
    params.update(
        {
            "action": "query",
            "format": "json",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": str(config.SOURCE_IMAGE_EDGE),
        }
    )
    payload = _get(f"{config.COMMONS_API}?{urllib.parse.urlencode(params)}")
    for page in (payload.get("query") or {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [None])[0]
        if info and is_image(page["title"]):
            yield {"title": page["title"], "info": info}


def category_members(category: str, limit: int) -> Iterator[dict[str, Any]]:
    """Files in a curated category. Higher precision than search, by a wide margin."""
    return _query(
        generator="categorymembers",
        gcmtitle=category,
        gcmtype="file",
        gcmlimit=str(limit),
    )


def search(query: str, limit: int) -> Iterator[dict[str, Any]]:
    """Free-text search of the File namespace. Used only where no category fits."""
    return _query(
        generator="search",
        # filetype:bitmap keeps out SVG diagrams and PDFs, which are not photographs.
        gsrsearch=f"filetype:bitmap {query}",
        gsrnamespace="6",
        gsrlimit=str(limit),
    )


def to_source(result: dict[str, Any], query: str, hint: str) -> SourceImage | None:
    """Build the attribution record, or None if the licence is not one we may reuse."""
    info = result["info"]
    meta = info.get("extmetadata", {})

    def field(name: str) -> str:
        return strip_html(str(meta.get(name, {}).get("value", "")))

    slug = str(meta.get("License", {}).get("value", "")).strip().lower()
    if not license_allowed(slug):
        return None
    if not info.get("thumburl"):
        return None

    return SourceImage(
        file_name=safe_name(result["title"]),
        title=result["title"],
        license=slug,
        license_short=field("LicenseShortName"),
        license_url=str(meta.get("LicenseUrl", {}).get("value", "")),
        artist=field("Artist"),
        credit=field("Credit"),
        source_url=info.get("descriptionurl", ""),
        query=query,
        query_hint=hint,
    )


def fetch(per_query: int, out_dir: Path) -> list[SourceImage]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "attribution.json"
    existing: dict[str, SourceImage] = {}
    if manifest_path.exists():
        existing = {
            record["file_name"]: SourceImage(**record)
            for record in json.loads(manifest_path.read_text())
        }

    def save() -> list[SourceImage]:
        """Flush attribution to disk.

        Called after every query, not once at the end. An interrupted run — Ctrl-C, a
        dead network, a closed laptop — must never leave images on disk whose licence
        was never recorded. That pile is indistinguishable from unlicensed content, and
        the only safe thing to do with it is delete it.
        """
        records = sorted(existing.values(), key=lambda s: s.file_name)
        manifest_path.write_text(json.dumps([asdict(r) for r in records], indent=2) + "\n")
        return records

    # Categories first, then the few conditions no category covers.
    sources: list[tuple[str, str, Iterator[dict[str, Any]]]] = [
        (hint, name, category_members(name, per_query))
        for hint, names in config.SOURCE_CATEGORIES.items()
        for name in names
    ] + [
        (hint, term, search(term, per_query))
        for hint, terms in config.SOURCE_QUERIES.items()
        for term in terms
    ]

    rejected = 0
    records = save()
    try:
        for hint, origin, results in sources:
            print(f"  {hint:15s} {origin}", flush=True)
            try:
                # The generator itself hits the network, so a source can die part-way
                # through. One unreachable category must cost that category, not the
                # eleven after it.
                results = list(results)
            except RuntimeError as exc:
                print(f"    source unavailable: {exc}", flush=True)
                continue

            for result in results:
                source = to_source(result, origin, hint)
                if source is None:
                    rejected += 1
                    continue
                if source.file_name in existing:
                    continue
                destination = out_dir / source.file_name
                try:
                    destination.write_bytes(_get(result["info"]["thumburl"], binary=True))
                except RuntimeError as exc:
                    print(f"    skip {source.file_name}: {exc}", flush=True)
                    continue
                existing[source.file_name] = source
                # Commons asks for considerate request rates, and enforces it. This
                # is the difference between a slow run and a throttled one.
                time.sleep(config.COMMONS_DELAY_S)
            records = save()
    except KeyboardInterrupt:
        records = save()
        print(f"\ninterrupted · {len(records)} images recorded and attributed")
        raise

    print(f"\n{len(records)} images on disk · {rejected} rejected on licence")
    print(f"attribution → {manifest_path}")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-query", type=int, default=config.SOURCE_PAGE_SIZE, help="files per category or query")
    parser.add_argument("--out", type=Path, default=config.SOURCES_DIR)
    args = parser.parse_args()

    print(f"Wikimedia Commons → {args.out}")
    fetch(args.per_query, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
