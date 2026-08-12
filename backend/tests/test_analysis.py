"""Phase 2: the temporal reasoning layer, tested against synthetic signals.

Synthetic signals rather than sample clips, because a test that needs footage tests the
footage. Step change, noisy linear ramp, noisy plateau, and sensor dropout are the four
shapes that break a filter, and each one has a named failure it is here to catch.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app import config
from app.analysis.filter import KalmanTWI
from app.analysis.pipeline import analyse_frames
from app.analysis.signal import frame_quality, twi_raw
from app.analysis.strategy import PitCallController
from app.analysis.trend import classify_trend, project_crossover
from app.analysis.weather import WeatherSnapshot, drying_rate_prior, fuse_rates, get_weather

DT = 1.0 / config.SAMPLE_FPS


# ---------------------------------------------------------------- synthetic signals


def step_signal(*, before: float = 60.0, after: float = 30.0, hold_s: float = 20.0,
                noise: float = 3.0, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    n = int(hold_s / DT)
    times = np.arange(2 * n) * DT
    clean = np.concatenate([np.full(n, before), np.full(n, after)])
    return times, clean + rng.normal(0.0, noise, size=clean.size)


def ramp_signal(*, start: float = 70.0, rate_per_min: float = -6.0, duration_s: float = 60.0,
                noise: float = 2.5, seed: int = 1) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    times = np.arange(int(duration_s / DT)) * DT
    clean = start + rate_per_min * (times / 60.0)
    return times, clean + rng.normal(0.0, noise, size=clean.size)


def plateau_signal(*, level: float = 45.0, duration_s: float = 60.0, noise: float = 6.0,
                   seed: int = 2) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    times = np.arange(int(duration_s / DT)) * DT
    return times, level + rng.normal(0.0, noise, size=times.size)


def solid_image(value: int = 90, size: tuple[int, int] = (240, 320)) -> np.ndarray:
    return np.full((*size, 3), value, dtype=np.uint8)


def textured_image(size: tuple[int, int] = (240, 320), seed: int = 3) -> np.ndarray:
    """High-frequency detail — what a sharp, in-focus trackside frame looks like to a Laplacian."""
    rng = np.random.default_rng(seed)
    return rng.integers(40, 200, size=(*size, 3), dtype=np.uint8)


CONFIDENT = {"dry": 0.02, "damp": 0.05, "wet": 0.90, "standing_water": 0.03}
AMBIGUOUS = {"dry": 0.30, "damp": 0.41, "wet": 0.23, "standing_water": 0.06}


# ---------------------------------------------------------------- B.1 track wetness index


def test_twi_raw_spans_the_full_scale_at_the_extremes() -> None:
    assert twi_raw({"dry": 1.0, "damp": 0.0, "wet": 0.0, "standing_water": 0.0}) == 0.0
    assert twi_raw({"dry": 0.0, "damp": 0.0, "wet": 0.0, "standing_water": 1.0}) == 100.0


def test_twi_raw_uses_the_whole_distribution_not_the_argmax() -> None:
    """60% wet / 40% damp and 95% wet both argmax to 'wet'. That difference is the signal."""
    mixed = twi_raw({"dry": 0.0, "damp": 0.40, "wet": 0.60, "standing_water": 0.0})
    peaked = twi_raw({"dry": 0.05, "damp": 0.0, "wet": 0.95, "standing_water": 0.0})

    assert mixed != peaked
    assert mixed == pytest.approx(100 * (0.35 * 0.40 + 0.75 * 0.60))


def test_twi_raw_is_monotone_as_probability_mass_moves_wetter() -> None:
    drier = twi_raw({"dry": 0.6, "damp": 0.4, "wet": 0.0, "standing_water": 0.0})
    wetter = twi_raw({"dry": 0.2, "damp": 0.4, "wet": 0.4, "standing_water": 0.0})

    assert drier < wetter


# ---------------------------------------------------------------- B.2 frame quality


def test_frame_quality_is_bounded() -> None:
    result = frame_quality(textured_image(), CONFIDENT)

    assert 0.0 <= result.score <= 1.0
    assert 0.0 <= result.entropy <= 1.0
    assert 0.0 <= result.clipping <= 1.0


def test_frame_quality_ranks_a_sharp_frame_above_a_blurred_one() -> None:
    sharp = frame_quality(textured_image(), CONFIDENT)
    flat = frame_quality(solid_image(), CONFIDENT)  # zero Laplacian variance

    assert flat.blur < sharp.blur
    assert flat.score < sharp.score


def test_frame_quality_penalises_an_ambiguous_distribution() -> None:
    """Entropy is the term that makes the system distrust its own uncertainty."""
    confident = frame_quality(textured_image(), CONFIDENT)
    ambiguous = frame_quality(textured_image(), AMBIGUOUS)

    assert ambiguous.entropy > confident.entropy
    assert ambiguous.score < confident.score


def test_frame_quality_penalises_clipped_exposure() -> None:
    blown = textured_image().copy()
    blown[:120, :] = 255  # half the frame blown out, as in a tunnel exit or lens glare

    result = frame_quality(blown, CONFIDENT)

    assert result.clipping > 0.4
    assert result.score < frame_quality(textured_image(), CONFIDENT).score


# ---------------------------------------------------------------- B.3 kalman


def test_kalman_tracks_a_step_change_within_the_specified_settling_time() -> None:
    """The tuning target for KALMAN_PROCESS_NOISE: a real 10-point swing inside ~15s."""
    times, measurements = step_signal(before=60.0, after=50.0, hold_s=20.0, noise=3.0)
    kalman = KalmanTWI()
    step_index = len(times) // 2

    estimates = [kalman.update(m, dt_s=DT, quality=0.9).twi for m in measurements]

    settled_at = next(
        i for i in range(step_index, len(estimates))
        if all(abs(e - 50.0) < 2.0 for e in estimates[i : i + 8])
    )
    assert (settled_at - step_index) * DT < 15.0


def test_kalman_smooths_a_noisy_plateau() -> None:
    times, measurements = plateau_signal(level=45.0, noise=6.0)
    kalman = KalmanTWI()

    estimates = np.array([kalman.update(m, dt_s=DT, quality=0.9).twi for m in measurements])

    warm = estimates[20:]  # skip the filter's own convergence from its initial guess
    assert warm.std() < measurements[20:].std() / 2
    assert abs(warm.mean() - 45.0) < 3.0


def test_kalman_reports_rate_in_twi_per_minute_not_per_second() -> None:
    """A factor-of-60 unit error here is invisible in the UI and wrong in every readout."""
    times, measurements = ramp_signal(start=70.0, rate_per_min=-6.0, duration_s=90.0, noise=0.5)
    kalman = KalmanTWI()

    for m in measurements:
        result = kalman.update(m, dt_s=DT, quality=0.9)

    assert result.rate_per_min == pytest.approx(-6.0, abs=1.5)


def test_kalman_barely_moves_for_low_quality_frames() -> None:
    """Measurement noise scales inversely with quality — a blurred frame must not yank the estimate."""
    trusted = KalmanTWI()
    distrusted = KalmanTWI()
    for _ in range(40):
        trusted.update(50.0, dt_s=DT, quality=0.9)
        distrusted.update(50.0, dt_s=DT, quality=0.9)

    trusted_jump = trusted.update(90.0, dt_s=DT, quality=0.9).twi - 50.0
    distrusted_jump = distrusted.update(90.0, dt_s=DT, quality=0.02).twi - 50.0

    assert abs(distrusted_jump) < abs(trusted_jump) / 4


def test_kalman_survives_a_five_frame_sensor_dropout() -> None:
    """Spray on the lens: five garbage frames flagged low-quality must not derail the estimate."""
    kalman = KalmanTWI()
    for _ in range(40):
        kalman.update(50.0, dt_s=DT, quality=0.9)

    for _ in range(5):
        kalman.update(0.0, dt_s=DT, quality=0.01)  # garbage readings, correctly distrusted

    assert abs(kalman.twi - 50.0) < 5.0


# ---------------------------------------------------------------- B.4 trend


def test_trend_reports_drying_on_a_falling_ramp() -> None:
    times, measurements = ramp_signal(start=70.0, rate_per_min=-6.0, noise=1.0)

    result = classify_trend(times, measurements)

    assert result.direction == "DRYING"
    assert result.rate_per_min == pytest.approx(-6.0, abs=1.0)
    assert result.sufficient_signal is True


def test_trend_reports_wetting_on_a_rising_ramp() -> None:
    times, measurements = ramp_signal(start=30.0, rate_per_min=+8.0, noise=1.0)

    result = classify_trend(times, measurements)

    assert result.direction == "WETTING"
    assert result.rate_per_min > config.TREND_RATE_THRESHOLD


def test_trend_calls_a_shallow_slope_stable() -> None:
    times, measurements = ramp_signal(start=50.0, rate_per_min=-0.5, noise=0.2)

    result = classify_trend(times, measurements)

    assert result.direction == "STABLE"


def test_trend_refuses_a_slope_the_noise_does_not_support() -> None:
    """The null state. A noisy plateau has a slope; it does not have a trend."""
    times, measurements = plateau_signal(level=45.0, noise=8.0)

    result = classify_trend(times, measurements)

    assert result.r_squared < config.TREND_R2_MIN
    assert result.sufficient_signal is False
    assert result.direction == "STABLE"


def test_trend_only_regresses_over_the_configured_window() -> None:
    """Ancient history must not drag the current slope."""
    times = np.arange(0, 600, DT)
    twi = np.where(times < 500, 80.0, 80.0 - 6.0 * (times - 500) / 60.0)

    result = classify_trend(times, twi)

    assert result.window_s == pytest.approx(config.TREND_WINDOW_S, abs=DT)
    assert result.rate_per_min == pytest.approx(-6.0, abs=0.5)


def test_trend_falls_back_to_stable_when_kalman_and_ols_disagree_in_sign() -> None:
    """Two estimators, cross-checked. Disagreement means we do not know, so we say so."""
    times, measurements = ramp_signal(start=70.0, rate_per_min=-6.0, noise=1.0)

    result = classify_trend(times, measurements, kalman_rate_per_min=+7.0)

    assert result.sufficient_signal is False
    assert result.direction == "STABLE"


# ---------------------------------------------------------------- B.5 crossover projection


def test_projection_estimates_a_crossing_with_an_uncertainty_cone() -> None:
    times, measurements = ramp_signal(start=45.0, rate_per_min=-6.0, noise=1.0)
    trend = classify_trend(times, measurements)

    crossover = project_crossover(twi_now=40.0, trend=trend)

    assert crossover is not None
    assert crossover.target_compound == "SLICK"
    assert crossover.threshold == 25.0
    assert crossover.eta_s == pytest.approx(150.0, rel=0.25)  # 15 points at ~6/min
    assert crossover.eta_optimistic_s < crossover.eta_s < crossover.eta_pessimistic_s


def test_projection_returns_null_when_the_signal_is_insufficient() -> None:
    """Never fabricate a number. The UI renders 'NO RELIABLE PROJECTION' from this null."""
    times, measurements = plateau_signal(level=45.0, noise=8.0)
    trend = classify_trend(times, measurements)

    assert project_crossover(twi_now=45.0, trend=trend) is None


def test_projection_returns_null_when_the_rate_is_below_threshold() -> None:
    times, measurements = ramp_signal(start=45.0, rate_per_min=-0.4, noise=0.1)
    trend = classify_trend(times, measurements)

    assert project_crossover(twi_now=45.0, trend=trend) is None


def test_projection_refuses_a_crossing_beyond_the_horizon() -> None:
    """The horizon gate is unreachable through config — the widest band at the minimum
    reportable rate crosses in ~26 minutes, inside the 30-minute limit. It stays as a
    guard against future threshold changes, so it is tested through the parameter."""
    times, measurements = ramp_signal(start=45.0, rate_per_min=-6.0, noise=1.0)
    trend = classify_trend(times, measurements)

    assert project_crossover(twi_now=40.0, trend=trend) is not None
    assert project_crossover(twi_now=40.0, trend=trend, horizon_s=60.0) is None


def test_projection_targets_the_boundary_it_is_heading_towards() -> None:
    times, measurements = ramp_signal(start=50.0, rate_per_min=+8.0, noise=1.0)
    trend = classify_trend(times, measurements)

    crossover = project_crossover(twi_now=55.0, trend=trend)

    assert crossover is not None
    assert crossover.target_compound == "FULL_WET"
    assert crossover.threshold == 65.0


# ---------------------------------------------------------------- B.6 pit call hysteresis


def test_pit_call_holds_until_the_margin_and_the_windows_are_both_satisfied() -> None:
    controller = PitCallController(initial="INTERMEDIATE")

    just_over = controller.update(24.0)  # past 25 but inside the 6-point margin
    assert just_over.current == "INTERMEDIATE"
    assert just_over.state == "HOLD"

    first = controller.update(18.0)  # clear of the margin, window 1 of 3
    assert first.state == "ARMING"
    assert first.windows_held == 1
    assert first.next == "SLICK"
    assert controller.update(18.0).windows_held == 2
    committed = controller.update(18.0)

    assert committed.state == "BOX"
    assert committed.current == "SLICK"
    assert committed.windows_held == config.HYSTERESIS_WINDOWS


def test_pit_call_does_not_flicker_on_a_signal_oscillating_across_a_boundary() -> None:
    """The failure a real strategist would mock. 40 crossings, zero compound changes."""
    controller = PitCallController(initial="INTERMEDIATE")

    calls = [controller.update(25.0 + offset) for _ in range(20) for offset in (-2.0, +2.0)]

    assert {c.current for c in calls} == {"INTERMEDIATE"}
    assert all(c.state != "BOX" for c in calls)


def test_pit_call_disarms_when_the_signal_retreats_inside_the_margin() -> None:
    controller = PitCallController(initial="INTERMEDIATE")

    controller.update(18.0)
    armed = controller.update(18.0)
    assert armed.windows_held == 2

    retreated = controller.update(24.0)

    assert retreated.windows_held == 0
    assert retreated.state == "HOLD"
    assert retreated.current == "INTERMEDIATE"


def test_pit_call_rationale_names_the_numbers_it_acted_on() -> None:
    controller = PitCallController(initial="INTERMEDIATE")

    call = controller.update(18.0)

    assert "18" in call.rationale
    assert call.rationale == call.rationale.strip()


# ---------------------------------------------------------------- B.7 weather fusion


def test_drying_prior_is_negative_in_warm_windy_clear_conditions() -> None:
    fast = WeatherSnapshot(temperature_c=28.0, wind_speed_kmh=25.0, relative_humidity=0.30,
                           cloud_cover=0.10, precipitation_mm_h=0.0, source="test")

    assert drying_rate_prior(fast) < 0.0


def test_drying_prior_is_slower_in_cold_humid_still_conditions() -> None:
    fast = WeatherSnapshot(temperature_c=28.0, wind_speed_kmh=25.0, relative_humidity=0.30,
                           cloud_cover=0.10, precipitation_mm_h=0.0, source="test")
    slow = WeatherSnapshot(temperature_c=6.0, wind_speed_kmh=2.0, relative_humidity=0.95,
                           cloud_cover=1.0, precipitation_mm_h=0.0, source="test")

    assert drying_rate_prior(slow) > drying_rate_prior(fast)


def test_drying_prior_turns_positive_while_it_is_raining() -> None:
    raining = WeatherSnapshot(temperature_c=14.0, wind_speed_kmh=10.0, relative_humidity=0.90,
                              cloud_cover=1.0, precipitation_mm_h=3.0, source="test")

    assert drying_rate_prior(raining) > 0.0


def test_fusion_weights_sum_to_one_and_favour_the_trusted_source() -> None:
    blended = fuse_rates(rate_visual=-4.0, rate_prior=-1.0, visual_weight=0.75)

    assert blended == pytest.approx(0.75 * -4.0 + 0.25 * -1.0)


def test_fusion_ignores_the_prior_when_the_footage_is_clean() -> None:
    assert fuse_rates(rate_visual=-4.0, rate_prior=+9.0, visual_weight=1.0) == pytest.approx(-4.0)


def test_weather_falls_back_to_bundled_values_when_the_network_is_down(monkeypatch) -> None:
    """Rule 4: must run with no internet. The demo cannot depend on venue Wi-Fi."""
    import app.analysis.weather as weather_module

    monkeypatch.setattr(config, "OFFLINE_MODE", False)  # exercise the real retry path
    monkeypatch.setattr(config, "WEATHER_BACKOFF_S", 0.01)
    monkeypatch.setattr(weather_module, "_cache", None)
    monkeypatch.setattr(weather_module, "_fetch_open_meteo",
                        lambda lat, lon: (_ for _ in ()).throw(OSError("network down")))

    snapshot = get_weather(52.07, -1.01)

    assert snapshot.source == "offline-fallback"
    assert math.isfinite(drying_rate_prior(snapshot))


# ---------------------------------------------------------------- pipeline


def test_pipeline_turns_a_drying_clip_into_a_falling_twi_curve() -> None:
    """End to end on synthetic probabilities: wet → damp → dry over 60 seconds."""
    n = int(60.0 / DT)
    states = analyse_frames(
        session_id="synthetic",
        frames=[(i, i * DT, textured_image(seed=i % 7)) for i in range(n)],
        probabilities=[_drying_distribution(i / (n - 1)) for i in range(n)],
        weather=None,
    )

    assert len(states) == n
    assert states[0].twi > states[-1].twi + 20
    assert states[-1].trend.direction == "DRYING"
    assert all(0.0 <= s.twi <= 100.0 for s in states)


def test_pipeline_emits_a_recommendation_for_every_frame() -> None:
    n = 40
    states = analyse_frames(
        session_id="synthetic",
        frames=[(i, i * DT, textured_image()) for i in range(n)],
        probabilities=[{"dry": 0.0, "damp": 0.1, "wet": 0.8, "standing_water": 0.1}] * n,
        weather=None,
    )

    assert all(s.recommendation.current in {"SLICK", "INTERMEDIATE", "FULL_WET"} for s in states)
    assert all(s.frame_quality.score >= 0.0 for s in states)
    assert states[-1].recommendation.current == "FULL_WET"


def _drying_distribution(progress: float) -> dict[str, float]:
    """Probability mass sliding from wet to dry as `progress` goes 0 → 1."""
    wet = max(0.0, 0.85 - progress)
    dry = max(0.0, progress - 0.15)
    damp = max(0.05, 1.0 - wet - dry - 0.05)
    total = wet + dry + damp + 0.05
    return {"dry": dry / total, "damp": damp / total, "wet": wet / total, "standing_water": 0.05 / total}
