
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_monthly_returns, portfolio_metrics, save_results)

STRATEGY_NAME = "Quality / Profitability (RMW)"
SAVE_NAME     = "quality_profitability"
STARTING_CAPITAL = 100_000
PARAMS = {
    "factor": "FF5 RMW (Robust Minus Weak profitability)",
    "signal": "long Mkt+half_RMW when 12m cumulative RMW signal positive; else long market only",
    "note": "Compustat fundamentals not in WRDS snapshot. FF5 RMW from ff_factors_monthly.csv (Fama-French Research Data). Period: 1963-2026."
}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)

print("Loading FF factors...")
RFR = os.path.join(BASE_DIR, "regime_factor_rotation", "data")
ff = pd.read_csv(f"{RFR}/ff_factors_monthly.csv", parse_dates=["Date"], index_col="Date").sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)   # align to month-end

mkt = ff["Mkt-RF"] + ff["RF"]   # total market return
rmw = ff["RMW"]
rf  = ff["RF"]

# Signal: 12m cumulative RMW positive => go long quality tilt
rmw_mom = rmw.rolling(12).apply(lambda x: (1+x).prod()-1, raw=True)
quality_signal = (rmw_mom > 0).astype(float).shift(1)   # 1-month lag to avoid look-ahead

# Portfolio: quality-on  = 50% Mkt + 50% RMW (market + quality tilt)
#            quality-off = 100% Mkt
port_ret = (quality_signal * (0.5*mkt + 0.5*rmw) +
            (1 - quality_signal) * mkt)
port_ret = port_ret.dropna()
monthly_ret_gross = port_ret.rename("ret")
monthly_ret_net   = monthly_ret_gross - 0.0002

print(f"Data: {monthly_ret_gross.index[0].date()} -> {monthly_ret_gross.index[-1].date()}, {len(monthly_ret_gross)} months")
print(f"Quality-on pct: {quality_signal.dropna().mean()*100:.1f}%")

eq_monthly   = STARTING_CAPITAL * (1 + monthly_ret_gross).cumprod()
daily_equity = eq_monthly.resample("D").ffill()
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%")

# Trades
trades_list = []
run_eq = STARTING_CAPITAL
for i in range(len(monthly_ret_gross)):
    dt = monthly_ret_gross.index[i]
    r  = float(monthly_ret_gross.iloc[i])
    gp = run_eq * r; np_ = run_eq * (r - 0.0002)
    eq_b = run_eq; run_eq += np_
    entry = monthly_ret_gross.index[i-1] if i > 0 else dt
    trades_list.append({"entry_time":entry,"exit_time":dt,"position":"long",
        "instrument":"FF_Mkt_Quality","entry_price":100.0,
        "exit_price":round(100.0*(1+r),4),"exit_reason":"monthly_hold",
        "risk":5.0,"shares":1,"gross_pnl":round(float(gp),2),
        "fees":round(float(gp-np_),2),"net_pnl":round(float(np_),2),
        "equity_before":round(float(eq_b),2),"equity":round(float(run_eq),2)})
trades_df = pd.DataFrame(trades_list)
trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
trades_df["exit_time"]  = pd.to_datetime(trades_df["exit_time"])
print(f"Trades: {len(trades_df)}")

save_results(STRATEGY_NAME, SAVE_NAME, ["FF_MktRF","FF_RMW"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")
