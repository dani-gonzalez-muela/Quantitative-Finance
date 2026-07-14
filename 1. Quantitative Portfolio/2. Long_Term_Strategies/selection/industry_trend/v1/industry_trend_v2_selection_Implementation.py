# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Industry Trend Following v2 (CRSP Sector Indices) — Selection Implementation

Loads the monthly basket signal output from industry_trend_v2_selection_backtest.py
and applies basket weighting variants via shared.basket_implementations.

The v2 backtest uses 11 CRSP US sector indices (vs. 9 SPDR ETFs in v1)
and selects the top 5 of 11 sectors by 12-1 month cross-sectional momentum.

Run industry_trend_v2_selection_backtest.py first to produce:
    results/industry_trend_v2_signal.csv   (sector x month signal scores)
    results/industry_trend_v2_trades.csv
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

SAVE_NAME        = "industry_trend_v2"
STRATEGY_NAME    = "Industry Trend Following v2 (CRSP Sectors)"
STARTING_CAPITAL = 100_000
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(EQUITY_DIR, exist_ok=True)

# -- Load signal --
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
if not os.path.exists(signal_path):
    raise FileNotFoundError(
        f"{signal_path} not found. Run industry_trend_v2_selection_backtest.py first.\n"
        "Expected: date-indexed CSV with sector columns and momentum scores as values."
    )

signal_df = pd.read_csv(signal_path, index_col=0, parse_dates=True)
print(f"Signal loaded: {signal_df.shape[0]} months x {signal_df.shape[1]} sectors")
print(f"  Period: {signal_df.index[0].date()} -> {signal_df.index[-1].date()}")
print(f"  Sectors: {list(signal_df.columns)}")

# -- Run basket implementations --
from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

comparison = compare_basket_implementations(
    signal_df=signal_df,
    prices=None,
    starting_capital=STARTING_CAPITAL,
    tc_bps=5,             # ~5bps for sector ETF/index execution
)

impl_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_implementations.json")
with open(impl_path, "w") as f:
    json.dump(comparison, f, indent=2, default=str)

print_basket_comparison(comparison)
print(f"\nImplementations saved -> {impl_path}")
print("Done.")
