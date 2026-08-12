# HANDOFF — start here in a new session

This file is **forward-looking only**: the plan, the reasoning behind it, and the traps
that will otherwise cost you an hour each.

**It is not the status board.** `docs/STATE.md` is, and it wins on any disagreement.
This file goes stale the moment a phase lands; STATE.md is rewritten every time.

---

## Resume in three commands

```bash
cat docs/STATE.md          # where the build actually is
git log --oneline -10      # what actually landed
cat docs/PHASES.md         # the plan of record
```

Then say one line back: last phase complete, next phase, any blocker. Then start.

---

## The plan, in order, with the reasoning

Remaining: **7, 9, 10, 8**. Phase 4 is deliberately skipped — `GET /api/sessions/{id}/states`
plus client replay is visually identical to a WebSocket during a demo, which PHASES.md
says outright.

### 1. Phase 7 — pit call and timeline

Do this first for a structural reason, not just a cosmetic one.

The product is about looking at footage, and the camera panel currently reads
*"Frame store offline · Phase 7"*. That is the first thing a judge sees. But the better
argument: **Phase 7 writes per-frame images to disk, and that frame store is exactly what
Phase 9's `build_dataset.py` needs.** Doing 7 first hands 9 its dataset substrate for
free. Doing 9 first means writing frame extraction twice.

Scope:
- Write thumbnails during analysis (`_run_video` in `backend/app/main.py` already has the
  decoded frames in hand — write them there, populate `TrackState.thumbnail_url`).
- Serve them: a `StaticFiles` mount, or an endpoint. `thumbnail_url` is already in the
  schema and already rendered by `components/observation.tsx`.
- Timeline strip shows real thumbnails instead of wetness blocks; keep the wetness ribbon
  beneath, keep the degraded hatching, keep the sodium playhead.
- Arrow-key stepping and click-to-scrub **already work** — do not rebuild them.
- `next` is null on a BOX recommendation, so the UI cannot show "INTERMEDIATE → SLICK"
  at the moment it fires. Decide there: either carry the previous compound in the schema
  or render the transition from history.

### 2. Phase 9 — Hugging Face (closes the only rule break)

**Build `scripts/label_tool.html` on day one of this phase.** PHASES.md warns the
labelling is the real time sink, not the code. With the tool built early, the two hours
of clicking can happen in the background while other work continues.

Order within the phase:
1. `scripts/build_dataset.py` — extract frames (reuse Phase 7's frame store), auto-label
   with CLIP, write a review manifest.
2. `scripts/label_tool.html` — single page, keyboard 1–4, writes corrections back.
3. `scripts/push_to_hub.py` — dataset first with an honest card. **This alone satisfies
   rule 3**, per the cut list.
4. `scripts/train_probe.py` — linear probe on frozen CLIP embeddings, held-out split,
   confusion matrix. Stretch goal.
5. Runtime toggle zero-shot ↔ probe, exposed in `/api/health` and the UI.

`HF_TOKEN` comes from the environment. Never hardcoded, never printed, never committed.

### 3. Phase 10 — hardening and the demo runbook

`docs/DEMO.md`: 90-second runbook, exact click order, a recovery plan per failure mode.
Then run `/hostile` and fix what it finds.

Written last on purpose — a runbook against an unfinished product goes stale.
The demo order that tells the best story: **drying → ambiguous → wetting.** Show the
system working, then show it admitting it does not know, then show conditions
deteriorating. The ambiguous clip is demoed on purpose; it is the answer to "what if
it's wrong?".

### 4. Phase 8 — motion, trimmed

Spring numerals and 400ms colour cross-fades only. The cut list says those carry 80% of
the polish. Already shipped: the chart draw-in, the ARMING pulse, the needle transition,
the load stagger. Then audit: no `transition: all`, no `linear`, nothing animating on an
idle screen.

### Riding along, five minutes, attach to whichever phase runs first

- Add a `LICENSE` file. There is none.
- Replace `docs/design/sample-frame.jpg` (CC BY-SA 4.0, share-alike) with own footage or
  a CC0 image. The app no longer ships it, so this is now hygiene rather than exposure.

---

## Change this order if the deadline is close

Rule 3 is binary. If you have less than about two working sessions left, do **Phase 9
first** — a beautiful disqualified project scores zero. Everything else is polish.

---

## Traps that will cost you an hour each

- **Next dev 403s its own JS.** If panels render empty with no error, check
  `allowedDevOrigins` in `next.config.ts`. Without `127.0.0.1` in that list, Next blocks
  `/_next/static/*` and the client bundle never loads — silently.
- **Only one `next dev` at a time.** A second one exits with "Another next dev server is
  already running". `pkill -f "next dev"` before restarting.
- **`npm run gen:api` needs the backend running.** It reads the live OpenAPI document. If
  you add an endpoint, restart uvicorn *before* regenerating, or the types will silently
  miss it.
- **Archivo must load as a variable font with no fixed `weight`.** `next/font` rejects
  `axes` alongside `weight`, and the design drives the `wdth` axis directly.
- **Tests never touch the network.** `backend/conftest.py` sets `WW_OFFLINE=1`. Tests that
  need the live-fetch path turn it off themselves via monkeypatch.
- **`WW_DEVICE=cpu`** is the mid-demo recovery lever if `mps` misbehaves.
- The in-app browser blocks cross-origin fetches; the app talks to `/api/*` same-origin
  through the Next rewrite, so this only matters if you point it back at `:8000`.

---

## Rules of the build that are not obvious from the code

- **The frontend never computes analysis.** It renders what the backend returns. If the UI
  needs a value, add it to the schema — do not derive it client-side. The one exception is
  presentation geometry (pixel positions, gradient stops), which is drawing, not analysis.
- **Never fabricate a number.** When a gate fails the backend returns null and the UI says
  so, naming the gate that actually failed. `lib/chart.ts:projectionGap()` exists because
  the first version printed one stock reason and was wrong in the common case.
- **Four appearance classes, forever.** Trend is derived from the time-derivative of the
  smoothed index. If you find yourself adding "drying" as a fifth class, stop.
- **Types are generated, never hand-written.** `frontend/lib/schema.d.ts` is output.
- Check `## Rejected, do not revisit` in STATE.md before re-proposing anything. Several
  entries are there because they were tried and failed.

---

## Run it

```bash
# terminal 1 — backend
cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000 --reload

# terminal 2 — frontend
cd frontend && npm run dev
# http://localhost:3000, then click a sample clip

# checks, all of which must stay green
cd backend  && ../.venv/bin/python -m pytest tests/ -q
cd frontend && npm test && npx tsc --noEmit && npm run lint && npm run build
```
