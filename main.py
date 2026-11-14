#!/usr/bin/env python3
"""Offline quantile forecaster (v1) for make.fun competition polymarket-faa-attribution-02."""

import json
import math
import os
import statistics
from typing import Dict, List

# --- Tunable Constants ---
CENTER_MODE: str = "last"        # 'last', 'median15', or 'mean15'
SIGMA_MODE: str = "adaptive"     # 'adaptive' or 'fixed'
SIGMA_MULT: float = 1.0
SIGMA_FLOOR: float = 0.0008
SIGMA_CAP: float = 0.002
FIXED_SIGMA: float = 0.00125
BOUNDARY_SHRINK: bool = True
SHRINK_SCALE: float = 0.05
MAD_SCALE: float = 1.4826

QUANTILES: List[float] = [0.05, 0.25, 0.5, 0.75, 0.95]
Z: List[float] = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]


def round6(x: float) -> float:
    """Clamp x to [0, 1] and round to 6 decimals (never -0.0)."""
    clamped = min(1.0, max(0.0, x))
    val = round(clamped, 6)
    return 0.0 if val == 0.0 else val


def compute_center(prices: List[float]) -> float:
    """Compute center price c according to CENTER_MODE."""
    if not prices:
        raise ValueError("Market has no prices")
    if CENTER_MODE == "last":
        return float(prices[-1])
    window = min(15, len(prices))
    tail = prices[-window:]
    if CENTER_MODE == "median15":
        return float(statistics.median(tail))
    if CENTER_MODE == "mean15":
        return float(sum(tail) / len(tail))
    raise ValueError(f"Unknown CENTER_MODE: {CENTER_MODE}")


def compute_sigma1(prices: List[float]) -> float:
    """Compute per-market 1-minute volatility sigma1 over the whole price series."""
    n = len(prices)
    if n < 2:
        return 0.0
    diffs = [prices[i] - prices[i - 1] for i in range(1, n)]
    abs_diffs = [abs(d) for d in diffs]
    if all(d == 0.0 for d in abs_diffs):
        return 0.0
    med_abs = float(statistics.median(abs_diffs))
    sigma1 = MAD_SCALE * med_abs
    if sigma1 == 0.0:
        if len(diffs) >= 2:
            st = float(statistics.stdev(diffs))
        else:
            st = float(abs_diffs[0])
        if st > 0.0:
            sigma1 = st
    return sigma1


def compute_sigma_eff(prices: List[float], c: float) -> float:
    """Compute effective per-root-minute spread SIGMA_EFF."""
    if SIGMA_MODE == "fixed":
        sigma_eff = FIXED_SIGMA
    elif SIGMA_MODE == "adaptive":
        sigma1 = compute_sigma1(prices)
        sigma_eff = min(SIGMA_CAP, max(SIGMA_FLOOR, SIGMA_MULT * sigma1))
    else:
        raise ValueError(f"Unknown SIGMA_MODE: {SIGMA_MODE}")

    if BOUNDARY_SHRINK:
        c_clamped = min(1.0, max(0.0, c))
        shrink = min(1.0, min(c_clamped, 1.0 - c_clamped) / SHRINK_SCALE)
        sigma_eff *= shrink

    return sigma_eff


def forecast_market(prices: List[float], horizon: int) -> List[List[float]]:
    """Forecast horizon rows of 5 quantiles for a single market."""
    c = compute_center(prices)
    sigma_eff = compute_sigma_eff(prices, c)
    rows: List[List[float]] = []
    for h in range(1, horizon + 1):
        spread = sigma_eff * math.sqrt(h)
        row = [round6(c + z * spread) for z in Z]
        for j in range(1, len(row)):
            if row[j] < row[j - 1]:
                row[j] = row[j - 1]
        rows.append(row)
    return rows


def process_case(in_path: str, out_path: str) -> None:
    """Read one case file and write its forecast output."""
    with open(in_path, "r", encoding="utf-8") as f:
        case_data = json.load(f)

    horizon = int(case_data["horizon_minutes"])
    quantiles = case_data["quantiles"]
    if len(quantiles) != len(QUANTILES) or any(
        q != t for q, t in zip(quantiles, QUANTILES)
    ):
        raise ValueError(f"Unexpected quantiles in {in_path}: {quantiles}")

    forecasts: List[Dict[str, object]] = []
    for market in case_data["markets"]:
        m_id = market["id"]
        prices = market["prices"]
        q_rows = forecast_market(prices, horizon)
        forecasts.append({"id": m_id, "q": q_rows})

    output_obj = {"forecasts": forecasts}
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(output_obj, separators=(",", ":")) + "\n")


def main() -> None:
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    input_files = sorted(f for f in os.listdir(input_dir) if f.endswith(".in"))
    for filename in input_files:
        case_id = filename[:-3]
        in_path = os.path.join(input_dir, filename)
        out_path = os.path.join(output_dir, f"{case_id}.out")
        process_case(in_path, out_path)


if __name__ == "__main__":
    main()
