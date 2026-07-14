"""
EM/DM Carry — Implementation Comparison

Loads `results/em_dm_carry_signal.csv` output from em_dm_carry_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: ["EM_basket", "DM_basket"]

EM/DM carry: binary switch. top_n=1 is meaningful; top_n=2 blends both.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "em_dm_carry"
STRATEGY_NAME    = "EM/DM Carry"
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
    WHERE date >= '2000-01-01' ORDER BY fic, date
""").df()
_df['date'] = pd.to_datetime(_df['date'])
EM = ['BRA','MEX','IND','CHN','KOR','THA','MYS','IDN','PHL','POL']
DM = ['GBR','AUS','SWE','SGP','CHE','NOR','DNK','NZL','JPN','HKG','TWN']
em_daily = _df[_df['fic'].isin(EM)].groupby('date')['portret'].mean()
dm_daily = _df[_df['fic'].isin(DM)].groupby('date')['portret'].mean()
# Build price indexes
em_prices = (1 + em_daily.fillna(0)).cumprod()
dm_prices = (1 + dm_daily.fillna(0)).cumprod()
prices = pd.DataFrame({"EM_basket": em_prices, "DM_basket": dm_prices})
prices.index = pd.to_datetime(prices.index)
prices = prices.resample("B").last().ffill()
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: EM/DM carry: binary switch. top_n=1 is meaningful; top_n=2 blends both.
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
