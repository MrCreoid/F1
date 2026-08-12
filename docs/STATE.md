# STATE

Last updated: 2026-08-12 · after Phase 5

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer), 3 (design proof), 5 (frontend shell)
- Next phase: 6 — the signature element. The projection panel already renders threshold bands, the dashed projection, the shaded cone, the sodium crossing marker and the null state; Phase 6 owns the client-interpolated 60fps countdown and a polish pass on that panel.
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
- Backend suite: 54 passed in 14.4 s. Frontend: `tsc --noEmit` clean, `eslint` clean, `next build` succeeds.

## Decisions made and why
- **Next rewrites `/api/*` to FastAPI** rather than the browser calling :8000 directly. Same-origin means no CORS to configure and no backend host baked into client code; the boundary is still two processes over HTTP. `WW_BACKEND` splits them across machines.
- **`allowedDevOrigins: ["127.0.0.1", "localhost"]`** — without it Next dev 403s its own `/_next/static` chunks when the app is opened on `127.0.0.1`, so the client bundle never loads and every panel silently stays empty. Cost an hour; worth the comment in `next.config.ts`.
- **Archivo loads as a variable font with no fixed weight.** `next/font` rejects `axes` alongside `weight`, and the design drives the `wdth` axis directly.
- **Types are generated, never hand-written** — `npm run gen:api` runs `openapi-typescript` against the live schema. If the backend changes a field, the frontend stops compiling.
- **`GET /api/sessions/{id}/states`** returns every frame's full TrackState. This is what makes the transport controls real: play/step/scrub move an index through that history and every panel re-renders what the system knew at that frame.
- Replay runs at 4 fps, the analysis rate, so one second on screen is one second of footage. It stops at the end rather than looping — an instrument that silently restarts would misrepresent the data.
- The event log is **derived from state transitions**, not authored. Every row is a real change the backend reported.
- Sample clips are committed under `backend/samples/` (10 MB total), not generated at runtime. The demo must not depend on anything being produced on the night. Pixel grain was removed from the ambiguous clip — it was incompressible and pushed that file to 36 MB with no analytical benefit.

## Rejected, do not revisit
- Wikimedia thumbnail URLs without a User-Agent — HTTP 403.
- A separate `/api/classify` endpoint — `POST /api/sessions/{id}/frames` is already in the contract.
- Arithmetic mean for frame quality — one catastrophic factor must not be averaged away.
- An "unlit segment" ghost behind the TWI digits — at any readable opacity, 47.5 scanned as 47.8.
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
