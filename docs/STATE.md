# STATE

Last updated: 2026-08-12 · after Phase 9a

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer), 3 (design proof), 5 (frontend shell), 6 (signature element), 7 (pit call + timeline), **9a (dataset pipeline — built, not yet published)**
- Next phase: 10 — hardening and `docs/DEMO.md`, then `/hostile`.
- Phase 4 (WebSocket realtime) is **skipped**, per the cut list.
- Phase 8 (motion, trimmed) is last.
- **Blocker on Rule 3: two things only a human can supply.** See below.

## Rule 3 — what is left, precisely

The pipeline is built, tested and proven end to end on real data. It has not published,
because publishing needs two inputs that are not code:

1. **~2 hours of labelling.** Run `scripts/build_dataset.py`, open the tool it writes,
   press 1–4 and 0 through the queue, save `labels.json` back into `data/dataset/`.
2. **`HF_TOKEN` in the environment.** Not set on this machine. `push_to_hub.py` stops
   and says how to make one rather than attempting an anonymous push.

Until both happen, **Rule 3 is still broken**. Everything else about it is done:
`fetch_sources.py`, `build_dataset.py`, `label_tool.html`, `push_to_hub.py`, an honest
generated card, and 37 tests over the licensing and review gates.

## Competition rules — current standing
- **Rule 1 (real frontend + backend, genuine boundary): SATISFIED.**
- **Rule 2 (not a wrapper): SATISFIED.** The temporal layer is the product.
- **Rule 3 (HF visible + our own published dataset/model): PIPELINE READY, NOT PUBLISHED.**
- **Rule 4 (runs with no internet): SATISFIED for the app.** The dataset scripts are the
  only network consumers and none of them runs during a demo.

## Hard measurements
- Device: mps. Single-frame classification 18.5 ms. Full 70s clip: 263 frames in 2.0 s.
- Kalman Q = 0.05 — settles a 10-point step in 3.0 s, holds plateau noise at 0.9.
- Backend suite: **98 passed in 19.9 s**. Frontend: 8 chart tests, `tsc`, `eslint`,
  `next build` all clean.
- Thumbnails 480px q80; a 300-frame clip writes ~300 files under `backend/data/frames/`.
- **Retrieval precision, measured:** free-text Commons search put a road word in only
  **36% of 288 titles**. Curated categories are near 100% on inspection of the first 20.

## Phase 9a — the dataset pipeline
- **Categories, not free-text search.** Commons search matches the description page, not
  the picture. `wet racetrack` returned a passenger's photographs out of an aeroplane
  window (`2007_07_21_lhr-lax_328.jpg`); `standing water on road` returned four Norfolk
  water towers, matched on "Water" and "standing by"; `road drying after rain` returned a
  Tudor house. CLIP labels them anyway — it called the house `damp` at 0.56 — because it
  always returns a distribution over four classes whatever you show it.
- **Every category was verified to contain files before being configured.** Plausible
  names are routinely empty: `Category:Wet asphalt`, `Category:Tarmac`,
  `Category:Dry asphalt`, `Category:Standing water` all return zero. An empty category is
  indistinguishable from a typo, so do not add one unchecked.
- **Free text survives only for `damp`.** Commons has no damp-roads category, because
  nobody photographs a slightly wet road deliberately. That absence is the same reason
  zero-shot CLIP is worst at damp, and the reason the dataset is worth building.
- **`Category:Puddles` contains `.ogg` and `.wav`** recordings of people pronouncing the
  word. `is_image()` filters on extension before anything reaches a decoder.
- **Attribution is flushed after every source, not at the end.** The first version wrote
  it once on completion; an interrupted run left 181 images on disk with no licence
  recorded, which is indistinguishable from unlicensed content. Caught by looking at the
  directory, not by a test — and then vindicated within the hour: the fetch died on
  `Category:Aquaplaning` with `RemoteDisconnected`, and all 322 images already on disk
  were still fully attributed. The earlier design would have lost every licence.
- **The retry loop must catch `OSError`, not `urllib.error.URLError`.**
  `http.client.RemoteDisconnected` is a `ConnectionResetError` and therefore an
  `OSError`, but it is *not* a `URLError`, and urllib does not wrap it. The narrow catch
  let one dropped connection abort a forty-minute run. `URLError` and `HTTPError` are
  both `OSError` subclasses, so the broader catch loses nothing.
- **A dying source costs that source, not the run.** The retrieval generators hit the
  network lazily, so they are drained inside their own try — one unreachable category no
  longer takes the eleven after it with it.
- **An orphan cannot reach the export.** If a source directory has an `attribution.json`,
  `build_dataset.collect()` skips any image missing from it. A directory with no
  attribution file is treated as own footage and passes freely.
- **The retrieval hint is never a label.** Recorded as `query_hint`, read by nothing.
- **A frame no human reviewed is dropped by `apply_labels`.** Shipping auto-labels as
  ground truth would make the dataset a record of the model's own opinion.
- **`auto_label` is written once and never overwritten**, so the card can state how many
  frames the reviewer changed. That number is the argument for the dataset existing.
- **The card is generated from the manifest's own counts**, including the unflattering
  parts: class imbalance, single-annotator, retrieval bias, geographic and night skew.
- **`push_to_hub.py` is dry-run by default.** Publishing is a deliberate act.
- **`HF_TOKEN` from the environment only** — never written, printed, or put in an error.
- The label tool needs no server: `build_dataset.py` emits `manifest.js` beside it,
  because a browser will not `fetch` a sibling JSON over `file://` but will load a script
  tag. Progress goes to `localStorage` on every keystroke, so a closed tab costs nothing.

## Phase 7 — the frame store and the filmstrip
- Thumbnails are written in `main.py:_analyse_and_store`, the one function holding both
  the decoded images and the session, and the single path both ingest routes go through.
  `analysis/pipeline.py` stays pure and never touches the filesystem.
- `write_thumbnail` converts RGB→BGR before `cv2.imwrite`; skipping it tints every frame
  blue, which is what the classifier reads as wet, so the bug would look like a model
  failure. Tested with a red frame.
- Served by `StaticFiles` at `/media` with `check_dir=False` — the directory is made in
  the lifespan, which runs after import.
- The filmstrip measures itself with a `ResizeObserver` and picks `floor(width / 104)`
  cells. Each cell covers a range and shows its middle frame; a cell is degraded if *any*
  frame inside it is, because a warning must not be averaged away.
- Degraded cells are hatched **and** dimmed to 0.5. Hatching alone at 55% read as a warm
  cast over bright spray. Verified at 1:1 — the downscaled screenshot was hiding it.
- `next` is null on BOX, so the transition is read from `history.at(-2)`. Presentation,
  not analysis, so it earned no schema field.

## Phase 6 — the signature element
- Hand-rolled SVG, not Recharts: the cone's three vertices are separate scalars, and the
  stroke gradient's stops are computed from where the data crosses 25 and 65.
- The line shifts hue at each band crossing; history and projection share one gradient.
- The countdown interpolates at 60fps against wall time, and only while replay advances.
- `projectionGap()` names the gate that actually failed. Verified again in Phase 7: the
  ambiguous clip reads `R² 0.28 BELOW 0.40 THRESHOLD`, the drying clip past its boundary
  reads `ALREADY BELOW THE SLICK THRESHOLD`.

## Rejected, do not revisit
- Free-text Commons search as primary retrieval — 36% precision, measured.
- Treating a search term or category as a label — the whole point is correcting it.
- Wikimedia requests without a User-Agent — HTTP 403.
- A 2s backoff on HTTP 429 — it just earns another 429. Needs ~30s.
- A separate `/api/classify` endpoint — `POST /api/sessions/{id}/frames` covers it.
- Arithmetic mean for frame quality — one catastrophic factor must not be averaged away.
- An "unlit segment" ghost behind the TWI digits — 47.5 scanned as 47.8.
- A single stock reason for a missing projection — it misreports the common case.
- Browser-direct calls to :8000 — replaced by the Next rewrite.
- A second, smaller thumbnail size for the strip — one 480px JPEG serves both.
- Preloading the next frame's thumbnail — measured, the monitor never blanks.
- A `previous_compound` field on `Recommendation` — history already carries it.
- `datasets` as a dependency — `huggingface_hub.upload_folder` publishes an imagefolder.

## Known broken / deferred
- **Rule 3 is not closed.** Labelling and `HF_TOKEN` outstanding — see the top.
- **Commons categories contain near-duplicate photo series** (the same driveway seconds
  apart). Phase 9b's train/test split **must split by source photo**, or duplicates leak
  across the split and the reported accuracy is fiction.
- **The layout does not stack below 1024px.** SPEC-DESIGN D.3 asks for it, D.7 wants
  375px. The grid is a fixed `348px 1fr 324px` with no breakpoint; at 800px the
  projection panel is clipped. A layout pass, not a filmstrip change.
- **The sample clips are one unlicensed photograph with its exposure ramped.** Measured:
  structural correlation against frame 0 falls to −0.005 by frame 599 — the picture is
  gone, leaving flat noise. Provenance was never recorded and `scripts/build_samples.py`
  was never committed. They are fine as a *demo of the temporal layer* and must never
  become training data or be published.
- The synthetic `drying` clip therefore washes out to white at the end, in the monitor
  and the last filmstrip cells.
- `main.py` still names `scripts/build_samples.py` in an error string; that file does not
  exist.
- Each upload is analysed as its own run; the Kalman filter restarts rather than resuming.
- The 30-minute crossover horizon gate is unreachable through config (~26.7 min worst
  case). Kept as a guard, tested via the `horizon_s` parameter.
- Zero-shot still cannot separate dry from damp. Demo the trend, not the label.
- The rail's `280 FRAMES · 01:10` label is clipped by the playhead at the far right.

## Run it

```bash
# terminal 1 — backend
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# terminal 2 — frontend
cd frontend && npm run dev
# open http://localhost:3000 and click a sample clip

# the dataset, in order — see docs/DATASET.md
.venv/bin/python scripts/fetch_sources.py
.venv/bin/python scripts/build_dataset.py
open data/dataset/label_tool.html
.venv/bin/python scripts/push_to_hub.py          # dry run
HF_TOKEN=hf_... .venv/bin/python scripts/push_to_hub.py --push

# checks
cd backend  && ../.venv/bin/python -m pytest tests/ -q
cd frontend && npm test && npx tsc --noEmit && npm run lint && npm run build
```
