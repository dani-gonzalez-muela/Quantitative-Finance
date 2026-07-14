# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Low Volatility / BAB v2 (CRSP Beta Decile 1) — Timing Implementation

Loads the trades output from low_vol_v2_timing_backtest.py and applies
sizing variants via shared.implementations.

The v2 backtest goes long the CRSP Beta Decile 1 portfolio (lowest-beta
NYSE/NYSEMKT stocks, ~100-year history from 1926-2025). This is a single-
instrument timing strategy — basket weighting variants do not apply.

Run low_vol_v2_timing_backtest.py first to produce:
    results/low_vol_v2_trades.csv
    results/low_vol_v2_daily_equity/
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

SAVE_NAME        = "low_vol_v2"
STRATEGY_NAME    = "Low Volatility / BAB v2 (CRSP Beta Decile 1)"
STARTING_CAPITAL = 100_000
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

# -- Load trades --
trades_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_trades.csv")
if not os.path.exists(trades_path):
    print(f"ERROR: {trades_path} not found. Run low_vol_v2_timing_backtest.py first.")
    sys.exit(1)

trades = pd.read_csv(trades_path, parse_dates=["entry_time", "exit_time"])
print(f"Loaded {len(trades)} trades from {SAVE_NAME}_trades.csv")

# -- Sizing comparison via shared.implementations --
from _shared.implementations import simple_bet, vol_targeting, risk_based, compare_implementations

results = compare_implementations(
    trades,
    starting_capital=STARTING_CAPITAL,
    strategy_name=STRATEGY_NAME,
    save_name=SAVE_NAME,
    output_base=OUTPUT_BASE,
)

impl_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_implementations.json")
with open(impl_path, "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"Implementations saved -> {impl_path}")
print("Done.")
