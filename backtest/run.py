"""Backtest: does a trialsim-based duration model beat simple baselines on held-out trials?

The registry gives start date, primary completion date, enrollment and site count, but not per-site
activation or the pre-launch plan. So the target here is total months from start to primary completion
(enrollment plus follow-up), not enrollment duration. The simulator model is therefore:

    predicted duration = simulated months to enroll + a fitted follow-up constant per phase

Models are fit on one half of the trials and scored on the other half (split by NCT id parity).

Usage: python -m backtest.run [--csv backtest/data/trials.csv] [--runs 60]
"""
from __future__ import annotations

import argparse
import csv

import numpy as np

from trialsim import Dist, Scenario, simulate

HORIZON = 150.0
RATE_GRID = (0.15, 0.3, 0.6, 1.2, 2.4)  # randomized patients per site-month (median of lognormal)
FIT_SAMPLE = 600


def month_index(s: str) -> float | None:
    parts = s.split("-")
    if len(parts) < 2:
        return None
    day = int(parts[2]) if len(parts) > 2 else 15
    return int(parts[0]) * 12 + int(parts[1]) + day / 30.0


def load(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            a, b = month_index(r["start"]), month_index(r["primary_completion"])
            if a is None or b is None or r["phase"] not in ("PHASE2", "PHASE3"):
                continue
            if r["enrollment_type"] != "ACTUAL" or int(r["n_sites"]) < 1:
                continue
            dur = b - a
            if not 3 <= dur <= 120:
                continue
            rows.append({
                "id": int(r["nct_id"][3:]), "phase": r["phase"], "n": int(r["enrollment"]),
                "sites": min(int(r["n_sites"]), 300), "industry": r["sponsor_class"] == "INDUSTRY",
                "dur": dur,
            })
    return rows


def sim_enroll_months(n: int, sites: int, rate: float, runs: int) -> float:
    s = Scenario(
        name="bt", target_n=n, n_sites=sites,
        activation_months=Dist.from_spec({"kind": "triangular", "low": 1, "mode": 3, "high": 9}),
        site_rate_per_month=Dist.from_spec({"kind": "lognormal", "median": rate, "sigma": 0.6}),
        screen_fail=Dist.from_spec(0.0), dropout=Dist.from_spec(0.0), horizon_months=HORIZON,
    )
    m = simulate(s, runs, seed=n * 1000 + sites).months_to_target
    return HORIZON if np.isnan(m).mean() > 0.5 else float(np.nanmedian(m))


def size_bin(n: int) -> int:
    return 0 if n < 100 else 1 if n < 300 else 2


def group_median(train, key, fallback):
    groups: dict = {}
    for r in train:
        groups.setdefault(key(r), []).append(np.log(r["dur"]))
    med = {k: float(np.median(v)) for k, v in groups.items() if len(v) >= 5}
    return lambda r: med.get(key(r), fallback(r))


def design(rows):
    return np.array([[1.0, np.log(r["n"]), np.log(r["sites"]), r["phase"] == "PHASE3", r["industry"]]
                     for r in rows], dtype=float)


def fit_sim(train, runs):
    """Per phase: pick the site rate and follow-up constant that minimise log error on a sample."""
    rng = np.random.default_rng(0)
    params = {}
    for phase in ("PHASE2", "PHASE3"):
        pool = [r for r in train if r["phase"] == phase]
        sample = [pool[i] for i in rng.choice(len(pool), min(FIT_SAMPLE, len(pool)), replace=False)]
        best = None
        for rate in RATE_GRID:
            enr = np.array([sim_enroll_months(r["n"], r["sites"], rate, runs) for r in sample])
            dur = np.array([r["dur"] for r in sample])
            follow = max(float(np.median(dur - enr)), 0.0)
            loss = float(np.mean(np.abs(np.log(enr + follow) - np.log(dur))))
            if best is None or loss < best[0]:
                best = (loss, rate, follow)
        params[phase] = best[1:]
        print(f"  fitted {phase}: rate={best[1]}/site-month, follow-up={best[2]:.1f} months")
    return params


def ranks(x):
    return np.argsort(np.argsort(x)).astype(float)


def score(name, pred, actual):
    lr = np.log(pred) - np.log(actual)
    return (name, float(np.mean(np.abs(lr))), float(np.mean(np.abs(lr) <= np.log(1.3))),
            float(np.corrcoef(ranks(pred), ranks(actual))[0, 1]))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="backtest/data/trials.csv")
    ap.add_argument("--runs", type=int, default=60)
    args = ap.parse_args()

    rows = load(args.csv)
    train = [r for r in rows if r["id"] % 2 == 0]
    test = [r for r in rows if r["id"] % 2 == 1]
    actual = np.array([r["dur"] for r in test])
    print(f"{len(rows)} usable trials: {len(train)} train / {len(test)} test")

    overall = float(np.median([np.log(r["dur"]) for r in train]))
    by_phase = group_median(train, lambda r: r["phase"], lambda r: overall)
    by_group = group_median(
        train, lambda r: (r["phase"], r["industry"], size_bin(r["n"])), by_phase)
    beta, *_ = np.linalg.lstsq(design(train), np.log([r["dur"] for r in train]), rcond=None)

    print("fitting simulator parameters on train set...")
    params = fit_sim(train, args.runs)
    print("scoring on test set...")
    sim_pred = np.array([
        sim_enroll_months(r["n"], r["sites"], params[r["phase"]][0], args.runs) + params[r["phase"]][1]
        for r in test])

    results = [
        score("phase median", np.exp([by_phase(r) for r in test]), actual),
        score("phase x sponsor x size median", np.exp([by_group(r) for r in test]), actual),
        score("log-linear regression", np.exp(design(test) @ beta), actual),
        score("trialsim + follow-up", sim_pred, actual),
    ]
    print(f"\n{'model':32} {'MAE(log)':>9} {'within 30%':>11} {'rank corr':>10}")
    for name, mae, within, rho in results:
        print(f"{name:32} {mae:9.3f} {within:11.0%} {rho:10.3f}")


if __name__ == "__main__":
    main()
