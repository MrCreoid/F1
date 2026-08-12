/**
 * Chart maths checks. `node --test lib/chart.test.mjs` after `npm run build`.
 *
 * The hue-shifting stroke is the one piece of frontend logic with real branching, and a
 * wrong gradient would colour the line by the wrong condition — a lie told in a colour
 * nobody would think to question. So it gets asserted.
 */

import { strict as assert } from "node:assert";
import test from "node:test";
import { bandColor, conditionStops, interpolateEta, projectionGap, ratePerMin, TWI_THRESHOLDS } from "./chart.ts";

const DRY = bandColor(10);
const DAMP = bandColor(45);
const WET = bandColor(80);

test("bands map to distinct colours at the thresholds", () => {
  assert.notEqual(DRY, DAMP);
  assert.notEqual(DAMP, WET);
  assert.equal(bandColor(TWI_THRESHOLDS.slick), DAMP, "25 is intermediate, not slick");
  assert.equal(bandColor(TWI_THRESHOLDS.fullWet), WET, "65 is full wet");
  assert.equal(bandColor(TWI_THRESHOLDS.slick - 0.01), DRY);
});

test("a series inside one band produces a single colour", () => {
  const stops = conditionStops(
    [
      { x: 0, twi: 40 },
      { x: 50, twi: 45 },
      { x: 100, twi: 38 },
    ],
    0,
    100,
  );
  assert.deepEqual(new Set(stops.map((s) => s.color)), new Set([DAMP]));
});

test("crossing a threshold puts a hard edge at the crossing point", () => {
  // 65 → 25 over x 0..100: crosses 65 immediately and 25 at the far end.
  const stops = conditionStops(
    [
      { x: 0, twi: 70 },
      { x: 100, twi: 20 },
    ],
    0,
    100,
  );
  const colors = stops.map((s) => s.color);
  assert.ok(colors.includes(WET), "starts wet");
  assert.ok(colors.includes(DAMP), "passes through damp");
  assert.ok(colors.includes(DRY), "ends dry");

  // Hard edges: each transition is a pair of stops sharing one offset.
  const offsets = stops.map((s) => s.offset);
  const duplicated = offsets.filter((o, i) => offsets.indexOf(o) !== i);
  assert.equal(duplicated.length, 2, "two crossings, two paired stops");

  // 70 → 20 is linear, so 65 lands at 10% and 25 at 90%.
  assert.ok(Math.abs(duplicated[0] - 0.1) < 1e-6, `65 crossing at ${duplicated[0]}`);
  assert.ok(Math.abs(duplicated[1] - 0.9) < 1e-6, `25 crossing at ${duplicated[1]}`);
});

test("a rising series crosses in the other direction", () => {
  const stops = conditionStops(
    [
      { x: 0, twi: 10 },
      { x: 100, twi: 90 },
    ],
    0,
    100,
  );
  assert.equal(stops[0].color, DRY);
  assert.equal(stops.at(-1).color, WET);
});

test("offsets stay within the gradient and are ordered", () => {
  const stops = conditionStops(
    [
      { x: 0, twi: 80 },
      { x: 30, twi: 30 },
      { x: 60, twi: 70 },
      { x: 100, twi: 10 },
    ],
    0,
    100,
  );
  for (const s of stops) {
    assert.ok(s.offset >= 0 && s.offset <= 1, `offset ${s.offset} out of range`);
  }
  const offsets = stops.map((s) => s.offset);
  assert.deepEqual(offsets, [...offsets].sort((a, b) => a - b), "stops must not go backwards");
});

test("degenerate input does not throw", () => {
  assert.deepEqual(conditionStops([], 0, 100), []);
  assert.equal(conditionStops([{ x: 0, twi: 50 }], 0, 0).length, 1);
});

test("the countdown interpolates against wall time and never goes negative", () => {
  assert.equal(interpolateEta(270, 0), 270);
  assert.equal(interpolateEta(270, 1000), 269);
  assert.equal(interpolateEta(0.5, 2000), 0, "a passed crossing reads zero, not negative");
});

test("the null-state reason names the gate that actually failed", () => {
  // low fit
  assert.match(
    projectionGap({ twi: 45, ratePerMin: -6, rSquared: 0.22, sufficientSignal: false }),
    /R² 0\.22 below/,
  );
  // estimators disagree despite a good fit
  assert.match(
    projectionGap({ twi: 45, ratePerMin: -6, rSquared: 0.81, sufficientSignal: false }),
    /disagree/,
  );
  // shallow slope
  assert.match(
    projectionGap({ twi: 45, ratePerMin: -0.4, rSquared: 0.9, sufficientSignal: true }),
    /Rate 0\.4\/min below/,
  );
  // the case that was reported wrongly: already past the last boundary while drying
  assert.equal(
    projectionGap({ twi: 21.3, ratePerMin: -59.2, rSquared: 0.72, sufficientSignal: true }),
    "Already below the slick threshold",
  );
  assert.equal(
    projectionGap({ twi: 92, ratePerMin: +40, rSquared: 0.9, sufficientSignal: true }),
    "Already above the full wet threshold",
  );
  // a real crossing that is simply too far out
  assert.match(
    projectionGap({ twi: 45, ratePerMin: -2, rSquared: 0.9, sufficientSignal: true }),
    /horizon/,
  );
});

/* The rate readout is gated on the same signal the projection is gated on. Without it
   the hero printed "STABLE -64.0/min" — an instrument contradicting itself — on 80 of
   the 300 frames of the wetting sample. */

test("a rate the backend does not stand behind is not printed", () => {
  assert.equal(ratePerMin(-64.0, false), "\u2014");
  assert.equal(ratePerMin(0.2, false), "\u2014");
});

test("a supported rate is printed with sign and one decimal", () => {
  assert.equal(ratePerMin(-3.24, true), "\u22123.2");
  assert.equal(ratePerMin(3.24, true), "+3.2");
});
