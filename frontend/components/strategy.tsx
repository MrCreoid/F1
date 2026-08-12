"use client";

/**
 * Column C — the call and the inputs behind it.
 *
 * The pit call separates three things visually: what the track is now, what is
 * recommended, and how long until it changes. The recommendation is the most important
 * element in the module.
 */

import {
  COMPOUND_LABEL,
  FALLBACK_THRESHOLDS,
  clock,
  trendColor,
  type Thresholds,
  type TrackState,
  type WeatherResponse,
} from "@/lib/api";
import { ratePerMin } from "@/lib/chart";

/* ─────────────────────────────────────── pit call ───────────────────────────────── */

export function PitCall({ state, history }: { state: TrackState; history: TrackState[] }) {
  const rec = state.recommendation;
  const arming = rec.state === "ARMING";
  const boxing = rec.state === "BOX";

  /* On BOX the change has already happened: `current` is the new compound and `next` is
     null, so the schema alone cannot say what was left behind — and the instant the call
     fires is the one moment the transition matters most. The compound being left is in
     the previous frame's state. Reading it from history keeps this a drawing decision
     rather than a new analysis field. */
  const left = boxing ? history.at(-2)?.recommendation.current : undefined;
  const from = left && left !== rec.current ? left : rec.current;
  const to = boxing ? (from === rec.current ? null : rec.current) : rec.next;

  const accent = boxing
    ? "var(--color-sodium)"
    : arming
      ? "var(--color-state-dry)"
      : "var(--color-rule)";

  return (
    <div className="relative border-b border-rule bg-mat-panel" aria-live="polite">
      <div className="panel-head">
        <span className="section-title">Pit call</span>
        <span
          className="font-mono text-[10px] tracking-[.1em]"
          style={{ color: arming || boxing ? "var(--color-state-dry)" : "var(--color-text-muted)" }}
        >
          {rec.state}
          {rec.state !== "HOLD" ? ` ${rec.windows_held}/${rec.windows_required}` : ""}
        </span>
      </div>

      <div className="px-3 pt-[11px] pb-3">
        {/* current condition — recessed, secondary */}
        <div
          className="flex items-center justify-between px-[11px] py-2"
          style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.85), inset 0 -1px 0 var(--edge-hi)" }}
        >
          <span className="tag">Current</span>
          <span className="tnum text-t13" style={{ color: "var(--color-state-damp)" }}>
            {COMPOUND_LABEL[rec.current].toUpperCase()} · TWI {state.twi.toFixed(1)}
          </span>
        </div>

        {/* recommended action — raised, primary. Border pulses while arming. */}
        <div
          className={`chamfer-sm mt-[9px] p-px ${arming ? "ww-arm" : ""}`}
          style={{ background: accent }}
        >
          <div
            className="chamfer-sm px-[13px] pt-[11px] pb-3"
            style={{
              background: "linear-gradient(180deg, #1C222A 0%, #12161B 100%)",
              boxShadow: "inset 0 1px 0 var(--edge-hi), inset 0 -2px 6px rgba(0,0,0,.55)",
            }}
          >
            <span className="tag mb-[9px] block">Recommended action</span>
            <div
              className="flex items-center gap-[11px] font-display uppercase leading-none"
              style={{ fontSize: 27, fontVariationSettings: '"wdth" 112', fontWeight: 800 }}
            >
              <span style={{ color: "#8D969E" }}>{COMPOUND_LABEL[from]}</span>
              {to && (
                <>
                  <span className="relative h-px w-[22px] bg-sodium">
                    <span className="absolute -top-[3.5px] right-0 border-y-[3.5px] border-l-[6px] border-y-transparent" style={{ borderLeftColor: "var(--color-sodium)" }} />
                  </span>
                  <span
                    style={
                      boxing
                        ? { color: "var(--color-sodium)", textShadow: "0 0 18px rgba(255,122,26,.45)" }
                        : { color: "var(--color-state-dry)", textShadow: "0 0 16px rgba(201,209,217,.3)" }
                    }
                  >
                    {COMPOUND_LABEL[to]}
                  </span>
                </>
              )}
              {!to && <span className="tag ml-2">{boxing ? "now" : "held"}</span>}
            </div>

            {/* windows held — the call arming before it fires */}
            <div className="mt-3 flex gap-1">
              {Array.from({ length: rec.windows_required }, (_, i) => (
                <i
                  key={i}
                  className="h-2 flex-1"
                  style={
                    i < rec.windows_held
                      ? {
                          background:
                            "linear-gradient(180deg, rgba(255,255,255,.28), rgba(255,255,255,0) 60%), var(--color-state-dry)",
                          boxShadow: "0 0 8px rgba(201,209,217,.28)",
                        }
                      : {
                          background: "var(--color-mat-well)",
                          boxShadow: "inset 0 1px 2px rgba(0,0,0,.9), inset 0 -1px 0 var(--edge-hi)",
                        }
                  }
                />
              ))}
            </div>
          </div>
        </div>

        {/* time to transition — its own field */}
        <div
          className="mt-[9px] flex items-baseline justify-between px-[11px] py-2"
          style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.85), inset 0 -1px 0 var(--edge-hi)" }}
        >
          <span className="tag">Time to transition</span>
          <span
            className="tnum text-t20 font-semibold"
            style={{ color: state.crossover ? "var(--color-sodium)" : "var(--color-text-muted)", textShadow: state.crossover ? "0 0 12px rgba(255,122,26,.35)" : "none" }}
          >
            {state.crossover ? clock(state.crossover.eta_s) : "—:—"}
          </span>
        </div>

        <p className="mt-[11px] text-t13 leading-[1.36] text-[#B9C2CA]">{rec.rationale}</p>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────── weather ────────────────────────────────── */

export function WeatherPanel({ weather }: { weather: WeatherResponse | null }) {
  return (
    <div className="border-b border-rule bg-mat-panel">
      <div className="panel-head">
        <span className="section-title">Weather</span>
        <span className="font-mono text-[10px] tracking-[.06em] text-text-muted">
          {weather ? weather.source.toUpperCase() : "…"}
          {weather?.cache_age_s != null ? ` · ${Math.round(weather.cache_age_s)}s` : ""}
        </span>
      </div>

      <div className="grid grid-cols-2">
        <WxCell label="Air" value={weather ? weather.temperature_c.toFixed(1) : "—"} unit="°C" border />
        <WxCell label="Humidity" value={weather ? Math.round(weather.relative_humidity * 100).toString() : "—"} unit="%" />
        <WxCell label="Wind" value={weather ? weather.wind_speed_kmh.toFixed(1) : "—"} unit="km/h" border top />
        <WxCell label="Cloud" value={weather ? Math.round(weather.cloud_cover * 100).toString() : "—"} unit="%" top />
      </div>

      <div
        className="mx-3 mb-[11px] flex items-center justify-between px-2.5 py-[7px]"
        style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.85), inset 0 -1px 0 var(--edge-hi)" }}
      >
        <span className="tag">Drying prior</span>
        <span className="tnum text-t15" style={{ color: "var(--color-trend-improving)" }}>
          {weather ? `${weather.drying_rate_prior > 0 ? "+" : "−"}${Math.abs(weather.drying_rate_prior).toFixed(2)}` : "—"}
          <span className="text-[.78em] text-text-muted">/min</span>
        </span>
      </div>
    </div>
  );
}

function WxCell({
  label,
  value,
  unit,
  border = false,
  top = false,
}: {
  label: string;
  value: string;
  unit: string;
  border?: boolean;
  top?: boolean;
}) {
  return (
    <div
      className={`flex flex-col gap-1 px-3 py-[7px] ${border ? "border-r border-black/55" : ""} ${top ? "border-t border-black/50" : ""}`}
    >
      <span className="tag">{label}</span>
      <span className="tnum text-t15">
        {value}
        <span className="text-[.78em] text-text-muted">{unit}</span>
      </span>
    </div>
  );
}

/* ────────────────────────────────────── rate fusion ─────────────────────────────── */

export function RateFusion({ state }: { state: TrackState }) {
  const visual = Math.round(state.fusion.visual_weight * 100);
  return (
    <div className="border-b border-rule bg-mat-panel px-3 pt-2.5 pb-[11px]">
      <div className="flex items-baseline justify-between">
        <span className="section-title">Rate fusion</span>
        <span className="font-mono text-[10px] text-text-muted">2 SOURCES</span>
      </div>

      {/* Segmented bargraph: two sources on one shared scale, discrete elements. */}
      <div
        className="my-[9px] flex h-3.5 p-0.5"
        style={{ background: "var(--color-mat-well)", boxShadow: "inset 0 1px 3px rgba(0,0,0,.9), inset 0 -1px 0 var(--edge-hi)" }}
      >
        <span
          className="block transition-[width] duration-300 ease-out"
          style={{
            width: `${visual}%`,
            color: "var(--color-state-dry)",
            backgroundImage: "repeating-linear-gradient(90deg, currentColor 0 4px, transparent 4px 6px)",
          }}
        />
        <span
          className="block transition-[width] duration-300 ease-out"
          style={{
            width: `${100 - visual}%`,
            color: "var(--color-state-wet)",
            backgroundImage: "repeating-linear-gradient(90deg, currentColor 0 4px, transparent 4px 6px)",
          }}
        />
      </div>

      <div className="flex items-baseline justify-between">
        <span className="tag">
          Visual <b className="tnum font-medium text-text-primary">{visual}%</b>
        </span>
        <span className="tag">
          Weather <b className="tnum font-medium text-text-primary">{100 - visual}%</b>
        </span>
      </div>

      <div className="mt-2 flex items-baseline justify-between border-t border-black/50 pt-2">
        <span className="tag">Fused rate</span>
        {/* Also gated: the colour said "improving" regardless of sign, and the number was
            printed even when the fit behind it had already failed. */}
        <span
          className="tnum text-t15"
          style={{
            color: state.trend.sufficient_signal
              ? trendColor(state.trend.direction)
              : "var(--color-text-muted)",
          }}
        >
          {ratePerMin(state.trend.rate_per_min, state.trend.sufficient_signal)}
          <span className="text-[.78em] text-text-muted">/min</span>
        </span>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────── event log ──────────────────────────────── */

export type LogEntry = { t: string; text: string; level: "info" | "good" | "warn" | "act" };

const LEVEL_COLOR: Record<LogEntry["level"], string> = {
  info: "#4A535C",
  good: "var(--color-trend-improving)",
  warn: "var(--color-state-damp)",
  act: "var(--color-sodium)",
};

export function EventLog({ entries }: { entries: LogEntry[] }) {
  return (
    <div className="ww-log grid min-h-0 grid-rows-[auto_minmax(0,1fr)] bg-mat-panel">
      <div className="panel-head">
        <span className="section-title">Event log</span>
        <span className="font-mono text-[10px] text-text-muted">{entries.length}</span>
      </div>
      <div className="overflow-auto">
        {entries.length === 0 ? (
          <p className="tag px-3 py-3">No events yet.</p>
        ) : (
          entries.map((e, i) => (
            <div
              key={`${e.t}-${i}`}
              className="grid grid-cols-[8px_60px_minmax(0,1fr)] items-baseline gap-[9px] border-b border-black/45 px-3 py-1.5 text-[11px]"
            >
              <span
                className="h-1.5 w-1.5 -translate-y-px"
                style={{ background: LEVEL_COLOR[e.level], boxShadow: e.level === "info" ? "none" : `0 0 5px ${LEVEL_COLOR[e.level]}` }}
              />
              <span className="tnum text-[10px] text-text-muted">{e.t}</span>
              <span
                className="tracking-[.02em]"
                style={{ color: e.level === "act" ? "var(--color-sodium)" : e.level === "warn" ? "var(--color-state-damp)" : "#B9C2CA" }}
              >
                {e.text}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/**
 * Events are derived from the state history — every entry is a real transition the
 * backend reported, not a decorative feed.
 */
export function deriveEvents(
  history: TrackState[],
  sourceName: string,
  thresholds: Thresholds = FALLBACK_THRESHOLDS,
): LogEntry[] {
  const out: LogEntry[] = [];
  const hhmmss = (iso: string) => new Date(iso).toISOString().slice(11, 19);

  history.forEach((s, i) => {
    const prev = i > 0 ? history[i - 1] : null;
    if (!prev) {
      out.push({ t: hhmmss(s.timestamp), text: `Session opened · ${sourceName}`, level: "info" });
      return;
    }
    if (s.recommendation.state !== prev.recommendation.state) {
      const level = s.recommendation.state === "BOX" ? "act" : s.recommendation.state === "ARMING" ? "act" : "info";
      const label =
        s.recommendation.state === "BOX"
          ? `Box · ${COMPOUND_LABEL[prev.recommendation.current].toLowerCase()} → ${COMPOUND_LABEL[s.recommendation.current].toLowerCase()}`
          : s.recommendation.state === "ARMING"
            ? `Arming · ${COMPOUND_LABEL[s.recommendation.next ?? s.recommendation.current].toLowerCase()} · window ${s.recommendation.windows_held}/${s.recommendation.windows_required}`
            : "Call disarmed · margin lost";
      out.push({ t: hhmmss(s.timestamp), text: label, level });
    }
    if (s.trend.direction !== prev.trend.direction) {
      out.push({
        t: hhmmss(s.timestamp),
        text:
          s.trend.direction === "STABLE"
            ? `Stable · ${s.trend.sufficient_signal ? "rate below threshold" : "insufficient signal"}`
            : `Trend ${s.trend.direction.toLowerCase()} · R² ${s.trend.r_squared.toFixed(2)}`,
        level: s.trend.direction === "STABLE" ? "info" : "good",
      });
    }
    const wasDegraded = prev.frame_quality.score < thresholds.quality_flag;
    const isDegraded = s.frame_quality.score < thresholds.quality_flag;
    if (isDegraded && !wasDegraded) {
      out.push({ t: hhmmss(s.timestamp), text: "Signal degraded · frame distrusted", level: "warn" });
    }
    if (!isDegraded && wasDegraded) {
      out.push({ t: hhmmss(s.timestamp), text: `Signal recovered · ${s.frame_quality.score.toFixed(2)}`, level: "good" });
    }
  });

  return out.reverse();
}
