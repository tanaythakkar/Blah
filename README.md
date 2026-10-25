# Blah

## trialsim

Monte Carlo clinical trial enrollment, timeline and power simulator (early scaffold).

```
pip install numpy pytest
python -m trialsim examples/baseline.json --runs 5000 --seed 0
python -m pytest
```

Each run draws a screen-failure rate, a dropout rate, and a per-site activation time and recruitment rate,
then accrues randomizations weekly until the target or horizon. Output is P10/P50/P90 months to target,
probability of meeting a deadline, and probability the completers still give adequate power.

Not yet built: backtest against ClinicalTrials.gov, supply/randomization modelling, historical calibration.
Inputs in `examples/` are illustrative, not from a real study.
