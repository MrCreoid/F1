"use client";

/**
 * The timeline rail and the status bar.
 *
 * The transport controls are real: they drive replay through the session's stored
 * states. Micro-neumorphism is used here and nowhere else in the app.
 */

import { clock, twiColor, type HealthResponse, type TrackState, type WeatherResponse } from "@/lib/api";

/* ─────────────────────────────────────── status bar ─────────────────────────────── */

export function StatusBar({
  health,
  weather,
  sessionName,
  elapsed,
  frameRate,
}: {
  health: HealthResponse | null;
  weather: WeatherResponse | null;
  sessionName: string;
  elapsed: number;
  frameRate: number;
}) {
  return (
    <header
      className="ww-rise flex items-stretch overflow-x-auto border-b border-rule"
      style={{
        background: "linear-gradient(180deg, #1B2028 0%, #12161B 100%)",
        boxShadow: "inset 0 1px 0 var(--edge-hi), 0 1px 0 rgba(0,0,0,.5)",
        scrollbarWidth: "none",
      }}
    >
      <div className="flex items-center gap-2.5 pr-[15px] pl-4">
        <span className="h-3.5 w-1 bg-sodium" style={{ boxShadow: "0 0 7px rgba(255,122,26,.5)" }} />
        <span
          className="font-display text-t11 whitespace-nowrap uppercase"
          style={{ fontVariationSettings: '"wdth" 120', fontWeight: 800, letterSpacing: ".15em" }}
        >
          Weather Whiplash
        </span>
      </div>

      <Field label="Session" value={sessionName} />
      <Field label="Elapsed" value={clock(elapsed)} />
      <Field label="Air" value={weather ? weather.temperature_c.toFixed(1) : "—"} unit="°C" />
      <Field label="RH" value={weather ? Math.round(weather.relative_humidity * 100).toString() : "—"} unit="%" />
      <Field label="Wind" value={weather ? weather.wind_speed_kmh.toFixed(1) : "—"} unit="km/h" />
      <Field label="Precip" value={weather ? weather.precipitation_mm_h.toFixed(1) : "—"} unit="mm/h" />
      <Field label="Model" value={health ? health.model_id.split("/")[1] ?? health.model_id : "—"} />
      <Field label="Device" value={health ? health.device.toUpperCase() : "—"} />
      <Field label="Mode" value={health ? health.mode : "—"} />

      <div
        className="ml-auto flex items-center gap-[7px] border-l border-black/50 px-3 whitespace-nowrap"
        style={{ boxShadow: "inset 1px 0 0 var(--edge-hi)" }}
      >
        <span
          className={`h-1.5 w-1.5 rounded-full ${health?.warm ? "ww-breathe" : ""}`}
          style={{
            background: health?.warm ? "var(--color-trend-improving)" : "var(--color-state-damp)",
            boxShadow: health?.warm ? "0 0 6px rgba(79,180,119,.7)" : "none",
          }}
        />
        <span className="text-[9.5px] font-semibold tracking-[.15em] text-[#7C8791] uppercase">
          {health?.warm ? "Ready" : "Cold"}
        </span>
        <span className="tnum text-t11">
          {frameRate}
          <span className="text-[.78em] text-text-muted">fps</span>
        </span>
      </div>
    </header>
  );
}

function Field({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div
      className="flex items-center gap-[7px] border-l border-black/50 px-3 whitespace-nowrap"
      style={{ boxShadow: "inset 1px 0 0 var(--edge-hi)" }}
    >
      <span className="text-[9.5px] font-semibold tracking-[.15em] text-[#7C8791] uppercase">{label}</span>
      <span className="tnum text-t11">
        {value}
        {unit && <span className="text-[.78em] text-text-muted">{unit}</span>}
      </span>
    </div>
  );
}

/* ──────────────────────────────────────── the rail ──────────────────────────────── */

export function TimelineRail({
  history,
  index,
  playing,
  onScrub,
  onTogglePlay,
  onStep,
}: {
  history: TrackState[];
  index: number;
  playing: boolean;
  onScrub: (i: number) => void;
  onTogglePlay: () => void;
  onStep: (delta: number) => void;
}) {
  const total = history.length;
  const position = total > 1 ? index / (total - 1) : 0;
  const duration = total ? (new Date(history[total - 1].timestamp).getTime() - new Date(history[0].timestamp).getTime()) / 1000 : 0;

  /* The wetness ribbon is a continuous read of the index, so it is drawn as a gradient
     rather than discrete blocks. Every stop is a real frame. */
  const ribbon =
    total > 1
      ? `linear-gradient(90deg, ${history
          .filter((_, i) => i % Math.max(1, Math.floor(total / 40)) === 0 || i === total - 1)
          .map((s, i, arr) => `${twiColor(s.twi)} ${((i / (arr.length - 1)) * 100).toFixed(1)}%`)
          .join(", ")})`
      : "var(--color-mat-well)";

  const handleScrub = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    onScrub(Math.round(frac * (total - 1)));
  };

  return (
    <footer
      className="ww-rise grid grid-cols-[auto_minmax(0,1fr)] border-t border-rule"
      style={{ background: "linear-gradient(180deg, #171C22 0%, #101419 100%)", boxShadow: "inset 0 1px 0 var(--edge-hi)", animationDelay: ".17s" }}
    >
      <div
        className="flex items-center gap-[7px] border-r border-black/60 px-[15px]"
        style={{ boxShadow: "inset -1px 0 0 var(--edge-hi)" }}
      >
        <TransportButton label="Step back one frame" onClick={() => onStep(-1)}>
          <path d="M10 1 4 6l6 5zM3 1h1.4v10H3z" />
        </TransportButton>
        <TransportButton label={playing ? "Pause replay" : "Play replay"} onClick={onTogglePlay} primary>
          {playing ? <path d="M2.5 1h3v10h-3zM6.5 1h3v10h-3z" /> : <path d="M2 1l9 5-9 5z" />}
        </TransportButton>
        <TransportButton label="Step forward one frame" onClick={() => onStep(1)}>
          <path d="M2 1l6 5-6 5zM7.6 1H9v10H7.6z" />
        </TransportButton>
      </div>

      <div className="relative grid min-w-0 grid-rows-[15px_minmax(0,1fr)_6px] gap-[5px] px-4 pt-2 pb-[9px]">
        <div
          className="relative"
          style={{
            backgroundImage:
              "repeating-linear-gradient(90deg, #39414A 0 1px, transparent 1px 3.571%), repeating-linear-gradient(90deg, #6B747D 0 1px, transparent 1px 21.43%)",
            backgroundSize: "100% 4px, 100% 8px",
            backgroundPosition: "0 100%, 0 100%",
            backgroundRepeat: "no-repeat",
          }}
        >
          {[0, 0.25, 0.5, 0.75].map((f) => (
            <span
              key={f}
              className="absolute top-0 -translate-x-1/2 font-mono text-[9px] tracking-[.06em] text-text-muted"
              style={{ left: `${f * 100}%` }}
            >
              {clock(duration * f)}
            </span>
          ))}
          <span className="absolute top-0 right-0 font-mono text-[9px] tracking-[.13em] text-text-muted uppercase">
            {total} frames · {clock(duration)}
          </span>

          {/* Event markers: degraded frames and the moment the call armed. */}
          {history.map((s, i) =>
            s.frame_quality.score < 0.25 || s.recommendation.state !== "HOLD" ? (
              <span
                key={i}
                className="absolute bottom-0 h-[9px] w-px"
                style={{
                  left: `${(i / Math.max(1, total - 1)) * 100}%`,
                  background:
                    s.recommendation.state !== "HOLD" ? "var(--color-sodium)" : "var(--color-state-damp)",
                }}
              />
            ) : null,
          )}
        </div>

        {/* Frame strip. Phase 7 writes real thumbnails; until then each cell shows the
            frame's own wetness so the strip carries data rather than decoration. */}
        <div className="well cursor-pointer p-0.5" onClick={handleScrub} role="presentation">
          <div className="flex h-full min-w-0 gap-px">
            {history.map((s, i) => (
              <span
                key={i}
                className="min-w-0 flex-1"
                style={{
                  background: twiColor(s.twi),
                  opacity: s.frame_quality.score < 0.25 ? 0.28 : 0.55 + 0.45 * s.frame_quality.score,
                  boxShadow: i === index ? "inset 0 0 0 2px var(--color-sodium)" : undefined,
                }}
              />
            ))}
          </div>
        </div>

        <div style={{ background: ribbon, boxShadow: "inset 0 1px 2px rgba(0,0,0,.5)" }} />

        <span
          className="pointer-events-none absolute top-2 bottom-[9px] z-4 w-px bg-sodium"
          style={{ left: `calc(16px + (100% - 32px) * ${position})`, boxShadow: "0 0 8px rgba(255,122,26,.75)" }}
        >
          <span
            className="absolute -top-px -left-[5px] h-[7px] w-[11px] bg-sodium"
            style={{ clipPath: "polygon(0 0, 100% 0, 50% 100%)" }}
          />
        </span>
      </div>
    </footer>
  );
}

function TransportButton({
  children,
  label,
  onClick,
  primary = false,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
  primary?: boolean;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="grid h-[30px] w-[30px] place-items-center active:translate-y-px"
      style={{
        background: "linear-gradient(180deg, #1F252D 0%, #141A20 100%)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,.09), 0 1px 2px rgba(0,0,0,.6), 0 0 0 1px rgba(0,0,0,.5)",
        color: primary ? "var(--color-sodium)" : "#A7B0B9",
      }}
    >
      <svg viewBox="0 0 12 12" className="h-[11px] w-[11px]" fill="currentColor">
        {children}
      </svg>
    </button>
  );
}
