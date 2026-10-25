"""Monte Carlo enrollment / timeline / power simulation.

Each run draws one plausible "world": a screen-failure rate and dropout rate for the whole trial,
plus an activation time and a recruitment rate for every site. Randomizations then accrue as a
Poisson process per site, stepped weekly, until the target is reached or the horizon ends.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from .dists import Dist

WEEK_MONTHS = 12 / 52


@dataclass(frozen=True)
class Scenario:
    name: str
    target_n: int  # randomized patients needed
    n_sites: int
    activation_months: Dist  # per site: months from study start until it can screen
    site_rate_per_month: Dist  # per site: patients screened per active month
    screen_fail: Dist  # per trial: fraction of screened who fail screening
    dropout: Dist  # per trial: fraction of randomized who do not complete
    horizon_months: float = 72.0
    deadline_months: float | None = None
    effect_size: float | None = None  # raw treatment difference for the power check
    sd: float | None = None
    alpha: float = 0.05
    required_power: float = 0.80

    @classmethod
    def from_dict(cls, d: dict) -> "Scenario":
        d = dict(d)
        for key in ("activation_months", "site_rate_per_month", "screen_fail", "dropout"):
            d[key] = Dist.from_spec(d[key])
        return cls(**d)


@dataclass
class Results:
    scenario: Scenario
    seed: int
    months_to_target: np.ndarray  # NaN where the target was not reached within the horizon
    enrolled: np.ndarray
    completers: np.ndarray
    power: np.ndarray | None


def simulate(scenario: Scenario, n_runs: int = 5000, seed: int = 0) -> Results:
    s = scenario
    rng = np.random.default_rng(seed)
    shape = (n_runs, s.n_sites)

    activation = s.activation_months.sample(rng, shape)
    rate = s.site_rate_per_month.sample(rng, shape)
    screen_fail = np.clip(s.screen_fail.sample(rng, (n_runs, 1)), 0.0, 0.99)
    dropout = np.clip(s.dropout.sample(rng, n_runs), 0.0, 1.0)
    rand_rate = rate * (1.0 - screen_fail)  # randomized per active month

    cum = np.zeros(n_runs)
    done = np.full(n_runs, np.nan)
    dt = WEEK_MONTHS
    for k in range(int(np.ceil(s.horizon_months / dt))):
        t0 = k * dt
        active = np.clip((t0 + dt - activation) / dt, 0.0, 1.0)  # share of this week a site is open
        new = rng.poisson(rand_rate * dt * active).sum(axis=1)
        prev = cum.copy()
        cum += new
        hit = np.isnan(done) & (cum >= s.target_n)
        if hit.any():
            done[hit] = t0 + dt * (s.target_n - prev[hit]) / new[hit]  # new > 0 whenever hit
        if not np.isnan(done).any():
            break

    enrolled = np.minimum(cum, s.target_n)
    completers = rng.binomial(enrolled.astype(int), 1.0 - dropout)
    return Results(s, seed, done, enrolled, completers, _power(s, completers))


def _power(s: Scenario, completers: np.ndarray) -> np.ndarray | None:
    """Two-arm 1:1 continuous endpoint, normal approximation, on patients who complete."""
    if s.effect_size is None or s.sd is None:
        return None
    nd = NormalDist()
    z_crit = nd.inv_cdf(1 - s.alpha / 2)
    per_arm = np.maximum(completers / 2, 1)
    z = s.effect_size / (s.sd * np.sqrt(2 / per_arm))
    return np.array([nd.cdf(v - z_crit) for v in z])
