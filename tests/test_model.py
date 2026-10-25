import dataclasses

import numpy as np
import pytest

from trialsim import Dist, Scenario, simulate, summarize


def make(**over) -> Scenario:
    base = dict(
        name="t",
        target_n=200,
        n_sites=20,
        activation_months=Dist.from_spec({"kind": "triangular", "low": 2, "mode": 4, "high": 8}),
        site_rate_per_month=Dist.from_spec({"kind": "lognormal", "median": 1.0, "sigma": 0.5}),
        screen_fail=Dist.from_spec(0.2),
        dropout=Dist.from_spec(0.1),
        deadline_months=24,
        effect_size=4.0,
        sd=12.0,
    )
    base.update(over)
    return Scenario(**base)


def test_same_seed_is_reproducible():
    a = simulate(make(), 300, seed=7)
    b = simulate(make(), 300, seed=7)
    assert np.array_equal(a.months_to_target, b.months_to_target, equal_nan=True)


def test_more_sites_finish_sooner():
    few = summarize(simulate(make(n_sites=15), 1000, seed=1))
    many = summarize(simulate(make(n_sites=30), 1000, seed=1))
    assert many["months_to_target"]["p50"] < few["months_to_target"]["p50"]


def test_higher_screen_failure_slows_enrollment():
    low = summarize(simulate(make(screen_fail=Dist.from_spec(0.1)), 1000, seed=2))
    high = summarize(simulate(make(screen_fail=Dist.from_spec(0.5)), 1000, seed=2))
    assert high["months_to_target"]["p50"] > low["months_to_target"]["p50"]


def test_higher_dropout_erodes_power():
    low = summarize(simulate(make(dropout=Dist.from_spec(0.05)), 1000, seed=3))
    high = summarize(simulate(make(dropout=Dist.from_spec(0.4)), 1000, seed=3))
    assert high["mean_power"] < low["mean_power"]


def test_single_site_matches_analytic_expectation():
    # one site open from t=0 at 2 randomized/month, no screen failure: target 100 takes about 50 months
    s = make(
        n_sites=1, target_n=100, horizon_months=200,
        activation_months=Dist.from_spec(0.0),
        site_rate_per_month=Dist.from_spec(2.0),
        screen_fail=Dist.from_spec(0.0),
    )
    out = summarize(simulate(s, 2000, seed=4))
    assert out["months_to_target"]["p50"] == pytest.approx(50, rel=0.05)


def test_short_horizon_counts_as_misses():
    out = summarize(simulate(make(horizon_months=3), 500, seed=5))
    assert out["prob_target_within_horizon"] == 0.0
    assert out["prob_by_deadline"] == 0.0
    assert out["months_to_target"]["p50"] is None


def test_deadline_probability_is_monotonic():
    r = simulate(make(), 1000, seed=6)
    probs = [
        summarize(dataclasses.replace(r, scenario=make(deadline_months=d)))["prob_by_deadline"]
        for d in (12, 18, 24, 36)
    ]
    assert probs == sorted(probs)


def test_unknown_distribution_rejected():
    with pytest.raises(ValueError):
        Dist("weibull")
