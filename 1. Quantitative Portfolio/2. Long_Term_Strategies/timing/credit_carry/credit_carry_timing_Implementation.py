# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Credit Carry — Implementation Comparison

Loads `results/credit_carry_signal.csv` output from credit_carry_Backtest.py
and tests basket weighting variants via shared.basket_implementations.

Instruments: ["bonds_hg", "tsy_proxy"]

Credit carry: 2-instrument binary switch, top_n=1 most meaningful
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

from _shared.basket_implementations import compare_basket_implementations, print_basket_comparison

SAVE_NAME        = "credit_carry"
STRATEGY_NAME    = "Credit Carry"
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
COMM = os.path.join(BASE_DIR, "vol_overlay", "data", "processed")
macro = pd.read_csv(f"{COMM}/macros_daily.csv", parse_dates=["date"], index_col="date").sort_index()
bonds_hg = macro["bonds_yahoo"].dropna()
bonds_hg = bonds_hg[~bonds_hg.index.duplicated(keep="last")]
ir = macro["interest_rates_yahoo"].dropna()
ir = ir[~ir.index.duplicated(keep="last")]
ir_monthly = ir.resample("ME").last()
ir_ret = -7.5 * ir_monthly.diff() / 100
tsy_price = 100.0 * (1 + ir_ret.fillna(0)).cumprod()
tsy_daily = tsy_price.resample("D").ffill()
prices = pd.DataFrame({"bonds_hg": bonds_hg, "tsy_proxy": tsy_daily})
prices = prices.resample("B").last().ffill().dropna(how="all")
prices = prices[(prices.index >= "2001-01-01") & (prices.index <= "2026-01-01")]
print(f"Prices: {prices.shape[0]} rows, {list(prices.columns)}")

# ── Run basket implementations ──
print("Running compare_basket_implementations...")
# Note: Credit carry: 2-instrument binary switch, top_n=1 most meaningful
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
