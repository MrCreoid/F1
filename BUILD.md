# BUILD.md — Weather Whiplash

**Drop this file into an empty folder. Open Claude Code there. Send exactly this:**

> Read BUILD.md in full, then execute Step 0. Stop when Step 0 is done.

Everything else is in the file. Claude Code drives; you approve.

---
---

# AGENT INSTRUCTIONS — everything below this line is for Claude Code

You are the lead engineer and design lead on a hackathon build that has to win. Not a demo — a product a Formula 1 race engineer could plausibly have open on the pit wall. Work to the standard of a senior studio: opinionated, precise, allergic to anything templated.

The human is a second-year CS student on Windows who has never used Linux, is new to ML, and is short on time. Optimise for working checkpoints, honest failure reports, Windows-first commands, and never handing back code you haven't run.

---

# STEP 0 — BOOTSTRAP (do this, then stop)

## 0.1 Discover your tools

Enumerate every skill available to you. If a `find-skills` skill exists, use it. Report the list with a one-line description each.

Then bind them to this build and tell me the bindings:

- Any **frontend / UI / UX / design** skill → mandatory for Phases 5–8. Do not build a single component without invoking it. If several exist, use the most specialised.
- Any **task-tracking / observer / progress** skill → run across the whole build so phase state survives context loss.
- Any **memory / persistence** skill → record every design decision, tuned constant, and rejected alternative. When I ask in six hours why `Q` is 0.4, the answer must exist.
- Any **research / docs-lookup** skill → use before guessing at a library API. Never guess.
- Any **planning / decomposition** skill → run at the head of every phase.

If a capability I've assumed doesn't exist, say so plainly rather than pretending.

## 0.2 Write the scaffold

Create these from the appendices at the bottom of this file. Copy the substance exactly; do not paraphrase.

```
CLAUDE.md                    ← Appendix A. Project law. Reloaded every session.
docs/SPEC-ANALYSIS.md        ← Appendix B. The maths.
docs/SPEC-API.md             ← Appendix C. The contract.
docs/SPEC-DESIGN.md          ← Appendix D. Art direction.
docs/PHASES.md               ← Appendix E. The build plan.
docs/STATE.md                ← Appendix G. Where we are. Rewritten after every phase.
.claude/commands/phase.md    ← Appendix F
.claude/commands/prove.md    ← Appendix F
.claude/commands/hostile.md  ← Appendix F
.claude/commands/slop.md     ← Appendix F
.gitignore                   ← .env, .cache/, node_modules/, __pycache__/, *.db
```

Then `git init` and commit: `chore: project constitution and specs`.

## 0.3 Prove the machine can do this at all

Before any architecture, run a throwaway script that downloads `openai/clip-vit-base-patch32`, loads it, and classifies one test image against the four appearance prompts.

Report as real measured output:

1. Did it load? Paste the actual result.
2. Which torch device resolved — cuda, cpu, or mps.
3. **Wall-clock milliseconds for a single frame classification.**

That third number decides whether realtime streaming is viable. If it's above ~250ms, say so now and propose the batch-and-replay fallback instead. Learning this on day one is worth more than anything else in Step 0.

If the model fails to load, stop and report why. Never substitute a different model.

## 0.4 Stop

Report skill bindings, files created, the three measurements, and the two riskiest things you see in this plan. Then wait.

---

# THE PRODUCT

**Weather Whiplash** — a live track condition detector.

Track conditions change faster than any weather report. A race engineer needs to know, right now, whether the track is getting safer or riskier, and whether to box for a tire change.

Ingest trackside or onboard frames (uploaded video, image sequence, webcam). Classify surface state per frame. Fuse that noisy signal into a stable continuous **Track Wetness Index**. Derive whether conditions are improving or deteriorating. Project forward to estimate when the track crosses a tire-change threshold. Issue a pit call with a confidence level.

The output that matters is one sentence:

> *Track drying. Crossover to slicks in 4:30. Confidence high.*

Every pixel in the UI exists to make that sentence trustworthy.

---

# THE THING THAT MUST NOT BE GOT WRONG

Most teams will classify each frame and print the label. That is a wrapper, and the rules disqualify wrappers.

**"Dry / damp / wet" is an appearance state. "Drying / wetting" is a temporal state. Different axes. Never the same classifier.**

- The vision model outputs four classes: `dry`, `damp`, `wet`, `standing_water`.
- Trend is *derived* from the time-derivative of the smoothed index. Never predicted.

If you find yourself adding "drying" as a fifth output class, stop. That is the exact error this architecture exists to prevent, and it is the error every other team will make.

---
---

# APPENDIX A — `CLAUDE.md`

```markdown
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

Windows, never used Linux. Every command PowerShell-first. No `make`, no POSIX shell
assumptions, no WSL requirement. Docker optional, never the only path.

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
2. Run `git log --oneline -10` to see what actually landed.
3. State in one line: last phase completed, next phase, any open blocker.
4. Then do what I asked.

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
```

---

# APPENDIX B — `docs/SPEC-ANALYSIS.md`

This is where the project wins. Each item is a separate pure function in `backend/app/analysis/`, unit-tested. Every constant lives in `config.py` with a comment.

### B.1 Track Wetness Index, 0–100

Never `argmax`. Weighted sum over the full distribution, so the index is continuous and can move smoothly:

```
TWI_raw = 100 * (0.00*p_dry + 0.35*p_damp + 0.75*p_wet + 1.00*p_standing_water)
```

Comment for the code: argmax discards the information that makes trend detection possible. 60% wet / 40% damp is meaningfully different from 95% wet, and that difference *is* the drying signal.

### B.2 Frame quality gate

Bad frames poison the trend. Per frame:

- **Blur** — variance of the Laplacian (`cv2.Laplacian(gray, cv2.CV_64F).var()`).
- **Exposure** — fraction of pixels clipped at 0 or 255. Glare off wet asphalt, tunnel exits.
- **Entropy** — `H = -Σ p log p`, normalised `H/log(K)`. Confidence `= 1 - H_norm`.

Combine into `frame_quality ∈ [0,1]`. Frames below 0.25 are still displayed but flagged and heavily downweighted — never silently dropped. The user must see *why* the system distrusts a moment.

### B.3 Adaptive smoothing — 1D Kalman filter

Not a rolling average; a rolling average lags exactly when responsiveness matters.

- State `[twi, twi_rate]`, constant-velocity model. The rate term gives you trend for free.
- Measurement noise `R` scales inversely with `frame_quality`. A blurry low-confidence frame barely moves the estimate; a crisp one moves it hard.
- Process noise `Q` tuned so a genuine 10-point swing tracks within ~15 seconds of footage.

Test: synthetic step change plus Gaussian noise, assert convergence within tolerance.

### B.4 Trend classification

Slope computed two ways, cross-checked:
- The Kalman rate term.
- OLS over the last `W` seconds of filtered TWI, keeping R².

```
rate < -1.5 TWI/min  → DRYING
rate > +1.5 TWI/min  → WETTING
otherwise            → STABLE
```

If OLS R² < 0.4 → `STABLE — INSUFFICIENT SIGNAL` regardless of slope. Never present a trend the data doesn't support.

### B.5 Crossover projection — the signature feature

```
t_cross = (TWI_threshold - TWI_now) / rate
```

Report only if `|rate| > 1.5` **and** `R² ≥ 0.4` **and** `t_cross` is within a 30-minute horizon.

Uncertainty band from the standard error of the OLS slope: compute `t_cross` at `rate ± 1.96·SE` for an optimistic/pessimistic window. The UI renders a cone, not a line.

Any gate fails → return `null`, and the UI says *"No reliable projection"*. Never fabricate a number. When a judge asks "how confident is that?", this is where you win or lose.

### B.6 Pit call with hysteresis

```
TWI  0–25  → SLICK
TWI 25–65  → INTERMEDIATE
TWI 65–100 → FULL WET
```

Naive thresholding flickers between compounds on the boundary — the exact failure a real strategist would mock. So:

- A recommendation changes only after crossing the boundary by a **margin of 6 points** *and* holding for **3 consecutive analysis windows**.
- Expose `windows_held` so the UI can show a call *arming* before it fires. That "about to change" state is the best visual moment in the product.

States: `HOLD` · `ARMING` · `BOX`.

Fifteen lines of code, and the single most convincing sign that someone thought about the problem rather than the demo.

### B.7 Weather fusion — real API, no key

**Open-Meteo**, `https://api.open-meteo.com/v1/forecast` — free, no API key, so nothing to leak or expire mid-demo. Request `precipitation`, `temperature_2m`, `wind_speed_10m`, `cloud_cover`, `relative_humidity_2m`.

Build a physical drying-rate prior: warm, windy, dry, clear → the track dries fast. Cold, humid, still, raining → it won't. Blend by visual confidence:

```
rate_final = w·rate_visual + (1−w)·rate_prior,   w = mean frame_quality over window
```

Surface the blend in the UI ("visual 78% / weather 22%"). Almost no team will show their fusion weights, and it takes ten minutes.

Cache 10 minutes. Ship a bundled JSON fallback so the demo survives a dead network.

### B.8 Hugging Face

- **Baseline, ships day one:** `openai/clip-vit-base-patch32` zero-shot against engineered prompts — *a dry asphalt racetrack surface* / *a damp racetrack with a darkened surface* / *a wet racetrack surface reflecting light* / *a racetrack with standing water and visible spray*. Prompts live in `config.py` as a tunable; the README shows the accuracy delta from tuning them.
- **Upgrade — this is what satisfies "balanced difficulty":** a **linear probe** on frozen CLIP embeddings, trained on our own labelled frames. Not from scratch, not a ready-made tool — precisely "somewhere in between." A few hundred frames is enough. Ship both with a runtime toggle so the accuracy jump demos live on stage.
- **Dataset:** ours. `scripts/build_dataset.py` extracts frames, auto-labels with CLIP, writes a review manifest. `scripts/label_tool.html` is a single-page keyboard-driven corrector (keys 1–4). Push as an `imagefolder` dataset with a card documenting label definitions and the auto-then-human process.
- **Publishing:** `scripts/push_to_hub.py` uploads probe + dataset with honest cards. Token from `HF_TOKEN`. Never hardcoded, never printed.
- **Inference:** local by default, weights cached in `backend/.cache/`. HF Inference API opt-in via env var.

---

# APPENDIX C — `docs/SPEC-API.md`

Define this before either side is written. Generate the TypeScript client from FastAPI's OpenAPI schema — never hand-write the types.

```
POST   /api/sessions                 → { session_id, created_at, name }
GET    /api/sessions/{id}            → session + frame history + current state
DELETE /api/sessions/{id}
POST   /api/sessions/{id}/video      multipart → { job_id, frame_count, duration_s }
POST   /api/sessions/{id}/frames     batch image upload
GET    /api/sessions/{id}/state      → TrackState
WS     /ws/sessions/{id}             live analysis stream
GET    /api/health                   → { model_id, mode, device, warm, weather_cache_age_s }
GET    /api/weather?lat=&lon=        → normalised weather + drying prior
```

`TrackState` — the single object the whole UI renders from:

```jsonc
{
  "session_id": "…",
  "timestamp": "2026-08-11T14:03:22Z",
  "twi": 47.3,
  "twi_raw": 51.8,
  "probabilities": { "dry": 0.11, "damp": 0.42, "wet": 0.39, "standing_water": 0.08 },
  "dominant_class": "damp",
  "trend": {
    "direction": "DRYING",
    "rate_per_min": -3.2,
    "r_squared": 0.81,
    "window_s": 45,
    "sufficient_signal": true
  },
  "crossover": {
    "target_compound": "SLICK",
    "threshold": 25.0,
    "eta_s": 270,
    "eta_optimistic_s": 205,
    "eta_pessimistic_s": 400
  },
  "recommendation": {
    "current": "INTERMEDIATE",
    "next": "SLICK",
    "state": "ARMING",
    "windows_held": 2,
    "windows_required": 3,
    "rationale": "TWI 47.3 falling at 3.2/min. Slick threshold in ~4m30s."
  },
  "frame_quality": { "score": 0.83, "blur": 142.6, "clipping": 0.02, "entropy": 0.31 },
  "fusion": { "visual_weight": 0.83, "weather_weight": 0.17, "weather_rate_prior": -2.1 },
  "frame_index": 128,
  "thumbnail_url": "/media/…/128.jpg"
}
```

`crossover` is `null` when gates fail. Every number the UI shows comes from this object. If the UI needs a value not here, add it to the schema — never compute analysis in the frontend.

---

# APPENDIX D — `docs/SPEC-DESIGN.md`

Invoke the UI/UX skill before building anything here. This half decides the outcome — judges see the interface before they read a line of code.

### D.1 What we deliberately do not do

The hackathon deck is red-on-black with italic condensed type. Every other team will clone it, because it's sitting right in front of them. Cloning the poster reads as derivative; looking like a real broadcast instrument reads as finished. That gap is second place versus first.

**Hard bans. Violating any is a bug:**

- No purple/indigo/violet gradients.
- No frosted glass as a default surface. At most one glass element in the entire app, if it earns it.
- No emoji. No sparkle icons. No "Powered by AI" badge.
- No symmetrical three-equal-cards hero. No 2×2 grid of identical tiles.
- No `rounded-3xl` on everything. Radii vary by role and stay small — this is an instrument.
- No pure `#000000` background, no pure `#FFFFFF` text.
- No drop shadows on flat dark surfaces. Depth comes from value steps and hairlines.
- No `transition: all`. No `linear` easing.
- No placeholder copy. Every string ships final.

### D.2 Direction — pit wall instrumentation, at night, in the rain

The reference is an FIA timing screen and a race engineer's laptop: dark, dense, quiet, legible from a metre away under floodlights. Colour carries meaning only, never decoration. A judge should read the track state from across the room without reading a word.

**Palette — six tokens, no others:**

```
--surface-base    #0E1114   graphite with a cool cast — wet asphalt at night
--surface-raised  #161A1F   panel fill, one clear value step up
--hairline        #262C33   1px borders, the only structural divider
--text-primary    #E8EBED   bone, never pure white
--text-muted      #7C8791   labels, units, secondary
--sodium          #FF7A1A   THE accent — trackside sodium floodlight orange
```

`--sodium` appears at most three times per screen. Choosing it over the obvious signal red is the one real risk in this design, and it's justified: red already carries meaning in motorsport (red flag = session stopped), so using it decoratively on a product about track safety would be semantically wrong. Orange is the colour of the lamps actually lighting a wet track at night. It belongs to the subject.

**State colours — semantic, on state indicators only, never on chrome:**

```
--state-dry       #C9D1D9   bone-silver
--state-damp      #E0A33E   amber
--state-wet       #3D7DBF   signal blue
--state-standing  #7B5CD6   deep violet, the extremity
--trend-improving #4FB477   sector green
--trend-worsening #D4574E   the ONLY red in the app
```

**Type — three faces, three jobs, all on Google Fonts:**

- **Archivo** 700–800, expanded width, uppercase, tight tracking → display numerals, section headers. Expanded-heavy grotesk is the timing-tower voice and nobody's default.
- **Inter Tight** 400/500 → body, labels, rationale.
- **IBM Plex Mono** 400/500, `font-variant-numeric: tabular-nums` → every telemetry readout.

**Every changing number in this app is tabular and monospaced.** Digits must not shift horizontally as they update. This one detail separates "instrument" from "webpage," and almost every team will miss it.

Scale, strict: `11 / 13 / 15 / 20 / 32 / 64 / 128`. The 128 is used exactly once — the TWI readout.

### D.3 Layout — asymmetric, weighted left

```
┌────────────────────────────────────────────────────────────────────┐
│ ▌WEATHER WHIPLASH      session · source · model        ● LIVE 24fps│  40px
├───────────────────────────────┬────────────────────────────────────┤
│                               │  CROSSOVER PROJECTION              │
│   [ live frame, full bleed ]  │  ╱ signature element ╲             │
│                               │  history solid → future dashed     │
│   ─── surface readout ───     │  uncertainty cone shaded           │
│                               │  threshold bands as zones          │
│    4 7.3                      │  countdown pinned to the crossing  │
│    TRACK WETNESS INDEX        │                                    │
│    DAMP · DRYING 3.2/min      ├────────────────────────────────────┤
│                               │  PIT CALL                          │
│                               │  compound · state · rationale      │
├───────────────────────────────┴────────────────────────────────────┤
│ ▐▐▐▐▐▐▐  frame timeline, wetness heat strip beneath  ▐▐▐▐▐▐▐▐▐▐▐▐▐ │  96px
└────────────────────────────────────────────────────────────────────┘
```

Left column bleeds to the viewport edge — no outer margin that side. The bottom timeline is a full-width editing rail, the vernacular of an engineer scrubbing footage. Below 1024px it stacks: frame, readout, projection, call, timeline.

### D.4 The signature element — Crossover Projection

Spend the design budget here. One memorable thing done properly beats six decorated panels.

- History: solid 2px line **that shifts hue as it crosses threshold bands** — the line is coloured by the condition it describes.
- Projection: same line continuing past *now* as 4px dashes at 50% opacity.
- Uncertainty: filled cone between optimistic and pessimistic, 12% opacity, widening with time — visually honest about decaying confidence.
- Threshold bands: full-width horizontal zones at 25 and 65, 4% opacity `--state-*`, labelled in Plex Mono at the right edge.
- Crossing point: small sodium marker with a monospace countdown that **ticks in real time between server updates** — client-side interpolation, so it feels live at 60fps instead of stepping once a second.
- **Null state keeps the panel.** Future region empties, and one Plex Mono line reads `NO RELIABLE PROJECTION · R² 0.22 BELOW THRESHOLD`. Showing the system's own uncertainty beats hiding it, and it's the best possible answer to a sceptical judge.

### D.5 Motion — one orchestrated sequence, then restraint

- **Load, 900ms, once:** hairlines draw in horizontally → panels fade up staggered 60ms → TWI numeral counts from 0 on a decelerating curve → chart line draws left-to-right → sodium accent arrives last.
- **Numerals never snap.** Spring interpolation, stiffness ~120, damping ~20.
- **State colour changes** cross-fade 400ms `cubic-bezier(0.4, 0, 0.2, 1)`.
- **`ARMING` is the emotional beat of the product.** Panel border pulses in the target compound's colour at 1.4s intervals; a segmented indicator fills — 2 of 3 windows held. The judge watches the system *decide*. Do not waste this on a static badge.
- `prefers-reduced-motion`: keep colour and layout, drop movement.
- **Idle is genuinely still.** Ambient animation with nothing happening is the loudest AI tell there is.

### D.6 Copy

Broadcast register. Terse, active, unhedged, no exclamation marks.

- Yes: `Track drying. Slicks viable in 4:30.` · `Signal degraded — heavy spray on lens.` · `Holding intermediates. Margin insufficient.`
- No: `Great news! The track is drying up!` · `Analyzing your data...` · `AI-powered insights`

Empty state instructs, never apologises: `Load footage to begin analysis.` with the three sample clips as one-click options. Errors name the failure and the fix: `Model not loaded. Run: python -m app.warmup` — never `Something went wrong.`

### D.7 Quality floor, unannounced

Responsive to 375px. Visible focus rings (sodium, 2px offset). Full keyboard reach. `aria-live="polite"` on the recommendation panel. Colour never the sole carrier of meaning — every state colour paired with a text label. Lighthouse accessibility ≥ 95.

---

# APPENDIX E — `docs/PHASES.md`

Stop after each. Commit after each. `/clear` before each.

**Stack:** FastAPI + PyTorch + transformers + OpenCV + SQLAlchemy/SQLite. Next.js 15 App Router + TypeScript strict + Tailwind + Framer Motion + Recharts. SQLite specifically because it needs zero setup and cannot fail to start during a demo.

### Phase 1 — Backbone
FastAPI with lifespan model loading and warmup. `config.py` with every constant commented. Pydantic schemas matching SPEC-API exactly. SQLAlchemy + SQLite. CLIP zero-shot over the four appearance classes, prompts in config. Video and image-sequence frame extraction via OpenCV. `/api/health`. Pytest on extraction and the classifier interface.
**Done when:** pytest output pasted green, `/api/health` curl pasted, single-image classification curl pasted, PowerShell repro commands given.

### Phase 2 — Intelligence layer
All of SPEC-ANALYSIS B.1–B.7 as separate pure modules. **Write the synthetic-signal tests first:** step change, noisy linear ramp, noisy plateau, 5-frame dropout. Assert the Kalman converges, the trend gate refuses low-R² slopes, and hysteresis does not flicker on a signal oscillating across a boundary. Then wire into a session pipeline: video → full TrackState history.
**Done when:** test output pasted, and a sample clip produces a plausible TWI curve shown as numbers.

### Phase 3 — Static design proof · 90 minutes maximum
One static page. No data, no API, no interactivity. The layout from SPEC-DESIGN D.3, real fonts loaded, real palette applied, hardcoded plausible numbers in every slot. **Invoke the UI/UX skill.**
*Why here:* leaving the design unverified until halfway through the build is the ordering flaw in most hackathon plans. Ninety minutes to de-risk the half judges see first is the best trade available.
**Done when:** the human has looked at it and approved the direction.

### Phase 4 — Realtime
`/ws/sessions/{id}` pushing TrackState per analysed frame, adaptive sampling for ≥8 analyses/sec on CPU. Backpressure: if inference falls behind, drop frames rather than queue, and report the drop rate in the payload. Client reconnect with exponential backoff. Persist every frame result so sessions replay after reload.
*If Step 0.3 measured >250ms per frame, skip this phase* — analyse server-side and replay on a timer. Visually identical during a demo, and it saves more time than anything else on the list.

### Phase 5 — Frontend shell
Design tokens as CSS custom properties + Tailwind theme extension. Fonts via `next/font`, correctly subset. The asymmetric layout, properly. Typed API client generated from the OpenAPI schema. WebSocket hook. Empty state and the three sample-clip loaders. **UI/UX skill mandatory.**

### Phase 6 — The signature element
Crossover Projection exactly as SPEC-DESIGN D.4. Recharts or hand-rolled SVG — justify by which gives cleaner control over the uncertainty cone and the hue-shifting line. Threshold bands, dashed projection, shaded cone, sodium crossing marker, client-interpolated 60fps countdown. Implement the null state as specified. **This is the panel judges remember. Treat it accordingly.**

### Phase 7 — Pit call and timeline
HOLD / ARMING / BOX with the arming pulse and segmented windows-held indicator. Bottom timeline: scrolling thumbnails, wetness heat strip beneath, current frame ringed sodium, low-quality frames hatched, click to scrub, arrow keys to step. `aria-live` on the recommendation.

### Phase 8 — Motion pass
The 900ms load sequence, once per session. Springs on every numeral. 400ms colour cross-fades. Then audit every transition in the codebase: no `transition: all`, no `linear`, no animation on an idle screen. `prefers-reduced-motion`. Report the sequence timing as a table.

### Phase 9 — Hugging Face
`build_dataset.py`, `label_tool.html` (keyboard 1–4, writes corrections back), `train_probe.py` (held-out split, confusion matrix), `push_to_hub.py` (model + dataset, honest cards). Runtime toggle between zero-shot and probe, exposed in `/api/health` and the UI, so the accuracy jump demos live.
*Budget two focused hours for labelling. It is the real time sink — build the tool early so it isn't what you're doing at 3am.*

### Phase 10 — Hardening
Offline weather fallback. Warmup with visible progress. Graceful CPU-only degradation. Timeouts and retries everywhere. `docs/DEMO.md`: 90-second runbook, exact click order, recovery plan per failure mode. Then run `/hostile` and produce a numbered list of everything that breaks, confuses, or looks unfinished.

### Cut order, if time runs out

Keep 1, 2, 3, 5, 6, 7. That is a complete, coherent, genuinely impressive product.
Then cut in this order: Phase 4 → Phase 9's probe (still publish the dataset; rule 3 is satisfied by a Hub model plus a published dataset) → most of Phase 8, keeping only spring numerals and colour cross-fades, which carry 80% of the polish.

### Where the marks actually are

The brief says clarity of presentation decides it. Weight accordingly:

1. The uncertainty cone. No other team will do uncertainty at all.
2. The null state that admits ignorance. **Demo the ambiguous clip on purpose.** When a judge asks "what if it's wrong?", you've already answered.
3. Hysteresis on the pit call.
4. Tabular numerals. One CSS line, and it's why the interface looks built rather than generated.

### Two honest warnings

Damp versus drying asphalt is the hardest visual distinction in this problem, and CLIP zero-shot will be shaky at it. That's fine — it's *why* the temporal layer exists — but never let the demo hinge on one frame's label. **Demo the trend, not the label.**

And the labelling is the real time sink, not the code.

---

# APPENDIX F — `.claude/commands/`

**`phase.md`**
```
Build phase $ARGUMENTS from @docs/PHASES.md.

First: state what you'll create, what you'll modify, and the riskiest part. Invoke the
relevant bound skills. Then build.

When done: run the tests, paste the output, give me the exact PowerShell command to see
it working myself.

Then rewrite @docs/STATE.md completely and commit it with the phase work. Then stop.
Do not start the next phase.
```

**`prove.md`**
```
Don't describe what the code does. Run it.

Execute the tests, or start the server and hit the endpoint. Paste actual output —
pytest results, curl bodies, log lines. If anything fails, fix it and run again.
Report only what you have observed, never what you expect.
```

**`hostile.md`**
```
You are a hostile judge with fifteen years in ML and a bias against hackathon
vapourware. Walk the whole repo.

Find every place we've overclaimed, hardcoded a value that should be computed, swallowed
an error, or shipped something that only works on the sample clips.

Rank by how badly it would embarrass us on stage. Cite file and line. Be brutal.
```

**`slop.md`**
```
Audit the frontend against the hard bans in @docs/SPEC-DESIGN.md D.1 as a checklist.
List every violation with file and line.

Then hunt uniformity — everything the same size, radius, weight, spacing. That
flattening is the most common tell. Fix by making one element decisively dominant and
demoting the rest. Show before/after for each change.
```

---

# APPENDIX G — `docs/STATE.md`

Create it now with the content below. Rewrite it in full at the end of every phase — never append. A stale state file is worse than none, because it will be trusted.

Keep it under 40 lines. It is a status board, not a diary.

```markdown
# STATE

Last updated: <date> · after Phase <n>

## Position
- Phases complete: <list>
- Next phase: <n> — <one-line name>
- Blockers: <none, or the specific thing>

## Hard measurements
- Device: <cuda | cpu | mps>
- Single-frame classification: <n> ms
- Realtime viable (Phase 4): <yes | no — using batch-and-replay instead>

## Decisions made and why
- <constant or choice>: <value> — <one line of reasoning>
- <e.g. Kalman Q: 0.4 — tracks a 10-point swing in ~14s on sample-2 without
  amplifying frame-to-frame noise below 5 points>

## Rejected, do not revisit
- <thing we tried> — <why it failed>

## Known broken / deferred
- <what, and which phase it belongs to>

## Run it
```powershell
<the exact commands to start backend and frontend>
```
```
