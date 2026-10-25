"""Small distribution specs so scenarios can be written as plain JSON."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

KINDS = ("const", "uniform", "triangular", "normal", "lognormal", "beta")


@dataclass(frozen=True)
class Dist:
    kind: str
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown distribution {self.kind!r}; expected one of {KINDS}")

    @classmethod
    def from_spec(cls, spec) -> "Dist":
        """Accept a number (constant) or {"kind": ..., **params}."""
        if isinstance(spec, Dist):
            return spec
        if isinstance(spec, (int, float)):
            return cls("const", {"value": float(spec)})
        spec = dict(spec)
        return cls(spec.pop("kind"), spec)

    def sample(self, rng: np.random.Generator, size) -> np.ndarray:
        p = self.params
        if self.kind == "const":
            return np.full(size, p["value"], dtype=float)
        if self.kind == "uniform":
            return rng.uniform(p["low"], p["high"], size)
        if self.kind == "triangular":
            return rng.triangular(p["low"], p["mode"], p["high"], size)
        if self.kind == "normal":
            return np.maximum(rng.normal(p["mean"], p["sd"], size), p.get("min", 0.0))
        if self.kind == "lognormal":
            # parameterised by median and log-scale sigma: heavy right tail, always positive
            return rng.lognormal(np.log(p["median"]), p["sigma"], size)
        return rng.beta(p["a"], p["b"], size)
