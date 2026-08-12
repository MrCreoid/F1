"use client";

/**
 * The timeline rail and the status bar.
 *
 * The transport controls are real: they drive replay through the session's stored
 * states. Micro-neumorphism is used here and nowhere else in the app.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import {
  DEGRADED_BELOW,
  clock,
  twiColor,
  type HealthResponse,
  type TrackState,
  type WeatherResponse,
} from "@/lib/api";

/**
 * Target width of one filmstrip cell. At the rail's ~64px height a 16:9 frame is 114px
 * wide, so 104 crops a sliver off each side rather than letterboxing — an editor's
 * filmstrip is contiguous footage, not a row of thumbnails floating in gutters.
 */
const CELL_W = 104;

/* ─────────────────────────────────────── status bar ─────────────────────────────── */

export function StatusBar({
  health,
  weather,
  sessionName,
  elapsed,
  frameRate,
  warming = false,
}: {
  health: HealthResponse | null;
  weather: WeatherResponse | null;
  sessionName: string;
  elapsed: number;
  frameRate: number;
  warming?: boolean;
}) {
  /* Three states, not two. "Cold" was shown both while the model was loading and when
     nothing was listening, which are opposite situations for whoever is standing there. */
  const link = health?.warm
    ? { label: "Ready", color: "var(--color-trend-improving)", glow: "0 0 6px rgba(79,180,119,.7)" }
    : warming
      ? { label: "Warming", color: "var(--color-sodium)", glow: "0 0 6px rgba(255,122,26,.7)" }
      : { label: "Cold", color: "var(--color-state-damp)", glow: "none" };
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
          className={`h-1.5 w-1.5 rounded-full ${health?.warm || warming ? "ww-breathe" : ""}`}
          style={{ background: link.color, boxShadow: link.glow }}
        />
        <span className="text-[9.5px] font-semibold tracking-[.15em] text-[#7C8791] uppercase">
          {link.label}
        </span>
        {/* The real measured per-frame cost on this machine, not a number from a README. */}
        <span className="tnum text-t11">
          {health?.warmup_ms != null ? health.warmup_ms.toFixed(0) : frameRate}
          <span className="text-[.78em] text-text-muted">
            {health?.warmup_ms != null ? "ms/frm" : "fps"}
          </span>
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

  /* How many frames fit as legible thumbnails is a question only the rendered width can
     answer, and the answer changes with the viewport. Measure it rather than assume. */
  const strip = useRef<HTMLDivElement>(null);
  const [capacity, setCapacity] = useState(12);
  useEffect(() => {
    const element = strip.current;
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => {
      setCapacity(Math.max(1, Math.floor(entry.contentRect.width / CELL_W)));
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  /* Each cell stands for a contiguous run of frames and shows that run's middle frame.
     Ranges rather than samples, so the cell under the playhead is always well defined —
     and so a degraded frame anywhere inside a cell still marks it. A warning must not be
     averaged away by the frames either side of it. */
  const cells = useMemo(() => {
    const count = Math.min(Math.max(1, capacity), Math.max(1, total));
    return Array.from({ length: count }, (_, c) => {
      const from = Math.floor((c * total) / count);
      const to = Math.max(from + 1, Math.floor(((c + 1) * total) / count));
      const run = history.slice(from, to);
      return {
        from,
        frame: run[Math.floor(run.length / 2)] ?? history[from],
        degraded: run.some((s) => s.frame_quality.score < DEGRADED_BELOW),
        current: index >= from && index < to,
      };
    });
  }, [history, total, capacity, index]);

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
            s.frame_quality.score < DEGRADED_BELOW || s.recommendation.state !== "HOLD" ? (
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

        {/* The filmstrip. Click anywhere to scrub — the cell is the picture, but the
            landing frame is read continuously from the x position, so scrubbing is as
            fine-grained as the footage rather than as coarse as the thumbnails. */}
        <div
          ref={strip}
          className="well cursor-pointer p-0.5 outline-sodium focus-visible:outline-2 focus-visible:outline-offset-2"
          onClick={handleScrub}
          role="slider"
          tabIndex={0}
          aria-label="Frame timeline"
          aria-valuemin={0}
          aria-valuemax={Math.max(0, total - 1)}
          aria-valuenow={index}
          aria-valuetext={`Frame ${index + 1} of ${total} · ${clock((duration * position) || 0)}`}
        >
          <div className="flex h-full min-w-0">
            {cells.map((cell) => (
              <span
                key={cell.from}
                className="relative block min-w-0 flex-1 overflow-hidden border-r border-black/70 last:border-r-0"
                /* The wetness colour sits under the image, so a cell reads as data from
                   the first paint and resolves into footage as the JPEG lands. */
                style={{ background: twiColor(cell.frame.twi) }}
              >
                {cell.frame.thumbnail_url && (
                  // eslint-disable-next-line @next/next/no-img-element -- backend-served frame, not a static asset
                  <img
                    src={cell.frame.thumbnail_url}
                    alt=""
                    draggable={false}
                    className="h-full w-full object-cover"
                    /* Suppressed, not hidden. A distrusted frame still has to be
                       readable — the user is being told the system doubts it, not
                       that it is gone. */
                    style={cell.degraded ? { opacity: 0.5 } : undefined}
                  />
                )}
                {cell.degraded && (
                  /* Hatched, the drafting mark for a region that does not count. It
                     has to survive being 100px wide over bright spray, so the lines
                     carry weight rather than a tint. */
                  <span
                    className="absolute inset-0"
                    style={{
                      backgroundImage:
                        "repeating-linear-gradient(45deg, rgba(224,163,62,.85) 0 1.5px, transparent 1.5px 6px)",
                      boxShadow: "inset 0 0 0 1px rgba(224,163,62,.55)",
                    }}
                  />
                )}
                {cell.current && (
                  <span
                    className="absolute inset-0"
                    style={{ boxShadow: "inset 0 0 0 2px var(--color-sodium)" }}
                  />
                )}
              </span>
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
