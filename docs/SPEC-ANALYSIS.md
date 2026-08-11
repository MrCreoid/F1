# SPEC-ANALYSIS

This is where the project wins. Each item is a separate pure function in
`backend/app/analysis/`, unit-tested. Every constant lives in `config.py` with a comment.

### B.1 Track Wetness Index, 0–100

Never `argmax`. Weighted sum over the full distribution, so the index is continuous and
can move smoothly:

```
TWI_raw = 100 * (0.00*p_dry + 0.35*p_damp + 0.75*p_wet + 1.00*p_standing_water)
```

Comment for the code: argmax discards the information that makes trend detection
possible. 60% wet / 40% damp is meaningfully different from 95% wet, and that difference
*is* the drying signal.

### B.2 Frame quality gate

Bad frames poison the trend. Per frame:

- **Blur** — variance of the Laplacian (`cv2.Laplacian(gray, cv2.CV_64F).var()`).
- **Exposure** — fraction of pixels clipped at 0 or 255. Glare off wet asphalt, tunnel exits.
- **Entropy** — `H = -Σ p log p`, normalised `H/log(K)`. Confidence `= 1 - H_norm`.

Combine into `frame_quality ∈ [0,1]`. Frames below 0.25 are still displayed but flagged
and heavily downweighted — never silently dropped. The user must see *why* the system
distrusts a moment.

### B.3 Adaptive smoothing — 1D Kalman filter

Not a rolling average; a rolling average lags exactly when responsiveness matters.

- State `[twi, twi_rate]`, constant-velocity model. The rate term gives you trend for free.
- Measurement noise `R` scales inversely with `frame_quality`. A blurry low-confidence
  frame barely moves the estimate; a crisp one moves it hard.
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

If OLS R² < 0.4 → `STABLE — INSUFFICIENT SIGNAL` regardless of slope. Never present a
trend the data doesn't support.

### B.5 Crossover projection — the signature feature

```
t_cross = (TWI_threshold - TWI_now) / rate
```

Report only if `|rate| > 1.5` **and** `R² ≥ 0.4` **and** `t_cross` is within a 30-minute
horizon.

Uncertainty band from the standard error of the OLS slope: compute `t_cross` at
`rate ± 1.96·SE` for an optimistic/pessimistic window. The UI renders a cone, not a line.

Any gate fails → return `null`, and the UI says *"No reliable projection"*. Never
fabricate a number. When a judge asks "how confident is that?", this is where you win or
lose.

### B.6 Pit call with hysteresis

```
TWI  0–25  → SLICK
TWI 25–65  → INTERMEDIATE
TWI 65–100 → FULL WET
```

Naive thresholding flickers between compounds on the boundary — the exact failure a real
strategist would mock. So:

- A recommendation changes only after crossing the boundary by a **margin of 6 points**
  *and* holding for **3 consecutive analysis windows**.
- Expose `windows_held` so the UI can show a call *arming* before it fires. That "about
  to change" state is the best visual moment in the product.

States: `HOLD` · `ARMING` · `BOX`.

Fifteen lines of code, and the single most convincing sign that someone thought about the
problem rather than the demo.

### B.7 Weather fusion — real API, no key

**Open-Meteo**, `https://api.open-meteo.com/v1/forecast` — free, no API key, so nothing
to leak or expire mid-demo. Request `precipitation`, `temperature_2m`, `wind_speed_10m`,
`cloud_cover`, `relative_humidity_2m`.

Build a physical drying-rate prior: warm, windy, dry, clear → the track dries fast. Cold,
humid, still, raining → it won't. Blend by visual confidence:

```
rate_final = w·rate_visual + (1−w)·rate_prior,   w = mean frame_quality over window
```

Surface the blend in the UI ("visual 78% / weather 22%"). Almost no team will show their
fusion weights, and it takes ten minutes.

Cache 10 minutes. Ship a bundled JSON fallback so the demo survives a dead network.

### B.8 Hugging Face

- **Baseline, ships day one:** `openai/clip-vit-base-patch32` zero-shot against
  engineered prompts — *a dry asphalt racetrack surface* / *a damp racetrack with a
  darkened surface* / *a wet racetrack surface reflecting light* / *a racetrack with
  standing water and visible spray*. Prompts live in `config.py` as a tunable; the README
  shows the accuracy delta from tuning them.
- **Upgrade — this is what satisfies "balanced difficulty":** a **linear probe** on
  frozen CLIP embeddings, trained on our own labelled frames. Not from scratch, not a
  ready-made tool — precisely "somewhere in between." A few hundred frames is enough.
  Ship both with a runtime toggle so the accuracy jump demos live on stage.
- **Dataset:** ours. `scripts/build_dataset.py` extracts frames, auto-labels with CLIP,
  writes a review manifest. `scripts/label_tool.html` is a single-page keyboard-driven
  corrector (keys 1–4). Push as an `imagefolder` dataset with a card documenting label
  definitions and the auto-then-human process.
- **Publishing:** `scripts/push_to_hub.py` uploads probe + dataset with honest cards.
  Token from `HF_TOKEN`. Never hardcoded, never printed.
- **Inference:** local by default, weights cached in `backend/.cache/`. HF Inference API
  opt-in via env var.
