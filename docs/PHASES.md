# PHASES

Stop after each. Commit after each. `/clear` before each.

**Stack:** FastAPI + PyTorch + transformers + OpenCV + SQLAlchemy/SQLite. Next.js 15 App
Router + TypeScript strict + Tailwind + Framer Motion + Recharts. SQLite specifically
because it needs zero setup and cannot fail to start during a demo.

### Phase 1 — Backbone
FastAPI with lifespan model loading and warmup. `config.py` with every constant commented.
Pydantic schemas matching SPEC-API exactly. SQLAlchemy + SQLite. CLIP zero-shot over the
four appearance classes, prompts in config. Video and image-sequence frame extraction via
OpenCV. `/api/health`. Pytest on extraction and the classifier interface.
**Done when:** pytest output pasted green, `/api/health` curl pasted, single-image
classification curl pasted, PowerShell repro commands given.

### Phase 2 — Intelligence layer
All of SPEC-ANALYSIS B.1–B.7 as separate pure modules. **Write the synthetic-signal tests
first:** step change, noisy linear ramp, noisy plateau, 5-frame dropout. Assert the Kalman
converges, the trend gate refuses low-R² slopes, and hysteresis does not flicker on a
signal oscillating across a boundary. Then wire into a session pipeline: video → full
TrackState history.
**Done when:** test output pasted, and a sample clip produces a plausible TWI curve shown
as numbers.

### Phase 3 — Static design proof · 90 minutes maximum
One static page. No data, no API, no interactivity. The layout from SPEC-DESIGN D.3, real
fonts loaded, real palette applied, hardcoded plausible numbers in every slot. **Invoke
the UI/UX skill.**
*Why here:* leaving the design unverified until halfway through the build is the ordering
flaw in most hackathon plans. Ninety minutes to de-risk the half judges see first is the
best trade available.
**Done when:** the human has looked at it and approved the direction.

### Phase 4 — Realtime
`/ws/sessions/{id}` pushing TrackState per analysed frame, adaptive sampling for ≥8
analyses/sec on CPU. Backpressure: if inference falls behind, drop frames rather than
queue, and report the drop rate in the payload. Client reconnect with exponential backoff.
Persist every frame result so sessions replay after reload.
*If Step 0.3 measured >250ms per frame, skip this phase* — analyse server-side and replay
on a timer. Visually identical during a demo, and it saves more time than anything else on
the list.

### Phase 5 — Frontend shell
Design tokens as CSS custom properties + Tailwind theme extension. Fonts via `next/font`,
correctly subset. The asymmetric layout, properly. Typed API client generated from the
OpenAPI schema. WebSocket hook. Empty state and the three sample-clip loaders. **UI/UX
skill mandatory.**

### Phase 6 — The signature element
Crossover Projection exactly as SPEC-DESIGN D.4. Recharts or hand-rolled SVG — justify by
which gives cleaner control over the uncertainty cone and the hue-shifting line. Threshold
bands, dashed projection, shaded cone, sodium crossing marker, client-interpolated 60fps
countdown. Implement the null state as specified. **This is the panel judges remember.
Treat it accordingly.**

### Phase 7 — Pit call and timeline
HOLD / ARMING / BOX with the arming pulse and segmented windows-held indicator. Bottom
timeline: scrolling thumbnails, wetness heat strip beneath, current frame ringed sodium,
low-quality frames hatched, click to scrub, arrow keys to step. `aria-live` on the
recommendation.

### Phase 8 — Motion pass
The 900ms load sequence, once per session. Springs on every numeral. 400ms colour
cross-fades. Then audit every transition in the codebase: no `transition: all`, no
`linear`, no animation on an idle screen. `prefers-reduced-motion`. Report the sequence
timing as a table.

### Phase 9 — Hugging Face
`build_dataset.py`, `label_tool.html` (keyboard 1–4, writes corrections back),
`train_probe.py` (held-out split, confusion matrix), `push_to_hub.py` (model + dataset,
honest cards). Runtime toggle between zero-shot and probe, exposed in `/api/health` and
the UI, so the accuracy jump demos live.
*Budget two focused hours for labelling. It is the real time sink — build the tool early
so it isn't what you're doing at 3am.*

### Phase 10 — Hardening
Offline weather fallback. Warmup with visible progress. Graceful CPU-only degradation.
Timeouts and retries everywhere. `docs/DEMO.md`: 90-second runbook, exact click order,
recovery plan per failure mode. Then run `/hostile` and produce a numbered list of
everything that breaks, confuses, or looks unfinished.

### Cut order, if time runs out

Keep 1, 2, 3, 5, 6, 7. That is a complete, coherent, genuinely impressive product.
Then cut in this order: Phase 4 → Phase 9's probe (still publish the dataset; rule 3 is
satisfied by a Hub model plus a published dataset) → most of Phase 8, keeping only spring
numerals and colour cross-fades, which carry 80% of the polish.

### Where the marks actually are

The brief says clarity of presentation decides it. Weight accordingly:

1. The uncertainty cone. No other team will do uncertainty at all.
2. The null state that admits ignorance. **Demo the ambiguous clip on purpose.** When a
   judge asks "what if it's wrong?", you've already answered.
3. Hysteresis on the pit call.
4. Tabular numerals. One CSS line, and it's why the interface looks built rather than
   generated.

### Two honest warnings

Damp versus drying asphalt is the hardest visual distinction in this problem, and CLIP
zero-shot will be shaky at it. That's fine — it's *why* the temporal layer exists — but
never let the demo hinge on one frame's label. **Demo the trend, not the label.**

And the labelling is the real time sink, not the code.
