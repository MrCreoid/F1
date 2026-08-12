# STATE

Last updated: 2026-08-12 · after Phase 6

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer), 3 (design proof), 5 (frontend shell), 6 (signature element)
- Next phase: 7 — pit call and timeline: per-frame thumbnails, the wetness heat strip over real images, low-quality hatching, arrow-key stepping already works.
- Phase 4 (WebSocket realtime) is **skipped**, per the cut list. `GET /api/sessions/{id}/states` plus client replay gives the same thing visually — PHASES.md says batch-and-replay is "visually identical during a demo".
- Blockers: none.

## Competition rules — current standing
- **Rule 1 (real frontend + backend, genuine boundary): SATISFIED.** Next.js 16 app on :3000, FastAPI on :8000, separate processes, HTTP between them. No model code in the browser.
- **Rule 2 (not a wrapper): SATISFIED.** The temporal layer is the product.
- **Rule 3 (Hugging Face visible + our own published dataset/model): NOT YET.** `scripts/` still does not exist. This is the remaining rule gap. Minimum fix is publishing the dataset.
- **Rule 4 (runs with no internet): SATISFIED for the app.** Fonts are self-hosted by `next/font` at build time, weights are cached in `backend/.cache/`, weather has timeout + backoff + a bundled fallback + `WW_OFFLINE=1`. The remaining live call is Open-Meteo, which degrades correctly.

## Hard measurements
- Device: mps. Single-frame classification 18.5 ms. Full 70s clip: 263 frames end to end in 2.0 s.
- Kalman Q = 0.05 — settles a 10-point step in 3.0 s, holds plateau noise at 0.9 from 3.0 of measurement noise.
- Backend suite: 54 passed in 14.3 s. Frontend: 8 chart tests pass, `tsc --noEmit` clean, `eslint` clean, `next build` succeeds.

## Decisions made and why
- **Next rewrites `/api/*` to FastAPI** rather than the browser calling :8000 directly. Same-origin means no CORS to configure and no backend host baked into client code; the boundary is still two processes over HTTP. `WW_BACKEND` splits them across machines.
- **`allowedDevOrigins: ["127.0.0.1", "localhost"]`** — without it Next dev 403s its own `/_next/static` chunks when the app is opened on `127.0.0.1`, so the client bundle never loads and every panel silently stays empty. Cost an hour; worth the comment in `next.config.ts`.
- **Archivo loads as a variable font with no fixed weight.** `next/font` rejects `axes` alongside `weight`, and the design drives the `wdth` axis directly.
- **Types are generated, never hand-written** — `npm run gen:api` runs `openapi-typescript` against the live schema. If the backend changes a field, the frontend stops compiling.
- **`GET /api/sessions/{id}/states`** returns every frame's full TrackState. This is what makes the transport controls real: play/step/scrub move an index through that history and every panel re-renders what the system knew at that frame.
- Replay runs at 4 fps, the analysis rate, so one second on screen is one second of footage. It stops at the end rather than looping — an instrument that silently restarts would misrepresent the data.
- The event log is **derived from state transitions**, not authored. Every row is a real change the backend reported.
- Sample clips are committed under `backend/samples/` (10 MB total), not generated at runtime. The demo must not depend on anything being produced on the night. Pixel grain was removed from the ambiguous clip — it was incompressible and pushed that file to 36 MB with no analytical benefit.

## Phase 6 — the signature element
- **Hand-rolled SVG, not Recharts.** The cone is a polygon whose three vertices come from `eta_s`, `eta_optimistic_s` and `eta_pessimistic_s` — three separate scalars, not a series Recharts can plot. The stroke needs a gradient whose stops are computed from where the data crosses 25 and 65. Neither is expressible without escape hatches, and it avoids a dependency.
- **The line shifts hue at each band crossing** (D.4). `conditionStops()` finds the exact crossing x by linear interpolation and emits paired stops at the same offset, so the transition is a hard edge — the track is either side of a threshold, never smeared across it. History and projection share one gradient so colour carries continuously across *now*.
- **The countdown interpolates at 60fps** against wall time and re-syncs on each new backend value. Verified in-browser: 02:58.2 → 02:58.1 → 02:58.1, then a jump to 02:31.5 as a new frame landed. It only runs while replay is advancing — paused, it shows exactly what the backend said for that frame, because an instrument must not invent time that is not passing.
- **The null state names the gate that actually failed.** The first version printed "R² below threshold" whenever there was no crossover, which was a lie in the common case: a track already under 25 while drying has a fine R² and a steep rate. `projectionGap()` mirrors B.5's gates in order and distinguishes low fit, disagreeing estimators, a shallow rate, being past the last boundary, and the horizon. Caught by looking at the running app, which showed "R² 0.72 BELOW THRESHOLD" next to a readout saying R² 0.72 and Signal *Sufficient*.
- `lib/chart.ts` is pure and covered by 8 node:test assertions — the only frontend logic with real branching.

## Rejected, do not revisit
- Wikimedia thumbnail URLs without a User-Agent — HTTP 403.
- A separate `/api/classify` endpoint — `POST /api/sessions/{id}/frames` is already in the contract.
- Arithmetic mean for frame quality — one catastrophic factor must not be averaged away.
- An "unlit segment" ghost behind the TWI digits — at any readable opacity, 47.5 scanned as 47.8.
- A single stock reason for a missing projection — it misreports the common case.
- Browser-direct calls to :8000 — replaced by the Next rewrite.

## Known broken / deferred
- **Rule 3 is the open gap.** No `build_dataset.py`, `label_tool.html`, `train_probe.py` or `push_to_hub.py`. Phase 9.
- **The sample frame image is CC BY-SA 4.0** (Berlin E-Prix, Steffen Prößdorf) and is now only used in `docs/design/`. The live app does not ship it. Still worth replacing before publishing, and there is no LICENSE file in the repo.
- No per-frame thumbnails, so the camera monitor reads "Frame store offline · Phase 7" rather than showing a decorative placeholder, and the timeline strip encodes wetness instead of images. Phase 7.
- Each upload is analysed as its own run; the Kalman filter restarts rather than resuming stored history. Every demo path is a single upload.
- The 30-minute crossover horizon gate is unreachable through config (~26.7 min worst case). Kept as a guard, tested via the `horizon_s` parameter.
- Zero-shot still cannot separate dry from damp. Demo the trend, not the label.
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
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```
