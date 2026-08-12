"use client";

/**
 * The workstation.
 *
 * All analysis happens server-side; this file fetches a session's stored per-frame
 * states and replays them. Scrubbing and stepping move an index through that history —
 * every panel renders exactly what the backend knew at that frame.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ApiError,
  api,
  type HealthResponse,
  type Sample,
  type TrackState,
  type WeatherResponse,
} from "@/lib/api";
import { CameraMonitor, FrameQualityPanel, SurfaceDistribution } from "@/components/observation";
import { CrossoverProjection, HeroInstrument } from "@/components/decision";
import { EventLog, PitCall, RateFusion, WeatherPanel, deriveEvents } from "@/components/strategy";
import { StatusBar, TimelineRail } from "@/components/rail";
import { EmptyState } from "@/components/empty-state";

/** Replay runs at the analysis rate, so one second on screen is one second of footage. */
const REPLAY_FPS = 4;

export default function Workstation() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [weather, setWeather] = useState<WeatherResponse | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);

  const [history, setHistory] = useState<TrackState[]>([]);
  const [sourceName, setSourceName] = useState("—");
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void (async () => {
      const results = await Promise.allSettled([api.health(), api.weather(), api.samples()]);
      if (results[0].status === "fulfilled") setHealth(results[0].value);
      if (results[1].status === "fulfilled") setWeather(results[1].value);
      if (results[2].status === "fulfilled") setSamples(results[2].value);
      else if (results[2].reason instanceof ApiError) setError(results[2].reason.message);
    })();
  }, []);

  /* Replay. Stops itself at the end rather than looping — an instrument that silently
     restarts would misrepresent the data. */
  useEffect(() => {
    if (!playing || history.length === 0) return;
    timer.current = setInterval(() => {
      setIndex((i) => {
        if (i >= history.length - 1) {
          setPlaying(false);
          return i;
        }
        return i + 1;
      });
    }, 1000 / REPLAY_FPS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, history.length]);

  const step = useCallback(
    (delta: number) => {
      setPlaying(false);
      setIndex((i) => Math.max(0, Math.min(history.length - 1, i + delta)));
    },
    [history.length],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (history.length === 0) return;
      if (e.key === "ArrowLeft") { e.preventDefault(); step(-1); }
      if (e.key === "ArrowRight") { e.preventDefault(); step(1); }
      if (e.key === " ") { e.preventDefault(); setPlaying((p) => !p); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [history.length, step]);

  const start = useCallback(
    async (label: string, run: (sessionId: string) => Promise<unknown>) => {
      setBusy(label);
      setError(null);
      try {
        const session = await api.createSession(label, label);
        await run(session.session_id);
        const states = await api.states(session.session_id);
        if (states.length === 0) {
          setError("No frames analysed. The clip may be unreadable.");
          return;
        }
        setHistory(states);
        setSourceName(label);
        setIndex(states.length - 1);
        setPlaying(false);
        // Weather is fetched per session so the cache age shown is honest.
        void api.weather().then(setWeather).catch(() => undefined);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : String(e));
      } finally {
        setBusy(null);
      }
    },
    [],
  );

  const current = history[Math.min(index, history.length - 1)] ?? null;
  const upTo = useMemo(() => history.slice(0, index + 1), [history, index]);
  const events = useMemo(() => deriveEvents(upTo, sourceName), [upTo, sourceName]);
  const elapsed = current && history.length
    ? (new Date(current.timestamp).getTime() - new Date(history[0].timestamp).getTime()) / 1000
    : 0;

  if (!current) {
    return (
      <main className="grid h-dvh grid-rows-[30px_minmax(0,1fr)]">
        <StatusBar health={health} weather={weather} sessionName="No session" elapsed={0} frameRate={0} />
        <EmptyState
          samples={samples}
          busy={busy}
          error={error}
          onSample={(id) => {
            const s = samples.find((x) => x.id === id);
            void start(s?.name ?? id, (sid) => api.runSample(sid, id));
          }}
          onUpload={(file) => void start(file.name, (sid) => api.uploadVideo(sid, file))}
        />
      </main>
    );
  }

  return (
    <main
      className="grid h-dvh"
      style={{
        gridTemplateColumns: "348px minmax(0, 1fr) 324px",
        gridTemplateRows: "30px minmax(0, 1fr) 112px",
        gridTemplateAreas: '"bar bar bar" "a b c" "rail rail rail"',
      }}
    >
      <div style={{ gridArea: "bar" }}>
        <StatusBar
          health={health}
          weather={weather}
          sessionName={sourceName}
          elapsed={elapsed}
          frameRate={REPLAY_FPS}
        />
      </div>

      <section
        className="ww-rise grid min-h-0 grid-rows-[auto_auto_minmax(0,1fr)] border-r border-rule bg-mat-panel"
        style={{ gridArea: "a", animationDelay: ".05s" }}
      >
        <CameraMonitor state={current} sourceName={sourceName} />
        <SurfaceDistribution history={upTo} />
        <FrameQualityPanel quality={current.frame_quality} />
      </section>

      <section
        className="ww-rise grid min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)]"
        style={{ gridArea: "b", animationDelay: ".09s" }}
      >
        <HeroInstrument state={current} history={upTo} />
        <CrossoverProjection state={current} history={upTo} running={playing} />
      </section>

      <section
        className="ww-rise grid min-h-0 grid-rows-[auto_auto_auto_minmax(0,1fr)] border-l border-black/60 bg-mat-panel"
        style={{ gridArea: "c", animationDelay: ".13s", boxShadow: "inset 1px 0 0 var(--edge-hi)" }}
      >
        <PitCall state={current} history={upTo} />
        <WeatherPanel weather={weather} />
        <RateFusion state={current} />
        <EventLog entries={events} />
      </section>

      <div style={{ gridArea: "rail" }}>
        <TimelineRail
          history={history}
          index={index}
          playing={playing}
          onScrub={(i) => { setPlaying(false); setIndex(i); }}
          onTogglePlay={() => setPlaying((p) => !p)}
          onStep={step}
        />
      </div>
    </main>
  );
}
