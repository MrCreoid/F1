# STATE

Last updated: 2026-08-12 · after Phase 10

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer), 3 (design proof), 5 (frontend shell), 6 (signature element), 7 (pit call + timeline), **9a (dataset pipeline — built, not yet published)**, **10 (hardening + DEMO.md + hostile pass)**
- Next phase: 8 — motion, trimmed. Spring numerals and 400ms colour cross-fades only.
- Phase 4 (WebSocket realtime) is **skipped**, per the cut list.
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
- Device: mps. `/api/health` reports the real per-frame cost each start; **15.6 ms** on
  the last measured run. (The 18.5 ms in earlier revisions of this file was stale — the
  status bar now shows the live figure rather than a number anybody has to maintain.)
- Sample analysis, measured through the API: **drying 300 frames in 3.0 s**, wetting 300
  in 2.0 s, ambiguous 280 in 1.9 s.
- Kalman Q = 0.05 — settles a 10-point step in 3.0 s, holds plateau noise at 0.9.
- Backend suite: **113 passed in 25.6 s**. Frontend: 10 tests, `tsc`, `eslint`,
  `next build` all clean.
- No horizontal overflow at 375, 1000 or 1440 px: `scrollWidth === clientWidth`, zero
  overflowing elements.
- Thumbnails 480px q80; a 300-frame clip writes ~300 files under `backend/data/frames/`.
- **Retrieval precision, measured:** free-text Commons search put a road word in only
  **36% of 288 titles**. Curated categories are near 100% on inspection of the first 20.

## Demo beats, measured — see docs/DEMO.md
| clip | frames | BOX events |
|---|---|---|
| drying | 300 / 75s | frame 224 (56.0s) → INTERMEDIATE · frame 258 (64.5s) → SLICK |
| wetting | 300 / 75s | frame 102 (25.5s) → FULL_WET |
| ambiguous | 280 / 70s | none; only 19/280 frames yield a projection, 54 degraded |

**ARMING lasts two frames — 0.5 s of footage.** D.5 calls it the emotional beat of the
product and the pulse cannot complete one cycle at replay speed. Step through it with the
arrow keys; do not play it.

## Phase 10 — hardening, and what the hostile pass found

Nine findings, ranked by how badly they would embarrass us on stage. **1–4 are fixed.**

1. **The instrument contradicted itself.** The hero rendered `STABLE` next to
   `−64.0/min` on **80 of 300 frames** of the wetting clip and 12/300 of drying. When the
   fit fails its gates the backend forces direction to STABLE but still reports the slope
   it computed, and the UI printed it to one decimal as though it were a fact. Null-state
   discipline had been applied to the projection and never to the readout beside it.
   `chart.ts:ratePerMin()` now returns an em dash when `sufficient_signal` is false.
   Re-measured across 40 frames of the worst clip: **zero contradictions**, 20 dashes.
2. **A keyboard user could not start playback.** Space on the focused play button was
   handled by the window listener *and* by native button activation — two toggles, net
   no-op. The window handler now ignores space inside a button. D.7 wants full keyboard
   reach; the primary transport control had none.
3. **The upload size guard was decorative.** `await file.read()` ran before the length
   check, so a 2GB drop exhausted memory before producing the 413 it existed to produce.
   Now streamed in 1MB chunks and checked as it goes, with the partial file removed on
   refusal.
4. **Uploads were never cleaned up.** Phase 7 added an `rmtree` for the frame store and
   covered only half the problem; `data/uploads/` had reached 22MB. `delete_session` now
   removes both.

Deferred, with reasons:

5. **Backend tunables are re-typed in the frontend** — `25`/`65` in `decision.tsx` (four
   places) and `chart.ts:TWI_THRESHOLDS`; `150` and `0.15` in `observation.tsx`. Retune
   `COMPOUND_THRESHOLDS` and the chart silently disagrees with the pit call. The honest
   fix is serving them from `/api/health` or a `/api/config`, which is a schema change
   plus a regeneration — worth doing, too large to bolt onto this phase.
6. **A flat signal reports perfect confidence.** `trend.py:79` returns `R² = 1.0` on zero
   variance and `sufficient_signal` True; 0.001 of noise drops it to 0.004. **Not
   reachable end-to-end** — CLIP is not bit-identical across a batch on mps, so a frozen
   feed lands at R² 0.11 and correctly reads *Insufficient*. Latent, not live, but it is a
   public tested function whose comment argues the behaviour is correct.
7. **`weather.py:96` catches `Exception` and never logs.** An Open-Meteo field rename
   becomes a permanent silent fallback. The UI does say `offline-fallback`, so it is
   honest on screen and invisible in the logs.
8. Doc drift — fixed in this rewrite; the status bar now shows the live `warmup_ms`.
9. **`Lighthouse accessibility ≥ 95` (D.7) has never been run.**

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
- **`localStorage` is namespaced by a `build_id`.** Frame ids are positional, so a
  rebuild reuses `00000` for a different image. The first version keyed progress on a
  fixed string, and opening the real 400-image queue showed "4 labelled · Reject 4" from
  a twenty-image test build an hour earlier — old labels landing on unrelated images.
  Caught by reading the header, not by a test. `build_id` is a hash of the candidate
  origins, so the same build resumes and a different one starts clean.
- `push_to_hub.load_manifest()` reads both the old bare-list and the new wrapped
  manifest, so a labelling session already in flight survives pulling that change.

## The corpus, as fetched
- **430 images, every one attributed, 17 rejected on licence.** By retrieval hint:
  dry 135, wet 146, standing_water 98, damp 51. Licences: `cc-by-sa-4.0` 173,
  `cc-by-2.0` 59, `cc-by-sa-2.0` 49, `cc-by-sa-3.0` 44, `pd` 33, `cc0` 26, and a tail.
- **400 queued for review, 29 dropped below quality 0.35.**
- CLIP's proposals against the retrieval hint, which is the argument for the dataset:

  | hint ↓ / auto → | dry | damp | wet | standing |
  |---|---|---|---|---|
  | dry            | 111 |  3 |  6 |  5 |
  | damp           |  25 |  8 | 10 |  4 |
  | wet            |  14 | 49 | 59 | 18 |
  | standing_water |  14 |  9 | 23 | 42 |

  Zero-shot calls 25 of 47 damp-sourced images *dry*, and splits wet-sourced images
  59/49 between wet and damp. That is the documented weakness, in real data.

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
- **Hostile findings 5–7 and 9 are open.** See the Phase 10 section for each.
- Pressing play with the playhead at the end does nothing and says nothing. A clip opens
  at its last frame, so this is the first thing a new user tries. Stopping rather than
  looping is deliberate; the silence is not.
- The layout stacks below 1024px but the three-column instrument is the version worth
  showing. Demo at 1440×860 or wider.
- **Commons categories contain near-duplicate photo series** (the same driveway seconds
  apart). Phase 9b's train/test split **must split by source photo**, or duplicates leak
  across the split and the reported accuracy is fiction.

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
