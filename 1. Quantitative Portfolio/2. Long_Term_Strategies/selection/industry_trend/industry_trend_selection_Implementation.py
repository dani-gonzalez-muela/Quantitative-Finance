# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Industry Trend Following — Implementation Comparison

Loads `results/industry_trend_signal.csv` output from industry_trend_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: "SPDR sector ETFs (XLE/XLK/XLY/XLP/XLU/XLF/XLI/XLV/XLB)"

Industry trend: hold top 3 of 9 sectors
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "industry_trend"
STRATEGY_NAME    = "Industry Trend Following"
STARTING_CAPITAL = 100_000
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(EQUITY_DIR, exist_ok=True)

# ── Load signal ──
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
if not os.path.exists(signal_path):
    raise FileNotFoundError(
        f"{signal_path} not found. Run {SAVE_NAME}_Backtest.py first."
    )
signal_long = pd.read_csv(signal_path, parse_dates=["date"])
signal_df = signal_long.pivot(index="date", columns="instrument", values="score")
signal_df.index = pd.to_datetime(signal_df.index)
print(f"Signal loaded: {signal_df.shape} — instruments: {list(signal_df.columns)}")

# ── Load prices (for inverse_vol_weight and equity simulation) ──
print("Loading prices...")
ARCH = os.path.join(os.path.dirname(BASE_DIR), "archived_strategies", "output")  # fable fix: archived_strategies sits under long_term/, not selection/
prices_val = pd.read_parquet(f"{ARCH}/prices_validated.parquet")
SECTORS = ["XLE", "XLK", "XLY", "XLP", "XLU", "XLF", "XLI", "XLV", "XLB"]
available_cols = [s for s in SECTORS if s in prices_val.columns]
prices = prices_val[available_cols].dropna(how="all")
prices = prices.resample("B").last().ffill()
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: Industry trend: hold top 3 of 9 sectors
results = compare_basket_implementations(
    signal_df,
    prices,
    starting_capital=STARTING_CAPITAL,
    tc_bps=5.0,
)

print_basket_comparison(results)

# ── Save implementations.json ──
impl_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_implementations.json")
with open(impl_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"Saved → {impl_path}")
print("Done.")
