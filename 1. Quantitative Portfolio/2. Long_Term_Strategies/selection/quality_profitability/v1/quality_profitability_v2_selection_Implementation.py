# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Quality / Profitability v2 (Novy-Marx, Compustat) — Selection Implementation

Loads the monthly basket signal output from quality_v2_selection_backtest.py
and applies basket weighting variants via shared.basket_implementations.

The v2 backtest selects the top GP quintile (~100 stocks) from the S&P 500
each month. This Implementation tests equal-weight vs. signal-strength-weight
variants on that same selection.

Run quality_v2_selection_backtest.py first to produce:
    results/quality_v2_signal.csv   (permno x month_end signal scores)
    results/quality_v2_trades.csv
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

SAVE_NAME        = "quality_v2"
STRATEGY_NAME    = "Quality / Profitability v2 (Novy-Marx)"
STARTING_CAPITAL = 100_000
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(EQUITY_DIR, exist_ok=True)

# -- Load signal --
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
if not os.path.exists(signal_path):
    raise FileNotFoundError(
        f"{signal_path} not found. Run quality_v2_selection_backtest.py first.\n"
        "Expected: date-indexed CSV with permno columns and GP scores as values."
    )

signal_df = pd.read_csv(signal_path, index_col=0, parse_dates=True)
print(f"Signal loaded: {signal_df.shape[0]} months x {signal_df.shape[1]} instruments")
print(f"  Period: {signal_df.index[0].date()} -> {signal_df.index[-1].date()}")

# -- Run basket implementations --
from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

# No price data needed for equal-weight; basket_implementations handles top-N selection
comparison = compare_basket_implementations(
    signal_df=signal_df,
    prices=None,          # equal-weight only (no price data for inv-vol weighting)
    starting_capital=STARTING_CAPITAL,
    tc_bps=10,            # ~10bps per trade for equity basket
)

impl_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_implementations.json")
with open(impl_path, "w") as f:
    json.dump(comparison, f, indent=2, default=str)

print_basket_comparison(comparison)
print(f"\nImplementations saved -> {impl_path}")
print("Done.")
