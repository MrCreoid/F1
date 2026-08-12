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

/* A cold start loads CLIP and runs three warmup passes before the port opens. Measured
   at ~12s here, worst case slower on a cold filesystem cache — 20 attempts at 1.5s
   covers 30s before the UI concludes nothing is listening. */
const HEALTH_ATTEMPTS = 20;
const HEALTH_RETRY_MS = 1500;

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
  const [warming, setWarming] = useState(false);

  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  /* The backend does not accept connections until the model is loaded and warmed —
     FastAPI's lifespan blocks startup — so on a cold start the first health call fails
     for as long as that takes. Reporting "backend unreachable" then is simply wrong, and
     it is wrong at the worst possible moment. Poll instead, say it is warming, and only
     escalate to the actionable error once waiting has stopped being a plausible
     explanation. */
  useEffect(() => {
    let live = true;
    void (async () => {
      for (let attempt = 0; live; attempt++) {
        try {
          const ready = await api.health();
          if (!live) return;
          setHealth(ready);
          setWarming(false);
          setError(null);
          break;
        } catch (e) {
          if (!live) return;
          if (attempt >= HEALTH_ATTEMPTS) {
            setWarming(false);
            setError(e instanceof ApiError ? e.message : String(e));
            return;
          }
          setWarming(true);
          await new Promise((r) => setTimeout(r, HEALTH_RETRY_MS));
        }
      }
      if (!live) return;
      const rest = await Promise.allSettled([api.weather(), api.samples()]);
      if (!live) return;
      if (rest[0].status === "fulfilled") setWeather(rest[0].value);
      if (rest[1].status === "fulfilled") setSamples(rest[1].value);
      else if (rest[1].reason instanceof ApiError) setError(rest[1].reason.message);
    })();
    return () => {
      live = false;
    };
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
      // Space on a focused button already activates it. Handling it here as well
      // toggled twice and cancelled out, so a keyboard user could not start playback
      // with the one control they can reach. Let the button own its own key.
      if (e.key === " " && !(e.target as HTMLElement)?.closest("button")) {
        e.preventDefault();
        setPlaying((p) => !p);
      }
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
    // min-h rather than h: on a short or narrow viewport the three sample cards and the
    // upload row are taller than the screen, and a fixed height would clip the only
    // controls the app has at that moment.
    return (
      <main className="grid min-h-dvh grid-rows-[30px_minmax(0,1fr)]">
        <StatusBar health={health} weather={weather} sessionName="No session" elapsed={0} frameRate={0} warming={warming} />
        <EmptyState
          samples={samples}
          busy={busy}
          error={error}
          warming={warming}
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
    <main className="workstation">
      <div style={{ gridArea: "bar" }}>
        <StatusBar
          health={health}
          weather={weather}
          sessionName={sourceName}
          elapsed={elapsed}
          frameRate={REPLAY_FPS}
          warming={warming}
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
