/**
 * Typed client over the FastAPI backend.
 *
 * Every type here is pulled from `schema.d.ts`, which is generated from the live
 * OpenAPI document (`npm run gen:api`). Nothing on this side is hand-written, so the
 * contract cannot drift silently — if the backend changes a field, this stops compiling.
 *
 * The frontend never computes analysis. It renders what the backend returns.
 */

import type { components } from "./schema";

export type TrackState = components["schemas"]["TrackState"];
export type FrameClassification = components["schemas"]["FrameClassification"];
export type SessionDetail = components["schemas"]["SessionDetail"];
export type SessionSummary = components["schemas"]["SessionSummary"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type WeatherResponse = components["schemas"]["WeatherResponse"];
export type VideoUploadResponse = components["schemas"]["VideoUploadResponse"];
export type Sample = components["schemas"]["Sample"];
export type Trend = components["schemas"]["Trend"];
export type Crossover = components["schemas"]["Crossover"];
export type Recommendation = components["schemas"]["Recommendation"];
export type FrameQuality = components["schemas"]["FrameQuality"];
export type Fusion = components["schemas"]["Fusion"];
export type ClassProbabilities = components["schemas"]["ClassProbabilities"];
export type AppearanceClass = keyof ClassProbabilities;
export type Compound = Recommendation["current"];

/**
 * Empty by default: `/api/*` is same-origin and rewritten to FastAPI by next.config.ts.
 * Set NEXT_PUBLIC_API_BASE to call a backend directly instead (it must then allow CORS).
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

/** Errors name the failure and, where the backend gave one, the fix. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new ApiError(
      "Backend unreachable. Start it: cd backend && ../.venv/bin/python -m uvicorn app.main:app --port 8000",
      0,
    );
  }

  if (!response.ok) {
    // FastAPI puts the human-readable reason in `detail`; surface it verbatim rather
    // than replacing it with "Something went wrong".
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) {
        detail = String((body as { detail: unknown }).detail);
      }
    } catch {
      /* non-JSON error body: keep the status line */
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  weather: () => request<WeatherResponse>("/api/weather"),

  samples: () => request<Sample[]>("/api/samples"),

  createSession: (name: string, source?: string | null) =>
    request<SessionSummary>("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, source: source ?? null }),
    }),

  session: (id: string) => request<SessionDetail>(`/api/sessions/${id}`),

  /** Every analysed frame's full state, in order. This is the replay path. */
  states: (id: string) => request<TrackState[]>(`/api/sessions/${id}/states`),

  runSample: (sessionId: string, sampleId: string) =>
    request<VideoUploadResponse>(`/api/sessions/${sessionId}/sample/${sampleId}`, {
      method: "POST",
    }),

  uploadVideo: (sessionId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<VideoUploadResponse>(`/api/sessions/${sessionId}/video`, {
      method: "POST",
      body: form,
    });
  },
};

/* ─────────────────────────────── shared presentation helpers ─────────────────────── */

export const CLASS_ORDER = ["dry", "damp", "wet", "standing_water"] as const;

export const CLASS_COLOR: Record<AppearanceClass, string> = {
  dry: "var(--color-state-dry)",
  damp: "var(--color-state-damp)",
  wet: "var(--color-state-wet)",
  standing_water: "var(--color-state-standing)",
};

export const CLASS_LABEL: Record<AppearanceClass, string> = {
  dry: "Dry",
  damp: "Damp",
  wet: "Wet",
  standing_water: "Stand",
};

export const COMPOUND_LABEL: Record<Compound, string> = {
  SLICK: "Slick",
  INTERMEDIATE: "Inter",
  FULL_WET: "Full wet",
};

/** mm:ss. Countdown values are always shown padded so the digits never jump width. */
export function clock(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function trendColor(direction: Trend["direction"]): string {
  if (direction === "DRYING") return "var(--color-trend-improving)";
  if (direction === "WETTING") return "var(--color-trend-worsening)";
  return "var(--color-text-muted)";
}

/**
 * Frame quality below which the backend flags a frame as degraded — the mirror of
 * `config.QUALITY_FLAG_THRESHOLD`. The gate itself lives server-side; this is only the
 * value the UI draws the warning at, and it must not drift from it.
 */
export const DEGRADED_BELOW = 0.25;

/** Colour the index by the band it sits in — the same scale the chart uses. */
export function twiColor(twi: number): string {
  if (twi < 25) return "var(--color-state-dry)";
  if (twi < 65) return "var(--color-state-damp)";
  return "var(--color-state-wet)";
}
