# SPEC-API

Define this before either side is written. Generate the TypeScript client from FastAPI's
OpenAPI schema — never hand-write the types.

```
POST   /api/sessions                 → { session_id, created_at, name }
GET    /api/sessions/{id}            → session + frame history + current state
DELETE /api/sessions/{id}
POST   /api/sessions/{id}/video      multipart → { job_id, frame_count, duration_s }
POST   /api/sessions/{id}/frames     batch image upload
GET    /api/sessions/{id}/state      → TrackState
WS     /ws/sessions/{id}             live analysis stream
GET    /api/health                   → { model_id, mode, device, warm, weather_cache_age_s }
GET    /api/weather?lat=&lon=        → normalised weather + drying prior
```

`TrackState` — the single object the whole UI renders from:

```jsonc
{
  "session_id": "…",
  "timestamp": "2026-08-11T14:03:22Z",
  "twi": 47.3,
  "twi_raw": 51.8,
  "probabilities": { "dry": 0.11, "damp": 0.42, "wet": 0.39, "standing_water": 0.08 },
  "dominant_class": "damp",
  "trend": {
    "direction": "DRYING",
    "rate_per_min": -3.2,
    "r_squared": 0.81,
    "window_s": 45,
    "sufficient_signal": true
  },
  "crossover": {
    "target_compound": "SLICK",
    "threshold": 25.0,
    "eta_s": 270,
    "eta_optimistic_s": 205,
    "eta_pessimistic_s": 400
  },
  "recommendation": {
    "current": "INTERMEDIATE",
    "next": "SLICK",
    "state": "ARMING",
    "windows_held": 2,
    "windows_required": 3,
    "rationale": "TWI 47.3 falling at 3.2/min. Slick threshold in ~4m30s."
  },
  "frame_quality": { "score": 0.83, "blur": 142.6, "clipping": 0.02, "entropy": 0.31 },
  "fusion": { "visual_weight": 0.83, "weather_weight": 0.17, "weather_rate_prior": -2.1 },
  "frame_index": 128,
  "thumbnail_url": "/media/…/128.jpg"
}
```

`crossover` is `null` when gates fail. Every number the UI shows comes from this object.
If the UI needs a value not here, add it to the schema — never compute analysis in the
frontend.
