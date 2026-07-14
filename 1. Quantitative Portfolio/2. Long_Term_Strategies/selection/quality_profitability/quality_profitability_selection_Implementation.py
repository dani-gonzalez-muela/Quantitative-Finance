# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Quality / Profitability (RMW) — Selection Implementation

NOTE: The v1 backtest (quality_profitability_selection_backtest.py) uses the
FF5 RMW factor as a single-signal timing overlay on the market — it is NOT a
basket selection strategy and does not produce a multi-instrument signal CSV.
Basket weighting variants (equal_weight, inverse_vol_weight, signal_strength_weight)
do not apply here because the signal is a single scalar (cumulative RMW momentum).

For basket selection style comparison, see quality_v2_selection_backtest.py which
selects the top GP quintile from S&P 500 stocks and outputs a proper per-stock
signal usable with shared.basket_implementations.

What this file CAN do:
- Load the v1 trades CSV from results/ and compare exposure-level sizing variants
  via shared.implementations (same as timing strategies).

To run full Implementation comparison for the v2 (true basket), see:
    quality_profitability_v2_selection_Implementation.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

SAVE_NAME        = "quality_profitability"
STRATEGY_NAME    = "Quality / Profitability (RMW)"
STARTING_CAPITAL = 100_000
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

# -- Load trades --
trades_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_trades.csv")
if not os.path.exists(trades_path):
    print(f"ERROR: {trades_path} not found. Run {SAVE_NAME}_selection_backtest.py first.")
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
