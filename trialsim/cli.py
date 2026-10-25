"""Usage: python -m trialsim examples/baseline.json [--runs N] [--seed S] [--json]"""
from __future__ import annotations

import argparse
import json

from .model import Scenario, simulate
from .report import render_table, summarize


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="trialsim")
    ap.add_argument("config", help="JSON file with a top-level 'scenarios' list")
    ap.add_argument("--runs", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", action="store_true", help="print full summaries as JSON")
    args = ap.parse_args(argv)

    with open(args.config) as f:
        scenarios = [Scenario.from_dict(d) for d in json.load(f)["scenarios"]]
    summaries = [summarize(simulate(s, args.runs, args.seed)) for s in scenarios]
    print(json.dumps(summaries, indent=2) if args.json else render_table(summaries))


if __name__ == "__main__":
    main()
