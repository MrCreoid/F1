/**
 * Chart maths for the crossover projection.
 *
 * Pure functions, no React, no DOM — the geometry is worth being able to reason about
 * on its own. Nothing here computes analysis; it turns the backend's numbers into
 * coordinates and colours.
 */

export type Bands = { slick: number; fullWet: number };

/**
 * Compound boundaries. The backend is authoritative and serves these on `/api/health`;
 * this is the shape to fall back on before it has answered, and the default that keeps
 * these functions callable from a test without an HTTP round trip.
 */
export const TWI_THRESHOLDS: Bands = { slick: 25, fullWet: 65 };

/** The condition a given index describes. The line is coloured by what it means. */
export function bandColor(twi: number, bands: Bands = TWI_THRESHOLDS): string {
  if (twi < bands.slick) return "#C9D1D9"; // state-dry
  if (twi < bands.fullWet) return "#E0A33E"; // state-damp
  return "#3D7DBF"; // state-wet
}

export type Stop = { offset: number; color: string };

/**
 * Gradient stops for a stroke that shifts hue wherever the series crosses a compound
 * boundary — SPEC-DESIGN D.4: "the line is coloured by the condition it describes".
 *
 * Stops are emitted in pairs at each crossing so the transition is a hard edge rather
 * than a blend: the track is either side of a threshold, never smeared across it.
 *
 * @param points series in draw order, x already in user space
 * @param x0 left edge of the gradient in user space
 * @param x1 right edge of the gradient in user space
 */
export function conditionStops(
  points: readonly { x: number; twi: number }[],
  x0: number,
  x1: number,
  bands: Bands = TWI_THRESHOLDS,
): Stop[] {
  if (points.length === 0) return [];
  const span = x1 - x0;
  if (span <= 0) return [{ offset: 0, color: bandColor(points[0].twi, bands) }];

  const at = (x: number) => Math.min(1, Math.max(0, (x - x0) / span));
  const stops: Stop[] = [{ offset: 0, color: bandColor(points[0].twi, bands) }];

  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const from = bandColor(prev.twi, bands);
    const to = bandColor(curr.twi, bands);
    if (from === to) continue;

    // Which boundary did this segment cross? Handle both, in travel order, so a segment
    // spanning an entire band still changes colour twice.
    const crossed = [bands.slick, bands.fullWet]
      .filter((t) => (prev.twi - t) * (curr.twi - t) < 0)
      .sort((a, b) => (curr.twi > prev.twi ? a - b : b - a));

    for (const threshold of crossed) {
      const f = (threshold - prev.twi) / (curr.twi - prev.twi);
      const offset = at(prev.x + f * (curr.x - prev.x));
      // A pair of stops at the same offset produces a hard edge.
      stops.push({ offset, color: stops[stops.length - 1].color });
      stops.push({ offset, color: bandColor(threshold + (curr.twi > prev.twi ? 0.001 : -0.001), bands) });
    }
  }

  stops.push({ offset: 1, color: stops[stops.length - 1].color });
  return stops;
}

/**
 * Seconds remaining, interpolated from a server value and the wall time since it
 * arrived. Never returns a negative countdown — a crossing that has passed reads 0.
 */
export function interpolateEta(etaAtSample: number, elapsedSinceSampleMs: number): number {
  return Math.max(0, etaAtSample - elapsedSinceSampleMs / 1000);
}

/**
 * Why there is no projection, stated accurately.
 *
 * The backend returns a bare null, and it is tempting to print one stock reason. That
 * would be a lie in the common case: a track already below the slick threshold has a
 * perfectly good R² and a steep rate, and blaming its fit would be wrong in a way a
 * sceptical reader could catch. These conditions mirror the gates in SPEC-ANALYSIS B.5,
 * in the order the backend applies them.
 */
export function projectionGap(args: {
  twi: number;
  ratePerMin: number;
  rSquared: number;
  sufficientSignal: boolean;
  rateThreshold?: number;
  r2Min?: number;
  bands?: Bands;
}): string {
  const { twi, ratePerMin, rSquared, sufficientSignal } = args;
  const rateThreshold = args.rateThreshold ?? 1.5;
  const r2Min = args.r2Min ?? 0.4;
  const bands = args.bands ?? TWI_THRESHOLDS;

  if (!sufficientSignal) {
    return rSquared < r2Min
      ? `R² ${rSquared.toFixed(2)} below ${r2Min.toFixed(2)} threshold`
      : "Estimators disagree on direction";
  }
  if (Math.abs(ratePerMin) <= rateThreshold) {
    return `Rate ${Math.abs(ratePerMin).toFixed(1)}/min below ${rateThreshold.toFixed(1)} threshold`;
  }

  const drying = ratePerMin < 0;
  const ahead = [bands.slick, bands.fullWet].filter((t) =>
    drying ? t < twi : t > twi,
  );
  if (ahead.length === 0) {
    return drying ? "Already below the slick threshold" : "Already above the full wet threshold";
  }
  return "Crossing beyond the 30 minute horizon";
}

/**
 * The rate, or an em dash when the backend does not stand behind it.
 *
 * When the fit fails its gates the backend forces the direction to STABLE but still
 * reports the slope it computed. Printing that slope to one decimal put "STABLE" next
 * to "-64.0/min" on 80 of the 300 frames of the wetting sample — an instrument
 * contradicting itself in the same breath. The projection panel has always refused to
 * draw an unsupported number; this is the same discipline applied to the readout
 * beside it. Takes primitives rather than the Trend type so it stays testable without
 * pulling in the API client.
 */
export function ratePerMin(ratePerMinute: number, sufficientSignal: boolean): string {
  if (!sufficientSignal) return "\u2014";
  return `${ratePerMinute > 0 ? "+" : "\u2212"}${Math.abs(ratePerMinute).toFixed(1)}`;
}
