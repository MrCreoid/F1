# DEMO — 90 seconds

Every number here was measured on this machine, not estimated. If something disagrees
with what is on screen, the screen is right and this file is stale.

---

## Before anyone is watching

```bash
# terminal 1
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000

# terminal 2
cd frontend && npm run dev
```

Wait for the status bar to read **READY** with a millisecond figure beside it. Cold start
is about 12 seconds — the port does not open until the model is loaded and warmed, so
until then the app says *Backend starting*, which is correct and not an error.

Then **click the drying clip once and let it analyse**, so the weights and the weather
cache are hot. Reload the page before you present. A first analysis takes 3.0s; a second
takes the same, but the very first request of the process pays for lazy kernel
compilation on `mps` and you do not want to discover that on stage.

Open at **1440×860 or wider**. Below 1024px the layout stacks correctly, but the
three-column instrument is the thing worth showing.

---

## The 90 seconds

The order is deliberate: it works, then it admits it does not know, then it gets worse.
Ending on "conditions deteriorating" leaves the product looking useful rather than tidy.

### 0:00–0:10 — the empty state

> "Live track condition detector. Frames in, tyre call out. Three clips — let's take the
> one where the track dries."

Click **01 · DRYING LINE**. Analysis takes **3.0 seconds** for 300 frames.

### 0:10–0:30 — what it landed on

The app opens on the **last** frame, not the first. That is deliberate: you are looking
at the end state, and you scrub back to see how it got there.

> "Track wetness 25.3, falling at 63 a minute. It's on slicks now. Started at 74.6 —
> full wets."

Point at the **crossover projection**: history solid, coloured by the condition it
describes, shifting hue as it crosses each threshold band.

### 0:30–0:55 — the pit call arming *(the money shot)*

**Do not press play.** Replay runs at 4 fps — one second on screen is one second of
footage — and the first call does not fire until 56 seconds in. Scrub instead.

Click the timeline at roughly **three-quarters along**, then use **← →** to land on
frame 222. Step forward one frame at a time:

| frame | t | what shows |
|---|---|---|
| 222 | 55.5s | `ARMING` · FULL WET → INTERMEDIATE · 1 of 3 |
| 223 | 55.8s | `ARMING` · 2 of 3, segmented indicator filling |
| 224 | 56.0s | `BOX` · **INTERMEDIATE**, panel border sodium |
| 256 | 64.0s | `ARMING` · INTERMEDIATE → SLICK |
| 258 | 64.5s | `BOX` · **SLICK** |

> "It doesn't switch the moment the number crosses 25 — that would flicker on the
> boundary and any strategist would laugh at it. It has to clear the threshold by six
> points and hold for three windows. You can watch it arm."

**ARMING lasts two frames — half a second of footage.** Stepping is the only way to hold
on it. If you press play you will miss it.

### 0:55–1:15 — the clip that admits defeat

Reload the page. Click **03 · AMBIGUOUS**.

> "Same system, a damp track that never commits, spray on the lens."

Scrub anywhere in the middle. The projection panel says **NO RELIABLE PROJECTION** and
names the gate that actually failed — `R² 0.28 BELOW 0.40 THRESHOLD`.

> "It has a number. It's refusing to show it, because the fit doesn't support it. 54 of
> those 280 frames are degraded — you can see them hatched on the filmstrip."

Measured: **only 19 of 280 frames** produce a projection at all. This is the answer to
"what if it's wrong?", and it is why this clip is in the demo on purpose.

### 1:15–1:30 — conditions deteriorating

Reload. Click **02 · RAIN ARRIVING**. Scrub to around a third along, step to frame 100.

| frame | t | what shows |
|---|---|---|
| 100 | 25.0s | `ARMING` · INTERMEDIATE → FULL WET |
| 102 | 25.5s | `BOX` · **FULL WET** |

> "26 up to 86. Same hysteresis, same honesty, opposite direction."

---

## If asked

**"Is this just CLIP?"** — No. CLIP answers one question about one frame: what does this
surface look like. Everything that makes it useful is above that: a weighted index over
the full distribution rather than an argmax, a Kalman filter whose measurement noise
scales with frame quality, a slope cross-checked two ways, hysteresis, and a projection
that refuses to print when its gates fail.

**"Why no 'drying' class?"** — Appearance and trend are different axes. Drying is a
property of a sequence, not of a photograph. It is derived from the time-derivative of
the smoothed index, so it can be wrong in a way you can inspect.

**"How accurate is the classifier?"** — Zero-shot cannot reliably separate dry from
damp, and we say so. That weakness is measurable: over our own 400-image review queue it
labels 25 of 47 damp-sourced images as dry. That is why there is a temporal layer, and
why the dataset exists. **Demo the trend, not the label.**

**"What's the Hugging Face part?"** — `openai/clip-vit-base-patch32` runs locally for
inference, and we publish our own dataset built from freely-licensed Commons imagery
with per-image attribution. See `docs/DATASET.md`.

---

## Recovery, per failure mode

| symptom | cause | fix |
|---|---|---|
| Status bar stuck on **WARMING**, then `Backend unreachable` | backend not running, or died | restart terminal 1. The message names the exact command. |
| Panels render but stay empty, no error | Next dev is 403ing its own `/_next/static` chunks | `allowedDevOrigins` in `next.config.ts` must list `127.0.0.1`. Open `localhost:3000`, not `127.0.0.1:3000`. |
| `Another next dev server is already running` | a stale dev server | `pkill -f "next dev"` then `npm run dev` |
| Analysis is slow, or output looks wrong | `mps` misbehaving | `WW_DEVICE=cpu` in terminal 1 and restart. Slower, never wrong. |
| Weather panel blank or the request hangs | venue Wi-Fi failing rather than failing fast | `WW_OFFLINE=1` in terminal 1. Uses the bundled snapshot; nothing else changes. |
| `Sample footage missing` | broken checkout | `git checkout -- backend/samples` |
| Camera monitor says `No frame stored` | session analysed before the frame store existed | reload the clip |
| A clip fails to analyse | unreadable file | the error names the file. Use a bundled sample. |

**The single most useful recovery move is reloading the page and clicking a sample
again.** Analysis is 3 seconds and nothing is cached in a way that can go stale.

---

## What not to do

- **Do not press play and wait.** Replay is real-time; the beats are 25–65 seconds in.
- **Play does nothing when the playhead is already at the end**, which is where a clip
  opens. Scrub back first. It stops rather than looping on purpose — an instrument that
  silently restarted would misrepresent the data — but there is no message saying so.
- **Do not demo a single frame's label.** Dry versus damp is the known weak point. Show
  the curve, the trend, and the call.
- **Do not resize the window mid-demo.** It reflows correctly, but the filmstrip
  recomputes its cell count and the movement pulls the eye away from the point.
- **Do not open `127.0.0.1:3000`.** Use `localhost:3000`.
