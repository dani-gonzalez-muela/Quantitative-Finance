"""
Country CAPE Rotation — Implementation Comparison

Loads `results/country_cape_rotation_signal.csv` output from country_cape_rotation_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: "CRSP world country returns (14 countries)"

Country CAPE rotation: hold 5 cheapest countries. Signal is NEGATED 12m return.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "country_cape_rotation"
STRATEGY_NAME    = "Country CAPE Rotation"
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
import duckdb as _duckdb
# -- fable path bootstrap (Phase C fix: replaces dead session-specific paths) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
_sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
WRDS = data_dir('wrds_parquet')
_con = _duckdb.connect()
_df = _con.execute(f"""
    SELECT fic, date, portret FROM '{WRDS}/11_world_country_returns.parquet'
    WHERE date >= '1995-01-01' ORDER BY fic, date
""").df()
_df['date'] = pd.to_datetime(_df['date'])
# Pivot to country x date
_prices_daily = _df.pivot(index='date', columns='fic', values='portret').dropna(how='all')
# Build synthetic price index from returns
prices = (1 + _prices_daily.fillna(0)).cumprod()
prices.index = pd.to_datetime(prices.index)
prices = prices.resample("B").last().ffill()
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: Country CAPE rotation: hold 5 cheapest countries. Signal is NEGATED 12m return.
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
