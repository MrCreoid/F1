# Weather Whiplash

**A live track-condition detector that tells you when to change tyres — and tells you
when it doesn't know.**

Frames in → surface classification → a stable wetness index → a trend → a crossover
projection with an uncertainty cone → a tyre call with hysteresis.

![The workstation at the moment a pit call fires](docs/screenshot.png)

---

## The idea

A vision model can tell you what a track surface looks like *right now*. That is not the
question a race engineer asks. They ask: **is it getting better or worse, how fast, and
when do I box?**

Those are different questions, and the gap between them is the entire product. Weather
Whiplash treats appearance and trend as separate axes:

- **Appearance** is what the model sees in one frame. Four classes, forever:
  `dry`, `damp`, `wet`, `standing_water`.
- **Trend** is never predicted. It is *derived* from the time-derivative of a smoothed
  index, which means it can be inspected, cross-checked, and — crucially — refused.

### A deliberate deviation from the brief

The problem statement lists the per-frame classes as *dry, damp, wet or **drying***.
This system does not classify "drying", and that is on purpose.

**Drying is not visible in a photograph.** A damp track that is drying and a damp track
that is about to get wetter look identical in a single frame — the difference is only
which way the number is moving. Ask a classifier to output "drying" and you are asking
it to guess at a time-derivative from one instant, and it will happily oblige with a
confident answer it has no evidence for.

So drying **is** delivered — as `DRYING`, `WETTING` or `STABLE`, computed from the slope
of the smoothed index over a 45-second window, cross-checked against a second estimator,
and suppressed entirely when the fit does not support it. You get the output the brief
asks for, from the only place it can honestly come from. The fourth appearance class is
`standing_water` instead, which *is* visible in one frame and is the condition that
actually causes aquaplaning.

That trade is the whole idea: appearance and trend are different axes, and keeping them
apart is what makes the trend inspectable, cross-checkable, and refusable.

## Why this isn't a wrapper around CLIP

CLIP answers one question about one frame. Everything that makes the output useful sits
above it:

| | what it does | why it matters |
|---|---|---|
| **Wetness index** | weighted sum over the *full* distribution, never `argmax` | 60% wet / 40% damp differs from 95% wet, and that difference **is** the drying signal |
| **Frame quality gate** | Laplacian blur, clipping, entropy → one score | spray on the lens must not silently poison the trend |
| **Kalman filter** | constant-velocity, measurement noise scaled by frame quality | a blurry frame barely moves the estimate; a crisp one moves it hard |
| **Trend** | OLS over a 45s window, cross-checked against the Kalman rate | two estimators; when they disagree on direction, the answer is "we don't know" |
| **Crossover projection** | `t = (threshold − twi) / rate`, with a cone from the slope's standard error | the cone widens with time because confidence decays with time |
| **Pit call** | hysteresis: clear the boundary by 6 points **and** hold 3 windows | naive thresholding flickers on the boundary; a real strategist would laugh at it |
| **Weather fusion** | blends a physical drying prior by mean frame quality | when the camera can't be trusted, physics carries more weight — and the UI shows the split |

Each of those is a separate pure function with unit tests against synthetic signals:
step change, noisy ramp, noisy plateau, sensor dropout.

## The part most projects skip

**It refuses to answer when it can't.** If the regression fit is weak, or the two rate
estimators disagree, or the crossing is beyond the horizon, the backend returns `null`
and the interface says so — naming *which gate actually failed*, not a stock message:

```
NO RELIABLE PROJECTION
R² 0.28 BELOW 0.40 THRESHOLD
```

On the deliberately ambiguous sample clip, only **19 of 280 frames** produce a
projection at all. That clip is in the demo on purpose. When someone asks "what if it's
wrong?", the answer is already on screen.

The same discipline applies to the rate readout: when the fit fails its gates, the
number is replaced by an em dash rather than printed to one decimal as though it were a
fact.

## Running it

Needs Python 3.11+ and Node. No Docker, no `make`, no global installs.

```bash
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

```bash
# terminal 1
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000

# terminal 2
cd frontend && npm run dev
```

Open <http://localhost:3000> and click a sample clip. First start loads and warms the
model (~12s); the port does not open until it is ready, and the interface says
*Backend starting* rather than pretending something is broken.

**It runs with no internet.** Fonts are self-hosted at build time, model weights are
cached under `backend/.cache/`, and the one live call (Open-Meteo, no API key) has a
timeout, bounded retries, a 10-minute cache, a bundled fallback snapshot, and a
`WW_OFFLINE=1` switch.

## Measured on the development machine

Apple Silicon, `mps`. Device selection is `cuda → mps → cpu` and never assumes a GPU.

| | |
|---|---|
| single-frame classification | **15.6 ms** (reported live by `/api/health`, not hardcoded) |
| 75-second clip, end to end | **300 frames in 3.0 s** |
| Kalman settling on a 10-point step | 3.0 s, holding plateau noise at 0.9 from 3.0 of measurement noise |
| tests | **113 backend, 10 frontend** |

`WW_DEVICE=cpu` forces the CPU path if `mps` misbehaves. Slower, never wrong.

## Architecture

A real network boundary: two processes, two languages, HTTP between them. **No model
code ever runs in the browser.**

```
Next.js 16 (:3000)  ──/api/*──►  FastAPI (:8000)  ──►  CLIP (local, cached)
   TypeScript strict                 Pydantic v2            transformers + torch
   Tailwind, hand-rolled SVG         SQLAlchemy/SQLite      OpenCV extraction
```

The browser only ever talks to one origin; Next rewrites `/api/*` and `/media/*` to the
backend, so there is no CORS to configure and no backend host baked into client code.
`WW_BACKEND` splits them across machines.

**The TypeScript client is generated, never hand-written** — `npm run gen:api` runs
`openapi-typescript` against the live OpenAPI document. If the backend changes a field,
the frontend stops compiling.

`GET /api/sessions/{id}/states` returns every frame's full `TrackState`. That is what
makes the transport controls real: play, step and scrub move an index through that
history, and every panel re-renders exactly what the system knew at that frame.

## Hugging Face

- **Inference:** [`openai/clip-vit-base-patch32`](https://huggingface.co/openai/clip-vit-base-patch32),
  zero-shot against four engineered prompts that live in `config.py` as a tunable.
- **Our own dataset:** built, not borrowed. `scripts/` fetches freely-licensed road-surface
  photographs from Wikimedia Commons with per-image licence and attribution, auto-labels
  them with CLIP, and queues them for human correction in a keyboard-driven tool. See
  **[docs/DATASET.md](docs/DATASET.md)**.

The auto-label is recorded separately from the human label, so the published card can
state exactly how many frames a reviewer changed. That number is the argument for the
dataset existing at all — zero-shot CLIP is weakest at precisely the distinction that
matters most here.

## Honest limitations

- **Zero-shot cannot reliably separate dry from damp.** It is the hardest visual
  distinction in this problem and we do not pretend otherwise. It is also *why* the
  temporal layer exists. Demo the trend, not the label.
- **The bundled sample clips are synthetic** — one photograph with its exposure ramped
  to simulate a track drying and wetting. They exercise the temporal layer honestly and
  are not training data.
- The dataset is small and single-annotator. Limitations are stated on the card itself.
- Each upload is analysed as its own run; the filter restarts rather than resuming
  stored history.

`docs/STATE.md` is the real status board, including everything currently known to be
broken. `docs/DEMO.md` is the runbook.

## Licence

MIT — see [LICENSE](LICENSE), which also names the third-party image assets and their
terms.
