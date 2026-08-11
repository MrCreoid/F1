# SPEC-DESIGN

Invoke the UI/UX skill before building anything here. This half decides the outcome —
judges see the interface before they read a line of code.

### D.1 What we deliberately do not do

The hackathon deck is red-on-black with italic condensed type. Every other team will
clone it, because it's sitting right in front of them. Cloning the poster reads as
derivative; looking like a real broadcast instrument reads as finished. That gap is
second place versus first.

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

The reference is an FIA timing screen and a race engineer's laptop: dark, dense, quiet,
legible from a metre away under floodlights. Colour carries meaning only, never
decoration. A judge should read the track state from across the room without reading a
word.

**Palette — six tokens, no others:**

```
--surface-base    #0E1114   graphite with a cool cast — wet asphalt at night
--surface-raised  #161A1F   panel fill, one clear value step up
--hairline        #262C33   1px borders, the only structural divider
--text-primary    #E8EBED   bone, never pure white
--text-muted      #7C8791   labels, units, secondary
--sodium          #FF7A1A   THE accent — trackside sodium floodlight orange
```

`--sodium` appears at most three times per screen. Choosing it over the obvious signal
red is the one real risk in this design, and it's justified: red already carries meaning
in motorsport (red flag = session stopped), so using it decoratively on a product about
track safety would be semantically wrong. Orange is the colour of the lamps actually
lighting a wet track at night. It belongs to the subject.

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

- **Archivo** 700–800, expanded width, uppercase, tight tracking → display numerals,
  section headers. Expanded-heavy grotesk is the timing-tower voice and nobody's default.
- **Inter Tight** 400/500 → body, labels, rationale.
- **IBM Plex Mono** 400/500, `font-variant-numeric: tabular-nums` → every telemetry readout.

**Every changing number in this app is tabular and monospaced.** Digits must not shift
horizontally as they update. This one detail separates "instrument" from "webpage," and
almost every team will miss it.

Scale, strict: `11 / 13 / 15 / 20 / 32 / 64 / 128`. The 128 is used exactly once — the
TWI readout.

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

Left column bleeds to the viewport edge — no outer margin that side. The bottom timeline
is a full-width editing rail, the vernacular of an engineer scrubbing footage. Below
1024px it stacks: frame, readout, projection, call, timeline.

### D.4 The signature element — Crossover Projection

Spend the design budget here. One memorable thing done properly beats six decorated
panels.

- History: solid 2px line **that shifts hue as it crosses threshold bands** — the line is
  coloured by the condition it describes.
- Projection: same line continuing past *now* as 4px dashes at 50% opacity.
- Uncertainty: filled cone between optimistic and pessimistic, 12% opacity, widening with
  time — visually honest about decaying confidence.
- Threshold bands: full-width horizontal zones at 25 and 65, 4% opacity `--state-*`,
  labelled in Plex Mono at the right edge.
- Crossing point: small sodium marker with a monospace countdown that **ticks in real
  time between server updates** — client-side interpolation, so it feels live at 60fps
  instead of stepping once a second.
- **Null state keeps the panel.** Future region empties, and one Plex Mono line reads
  `NO RELIABLE PROJECTION · R² 0.22 BELOW THRESHOLD`. Showing the system's own
  uncertainty beats hiding it, and it's the best possible answer to a sceptical judge.

### D.5 Motion — one orchestrated sequence, then restraint

- **Load, 900ms, once:** hairlines draw in horizontally → panels fade up staggered 60ms →
  TWI numeral counts from 0 on a decelerating curve → chart line draws left-to-right →
  sodium accent arrives last.
- **Numerals never snap.** Spring interpolation, stiffness ~120, damping ~20.
- **State colour changes** cross-fade 400ms `cubic-bezier(0.4, 0, 0.2, 1)`.
- **`ARMING` is the emotional beat of the product.** Panel border pulses in the target
  compound's colour at 1.4s intervals; a segmented indicator fills — 2 of 3 windows held.
  The judge watches the system *decide*. Do not waste this on a static badge.
- `prefers-reduced-motion`: keep colour and layout, drop movement.
- **Idle is genuinely still.** Ambient animation with nothing happening is the loudest AI
  tell there is.

### D.6 Copy

Broadcast register. Terse, active, unhedged, no exclamation marks.

- Yes: `Track drying. Slicks viable in 4:30.` · `Signal degraded — heavy spray on lens.` ·
  `Holding intermediates. Margin insufficient.`
- No: `Great news! The track is drying up!` · `Analyzing your data...` · `AI-powered insights`

Empty state instructs, never apologises: `Load footage to begin analysis.` with the three
sample clips as one-click options. Errors name the failure and the fix: `Model not loaded.
Run: python -m app.warmup` — never `Something went wrong.`

### D.7 Quality floor, unannounced

Responsive to 375px. Visible focus rings (sodium, 2px offset). Full keyboard reach.
`aria-live="polite"` on the recommendation panel. Colour never the sole carrier of meaning
— every state colour paired with a text label. Lighthouse accessibility ≥ 95.
