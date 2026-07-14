
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import pyarrow.parquet as pq
from _backtest_utils import (build_monthly_returns, portfolio_metrics, save_results)

STRATEGY_NAME = "Low Volatility / BAB Proxy"
SAVE_NAME     = "low_volatility"
STARTING_CAPITAL = 100_000
PARAMS = {
    "data": "CRSP NYSE cap decile 10 (largest stocks, lowest historical beta ~0.85)",
    "signal": "always long low-beta proxy (large cap decile 10)",
    "note": "True BAB factor requires individual stock betas. CRSP 10_crsp_market_portfolios.parquet has size deciles, not beta deciles. Decile 10 (largest cap) historically has beta ~0.85 vs market and lower volatility. Period: 1970-2025."
}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
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

print("Loading CRSP market portfolios...")
df = pq.read_table(f"{WRDS}/10_crsp_market_portfolios.parquet").to_pandas()
df["date"] = pd.to_datetime(df["dlycaldt"])
df["dlytotret"] = pd.to_numeric(df["dlytotret"], errors="coerce")

# indno 1000011 = NYSE Market Cap Decile 10 (largest = lowest beta)
# indno 1000000 = NYSE Value-Weighted Market
low_vol = df[df["indno"] == 1000011][["date","dlytotret"]].dropna().set_index("date").sort_index()
market  = df[df["indno"] == 1000000][["date","dlytotret"]].dropna().set_index("date").sort_index()

low_vol_m = (1 + low_vol["dlytotret"]).resample("ME").prod() - 1
market_m  = (1 + market["dlytotret"]).resample("ME").prod()  - 1

low_vol_m = low_vol_m[(low_vol_m.index >= "1970-01-01") & (low_vol_m.index <= "2026-01-01")]
market_m  = market_m [(market_m.index  >= "1970-01-01") & (market_m.index  <= "2026-01-01")]

# Long only low-vol (always invested)
monthly_ret_gross = low_vol_m.dropna()
monthly_ret_net   = monthly_ret_gross - 0.0003

eq_monthly   = STARTING_CAPITAL * (1 + monthly_ret_gross).cumprod()
daily_equity = eq_monthly.resample("D").ffill()
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%")

# Build trades
trades_list = []
run_eq = STARTING_CAPITAL
for i in range(len(monthly_ret_gross)):
    dt = monthly_ret_gross.index[i]
    r  = float(monthly_ret_gross.iloc[i])
    gp = run_eq * r; np_ = run_eq * (r - 0.0003)
    eq_b = run_eq; run_eq += np_
    entry = monthly_ret_gross.index[i-1] if i > 0 else dt
    trades_list.append({"entry_time":entry,"exit_time":dt,"position":"long",
        "instrument":"CRSP_LargeCap_D10","entry_price":100.0,
        "exit_price":round(100.0*(1+r),4),"exit_reason":"monthly_hold",
        "risk":5.0,"shares":1,"gross_pnl":round(float(gp),2),
        "fees":round(float(gp-np_),2),"net_pnl":round(float(np_),2),
        "equity_before":round(float(eq_b),2),"equity":round(float(run_eq),2)})
trades_df = pd.DataFrame(trades_list)
trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
trades_df["exit_time"]  = pd.to_datetime(trades_df["exit_time"])
print(f"Trades: {len(trades_df)}")

# Market benchmark stats
mkt_eq = STARTING_CAPITAL * (1 + market_m.dropna()).cumprod()
mkt_mets = portfolio_metrics(mkt_eq.resample("D").ffill())
print(f"Market benchmark: CAGR={mkt_mets['cagr']}%, Sharpe={mkt_mets['sharpe_daily']}")

save_results(STRATEGY_NAME, SAVE_NAME, ["CRSP_NYSE_CapDecile10"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")

# ── Save signal.csv for low_volatility_Implementation.py ──
# Single instrument, always long — signal = 1.0 (constant allocation)
# Note: basket weighting does not apply (see discussion_points.md §2.1, §3.4)
signal_data = pd.DataFrame(
    {"date": monthly_ret_gross.index, "instrument": "CRSP_LargeCap_D10", "score": 1.0}
)
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
