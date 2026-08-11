# STATE

Last updated: 2026-08-11 · after Phase 1

## Position
- Phases complete: 0 (scaffold + feasibility probe), 1 (backbone)
- Next phase: 2 — Intelligence layer (SPEC-ANALYSIS B.1–B.7 as pure modules, synthetic-signal tests first)
- Blockers: none

## Hard measurements
- Device: mps (Apple Silicon, torch 2.13.0, transformers 5.15.0). This Mac is the demo machine.
- Single-frame classification: 18.5 ms median (Step 0.3, standalone probe). Warmup path in `/api/health` reports the live per-frame figure each boot.
- Model cold load: 43.0 s first ever; ~3 s from `backend/.cache/` since.
- Realtime viable (Phase 4): yes — ~13x under the 250 ms cutoff, measured on the demo machine.
- Phase 1 test suite: 19 passed in 12.9 s.

## Decisions made and why
- Text embeddings precomputed once at startup, image embeddings per frame — removes the text tower from per-frame cost. `test_classify_matches_clips_own_single_shot_path` pins the result against `processor(text=…, images=…)` to ±1e-3, because a miscalibration here would be invisible and would poison every downstream TWI.
- `_features()` shim in `classifier.py`: transformers 4.x returned a tensor from `get_*_features`, 5.x returns `BaseModelOutputWithPooling` with the projection in `.pooler_output`. requirements.txt allows both, so both are handled rather than accidentally pinned.
- SAMPLE_FPS 4.0 — track conditions move over tens of seconds, so 4 Hz is ample resolution and cuts inference ~7x versus 30fps source. Phase 2's Kalman assumes roughly this arrival rate.
- FRAME_MAX_EDGE 640 — CLIP only sees 224px, but Phase 2's Laplacian blur metric needs more detail than 224 to tell defocus from motion blur, and 640 doubles as the UI thumbnail.
- CLASSIFY_BATCH_SIZE 16 — amortises per-call overhead without a memory spike on an 8GB machine.
- `WW_DEVICE` env override — mps is fast but the least battle-tested torch backend. `WW_DEVICE=cpu` is the mid-demo recovery lever, not a debugging session on stage.
- `WW_DATA_DIR` env override — `backend/conftest.py` points it at a temp dir so tests never touch dev data.
- Classifier tests assert the interface contract (valid distribution, determinism, batch-invariance, calibration), never which class wins. An accuracy assertion on zero-shot output would be a flaky test wearing a guarantee's clothes.
- Video upload extracts and classifies synchronously and returns a `job_id`. Honest about it in the code comment: Phase 4 makes it a real background job.
- httpx2 over httpx — starlette's TestClient deprecated plain httpx and warned on every run.

## Rejected, do not revisit
- Wikimedia direct thumbnail URLs without a User-Agent header — HTTP 403. Use the Commons API (`action=query&generator=search`) with a UA.
- COCO cats as a probe image — times the pipeline fine, proves nothing about the four prompts. Sanity checks use real road imagery.
- A separate `/api/classify` endpoint for the single-image proof — `POST /api/sessions/{id}/frames` is already in SPEC-API and does the job. Don't invent endpoints the contract doesn't have.

## Known broken / deferred
- Zero-shot dry-vs-damp is weak: clean dry asphalt scored dry=0.305 / damp=0.406 (argmax wrong). Wet and standing water are confident and correct — a real wet-road photo returns wet=0.894, a flooded road standing_water=0.640. Phase 2's temporal layer and Phase 9's probe exist to cover this. Never demo a single frame's label.
- `TrackState` is fully defined in `schemas.py` but nothing populates it — `GET /api/sessions/{id}` returns `state: null` until Phase 2.
- No thumbnails written yet; `thumbnail_url` stays null until the timeline needs it in Phase 7.
- No weather layer, so `/api/health` reports `weather_cache_age_s: null`. Phase 2.
- Target platform is macOS/zsh/`mps`. CLAUDE.md is correct; BUILD.md still carries the original Windows wording and is historical.

## Run it

```bash
# one-time: install backend deps into the repo-root venv
.venv/bin/pip install -r backend/requirements.txt

# tests (run from backend/)
cd backend && ../.venv/bin/python -m pytest tests/ -q

# server — http://127.0.0.1:8000/docs for the interactive API
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# health check, in a second terminal
curl -s http://127.0.0.1:8000/api/health
```
