# STATE

Last updated: 2026-08-12 · after Phase 2

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer)
- Next phase: 3 — Static design proof, 90 minutes maximum. Invoke the UI/UX skill. Needs human approval of the direction before Phase 5.
- Blockers: none

## Hard measurements
- Device: mps (Apple Silicon, torch 2.13.0, transformers 5.15.0). This Mac is the demo machine.
- Single-frame classification: 18.5 ms median (Step 0.3 probe).
- Full pipeline on a real 70s clip: 263 sampled frames extracted, classified, filtered, trended, projected and persisted in **2.0 s** end to end (~7.6 ms/frame).
- Kalman settling on a synthetic 10-point step under 3.0 TWI noise, measured across Q: 0.005→4.75s, 0.02→3.50s, **0.05→3.00s (chosen)**, 0.3→1.50s, 1.0→1.00s. Plateau noise std 0.85–1.19 across the same range.
- Realtime viable (Phase 4): yes, by a wide margin.
- Test suite: 54 passed in 18.6 s (19 Phase 1 + 35 Phase 2).

## Decisions made and why
- Kalman Q = 0.05 — every value tested clears the spec's ~15s target, so the binding constraint is noise, not speed. 0.05 is where settling stops improving much (3.0s) while still knocking 3.0 TWI of measurement noise down to 0.9.
- Kalman R = 25.0 / max(quality, 0.02) — 25 is CLIP's observed ±5 TWI frame-to-frame scatter squared. The floor stops a zero-quality frame dividing by zero.
- Rate is stored per second internally and exposed **only** as `rate_per_min`. A factor-of-60 error here is invisible in the UI, so a test asserts the unit directly on a known ramp.
- Frame quality is a weighted **geometric** mean of focus/exposure/confidence (0.40/0.20/0.40). Arithmetic would let two good factors average away one catastrophic one; a sharp, well-exposed frame that yields a coin-flip distribution is not a good frame.
- Trend cross-check: OLS is the authority (it has R²), but if the Kalman rate disagrees *in sign* and both exceed the threshold, the result is forced to STABLE / insufficient. Two estimators disagreeing means we do not know.
- `analysis/` is 6 modules grouped by axis, not 7 files one per spec item. SPEC-ANALYSIS asks for separate pure *functions*, and each B-item is a distinctly named function; one-function files would have been worse to read.
- `WW_OFFLINE=1` — keeps the test suite off the network, and is the lever for venue Wi-Fi that hangs rather than fails outright. A timeout costs seconds; a flag costs nothing.
- `FrameClassification` gained `twi` and `quality_score`. The Phase 6 projection chart plots TWI history, and SPEC-API's rule is to extend the schema rather than compute analysis in the frontend.
- Weather fusion uses mean frame quality over the trend window as the visual weight, and the blended rate feeds the projection. Direction is re-derived after fusion so the label always matches the number displayed beside it.

## Rejected, do not revisit
- Wikimedia direct thumbnail URLs without a User-Agent — HTTP 403. Use the Commons API with a UA.
- COCO cats as a probe image — proves nothing about the four prompts.
- A separate `/api/classify` endpoint — `POST /api/sessions/{id}/frames` is already in the contract.
- Arithmetic mean for frame quality — see above.

## Known broken / deferred
- **The 30-minute crossover horizon gate is unreachable through config.** Widest band (40 TWI) at the minimum reportable rate (1.5/min) crosses in ~26.7 min, inside the 1800s limit. Kept as a guard against future threshold changes and tested via the function's `horizon_s` parameter, not pretended to be live.
- Each upload is analysed as its own run — the Kalman filter restarts rather than resuming a session's stored history, because quality-weighted filtering needs the frame images and those are not persisted. Every demo path is a single upload, so nothing visible is affected. Phase 4's live per-session filter removes it.
- Zero-shot still cannot separate dry from damp. On the 70s cross-fade clip the index held ~72 for the first 45s and only moved once the fade was well advanced — the transition is detected late. This is the known weakness; the temporal layer is what makes it survivable, and Phase 9's probe is the fix. Demo the trend, not the label.
- No thumbnails written; `thumbnail_url` is null until Phase 7.
- `next` is null on a BOX result. The compound has already changed by then, so there is nothing pending — but the UI may want the previous compound for the "INTERMEDIATE → SLICK" readout. Revisit in Phase 7.
- BUILD.md still carries the original Windows wording and is historical. CLAUDE.md is correct: macOS/zsh/mps.

## Run it

```bash
# one-time
.venv/bin/pip install -r backend/requirements.txt

# tests
cd backend && ../.venv/bin/python -m pytest tests/ -q

# server — http://127.0.0.1:8000/docs
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# live weather + drying prior
curl -s "http://127.0.0.1:8000/api/weather" | python3 -m json.tool

# analyse a clip end to end
SID=$(curl -s -X POST http://127.0.0.1:8000/api/sessions -H "Content-Type: application/json" \
  -d '{"name":"test"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
curl -s -X POST "http://127.0.0.1:8000/api/sessions/$SID/video" -F "file=@yourclip.mp4"
curl -s "http://127.0.0.1:8000/api/sessions/$SID" | python3 -m json.tool
```
