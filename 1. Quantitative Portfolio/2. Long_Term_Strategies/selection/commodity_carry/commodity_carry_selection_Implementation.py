"""
Commodity Carry — Implementation Comparison

Loads `results/commodity_carry_signal.csv` output from commodity_carry_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: "gold, oil, corn, wheat, soybeans (available columns)"

Commodity carry: hold top 3 of available commodities
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "commodity_carry"
STRATEGY_NAME    = "Commodity Carry"
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
# -- fable data-manifest bootstrap (Phase E consolidation) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
if _bd not in _sys.path:
    _sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
COMM = data_dir('macros')
comm = pd.read_csv(f"{COMM}/commodities_daily.csv", parse_dates=["date"], index_col="date").sort_index()
COMMODITIES = ["gold", "oil", "corn", "wheat", "soybeans"]
available_cols = [c for c in COMMODITIES if c in comm.columns]
comm_dedup = comm[~comm.index.duplicated(keep="last")]
prices = comm_dedup[available_cols].dropna(how="all")
prices = prices.resample("B").last().ffill().dropna(how="all")
prices = prices[(prices.index >= "2002-01-01") & (prices.index <= "2026-01-01")]
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: Commodity carry: hold top 3 of available commodities
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
