"""
Cross-Asset Carry — Implementation Comparison

Loads `results/cross_asset_carry_signal.csv` output from cross_asset_carry_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: ["SPY", "TLT", "Gold", "Oil", "CorpBond"]

Cross-asset carry: hold top 3 of 5 assets
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "cross_asset_carry"
STRATEGY_NAME    = "Cross-Asset Carry"
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
prices_val = pd.read_parquet(f"{ARCH}/prices_validated.parquet")
comm = pd.read_csv(f"{COMM}/commodities_daily.csv", parse_dates=["date"], index_col="date").sort_index()
macro = pd.read_csv(f"{COMM}/macros_daily.csv", parse_dates=["date"], index_col="date").sort_index()
prices = pd.DataFrame({
    "SPY": prices_val["SPY"],
    "TLT": prices_val["TLT"],
    "Gold": comm["gold"].reindex(prices_val.index, method="ffill"),
    "Oil":  comm["oil"].reindex(prices_val.index, method="ffill"),
    "CorpBond": macro["bonds_yahoo"].reindex(prices_val.index, method="ffill"),
}).dropna(how="all")
prices = prices.resample("B").last().ffill()
prices = prices[(prices.index >= "2016-01-01") & (prices.index <= "2026-01-01")]
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: Cross-asset carry: hold top 3 of 5 assets
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
