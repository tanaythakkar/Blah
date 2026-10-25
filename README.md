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

## Backtest (public registry data)

`python -m backtest.fetch` then `python -m backtest.run` fits on half of ~6,300 completed Phase 2/3 trials from
ClinicalTrials.gov and scores on the other half, predicting months from start to primary completion.

First result (Oct 2026): trialsim + fitted follow-up did **worse** than simple baselines
(MAE of log duration 0.98 vs 0.57-0.64; rank correlation -0.10 vs 0.01-0.43). Diagnosis: in this data,
enrollment per site has almost no relationship with total duration (rank corr -0.11), 33% of trials list a
single site, and duration includes treatment and follow-up. The registry cannot test the enrollment model.
It needs real per-site enrollment histories (sponsor data or a pilot).
