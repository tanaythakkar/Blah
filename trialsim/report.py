"""Summaries and side-by-side comparison of simulation results."""
from __future__ import annotations

import numpy as np

from .model import Results


def _pcts(x: np.ndarray) -> dict:
    x = x[~np.isnan(x)]
    if x.size == 0:
        return {"p10": None, "p50": None, "p90": None}
    p10, p50, p90 = np.percentile(x, [10, 50, 90])
    return {"p10": float(p10), "p50": float(p50), "p90": float(p90)}


def summarize(r: Results) -> dict:
    s = r.scenario
    reached = ~np.isnan(r.months_to_target)
    out = {
        "scenario": s.name,
        "seed": r.seed,
        "runs": int(r.months_to_target.size),
        "prob_target_within_horizon": float(reached.mean()),
        "months_to_target": _pcts(r.months_to_target),
        "completers": _pcts(r.completers.astype(float)),
    }
    if s.deadline_months is not None:
        # runs that never reach the target count as misses
        out["prob_by_deadline"] = float((r.months_to_target <= s.deadline_months).mean())
    if r.power is not None:
        out["mean_power"] = float(r.power.mean())
        out["prob_power_ok"] = float((r.power >= s.required_power).mean())
    return out


def _fmt(v, spec=".1f") -> str:
    return "n/a" if v is None else format(v, spec)


def render_table(summaries: list[dict]) -> str:
    rows = [("scenario", "P10 mo", "P50 mo", "P90 mo", "by deadline", "P(power ok)")]
    for m in summaries:
        t = m["months_to_target"]
        rows.append((
            m["scenario"], _fmt(t["p10"]), _fmt(t["p50"]), _fmt(t["p90"]),
            _fmt(m.get("prob_by_deadline"), ".0%"), _fmt(m.get("prob_power_ok"), ".0%"),
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths)) for r in rows)
