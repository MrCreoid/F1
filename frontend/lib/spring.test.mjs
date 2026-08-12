/**
 * The spring is not decoration. A numeral that settles slowly is an instrument showing a
 * value the backend never reported, so the tuning gets asserted: it must land exactly,
 * land quickly enough to keep up with 4fps replay, and barely overshoot.
 */

import { strict as assert } from "node:assert";
import test from "node:test";
import { overshoot, settleTime, springStep, SETTLE_EPSILON } from "./spring.ts";

test("it lands exactly on the target, not near it", () => {
  let state = { value: 0, velocity: 0 };
  for (let i = 0; i < 600; i++) state = springStep(state, 47.3, 1 / 60);

  assert.equal(state.value, 47.3, "a readout must end on the number the backend gave");
  assert.equal(state.velocity, 0);
});

test("a realistic frame-to-frame step settles inside the frame interval", () => {
  // This is the case that actually happens. At 4fps the index moves a point or two
  // between frames; if that does not settle within 250ms the numeral is permanently
  // behind the data, which for an instrument is a misreport rather than a style.
  const typical = settleTime(47.3, 49.0);

  assert.ok(typical < 0.25, `a 1.7-point step took ${typical.toFixed(2)}s, longer than a frame`);
});

test("even a full-scale jump settles promptly", () => {
  // Scrubbing across a session can move the readout the whole way. The spec's suggested
  // 120/20 took 1.07s for this and overshot by 0.00% — a laggy fade, not a spring.
  const extreme = settleTime(0, 50);

  assert.ok(extreme < 0.7, `settled in ${extreme.toFixed(2)}s, too slow`);
  assert.ok(extreme > 0.1, `settled in ${extreme.toFixed(2)}s — that is a snap, not a spring`);
});

test("overshoot is visible but small", () => {
  const past = overshoot(0, 50);

  assert.ok(past > 0, "critically damped or worse reads as a snap");
  assert.ok(past < 0.05, `overshot by ${(past * 100).toFixed(1)}% — a readout must not bounce`);
});

test("a huge frame gap cannot fling the value past its target", () => {
  // A backgrounded tab delivers one enormous frame on return.
  const state = springStep({ value: 0, velocity: 0 }, 50, 10);

  assert.ok(Math.abs(state.value) <= 50, `clamping failed: ${state.value}`);
});

test("an unchanged target produces no movement", () => {
  // D.5: idle is genuinely still. A spring already at rest must not jitter.
  const state = springStep({ value: 47.3, velocity: 0 }, 47.3, 1 / 60);

  assert.equal(state.value, 47.3);
  assert.equal(state.velocity, 0);
});

test("it converges from either direction", () => {
  for (const [from, to] of [[80, 20], [20, 80]]) {
    let state = { value: from, velocity: 0 };
    for (let i = 0; i < 600; i++) state = springStep(state, to, 1 / 60);
    assert.equal(state.value, to, `failed going ${from} -> ${to}`);
  }
});

test("the settle epsilon is finer than the displayed precision", () => {
  // The readout shows one decimal. Settling coarser than that would let it stop on a
  // different number than the one it claims to have reached.
  assert.ok(SETTLE_EPSILON < 0.05);
});
