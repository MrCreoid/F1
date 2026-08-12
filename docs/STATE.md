# STATE

Last updated: 2026-08-12 · after Phase 3 (second pass)

## Position
- Phases complete: 0 (scaffold + probe), 1 (backbone), 2 (intelligence layer), 3 (static design proof — **awaiting a pick between two variants**)
- Next phase: 4 — Realtime WebSocket, or skip to 5 per the cut list. Phase 5 must not start until one variant is chosen; it decides the whole component structure.
- Blockers: none technical. **Choose `design-proof.html` (restrained) or `design-proof-dense.html` (telemetry wall).**

## The two variants
- `frontend/design-proof.html` — "instrument". The D.3 layout, restrained, one dominant reading.
- `frontend/design-proof-dense.html` — **"engineering workstation"**, the current front-runner. Same information architecture as before, redesigned to a human brief: modern industrial skeuomorphism as the primary personality, Swiss/flat for all information, restrained neo-brutalist structure, micro-neumorphism confined to the transport controls, and glass used exactly once (the camera OSD, where layering is literal).
- Decorative maximalism was rejected outright: it breaks D.1 and fights the pit-wall concept. Maximalism here means density of *information*.

## SPEC-DESIGN amendment — human-approved 2026-08-12
The workstation brief conflicts with two clauses of SPEC-DESIGN D.1. The human's instruction overrides; both are deliberate, not drift:
- **"No drop shadows on flat dark surfaces"** — depth is now central to the design. Reconciled by using *inset* wells and edge-lighting (bright top lip, shadowed underside) rather than cards floating on outer shadows. The interface reads as machined, not layered.
- **"Six palette tokens, no others"** — a structural **material ramp** was added (`--mat-well/chassis/panel/raised`, `--rule`). The six *semantic* tokens are untouched and still carry all meaning; material values are surface-only, exactly as `--hairline` always was. Density is the only reading of "maximalism" that is on-theme here.

## Hard measurements
- Device: mps (Apple Silicon, torch 2.13.0, transformers 5.15.0). This Mac is the demo machine.
- Single-frame classification: 18.5 ms median (Step 0.3 probe).
- Full pipeline on a real 70s clip: 263 frames extracted, classified, filtered, trended, projected, persisted in **2.0 s** (~7.6 ms/frame).
- Kalman settling on a synthetic 10-point step under 3.0 TWI noise: Q 0.005→4.75s, 0.02→3.50s, **0.05→3.00s (chosen)**, 0.3→1.50s, 1.0→1.00s.
- Test suite: 54 passed in 15.4 s.
- Contrast, measured in-browser on the design proof: text-primary 15.8:1, text-muted 5.2:1 on base and 4.8:1 on raised, sodium 6.7:1, state-damp 8.6:1, trend-improving 7.3:1. All ≥4.5:1.

## Decisions made and why
- Kalman Q = 0.05 — every value tested clears the ~15s target, so the binding constraint is noise, not speed. 0.05 is where settling stops improving while still knocking 3.0 TWI of noise down to 0.9.
- Kalman R = 25.0 / max(quality, 0.02) — 25 is CLIP's observed ±5 TWI scatter squared.
- Rate stored per second internally, exposed **only** as `rate_per_min`, with a test pinning the unit.
- Frame quality is a weighted **geometric** mean of focus/exposure/confidence (0.40/0.20/0.40).
- Trend cross-check: OLS is the authority; sign disagreement with the Kalman rate forces STABLE.
- `WW_OFFLINE=1` keeps tests off the network and is the venue-Wi-Fi lever.
- **Phase 3 is one static HTML file, not a Next.js app.** The phase is time-boxed and explicitly has no data, no API and no interactivity; standing up the framework to render hardcoded numbers would have spent the box on scaffolding. Every token, type step and grid rule ports directly into Phase 5.
- Design proof numbers were made **internally consistent**, which meant departing from SPEC-API's illustrative example — that example is self-contradictory (twi 47.3 falling 3.2/min reaching the 25 threshold in 270s implies 5.0/min, and its stated entropy 0.31 does not match its own probabilities). The proof uses TWI 47.5, −5.0/min, threshold 25, ETA 4:30, which checks out, and a quality score of 0.62 derived from the actual `frame_quality` formula.
- Quality reads 0.62, not the spec example's 0.83, because mid-range TWI states are inherently higher-entropy — a genuinely damp track produces a spread distribution and the confidence term correctly penalises it. Showing 0.62 is the honest number and makes the fusion split (62% visual / 38% weather) more interesting than a fabricated 83%.
- **What "premium" actually meant here**, after the first pass was rejected: the fix was not more effects. It was (1) machined edges — a hairline plus one lighter top pixel, depth from value steps since shadows are banned on flat dark; (2) evidence of measurement everywhere — tick marks, ruled axes, a real time ruler, a segmented signal meter with a tick scale, units demoted but never omitted; (3) rebuilding the timeline.
- **The timeline was the worst thing on the page** — 18 copies of one photo at 34px reads as a contact sheet. Rebuilt as an editing rail: a ruler with minor ticks every 5s and majors every 15s, a strip of varied crops so frames read as successive moments, degraded frames desaturated with a precise amber tick instead of crude 45° hatching, a continuous wetness ribbon instead of discrete blocks, and a sodium playhead spanning the full rail height. The redundant footer row was cut to give the strip its height back inside the spec's 96px.
- Six palette tokens enforced literally. The only raw hex outside them is the timeline heat ramp, which interpolates *between* state tokens to encode a continuous index — data, not chrome, and commented as such.
- Fonts load from the Google CDN in the proof only. Phase 5 self-hosts via `next/font`, which is what satisfies the offline rule.

## Rejected, do not revisit
- Wikimedia direct thumbnail URLs without a User-Agent — HTTP 403. Use the Commons API with a UA.
- COCO cats as a probe image — proves nothing about the four prompts.
- A separate `/api/classify` endpoint — `POST /api/sessions/{id}/frames` is already in the contract.
- Arithmetic mean for frame quality.
- The first sample frame (a city street puddle) — read as stock photography, not trackside. Replaced with motorsport footage on a damp circuit.

## Known broken / deferred
- **Phase 3 needs sign-off.** Look at it before Phase 5 builds on the direction.
- The workstation redesign added three **transport controls** (step back / play / step forward) to the timeline. This is the only element on screen with no counterpart in the previous version. It is not new scope — PHASES.md Phase 7 already specifies "click to scrub, arrow keys to step" — but it is currently a visual affordance with no behaviour, and Phase 7 must wire it.
- Content parity between the old and new dense variants was verified by diffing visible text: **every number and word survived**; the only delta is the `<title>` and added metadata labels (codec, resolution, REC, "recommended action", "time to transition", "fused rate").
- Sample frame is Berlin E-Prix 2023 by Steffen Prößdorf, Wikimedia Commons, **CC BY-SA 4.0 — attribution required, and share-alike**. Fine for a hackathon demo with the credit that is in the HTML comment, but swap it for own footage or a CC0 image before publishing anything derived from it.
- The impeccable design detector runs **degraded** on this machine (htmlparser2, css-select, css-tree, domutils missing). It returned no findings, which is an undercount, not a clean bill. Contrast and palette were checked by hand instead.
- The 30-minute crossover horizon gate is unreachable through config — widest band at the minimum rate crosses in ~26.7 min. Kept as a guard, tested via the `horizon_s` parameter.
- Each upload is analysed as its own run; the Kalman filter restarts rather than resuming stored history. Every demo path is a single upload. Phase 4 removes it.
- Zero-shot still cannot separate dry from damp; the 70s clip's transition is detected late. Demo the trend, not the label.
- No thumbnails written; `thumbnail_url` null until Phase 7.
- The design proof has no null-projection state. SPEC-DESIGN D.4 requires the panel to persist with `NO RELIABLE PROJECTION · R² … BELOW THRESHOLD`; the R²/window slot exists in the proof's footer to hold it. Phase 6 builds it.
- BUILD.md still carries the original Windows wording and is historical.

## Run it

```bash
# design proof (Phase 3)
cd frontend && ../.venv/bin/python -m http.server 4173
# then open http://127.0.0.1:4173/design-proof.html

# tests
cd backend && ../.venv/bin/python -m pytest tests/ -q

# server — http://127.0.0.1:8000/docs
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# live weather + drying prior
curl -s "http://127.0.0.1:8000/api/weather" | python3 -m json.tool
```
