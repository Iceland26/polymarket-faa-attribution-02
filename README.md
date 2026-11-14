# Polymarket FAA Outage Attribution Forecaster (`polymarket-faa-attribution-02`)

An offline, deterministic Python 3 quantile forecaster for the `polymarket-faa-attribution-02` competition on make.fun.

## Overview

For each case file `<id>.in` in `MAKEFUN_INPUT_DIR` (default `/input`), `main.py` reads the 1-minute historical Yes price series of each market up to the case checkpoint `at` and forecasts the five target quantiles (`0.05`, `0.25`, `0.50`, `0.75`, `0.95`) for each of the next `horizon_minutes` (`240`) minutes, writing `<id>.out` to `MAKEFUN_OUTPUT_DIR` (default `/output`).

## How to Run

Using Python 3.13 (standard library only, no external dependencies, no network access):

```bash
mkdir -p out
MAKEFUN_INPUT_DIR=/path/to/input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Forecasting Approach & Chosen Configuration

All model parameters are exposed as top-level constants in `main.py`. The final chosen configuration is:

- `CENTER_MODE = 'last'`: centers forecasts at the market's latest checkpoint price `prices[-1]` (also supports `'median15'` and `'mean15'`).
- `SIGMA_MODE = 'adaptive'`: estimates per-market 1-minute volatility `sigma1` as `1.4826 * median(|1-minute diffs|)` over the price series (falling back to the standard deviation of 1-minute diffs if the median is `0` and the series is non-constant, or `0` if constant), then clamps the effective volatility:
  `SIGMA_EFF = min(SIGMA_CAP, max(SIGMA_FLOOR, SIGMA_MULT * sigma1))`
  with `SIGMA_MULT = 1.0`, `SIGMA_FLOOR = 0.0008`, and `SIGMA_CAP = 0.002` (also supports `'fixed'` mode with `FIXED_SIGMA = 0.00125`).
- `BOUNDARY_SHRINK = True` with `SHRINK_SCALE = 0.05`: scales `SIGMA_EFF` by `min(1, min(c, 1 - c) / SHRINK_SCALE)` so spread narrows proportionally near the `0` and `1` price boundaries.
- **Horizon Quantiles**: at horizon `h = 1..240` and quantile level `tau`, predicts `clamp(c + z_tau * SIGMA_EFF * sqrt(h), 0, 1)` with `z = [-1.644854, -0.67449, 0, 0.67449, 1.644854]`, rounds to 6 decimals (never `-0.0`), and enforces non-decreasing order across each row.

## Local Practice Results (`p00..p04`)

Evaluated on practice cases `p00..p04` against actual next-case checkpoint trajectories (`p01..p05`), this configuration achieves an overall item-weighted mean pinball loss of **`0.336941`** vs the starter baseline's **`0.392518`** on the same local scorer, beating the starter on every case:

| Case | Starter Baseline Loss | `main.py` Loss |
| :--- | ---: | ---: |
| `p00` | `0.536138` | **`0.523511`** |
| `p01` | `0.380352` | **`0.308308`** |
| `p02` | `0.408408` | **`0.366034`** |
| `p03` | `0.368599` | **`0.304616`** |
| `p04` | `0.298794` | **`0.219856`** |
| **Overall (`p00..p04`, item-weighted)** | **`0.392518`** | **`0.336941`** |
| **Overall (`p00..p04`, case-unweighted)** | `0.398458` | **`0.344465`** |
