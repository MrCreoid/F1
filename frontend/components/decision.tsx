"use client";

/**
 * Column B — the measurement and what it implies.
 *
 * Nothing here computes analysis. The chart plots the backend's own numbers: the TWI
 * history it filtered, the slope it fitted, and the crossing times it gated. When the
 * backend returns `crossover: null`, the panel says so rather than drawing a guess.
 */

import { clock, trendColor, type TrackState } from "@/lib/api";

/* ────────────────────────────────── hero instrument ─────────────────────────────── */

export function HeroInstrument({ state, history }: { state: TrackState; history: TrackState[] }) {
  const whole = Math.floor(state.twi);
  const decimal = (state.twi - whole).toFixed(1).slice(1); // ".5"

  const minuteAgo = history.findLast(
    (s) => new Date(state.timestamp).getTime() - new Date(s.timestamp).getTime() >= 60_000,
  );
  const peak = history.reduce((max, s) => Math.max(max, s.twi), state.twi);
  const delta = minuteAgo ? state.twi - minuteAgo.twi : null;

  return (
    <div className="border-b border-rule bg-mat-panel px-[18px] pt-3.5 pb-4">
      <div className="chamfer bg-rule p-px">
        <div
          className="chamfer grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-[26px] px-5 pt-4 pb-3.5"
          style={{
            background: "radial-gradient(140% 120% at 22% 0%, #101419 0%, #090C0F 70%)",
            boxShadow:
              "inset 0 2px 6px rgba(0,0,0,.95), inset 0 1px 0 rgba(0,0,0,.9), inset 0 -1px 0 var(--edge-hi)",
          }}
        >
          <div>
            <span
              className="block font-display leading-[.76] tracking-[-.048em] text-t128 tabular-nums"
              style={{
                fontVariationSettings: '"wdth" 104',
                fontWeight: 800,
                textShadow: "0 0 26px rgba(232,235,237,.16)",
              }}
            >
              {whole}
              <span className="text-t32 tracking-[-.02em] text-[#8D969E]" style={{ textShadow: "none" }}>
                {decimal}
              </span>
              <span
                className="ml-2.5 align-[34px] font-mono text-t11 font-medium tracking-[.18em] text-text-muted"
                style={{ textShadow: "none" }}
              >
                TWI
              </span>
            </span>

            {/* 0–100 scale with the compound thresholds as majors and a sodium needle. */}
            <div className="relative mt-[15px] h-[22px]">
              <span
                className="absolute inset-x-0 top-0 h-[7px]"
                style={{ backgroundImage: "repeating-linear-gradient(90deg, #39414A 0 1px, transparent 1px 2.5%)" }}
              />
              {[0, 25, 65, 100].map((v) => (
                <span key={v}>
                  <span className="absolute top-0 h-[11px] w-px bg-[#5C666F]" style={{ left: `calc(${v}% - ${v === 100 ? 1 : 0}px)` }} />
                  <span
                    className="absolute top-[13px] -translate-x-1/2 font-mono text-[9px] text-text-muted"
                    style={{ left: `${v === 0 ? 2 : v === 100 ? 97 : v}%` }}
                  >
                    {v}
                  </span>
                </span>
              ))}
              <span
                className="absolute -top-[3px] h-[14px] w-px bg-sodium transition-[left] duration-300 ease-out"
                style={{ left: `${Math.max(0, Math.min(100, state.twi))}%`, boxShadow: "0 0 7px rgba(255,122,26,.85)" }}
              >
                <span
                  className="absolute -top-1 -left-[3.5px] border-x-[3.5px] border-t-[5px] border-x-transparent"
                  style={{ borderTopColor: "var(--color-sodium)" }}
                />
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-[13px]">
            <div className="flex flex-wrap items-center gap-[13px]">
              <span className="inline-flex items-center gap-[9px]">
                <span
                  className="inline-flex items-center gap-[9px] font-display text-t20 uppercase tracking-[.045em]"
                  style={{ fontVariationSettings: '"wdth" 112', fontWeight: 800, color: "var(--color-state-damp)" }}
                >
                  <span
                    className="h-2.5 w-2.5"
                    style={{ background: "var(--color-state-damp)", boxShadow: "0 0 9px rgba(224,163,62,.6)" }}
                  />
                  {state.dominant_class.replace("_", " ")}
                </span>
                <span className="relative h-px w-[22px] bg-[#4A535C]">
                  <span className="absolute -top-[3px] right-0 border-y-[3px] border-l-[5px] border-y-transparent border-l-[#4A535C]" />
                </span>
                <span
                  className="font-display text-t20 uppercase tracking-[.045em]"
                  style={{ fontVariationSettings: '"wdth" 112', fontWeight: 800, color: trendColor(state.trend.direction) }}
                >
                  {state.trend.direction}
                </span>
              </span>
              <span className="tnum text-t15" style={{ color: trendColor(state.trend.direction) }}>
                {state.trend.rate_per_min > 0 ? "+" : "−"}
                {Math.abs(state.trend.rate_per_min).toFixed(1)}
                <span className="text-[.78em] text-text-muted">/min</span>
              </span>
            </div>

            <div
              className="grid grid-cols-4"
              style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.9), inset 0 -1px 0 var(--edge-hi)" }}
            >
              <Cell label="Raw" value={state.twi_raw.toFixed(1)} />
              <Cell label="60s ago" value={minuteAgo ? minuteAgo.twi.toFixed(1) : "—"} />
              <Cell
                label="Δ 60s"
                value={delta === null ? "—" : `${delta > 0 ? "+" : "−"}${Math.abs(delta).toFixed(1)}`}
                color={delta === null ? undefined : delta < 0 ? "var(--color-trend-improving)" : "var(--color-trend-worsening)"}
              />
              <Cell label="Peak" value={peak.toFixed(1)} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Cell({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col gap-[3px] border-l border-black/65 px-[11px] py-2 first:border-l-0">
      <span className="tag">{label}</span>
      <span className="tnum text-t13" style={color ? { color } : undefined}>
        {value}
      </span>
    </div>
  );
}

/* ──────────────────────────────── crossover projection ──────────────────────────── */

const W = 560;
const H = 318;
const X0 = 54;
const X1 = 540;
const Y0 = 14;
const Y1 = 272;

export function CrossoverProjection({ state, history }: { state: TrackState; history: TrackState[] }) {
  const now = new Date(state.timestamp).getTime();
  const elapsed = history.length ? (now - new Date(history[0].timestamp).getTime()) / 1000 : 0;

  /* Window the plot so the crossing is always visible: the session so far on the left,
     and enough forward room for the pessimistic edge of the cone on the right. */
  const pastSpan = Math.max(30, Math.min(elapsed, 480));
  const futureSpan = state.crossover
    ? Math.max(60, Math.min(state.crossover.eta_pessimistic_s * 1.2, 1800))
    : Math.max(60, pastSpan);

  const x = (tRel: number) => X0 + ((tRel + pastSpan) / (pastSpan + futureSpan)) * (X1 - X0);
  const y = (twi: number) => Y1 - (Math.max(0, Math.min(100, twi)) / 100) * (Y1 - Y0);
  const xNow = x(0);

  const visible = history.filter((s) => (new Date(s.timestamp).getTime() - now) / 1000 >= -pastSpan);
  const historyPath = visible
    .map((s, i) => {
      const t = (new Date(s.timestamp).getTime() - now) / 1000;
      return `${i ? "L" : "M"}${x(t).toFixed(1)},${y(s.twi).toFixed(1)}`;
    })
    .join(" ");

  /* The projection is the backend's fitted slope drawn forward — not a refit. */
  const rate = state.trend.rate_per_min;
  const projEnd = state.twi + (rate * futureSpan) / 60;
  const cross = state.crossover;

  const coneOptimistic = cross ? x(cross.eta_optimistic_s) : 0;
  const conePessimistic = cross ? x(cross.eta_pessimistic_s) : 0;

  return (
    <div className="grid min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] bg-mat-panel">
      <div className="panel-head">
        <span className="section-title">Crossover projection</span>
        {cross ? (
          <span
            className="tnum text-t20 font-semibold text-sodium"
            style={{ textShadow: "0 0 14px rgba(255,122,26,.4)" }}
          >
            {clock(cross.eta_s)}
          </span>
        ) : (
          <span className="font-mono text-[10px] tracking-[.1em] text-text-muted">NO PROJECTION</span>
        )}
      </div>

      <div className="well mx-[13px] mt-2.5 flex min-h-0 px-1 pt-1.5">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
          className="block h-full w-full"
          role="img"
          aria-label={
            cross
              ? `Track wetness ${state.twi.toFixed(1)}, ${state.trend.direction.toLowerCase()} at ${Math.abs(rate).toFixed(1)} per minute, crossing ${cross.threshold} in ${clock(cross.eta_s)}.`
              : `Track wetness ${state.twi.toFixed(1)}. No reliable projection: R squared ${state.trend.r_squared.toFixed(2)}.`
          }
        >
          <defs>
            <linearGradient id="cone" gradientUnits="userSpaceOnUse" x1={xNow} y1="0" x2={X1} y2="0">
              <stop offset="0" stopColor="#FF7A1A" stopOpacity="0.3" />
              <stop offset="1" stopColor="#FF7A1A" stopOpacity="0.05" />
            </linearGradient>
            <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#FF7A1A" strokeWidth="1" strokeOpacity="0.16" />
            </pattern>
          </defs>

          {/* compound zones */}
          <rect x={X0} y={y(100)} width={X1 - X0} height={y(65) - y(100)} fill="#3D7DBF" opacity={0.055} />
          <rect x={X0} y={y(65)} width={X1 - X0} height={y(25) - y(65)} fill="#E0A33E" opacity={0.055} />
          <rect x={X0} y={y(25)} width={X1 - X0} height={y(0) - y(25)} fill="#C9D1D9" opacity={0.055} />

          {/* fine grid */}
          <g stroke="#1D242B" strokeWidth={1}>
            {[12.5, 37.5, 50, 75, 87.5].map((v) => (
              <line key={v} x1={X0} y1={y(v)} x2={X1} y2={y(v)} />
            ))}
          </g>

          <line x1={X0} y1={y(65)} x2={X1} y2={y(65)} stroke="#39414A" strokeDasharray="4 3" />
          <line x1={X0} y1={y(25)} x2={X1} y2={y(25)} stroke="#39414A" strokeDasharray="4 3" />
          <line x1={X0} y1={Y1} x2={X1} y2={Y1} stroke="#4A535C" />
          <line x1={X0} y1={Y0} x2={X0} y2={Y1} stroke="#4A535C" />

          <g stroke="#4A535C" strokeWidth={1}>
            {[0, 25, 65, 100].map((v) => (
              <line key={v} x1={X0 - 7} y1={y(v)} x2={X0} y2={y(v)} />
            ))}
          </g>
          <g fill="#7C8791" fontFamily="var(--font-mono)" fontSize="10" textAnchor="end">
            {[0, 25, 65, 100].map((v) => (
              <text key={v} x={X0 - 12} y={y(v) + 3}>
                {v}
              </text>
            ))}
          </g>
          <g fill="#7C8791" fontFamily="var(--font-mono)" fontSize="9" textAnchor="end" letterSpacing="0.14em">
            <text x={X1 - 5} y={y(100) + 14}>FULL WET</text>
            <text x={X1 - 5} y={y(65) + 14}>INTERMEDIATE</text>
            <text x={X1 - 5} y={y(25) + 14}>SLICK</text>
          </g>

          {/* confidence envelope — only when the backend gave one */}
          {cross && (
            <>
              <path d={`M${xNow},${y(state.twi)} L${conePessimistic},${y(cross.threshold)} L${coneOptimistic},${y(cross.threshold)} Z`} fill="url(#cone)" />
              <path d={`M${xNow},${y(state.twi)} L${conePessimistic},${y(cross.threshold)} L${coneOptimistic},${y(cross.threshold)} Z`} fill="url(#hatch)" />
            </>
          )}

          {/* history */}
          <path d={historyPath} fill="none" stroke="var(--color-state-damp)" strokeWidth={2.25} strokeLinejoin="round" strokeLinecap="round" />

          {/* projection, dashed past now — drawn only when the trend gate passed */}
          {state.trend.sufficient_signal && (
            <path
              d={`M${xNow},${y(state.twi)} L${x(futureSpan)},${y(projEnd)}`}
              fill="none"
              stroke="var(--color-state-damp)"
              strokeWidth={4}
              strokeDasharray="9 7"
              opacity={0.55}
              strokeLinecap="round"
            />
          )}

          {/* now */}
          <line x1={xNow} y1={Y0} x2={xNow} y2={Y1} stroke="#7C8791" strokeOpacity={0.5} strokeDasharray="2 3" />
          <line x1={xNow - 10} y1={y(state.twi)} x2={xNow + 10} y2={y(state.twi)} stroke="#E8EBED" strokeOpacity={0.55} />
          <circle cx={xNow} cy={y(state.twi)} r={4} fill="#0A0D10" stroke="#E8EBED" strokeWidth={1.5} />
          <text x={xNow} y={y(state.twi) - 12} textAnchor="middle" fill="#E8EBED" fontFamily="var(--font-mono)" fontSize="10">
            {state.twi.toFixed(1)}
          </text>

          <g fill="#7C8791" fontFamily="var(--font-mono)" fontSize="9" letterSpacing="0.1em">
            <text x={X0} y={Y1 + 18} textAnchor="start">−{clock(pastSpan)}</text>
            <text x={xNow} y={Y1 + 18} textAnchor="middle" fill="#B9C2CA">NOW</text>
            <text x={X1} y={Y1 + 18} textAnchor="end">+{clock(futureSpan)}</text>
          </g>

          {/* the crossing */}
          {cross && (
            <>
              <line x1={x(cross.eta_s)} y1={y(cross.threshold)} x2={x(cross.eta_s)} y2={y(cross.threshold) - 35} stroke="var(--color-sodium)" strokeWidth={1} />
              <circle cx={x(cross.eta_s)} cy={y(cross.threshold)} r={4.5} fill="var(--color-sodium)" />
              <circle cx={x(cross.eta_s)} cy={y(cross.threshold)} r={8} fill="none" stroke="var(--color-sodium)" strokeOpacity={0.35} />
              <rect x={x(cross.eta_s) - 28} y={y(cross.threshold) - 51} width={56} height={15} fill="#0A0D10" stroke="var(--color-sodium)" strokeOpacity={0.5} />
              <text x={x(cross.eta_s)} y={y(cross.threshold) - 40} textAnchor="middle" fill="var(--color-sodium)" fontFamily="var(--font-mono)" fontSize="11" fontWeight={500}>
                {clock(cross.eta_s)}
              </text>
            </>
          )}

          {/* The null state keeps the panel. Showing the system's own uncertainty beats
              hiding it, and it is the answer to "what if it's wrong?". */}
          {!cross && (
            <g textAnchor="middle" fontFamily="var(--font-mono)" letterSpacing="0.12em">
              <text x={(xNow + X1) / 2} y={(Y0 + Y1) / 2 - 8} fill="#B9C2CA" fontSize="12">
                NO RELIABLE PROJECTION
              </text>
              <text x={(xNow + X1) / 2} y={(Y0 + Y1) / 2 + 10} fill="#7C8791" fontSize="10">
                {state.trend.r_squared < 0.4
                  ? `R² ${state.trend.r_squared.toFixed(2)} BELOW THRESHOLD`
                  : `RATE ${Math.abs(rate).toFixed(1)}/MIN BELOW THRESHOLD`}
              </text>
            </g>
          )}
        </svg>
      </div>

      <div className="mt-2.5 flex border-t border-rule" style={{ boxShadow: "inset 0 1px 0 var(--edge-hi)" }}>
        <Readout label="R²" value={state.trend.r_squared.toFixed(2)} />
        <Readout label="Window" value={`${state.trend.window_s.toFixed(0)}s`} />
        <Readout label="Signal" value={state.trend.sufficient_signal ? "Sufficient" : "Insufficient"} />
        <Readout label="Optimistic" value={cross ? clock(cross.eta_optimistic_s) : "—"} />
        <Readout label="Pessimistic" value={cross ? clock(cross.eta_pessimistic_s) : "—"} />
        <Readout label="Target" value={cross ? `${cross.threshold.toFixed(0)} TWI` : "—"} />
      </div>
    </div>
  );
}

function Readout({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-1 flex-col gap-1 border-l border-black/55 px-[13px] py-[9px] first:border-l-0">
      <span className="tag">{label}</span>
      <span className="tnum text-t13">{value}</span>
    </div>
  );
}
