# STATE

Last updated: 2026-08-12 · after Phase 7

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer), 3 (design proof), 5 (frontend shell), 6 (signature element), 7 (pit call + timeline)
- Next phase: 9 — Hugging Face. `scripts/` still does not exist and this is the only rule break left. Phase 7's frame store is the substrate `build_dataset.py` reads from, so extraction never has to be written twice.
- Then 10 (hardening + `docs/DEMO.md`), then 8 (motion, trimmed).
- Phase 4 (WebSocket realtime) is **skipped**, per the cut list. `GET /api/sessions/{id}/states` plus client replay gives the same thing visually — PHASES.md says batch-and-replay is "visually identical during a demo".
- Blockers: none.

## Competition rules — current standing
- **Rule 1 (real frontend + backend, genuine boundary): SATISFIED.** Next.js 16 app on :3000, FastAPI on :8000, separate processes, HTTP between them. No model code in the browser.
- **Rule 2 (not a wrapper): SATISFIED.** The temporal layer is the product.
- **Rule 3 (Hugging Face visible + our own published dataset/model): NOT YET.** The remaining rule gap. Minimum fix is publishing the dataset.
- **Rule 4 (runs with no internet): SATISFIED for the app.** Fonts are self-hosted by `next/font` at build time, weights are cached in `backend/.cache/`, thumbnails are written to local disk and served from it, weather has timeout + backoff + a bundled fallback + `WW_OFFLINE=1`. The remaining live call is Open-Meteo, which degrades correctly.

## Hard measurements
- Device: mps. Single-frame classification 18.5 ms. Full 70s clip: 263 frames end to end in 2.0 s.
- Kalman Q = 0.05 — settles a 10-point step in 3.0 s, holds plateau noise at 0.9 from 3.0 of measurement noise.
- Backend suite: **61 passed in 19.0 s**. Frontend: 8 chart tests pass, `tsc --noEmit` clean, `eslint` clean, `next build` succeeds.
- Thumbnails: 480px wide, JPEG q80. A 300-frame clip writes ~300 files under `backend/data/frames/<session>/`.
- Measured in-browser during live replay: the camera monitor was never in an unloaded state across 60 samples over 3 s. No preloading needed.

## Decisions made and why
- **Next rewrites `/api/*` and `/media/*` to FastAPI** rather than the browser calling :8000 directly. Same-origin means no CORS to configure and no backend host baked into client code; the boundary is still two processes over HTTP. `WW_BACKEND` splits them across machines.
- **`allowedDevOrigins: ["127.0.0.1", "localhost"]`** — without it Next dev 403s its own `/_next/static` chunks when the app is opened on `127.0.0.1`, so the client bundle never loads and every panel silently stays empty. Cost an hour; worth the comment in `next.config.ts`.
- **Archivo loads as a variable font with no fixed weight.** `next/font` rejects `axes` alongside `weight`, and the design drives the `wdth` axis directly.
- **Types are generated, never hand-written** — `npm run gen:api` runs `openapi-typescript` against the live schema. If the backend changes a field, the frontend stops compiling.
- **`GET /api/sessions/{id}/states`** returns every frame's full TrackState. This is what makes the transport controls real: play/step/scrub move an index through that history and every panel re-renders what the system knew at that frame.
- Replay runs at 4 fps, the analysis rate, so one second on screen is one second of footage. It stops at the end rather than looping — an instrument that silently restarts would misrepresent the data.
- The event log is **derived from state transitions**, not authored. Every row is a real change the backend reported.
- Sample clips are committed under `backend/samples/` (10 MB total), not generated at runtime. The demo must not depend on anything being produced on the night.

## Phase 6 — the signature element
- **Hand-rolled SVG, not Recharts.** The cone is a polygon whose three vertices come from `eta_s`, `eta_optimistic_s` and `eta_pessimistic_s` — three separate scalars, not a series Recharts can plot. The stroke needs a gradient whose stops are computed from where the data crosses 25 and 65. Neither is expressible without escape hatches, and it avoids a dependency.
- **The line shifts hue at each band crossing** (D.4). `conditionStops()` finds the exact crossing x by linear interpolation and emits paired stops at the same offset, so the transition is a hard edge. History and projection share one gradient so colour carries continuously across *now*.
- **The countdown interpolates at 60fps** against wall time and re-syncs on each new backend value. It only runs while replay is advancing — paused, it shows exactly what the backend said for that frame.
- **The null state names the gate that actually failed.** `projectionGap()` mirrors B.5's gates in order. Verified again this phase: the ambiguous clip reads `R² 0.28 BELOW 0.40 THRESHOLD` while the drying clip past its boundary reads `ALREADY BELOW THE SLICK THRESHOLD` — two different real reasons, not one stock string.

## Phase 7 — the frame store and the filmstrip
- **Thumbnails are written in `main.py:_analyse_and_store`, not in the pipeline.** That function already holds both the decoded images and the session they belong to, and it is the single path both ingest routes go through — so uploads and one-click samples get images from one place. `analysis/pipeline.py` stays pure and never touches the filesystem; it still emits `thumbnail_url=None` and main.py fills it in before persisting.
- **`write_thumbnail` converts RGB→BGR before `cv2.imwrite`.** Extraction hands out RGB; cv2 writes BGR. Skipping the conversion tints every stored frame blue, which is exactly what the classifier reads as wet — the bug would present as a model failure. There is a test asserting a red frame comes back red.
- **Served by a `StaticFiles` mount at `/media`, with `check_dir=False`**, because the directory is created in the lifespan, which runs after the module is imported. Without the flag a cold checkout fails to start rather than simply having nothing to serve.
- **`DELETE /api/sessions/{id}` rmtree's the session's frames.** The frame store is outside the database, so the SQLAlchemy cascade cannot reach it.
- **The filmstrip measures itself.** How many frames fit as legible thumbnails is a question only the rendered width can answer, so a `ResizeObserver` reports it and the strip picks `floor(width / 104)` cells. Measured at 1440px: 13 cells at 111×62, which is 16:9 to within a pixel.
- **Each cell stands for a range of frames, not a sample of one.** It shows the range's middle frame, and the cell under the playhead is therefore always well defined. A cell is marked degraded if *any* frame inside it is — the same principle as the geometric mean in B.2, a warning must not be averaged away by its neighbours.
- **Degraded cells are hatched and dimmed to 0.5, not hidden.** First attempt was hatching alone at 1px/5px and 55% opacity; it read as a faint warm cast over bright spray rather than a mark. 1.5px/6px at 85% plus the dim survives a 100px-wide cell. Verified at 1:1 zoom — the downscaled screenshot was hiding the difference, not the design.
- **The strip is a real `role="slider"`**, focusable, with `aria-valuenow`/`aria-valuetext`. It was a clickable `div` with `role="presentation"` — reachable by mouse only. Arrow keys already worked at the window level and still do.
- **`next` is null on BOX, so the transition is rendered from history.** At the instant the call fires, `current` is already the new compound and the schema alone cannot say what was left. `history.at(-2).recommendation.current` is the compound being left. This is a drawing decision, not an analysis one, so it did not earn a schema field. Verified in-browser: at the firing frame the panel reads `BOX 3/3 · INTER → SLICK` with the destination in sodium, and the event log reads `Box · inter → slick`.
- `DEGRADED_BELOW` now lives in `lib/api.ts` mirroring `config.QUALITY_FLAG_THRESHOLD`; the literal `0.25` had been inlined in three places.

## Rejected, do not revisit
- Wikimedia thumbnail URLs without a User-Agent — HTTP 403.
- A separate `/api/classify` endpoint — `POST /api/sessions/{id}/frames` is already in the contract.
- Arithmetic mean for frame quality — one catastrophic factor must not be averaged away.
- An "unlit segment" ghost behind the TWI digits — at any readable opacity, 47.5 scanned as 47.8.
- A single stock reason for a missing projection — it misreports the common case.
- Browser-direct calls to :8000 — replaced by the Next rewrite.
- A second, smaller thumbnail size for the strip — one 480px JPEG serves both the monitor and the filmstrip, and the bandwidth it would save does not exist over localhost.
- Preloading the next frame's thumbnail — measured, the monitor never blanks during replay.
- Adding a `previous_compound` field to `Recommendation` — history already carries it.

## Known broken / deferred
- **Rule 3 is the open gap.** No `build_dataset.py`, `label_tool.html`, `train_probe.py` or `push_to_hub.py`. Phase 9.
- **The layout does not stack below 1024px.** SPEC-DESIGN D.3 calls for frame / readout / projection / call / timeline stacked, and D.7 wants 375px. The grid is a fixed `348px 1fr 324px` with no breakpoint, so at 800px the projection panel is clipped. Pre-dates this phase; belongs to a layout pass, not the filmstrip.
- `docs/design/sample-frame.jpg` is CC BY-SA 4.0 (Berlin E-Prix, Steffen Prößdorf) and is used only in `docs/design/`. The live app does not ship it. Now called out explicitly in `LICENSE`, which this phase added.
- Each upload is analysed as its own run; the Kalman filter restarts rather than resuming stored history. Every demo path is a single upload.
- The 30-minute crossover horizon gate is unreachable through config (~26.7 min worst case). Kept as a guard, tested via the `horizon_s` parameter.
- Zero-shot still cannot separate dry from damp. Demo the trend, not the label.
- The synthetic `drying` sample ends on near-white frames, so the camera monitor and the last filmstrip cells wash out at the end of that clip. It is the generated footage, not the renderer.
- The rail's `280 FRAMES · 01:10` label is clipped by the playhead when the playhead reaches the far right.
- Two design variants remain in `docs/design/`; the workstation is the one built.

## Run it

```bash
# terminal 1 — backend
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# terminal 2 — frontend
cd frontend && npm run dev
# open http://localhost:3000 and click a sample clip

# regenerate the typed client after any backend schema change
cd frontend && npm run gen:api

# checks
cd backend && ../.venv/bin/python -m pytest tests/ -q
cd frontend && npm test && npx tsc --noEmit && npm run lint && npm run build
```
