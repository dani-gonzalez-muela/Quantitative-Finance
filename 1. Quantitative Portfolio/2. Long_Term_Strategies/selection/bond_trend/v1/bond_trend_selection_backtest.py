
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME = "Bond Trend"
SAVE_NAME     = "bond_trend"
STARTING_CAPITAL = 100_000
PARAMS = {"mom_window_months": 12, "signal": "12m_return > 0 long; else flat",
           "sizing": "equal_weight",
           "data_note": "bonds_yahoo=long-bond ETF proxy (TLT-like 2000-2015) spliced with TLT (2016-2025); IEF_proxy=10yr-yield-based price; SHY_proxy=risk-free compounded. ETF download blocked in sandbox."}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)

print("Loading bond data...")
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

# Splice: bonds_yahoo (2000-2015) + TLT (2016-2025)
splice_date = tlt_auth.index[0]
bonds_pre = bonds_yahoo[bonds_yahoo.index < splice_date].copy()
if len(bonds_pre) > 0:
    scale = float(tlt_auth.iloc[0]) / float(bonds_pre.iloc[-1])
    bonds_pre = bonds_pre * scale
long_bond = pd.concat([bonds_pre, tlt_auth]).sort_index()
long_bond = long_bond[~long_bond.index.duplicated(keep="last")]

# IEF proxy: compute from 10yr yield (duration ~7.5yr)
ir = macro["interest_rates_yahoo"].dropna()
ir_monthly = ir.resample("ME").last()
ir_ret_monthly = -7.5 * ir_monthly.diff() / 100
ir_cum = 100.0 * (1 + ir_ret_monthly.fillna(0)).cumprod()
ief_proxy_daily = ir_cum.resample("D").ffill()

# SHY proxy: 0.5% annual return (like cash)
date_range = pd.date_range("2000-01-01", "2026-01-01", freq="D")
shy_proxy = pd.Series(100.0 * (1.005 ** (np.arange(len(date_range)) / 365)), index=date_range)

raw = pd.DataFrame({
    "TLT_proxy": long_bond,
    "IEF_proxy": ief_proxy_daily,
    "SHY_proxy": shy_proxy,
}).resample("B").last().ffill().dropna(how="all")
raw = raw[(raw.index >= "2001-01-01") & (raw.index <= "2026-01-01")]
print(f"Data: {raw.index[0].date()} -> {raw.index[-1].date()}, {len(raw)} rows")

monthly = raw.resample("ME").last()
mom = monthly.pct_change(12)
signal = (mom > 0).astype(float)
n_long = signal.sum(axis=1)
weights = signal.div(n_long.replace(0, np.nan), axis=0).fillna(0)
weights_applied = weights.shift(1).dropna(how="all")
print(f"Avg instruments held: {weights_applied.sum(axis=1).mean():.2f}")

daily_equity = build_equity_from_weights(raw, weights_applied, STARTING_CAPITAL)
monthly_ret_gross = build_monthly_returns(daily_equity)
monthly_ret_net = monthly_ret_gross - 0.0002
trades_df = build_trades(raw, weights_applied, daily_equity, STARTING_CAPITAL)
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

save_results(STRATEGY_NAME, SAVE_NAME, ["TLT_proxy","IEF_proxy","SHY_proxy"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")

# ── Save signal.csv for bond_trend_Implementation.py ──
# Signal: 12m momentum per bond proxy (raw score before 0/1 signal)
signal_raw = monthly.pct_change(12)
signal_raw.index.name = "date"
signal_long = signal_raw.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")  # fable fix: pre-existing NameError in original
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
