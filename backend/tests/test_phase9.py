"""Phase 9 proof: the dataset pipeline.

Nothing here touches the network. The Commons client is exercised through its pure
parts — licence filtering, HTML stripping, filename safety — because those are what
decide whether an image we have no right to redistribute ends up in a published folder.

The export tests matter most: they assert that an unreviewed frame cannot reach the
dataset, and that the card's numbers are the numbers on disk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import build_dataset  # noqa: E402
import fetch_sources  # noqa: E402
import push_to_hub  # noqa: E402

from app import config  # noqa: E402


# ---------------------------------------------------------------- licence gate


@pytest.mark.parametrize("slug", ["cc0", "cc-by-4.0", "cc-by-sa-3.0", "pd", "CC-BY-2.0", " cc0 "])
def test_licences_we_may_redistribute_are_allowed(slug: str) -> None:
    assert fetch_sources.license_allowed(slug)


@pytest.mark.parametrize(
    "slug",
    ["cc-by-nc-4.0", "cc-by-nd-4.0", "cc-by-nc-sa-3.0", "fairuse", "", "unknown", "gfdl"],
)
def test_licences_we_may_not_are_refused(slug: str) -> None:
    """Non-commercial, no-derivatives, and anything unrecognised. Unknown means no —
    the failure mode of guessing here is republishing someone's work without the right."""
    assert not fetch_sources.license_allowed(slug)


@pytest.mark.parametrize(
    "title,expected",
    [
        ("File:Wet road.jpg", True),
        ("File:Puddle.PNG", True),
        ("File:Scan.tiff", True),
        # Category:Puddles genuinely contains these: recordings of the spoken word.
        ("File:De-Pfütze.ogg", False),
        ("File:LL-Q1860 (eng)-Vealhurl-puddle.wav", False),
        ("File:Rain.webm", False),
        ("File:Diagram.svg", False),
    ],
)
def test_only_still_images_survive_retrieval(title: str, expected: bool) -> None:
    """Commons categories carry sound and video alongside photographs."""
    assert fetch_sources.is_image(title) is expected


def test_every_configured_category_is_namespaced() -> None:
    """A bare name silently returns nothing from the categorymembers generator, which
    looks like an empty category rather than a typo."""
    for hint, names in config.SOURCE_CATEGORIES.items():
        for name in names:
            assert name.startswith("Category:"), f"{hint}: {name!r} is missing the prefix"


def test_retrieval_hints_are_all_real_classes_or_absent() -> None:
    """A hint that is not a class would quietly become a label nobody can train on."""
    known = set(config.CLASS_NAMES)
    assert set(config.SOURCE_CATEGORIES) <= known
    assert set(config.SOURCE_QUERIES) <= known


def test_a_dropped_connection_is_retried_not_fatal(monkeypatch) -> None:
    """`RemoteDisconnected` is an OSError but not a URLError, and urllib does not wrap
    it. Catching the narrower type let one dropped connection abort a whole fetch."""
    import http.client

    attempts: list[int] = []

    def flaky(request, timeout):  # noqa: ANN001 - urlopen's signature
        attempts.append(1)
        if len(attempts) < 3:
            raise http.client.RemoteDisconnected("Remote end closed connection")
        raise AssertionError("unreachable: the retry loop should have been exercised")

    monkeypatch.setattr(fetch_sources.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(fetch_sources.time, "sleep", lambda _: None)

    with pytest.raises((RuntimeError, AssertionError)):
        fetch_sources._get("https://example.invalid/x.json")

    assert len(attempts) > 1, "a dropped connection was never retried"


def test_artist_html_becomes_a_plain_credit_line() -> None:
    raw = '<a href="//commons.wikimedia.org/wiki/User:Someone" title="x">Someone\n Else</a>'
    assert fetch_sources.strip_html(raw) == "Someone Else"


def test_strip_html_decodes_entities_after_removing_tags() -> None:
    """Decoding first would turn an escaped fragment into a tag and then delete it."""
    assert fetch_sources.strip_html("Ben &amp; Co &lt;b&gt;kept&lt;/b&gt;") == "Ben & Co <b>kept</b>"


def test_safe_name_strips_the_namespace_and_the_path_separators() -> None:
    assert fetch_sources.safe_name("File:Wet winding road.jpg") == "wet_winding_road.jpg"
    assert "/" not in fetch_sources.safe_name("File:a/b/../c.jpg")


def test_to_source_refuses_an_image_with_an_unusable_licence() -> None:
    result = {
        "title": "File:Nope.jpg",
        "info": {
            "thumburl": "https://example.invalid/x.jpg",
            "extmetadata": {"License": {"value": "cc-by-nc-4.0"}},
        },
    }
    assert fetch_sources.to_source(result, "q", "wet") is None


def test_to_source_records_the_query_as_a_hint_not_a_label() -> None:
    result = {
        "title": "File:Yes.jpg",
        "info": {
            "thumburl": "https://example.invalid/x.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Yes.jpg",
            "extmetadata": {
                "License": {"value": "cc0"},
                "LicenseShortName": {"value": "CC0"},
                "Artist": {"value": "<a href='#'>Someone</a>"},
            },
        },
    }
    source = fetch_sources.to_source(result, "wet asphalt road", "wet")

    assert source is not None
    assert source.query_hint == "wet"
    assert source.artist == "Someone"
    # There is no `label` field at all: retrieval must not be able to assert truth.
    assert not hasattr(source, "label")


# ---------------------------------------------------------------- review gate


def _manifest(*rows: tuple[str, str, str | None]) -> list[dict[str, object]]:
    return [
        {
            "id": ident,
            "file": f"images/{ident}.jpg",
            "origin": f"{ident}.jpg",
            "auto_label": auto,
            "auto_confidence": 0.9,
            "probabilities": {n: 0.25 for n in config.CLASS_NAMES},
            "quality": 0.8,
            "query_hint": None,
            "label": label,
        }
        for ident, auto, label in rows
    ]


def test_manifest_reads_both_shapes(tmp_path: Path) -> None:
    """A labelling session already in flight must survive pulling the build_id change."""
    rows = _manifest(("00000", "wet", None))
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(json.dumps(rows))
    new.write_text(json.dumps({"build_id": "abc123", "candidates": rows}))

    assert push_to_hub.load_manifest(old) == rows
    assert push_to_hub.load_manifest(new) == rows


def test_a_rebuild_gets_a_different_store_key(tmp_path: Path, monkeypatch) -> None:
    """Ids are positional. Two builds over different images must not share progress,
    or a rebuild silently applies old labels to whichever image now sits at that index."""
    ids = []
    for names in (("a.jpg", "b.jpg"), ("c.jpg", "d.jpg")):
        source = tmp_path / f"src{names[0]}"
        source.mkdir()
        for name in names:
            Image.fromarray(
                np.random.default_rng(1).integers(40, 200, (48, 64, 3), dtype=np.uint8)
            ).save(source / name)

        class Fake:
            device = "cpu"

            @staticmethod
            def load() -> "Fake":
                return Fake()

            @staticmethod
            def classify(images: list[np.ndarray]) -> list[dict[str, float]]:
                return [{"dry": 0.9, "damp": 0.05, "wet": 0.03, "standing_water": 0.02}] * len(images)

        monkeypatch.setattr(build_dataset, "ZeroShotClassifier", Fake)
        out = tmp_path / f"out{names[0]}"
        build_dataset.build(source, out, limit=None)
        ids.append(json.loads((out / "manifest.json").read_text())["build_id"])

    assert ids[0] != ids[1]


def test_a_frame_no_human_looked_at_never_reaches_the_dataset() -> None:
    manifest = _manifest(("00000", "wet", None), ("00001", "dry", None))

    assert push_to_hub.apply_labels(manifest, {}) == []


def test_a_human_label_overrides_clips_proposal() -> None:
    manifest = _manifest(("00000", "wet", None))

    merged = push_to_hub.apply_labels(manifest, {"00000": "damp"})

    assert len(merged) == 1
    assert merged[0]["label"] == "damp"
    # The proposal survives, so the card can count how often it was wrong.
    assert merged[0]["auto_label"] == "wet"


# ---------------------------------------------------------------- the export


@pytest.fixture()
def built(tmp_path: Path) -> tuple[Path, Path, list[dict[str, object]]]:
    build_dir = tmp_path / "dataset"
    (build_dir / "images").mkdir(parents=True)
    rows = _manifest(
        ("00000", "wet", "wet"),
        ("00001", "wet", "damp"),
        ("00002", "dry", "dry"),
        ("00003", "dry", "reject"),
    )
    for row in rows:
        Image.new("RGB", (32, 18), (60, 60, 64)).save(build_dir / str(row["file"]))

    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "attribution.json").write_text(
        json.dumps(
            [
                {
                    "file_name": f"{row['id']}.jpg",
                    "title": f"File:{row['id']}.jpg",
                    "license": "cc0" if i % 2 else "cc-by-sa-4.0",
                    "license_short": "CC0",
                    "license_url": "https://example.invalid",
                    "artist": "Someone",
                    "credit": "Own work",
                    "source_url": "https://example.invalid",
                    "query": "q",
                    "query_hint": "wet",
                }
                for i, row in enumerate(rows)
            ]
        )
    )
    return build_dir, sources, rows


def test_export_writes_imagefolder_layout_and_excludes_rejects(
    built: tuple[Path, Path, list[dict[str, object]]], tmp_path: Path
) -> None:
    build_dir, sources, rows = built
    export = tmp_path / "export"

    stats = push_to_hub.build_export(rows, build_dir, export, sources)

    assert (export / "data" / "wet" / "00000.jpg").exists()
    assert (export / "data" / "damp" / "00001.jpg").exists()
    assert (export / "data" / "dry" / "00002.jpg").exists()
    # The rejected frame is in no class directory at all.
    assert not list(export.rglob("00003.jpg"))
    assert stats["kept"] == 3
    assert stats["rejected"] == 1
    assert stats["counts"] == {"damp": 1, "dry": 1, "wet": 1}


def test_export_reports_the_agreement_rate_honestly(
    built: tuple[Path, Path, list[dict[str, object]]], tmp_path: Path
) -> None:
    """Two of three kept frames match CLIP; one was corrected. The card leans on this."""
    build_dir, sources, rows = built

    stats = push_to_hub.build_export(rows, build_dir, tmp_path / "export", sources)

    assert stats["corrected"] == 1
    assert stats["agreement"] == pytest.approx(2 / 3)


def test_export_carries_attribution_for_every_image_it_ships(
    built: tuple[Path, Path, list[dict[str, object]]], tmp_path: Path
) -> None:
    build_dir, sources, rows = built
    export = tmp_path / "export"

    push_to_hub.build_export(rows, build_dir, export, sources)

    credits = json.loads((export / "attribution.json").read_text())
    shipped = {p.stem for p in export.rglob("data/*/*.jpg")}
    credited = {row["file_name"].split(".")[0] for row in credits}
    assert shipped <= credited, "an image shipped with no author recorded"


def test_card_numbers_match_the_files_on_disk(
    built: tuple[Path, Path, list[dict[str, object]]], tmp_path: Path
) -> None:
    build_dir, sources, rows = built
    export = tmp_path / "export"
    stats = push_to_hub.build_export(rows, build_dir, export, sources)

    text = push_to_hub.card(stats)

    for label in ("wet", "damp", "dry"):
        actual = len(list((export / "data" / label).glob("*.jpg")))
        assert f"| `{label}` | {actual} |" in text
    assert "cc-by-sa-4.0" in text
    # The limitations are generated, not optional.
    assert "Known limitations" in text
    assert "Single-annotator" in text


def test_card_states_there_is_no_fifth_class() -> None:
    """The one modelling rule, written where a dataset consumer will actually read it."""
    stats = {"kept": 1, "reviewed": 1, "rejected": 0, "counts": {"wet": 1},
             "agreement": 1.0, "corrected": 0, "licenses": {"cc0": 1}, "sources": 1}

    text = push_to_hub.card(stats)

    assert "no \"drying\" class" in text or 'no\n"drying" class' in text


# ---------------------------------------------------------------- candidate build


def test_an_image_with_no_attribution_record_never_enters_a_fetched_corpus(tmp_path: Path) -> None:
    """The orphan of an interrupted fetch. On disk, licence unknown, therefore excluded."""
    source = tmp_path / "src"
    source.mkdir()
    for name in ("credited.jpg", "orphan.jpg"):
        Image.new("RGB", (32, 24), (90, 90, 94)).save(source / name)
    (source / "attribution.json").write_text(
        json.dumps([{"file_name": "credited.jpg", "query_hint": "wet"}])
    )

    found = build_dataset.collect(source)

    assert [origin for origin, _, _ in found] == ["credited.jpg"]


def test_own_footage_needs_no_attribution_file(tmp_path: Path) -> None:
    """No attribution.json means nobody to credit, not that everything is suspect."""
    source = tmp_path / "mine"
    source.mkdir()
    Image.new("RGB", (32, 24), (90, 90, 94)).save(source / "my_clip_frame.jpg")

    found = build_dataset.collect(source)

    assert [origin for origin, _, _ in found] == ["my_clip_frame.jpg"]
    assert found[0][2] is None


def test_build_drops_frames_too_poor_to_review(tmp_path: Path, monkeypatch) -> None:
    """A blown-out frame costs a reviewer the same two seconds and teaches nothing."""
    source = tmp_path / "src"
    source.mkdir()
    Image.new("RGB", (64, 48), (255, 255, 255)).save(source / "blown.jpg")
    Image.fromarray(
        np.random.default_rng(0).integers(40, 200, (64, 48, 3), dtype=np.uint8)
    ).save(source / "textured.png")

    flat = {name: 0.25 for name in config.CLASS_NAMES}
    sharp = {"dry": 0.9, "damp": 0.05, "wet": 0.03, "standing_water": 0.02}

    class FakeClassifier:
        device = "cpu"

        @staticmethod
        def load() -> "FakeClassifier":
            return FakeClassifier()

        @staticmethod
        def classify(images: list[np.ndarray]) -> list[dict[str, float]]:
            # The blown frame sorts first alphabetically; give it the flat distribution.
            return [flat, sharp][: len(images)]

    monkeypatch.setattr(build_dataset, "ZeroShotClassifier", FakeClassifier)

    candidates = build_dataset.build(source, tmp_path / "out", limit=None)

    assert [c.origin for c in candidates] == ["textured.png"]
    assert candidates[0].label is None, "build must never assert a label"
    assert candidates[0].auto_label == "dry"
