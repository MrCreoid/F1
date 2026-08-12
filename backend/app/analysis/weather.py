"""B.7 — weather fusion. Real API, no key, and it works with the network unplugged.

Open-Meteo needs no API key, so there is no secret to leak and no quota to exhaust
during judging. Everything here degrades: timeout, bounded retries, a 10-minute cache,
and a bundled fallback snapshot so the demo survives dead venue Wi-Fi (competition
rule 4).

The physical prior answers a question the camera cannot: a track under cloud at 6°C in
saturated air will not dry, however dry the last few frames looked.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app import config


@dataclass(frozen=True)
class WeatherSnapshot:
    temperature_c: float
    wind_speed_kmh: float
    relative_humidity: float  # 0-1
    cloud_cover: float  # 0-1
    precipitation_mm_h: float
    source: str  # "open-meteo" | "offline-fallback"


# Bundled so the app never has a hard network dependency. Deliberately unremarkable
# conditions — mild, damp, overcast — so the prior it produces is weak rather than
# confidently wrong when we are flying blind.
OFFLINE_FALLBACK = WeatherSnapshot(
    temperature_c=15.0,
    wind_speed_kmh=8.0,
    relative_humidity=0.75,
    cloud_cover=0.80,
    precipitation_mm_h=0.0,
    source="offline-fallback",
)

_cache: tuple[float, WeatherSnapshot] | None = None


def drying_rate_prior(weather: WeatherSnapshot) -> float:
    """Expected TWI change per minute from physics alone. Negative dries, positive wets.

    Rain dominates everything: while it is falling, evaporation is irrelevant to the
    net result, so precipitation short-circuits the evaporative terms.
    """
    if weather.precipitation_mm_h > 0.0:
        return config.WETTING_PER_MM_H * weather.precipitation_mm_h

    # Four normalised drivers of evaporation, averaged. Averaged rather than multiplied
    # so that one still afternoon does not zero out a hot dry day — evaporation slows,
    # it does not stop.
    warmth = _clamp(weather.temperature_c / 35.0)
    wind = _clamp(weather.wind_speed_kmh / 40.0)
    dryness = _clamp(1.0 - weather.relative_humidity)
    sun = _clamp(1.0 - weather.cloud_cover)
    forcing = (warmth + wind + dryness + sun) / 4.0

    return config.DRYING_BASE_RATE + config.DRYING_FORCING_RATE * forcing


def fuse_rates(*, rate_visual: float, rate_prior: float, visual_weight: float) -> float:
    """Blend by how much the footage can be trusted (B.7).

    The weight is mean frame quality: clean footage means the camera wins, degraded
    footage falls back on physics. The UI shows this split, because a system that
    admits where its answer came from is more trustworthy than one that does not.
    """
    weight = _clamp(visual_weight)
    return weight * rate_visual + (1.0 - weight) * rate_prior


def get_weather(lat: float = config.DEFAULT_LAT, lon: float = config.DEFAULT_LON) -> WeatherSnapshot:
    """Cached, retried, and guaranteed to return — falling back rather than raising."""
    global _cache

    if config.OFFLINE_MODE:
        return OFFLINE_FALLBACK

    if _cache is not None:
        fetched_at, snapshot = _cache
        if time.monotonic() - fetched_at < config.WEATHER_CACHE_TTL_S:
            return snapshot

    delay = config.WEATHER_BACKOFF_S
    for attempt in range(config.WEATHER_RETRIES):
        try:
            snapshot = _fetch_open_meteo(lat, lon)
        except Exception:  # noqa: BLE001 - any failure means fall back, never raise at the caller
            if attempt < config.WEATHER_RETRIES - 1:
                time.sleep(delay)
                delay *= 2  # exponential backoff
            continue
        _cache = (time.monotonic(), snapshot)
        return snapshot

    return OFFLINE_FALLBACK


def cache_age_s() -> float | None:
    """For /api/health, so the operator can see how stale the weather is."""
    return None if _cache is None else time.monotonic() - _cache[0]


def _fetch_open_meteo(lat: float, lon: float) -> WeatherSnapshot:
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m",
            "wind_speed_unit": "kmh",
        }
    )
    request = urllib.request.Request(f"{config.WEATHER_URL}?{query}", headers={"User-Agent": "weather-whiplash/0.1"})
    with urllib.request.urlopen(request, timeout=config.WEATHER_TIMEOUT_S) as response:
        current = json.load(response)["current"]

    return WeatherSnapshot(
        temperature_c=float(current["temperature_2m"]),
        wind_speed_kmh=float(current["wind_speed_10m"]),
        relative_humidity=float(current["relative_humidity_2m"]) / 100.0,
        cloud_cover=float(current["cloud_cover"]) / 100.0,
        precipitation_mm_h=float(current["precipitation"]),
        source="open-meteo",
    )


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
