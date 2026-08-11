# STATE

Last updated: 2026-08-11 · after Phase 0 (bootstrap)

## Position
- Phases complete: 0 (scaffold + feasibility probe)
- Next phase: 1 — Backbone (FastAPI, config, Pydantic schemas, SQLite, CLIP zero-shot, OpenCV extraction, /api/health)
- Blockers: none technical. One open question: BUILD.md/CLAUDE.md declare a Windows/PowerShell environment, but this repo is being built on macOS (Darwin arm64). Confirm which machine ships the demo before Phase 1 fixes commands and device handling.

## Hard measurements
- Device: mps (Apple Silicon, torch 2.13.0). No CUDA on this host.
- Single-frame classification: 18.5 ms median, full pipeline (preprocess + text encode + image encode + softmax), 10 runs after warmup. Forward-only on 640px Commons images: 27.6 ms.
- Model cold load: 43.0 s first time (download + init); weights now cached in `backend/.cache/`.
- Realtime viable (Phase 4): yes — 18.5 ms is ~13x under the 250 ms cutoff. Caveat: measured on mps, not on the Windows CPU box.

## Decisions made and why
- CLIP loaded with `cache_dir=backend/.cache` — matches CLAUDE.md local-first rule, survives venue Wi-Fi failure.
- Text prompts encoded per call in the probe; Phase 1 must precompute the four text embeddings once at lifespan startup — they never change, and that removes ~half the per-frame cost.
- venv at repo root `.venv/` (gitignored) rather than per-package, one interpreter for backend + scripts.
- Probe scripts kept in scratchpad, not committed — throwaway per BUILD.md 0.3.

## Rejected, do not revisit
- Wikimedia direct thumbnail URLs without a User-Agent header — HTTP 403. Use the Commons API (`action=query&generator=search`) with a UA when pulling reference imagery.
- COCO cats as the probe image — measures latency fine, proves nothing about the four prompts. Any future sanity check uses real road imagery.

## Known broken / deferred
- Zero-shot dry-vs-damp separation is weak: a clean dry asphalt texture scored dry=0.305 / damp=0.406 (argmax wrong). Wet (0.857) and standing_water (0.783) were confident and correct. This is the exact weakness PHASES.md warns about — Phase 2's temporal layer and Phase 9's linear probe exist to cover it. Do not demo a single frame's label.
- No backend/frontend code exists yet. Nothing to run.
- Windows/PowerShell command paths untested — see blocker above.

## Run it

```powershell
# Nothing to run yet — Phase 1 has not been built.
# Probe reproduction (macOS shell used for the numbers above):
#   .venv/bin/python scratchpad/clip_probe.py
```
