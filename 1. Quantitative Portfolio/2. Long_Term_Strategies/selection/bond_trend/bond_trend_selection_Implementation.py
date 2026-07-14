"""
Bond Trend — Implementation Comparison

Loads `results/bond_trend_signal.csv` output from bond_trend_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: ["TLT_proxy", "IEF_proxy", "SHY_proxy"]

Bond trend: typically 1-2 instruments held at a time
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "bond_trend"
STRATEGY_NAME    = "Bond Trend"
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
COMM  = data_dir('macros')
ARCH  = os.path.join(os.path.dirname(BASE_DIR), "archived_strategies", "output")  # fable fix: archived_strategies sits under long_term/, not selection/
macro = pd.read_csv(f"{COMM}/macros_daily.csv", parse_dates=["date"], index_col="date").sort_index()
bonds_yahoo = macro["bonds_yahoo"].dropna()
prices_val = pd.read_parquet(f"{ARCH}/prices_validated.parquet")
tlt_auth = prices_val["TLT"].dropna()
splice_date = tlt_auth.index[0]
bonds_pre = bonds_yahoo[bonds_yahoo.index < splice_date].copy()
if len(bonds_pre) > 0:
    scale = float(tlt_auth.iloc[0]) / float(bonds_pre.iloc[-1])
    bonds_pre = bonds_pre * scale
long_bond = pd.concat([bonds_pre, tlt_auth]).sort_index()
long_bond = long_bond[~long_bond.index.duplicated(keep="last")]
ir = macro["interest_rates_yahoo"].dropna()
ir_monthly = ir.resample("ME").last()
ir_ret_monthly = -7.5 * ir_monthly.diff() / 100
ir_cum = 100.0 * (1 + ir_ret_monthly.fillna(0)).cumprod()
ief_proxy_daily = ir_cum.resample("D").ffill()
date_range = pd.date_range("2000-01-01", "2026-01-01", freq="D")
shy_proxy = pd.Series(100.0 * (1.005 ** (np.arange(len(date_range)) / 365)), index=date_range)
prices = pd.DataFrame({
    "TLT_proxy": long_bond,
    "IEF_proxy": ief_proxy_daily,
    "SHY_proxy": shy_proxy,
}).resample("B").last().ffill().dropna(how="all")
prices = prices[(prices.index >= "2001-01-01") & (prices.index <= "2026-01-01")]
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: Bond trend: typically 1-2 instruments held at a time
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
