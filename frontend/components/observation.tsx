"use client";

/**
 * Column A — what the camera sees, and how much it can be trusted.
 * Camera monitor, surface distribution history, frame quality diagnostics.
 */

import {
  CLASS_COLOR,
  CLASS_LABEL,
  CLASS_ORDER,
  FALLBACK_THRESHOLDS,
  type Thresholds,
  type TrackState,
} from "@/lib/api";

/* ─────────────────────────────────── camera monitor ─────────────────────────────── */

export function CameraMonitor({
  state,
  sourceName,
}: {
  state: TrackState;
  sourceName: string;
}) {
  const stamp = new Date(state.timestamp);
  const hh = String(stamp.getUTCHours()).padStart(2, "0");
  const mm = String(stamp.getUTCMinutes()).padStart(2, "0");
  const ss = String(stamp.getUTCSeconds()).padStart(2, "0");
  const ms = String(stamp.getUTCMilliseconds()).padStart(3, "0");

  return (
    <div className="border-b border-rule bg-mat-panel p-[11px]">
      <div
        className="relative aspect-video overflow-hidden bg-mat-well"
        style={{
          boxShadow:
            "inset 0 0 0 1px rgba(0,0,0,.9), 0 0 0 1px var(--edge-hi), inset 0 2px 8px rgba(0,0,0,.7)",
        }}
      >
        {state.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element -- backend-served frame, not a static asset
          <img
            src={state.thumbnail_url}
            alt={`Frame ${state.frame_index}`}
            className="h-full w-full object-cover"
          />
        ) : (
          /* Sessions analysed before the frame store existed carry no image. The monitor
             says so rather than filling the space with a decorative placeholder. */
          <div className="flex h-full w-full items-center justify-center">
            <span className="tag">No frame stored · reload the clip</span>
          </div>
        )}

        {/* framing marks, as on a broadcast monitor */}
        <div className="pointer-events-none absolute inset-[9px] z-2">
          {(
            [
              "top-0 left-0 border-t border-l",
              "top-0 right-0 border-t border-r",
              "bottom-0 left-0 border-b border-l",
              "bottom-0 right-0 border-b border-r",
            ] as const
          ).map((cls) => (
            <span
              key={cls}
              className={`absolute h-[11px] w-[11px] border-text-primary/55 ${cls}`}
            />
          ))}
        </div>

        {/* The one glass element in the app: an overlay on live video, where layering
            is literally what is happening. */}
        <div
          className="absolute inset-x-[11px] bottom-[10px] z-3 flex items-center gap-3 border-t border-white/8 px-[9px] py-[5px] font-mono text-[10px] tracking-[.04em] text-text-primary/90"
          style={{ background: "rgba(7,10,12,.58)", backdropFilter: "blur(7px)" }}
        >
          <span className="tnum">{`${hh}:${mm}:${ss}.${ms}`}</span>
          <span>
            <em className="not-italic tracking-[.13em] text-text-muted">FRM</em>{" "}
            <span className="tnum">{state.frame_index}</span>
          </span>
          <span className="ml-auto inline-flex items-center gap-[5px] font-semibold tracking-[.12em] text-trend-worsening">
            <span
              className="ww-breathe h-[5px] w-[5px] rounded-full bg-trend-worsening"
              style={{ boxShadow: "0 0 5px rgba(212,87,78,.8)" }}
            />
            REC
          </span>
        </div>
      </div>

      <div
        className="mt-2 flex items-center justify-between px-[9px] py-[6px]"
        style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.85), inset 0 -1px 0 var(--edge-hi)" }}
      >
        <span className="tag">Signal</span>
        <span className="tnum text-[10px]" style={{ color: "var(--color-state-damp)" }}>
          {state.frame_quality.score.toFixed(2)}
        </span>
        <span className="tag">Source</span>
        <span className="tnum text-[10px]">{sourceName}</span>
      </div>
    </div>
  );
}

/* ────────────────────────────── surface distribution ────────────────────────────── */

export function SurfaceDistribution({ history }: { history: TrackState[] }) {
  const W = 304;
  const H = 108;
  const pad = 8;

  const points = history.length > 1 ? history : [];
  const x = (i: number) => pad + (i / Math.max(1, points.length - 1)) * (W - pad * 2);
  const y = (cum: number) => H - pad - cum * (H - pad * 2);

  /* Stacked bottom-to-top: dry, damp, wet, standing. Cumulative boundaries per frame. */
  const bands = CLASS_ORDER.map((_, band) =>
    points.map((s, i) => {
      let cum = 0;
      for (let k = 0; k <= band; k++) cum += s.probabilities[CLASS_ORDER[k]];
      return { x: x(i), y: y(cum) };
    }),
  );

  const areaPath = (band: number): string => {
    const top = bands[band];
    if (!top.length) return "";
    const under = band === 0 ? null : bands[band - 1];
    const forward = top.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const back = under
      ? [...under].reverse().map((p) => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")
      : `L${x(points.length - 1).toFixed(1)},${(H - pad).toFixed(1)} L${x(0).toFixed(1)},${(H - pad).toFixed(1)}`;
    return `${forward} ${back} Z`;
  };

  const latest = points.at(-1);

  return (
    <div className="border-b border-rule bg-mat-panel px-[13px] pt-3 pb-[13px]">
      <div className="flex items-baseline justify-between">
        <span className="section-title">Surface distribution</span>
        <span className="tnum text-[10px] text-text-muted">{points.length} FRAMES</span>
      </div>

      <div className="well mt-[9px] px-2 pt-2 pb-1.5">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="block h-[104px] w-full"
             role="img" aria-label="Probability mass across the four surface classes over the session.">
          <g stroke="#2A323A" strokeWidth={1}>
            {[0.25, 0.5, 0.75].map((f) => (
              <line key={f} x1={pad} y1={y(f)} x2={W - pad} y2={y(f)} />
            ))}
          </g>
          {CLASS_ORDER.map((name, band) => (
            <path key={name} d={areaPath(band)} fill={CLASS_COLOR[name]} fillOpacity={0.88} />
          ))}
          {points.length > 0 && (
            <line x1={W - pad} y1={pad} x2={W - pad} y2={H - pad} stroke="var(--color-sodium)" strokeWidth={1} />
          )}
        </svg>
      </div>

      <div className="mt-[10px] grid grid-cols-4 gap-2">
        {CLASS_ORDER.map((name) => (
          <div key={name} className="flex flex-col gap-1">
            <span className="h-[3px]" style={{ background: CLASS_COLOR[name], boxShadow: `0 0 5px ${CLASS_COLOR[name]}` }} />
            <span className="text-[9px] uppercase tracking-[.12em] text-text-muted">{CLASS_LABEL[name]}</span>
            <span className="tnum text-t13">{(latest?.probabilities[name] ?? 0).toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ────────────────────────────────── frame quality ───────────────────────────────── */

/** Gauge fills are a presentation scaling of the backend's raw metric, not a recomputation. */
function Gauge({
  label,
  fill,
  value,
  flagAt,
  warn = false,
}: {
  label: string;
  fill: number;
  value: string;
  flagAt: number;
  warn?: boolean;
}) {
  return (
    <div className="grid grid-cols-[76px_minmax(0,1fr)_52px] items-center gap-[11px]">
      <span className="text-[9px] uppercase tracking-[.13em] text-text-muted">{label}</span>
      <span
        className="relative h-[9px]"
        style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.9), inset 0 -1px 0 var(--edge-hi)" }}
      >
        <i
          className="absolute inset-y-px left-px block"
          style={{
            width: `${Math.max(0, Math.min(100, fill * 100))}%`,
            background: `linear-gradient(180deg, rgba(255,255,255,.22), rgba(255,255,255,0) 55%), ${
              warn ? "var(--color-state-damp)" : "var(--color-state-dry)"
            }`,
          }}
        />
        {/* printed tick scale, every 10% */}
        <span
          className="pointer-events-none absolute inset-0"
          style={{ backgroundImage: "repeating-linear-gradient(90deg, rgba(0,0,0,.55) 0 1px, transparent 1px 10%)" }}
        />
        {/* the quality flag threshold the backend actually gates on, at the position
            the backend actually reports */}
        <span
          className="absolute -top-0.5 -bottom-0.5 w-px bg-sodium opacity-80"
          style={{ left: `${flagAt * 100}%` }}
        />
      </span>
      <span className="tnum text-right text-t11">{value}</span>
    </div>
  );
}

export function FrameQualityPanel({
  quality,
  thresholds = FALLBACK_THRESHOLDS,
}: {
  quality: TrackState["frame_quality"];
  thresholds?: Thresholds;
}) {
  return (
    <div>
      <div className="panel-head">
        <span className="section-title">Frame quality</span>
        <span className="font-mono text-[10px] tracking-[.06em] text-text-muted">GEOMETRIC MEAN</span>
      </div>
      <div className="flex flex-col gap-3 px-[13px] pt-3 pb-3.5">
        {/* Every reference below is the backend's own, served on /api/health. They were
            re-typed here, so retuning config.py left these bars quietly misreporting. */}
        <Gauge
          label="Focus"
          fill={quality.blur / thresholds.blur_reference}
          value={quality.blur.toFixed(1)}
          flagAt={thresholds.quality_flag}
        />
        <Gauge
          label="Exposure"
          fill={1 - quality.clipping / thresholds.clipping_tolerance}
          value={quality.clipping.toFixed(2)}
          flagAt={thresholds.quality_flag}
        />
        <Gauge
          label="Confidence"
          fill={1 - quality.entropy}
          value={quality.entropy.toFixed(2)}
          flagAt={thresholds.quality_flag}
          warn
        />

        <div
          className="mt-0.5 flex items-center justify-between px-[11px] py-[9px]"
          style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.85), inset 0 -1px 0 var(--edge-hi)" }}
        >
          <span className="tag">Signal</span>
          <span
            className="tnum text-t20 font-semibold"
            style={{ color: "var(--color-state-damp)", textShadow: "0 0 12px rgba(224,163,62,.35)" }}
          >
            {quality.score.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
