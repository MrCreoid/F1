# Weather Whiplash

Live track condition detector. Frames in → surface classification → stable wetness
index → trend → crossover projection → tire-change call with confidence.

Hackathon build. Judged on execution and clarity of presentation.

## Competition rules — these override everything

1. Real frontend AND real backend, genuine network boundary between them. Notebook-only
   or backend-only is disqualified. Never call a model from browser JavaScript.
2. Not one ready-made tool called once. Not a model trained from scratch. The
   intelligence lives in the temporal reasoning layer above the classifier.
3. Hugging Face must be used and visible: a Hub model for inference, plus a dataset and
   a model we publish ourselves. Not a hidden import.
4. Must run with no internet. Every network dependency needs a local fallback.

## The one modelling rule

Appearance and trend are different axes. The vision model outputs exactly four classes:
dry, damp, wet, standing_water. Trend is DERIVED from the time-derivative of the
smoothed index — never a predicted class. If you are adding "drying" as a fifth class,
stop.

## Working agreement

- Plan before every phase. Show the plan. Wait.
- One phase at a time. Stop at the end of each and wait for approval.
- More than ~8 files in a phase: stop at 8 and check in.
- NEVER report complete without running it. Paste real output — pytest results, curl
  bodies, log lines. "Should work" is not done.
- About to guess at an API, model ID, or library signature? Stop and say so.
- Spec wrong or over-scoped? Say so before building. Cutting scope beats half-building.
- Use the bound skills. Frontend work without the UI skill is a bug.

## Technical law

- Python: full type hints, Pydantic v2 at every boundary.
- TypeScript: strict true. No `any`. No `@ts-ignore`.
- Every analysis function pure and unit-tested against synthetic signals: step change,
  linear ramp with noise, noisy plateau, sensor dropout.
- No magic numbers inline. Every tunable in `backend/app/config.py` with a comment
  explaining the value.
- Every network call: timeout, exponential-backoff retry, local fallback.
- `.env` gitignored in commit #1. No secret ever logged, printed, or committed.
- Conventional commits, one per logical unit.

## Environment

macOS, Apple Silicon, zsh. New to the shell — every command copy-pasteable, run from the
repo root, no `make`, no Docker requirement, no assumed global installs. One Python venv
at `.venv/` for backend and scripts; `nvm`/`node` for the frontend.

Torch resolves to `mps` here, not `cuda`. Device selection must be
`cuda → mps → cpu` and must never assume the GPU path exists — the demo machine is this
Mac.

Models run locally via transformers + torch, cached in `backend/.cache/`. Local-first
is deliberate: venue Wi-Fi will fail, and rate limits during judging would be fatal.

## Pinned model IDs — never substitute

- `openai/clip-vit-base-patch32`     zero-shot baseline
- `google/siglip-base-patch16-224`   optional second backbone, only if time allows

ID fails to resolve → report which one and stop. Never invent a replacement. There is
no ready-made Hub dataset for this task; we build and publish our own.

## Where we are

@docs/STATE.md

This file is the single source of truth for build progress. Read it before doing
anything. It is deterministic — memory plugins, session summaries, and your own recall
are all secondary to it. If STATE.md and your recollection disagree, STATE.md is right.

## Every session starts like this

1. Read @docs/STATE.md.
2. Read @docs/HANDOFF.md for the ordered plan and the traps that waste an hour each.
   STATE.md is where we are; HANDOFF.md is where we're going. STATE.md wins on conflict.
3. Run `git log --oneline -10` to see what actually landed.
4. State in one line: last phase completed, next phase, any open blocker.
5. Then do what I asked.

## Every phase ends like this

1. Rewrite @docs/STATE.md completely — not an append, a rewrite. Stale state is worse
   than no state.
2. Commit it with the phase work.
3. Only then report done.

A phase is not complete until STATE.md reflects reality.

## Specs — load on demand

@docs/SPEC-ANALYSIS.md · @docs/SPEC-API.md · @docs/SPEC-DESIGN.md · @docs/PHASES.md

## Done

A stranger opens the app, clicks one sample clip, and within ten seconds understands
what the track is doing, what the system recommends, and how much it trusts itself —
with nobody explaining the interface to them.
