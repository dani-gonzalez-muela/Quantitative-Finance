
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME = "Commodity Trend"
SAVE_NAME     = "commodity_trend"
STARTING_CAPITAL = 100_000
PARAMS = {"mom_window_months": 12, "signal": "12m_return > 0 long; else flat",
           "sizing": "equal_weight",
           "instruments": ["gold","oil"],
           "data_note": "Futures-price proxies from commodities_daily.csv (vol_overlay). DBC/GSG ETF download blocked."}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)

print("Loading commodity data...")
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

# Use gold and oil as the two commodity trend instruments
raw = comm[["gold","oil"]].dropna(how="all")
raw = raw.resample("B").last().ffill().dropna(how="all")
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
monthly_ret_net = monthly_ret_gross - 0.0003
trades_df = build_trades(raw, weights_applied, daily_equity, STARTING_CAPITAL)
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

save_results(STRATEGY_NAME, SAVE_NAME, ["gold","oil"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")

# ── Save signal.csv for commodity_trend_Implementation.py ──
# Signal: 12m momentum per commodity (raw score before binary 0/1 signal)
signal_raw = monthly.pct_change(12)
signal_raw.index.name = "date"
signal_long = signal_raw.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
