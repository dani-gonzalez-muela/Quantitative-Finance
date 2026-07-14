"""
Industry Trend v2 — CRSP Sector Indices (2011-2025)
=====================================================
Enhancement over v1:
- Uses 11 CRSP US sector indices (from WRDS 10_crsp_market_portfolios.parquet)
  instead of 9 SPDR ETFs
- CRSP sectors: Technology, Telecom, Health Care, Financials, Real Estate,
  Consumer Discretionary, Consumer Staples, Industrials, Basic Materials, Energy, Utilities
- Longer history: 2011-2025 (vs 2016-2025 in v1)
- Top 5 of 11 (vs top 3 of 9 in v1) — more diversification
- Signal: 12-1 month cross-sectional momentum
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import pyarrow.parquet as pq
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME    = "Industry Trend Following v2 (CRSP Sectors)"
SAVE_NAME        = "industry_trend_v2"
STARTING_CAPITAL = 100_000
TOP_N            = 5   # top 5 of 11 sectors
OUTPUT_BASE      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR         = os.path.dirname(OUTPUT_BASE)

PARAMS = {
    "top_n": TOP_N,
    "mom_window_months": 12,
    "skip_last_month": True,
    "signal": "12-1m momentum, long top 5 of 11 CRSP sector indices",
    "data_note": (
        "CRSP US Sector Indices from 10_crsp_market_portfolios.parquet "
        "(indno 1001630-1001640). 11 sectors: Technology, Telecom, Health Care, "
        "Financials, Real Estate, Consumer Discretionary, Consumer Staples, "
        "Industrials, Basic Materials, Energy, Utilities. Period: 2011-2025."
    )
}

# CRSP sector index ids and names
SECTOR_INDNO = {
    1001630: "Technology",
    1001631: "Telecom",
    1001632: "HealthCare",
    1001633: "Financials",
    1001634: "RealEstate",
    1001635: "ConsDisc",
    1001636: "ConsStaples",
    1001637: "Industrials",
    1001638: "BasicMats",
    1001639: "Energy",
    1001640: "Utilities",
}

print("Loading CRSP market portfolios...")
WRDS = os.path.join(BASE_DIR, os.pardir, os.pardir, "algo_trading", "data", "wrds")
mkt_path = os.path.join(BASE_DIR, "..", "..", "algo_trading", "data", "wrds",
                        "10_crsp_market_portfolios.parquet")
mkt_path = os.path.normpath(mkt_path)
df_all = pq.read_table(mkt_path).to_pandas()

sector_ids = list(SECTOR_INDNO.keys())
df_sec = df_all[df_all["indno"].isin(sector_ids)].copy()
df_sec["date"]    = pd.to_datetime(df_sec["dlycaldt"])
df_sec["sector"]  = df_sec["indno"].map(SECTOR_INDNO)
df_sec["ret"]     = df_sec["dlytotret"]          # total return (incl. dividends)

# Build daily price index per sector (start at 1.0 on first day)
df_sec = df_sec.sort_values(["sector", "date"])
df_sec = df_sec[df_sec["ret"].notna()]

# Pivot to wide (each sector = column of daily returns)
daily_ret = df_sec.pivot(index="date", columns="sector", values="ret")
daily_ret = daily_ret.sort_index()

# Filter to data start
daily_ret = daily_ret.loc["2011-01-01":]
print(f"Data: {daily_ret.index[0].date()} -> {daily_ret.index[-1].date()}, "
      f"{len(daily_ret)} rows, {daily_ret.shape[1]} sectors")
print(f"Sectors: {list(daily_ret.columns)}")

# Build price series from returns (needed for equity calc)
prices = (1 + daily_ret.fillna(0)).cumprod() * 100

# ── MOMENTUM SIGNAL ──────────────────────────────────────────────────────────
monthly_price = prices.resample("ME").last()

weights_list = []
for i in range(len(monthly_price)):
    if i < 13:
        weights_list.append(pd.Series(0.0, index=daily_ret.columns))
        continue
    past_px   = monthly_price.iloc[i - 13]   # 13 months ago
    recent_px = monthly_price.iloc[i - 1]    # 1 month ago (skip last month)
    mom       = (recent_px / past_px) - 1
    mom_valid = mom.dropna()
    if len(mom_valid) >= TOP_N:
        top_sectors = mom_valid.nlargest(TOP_N).index.tolist()
        w = pd.Series(0.0, index=daily_ret.columns)
        w[top_sectors] = 1.0 / TOP_N
        weights_list.append(w)
    else:
        weights_list.append(pd.Series(0.0, index=daily_ret.columns))

weights = pd.DataFrame(weights_list, index=monthly_price.index)
weights_applied = weights.shift(1).dropna(how="all")

avg_held = weights_applied.sum(axis=1)
print(f"Avg sectors held: {avg_held[avg_held > 0].mean():.2f}")

# ── BACKTEST ─────────────────────────────────────────────────────────────────
daily_equity = build_equity_from_weights(prices, weights_applied, STARTING_CAPITAL)
monthly_ret_gross = build_monthly_returns(daily_equity)
monthly_ret_net   = monthly_ret_gross - 0.0005
trades_df = build_trades(prices, weights_applied, daily_equity, STARTING_CAPITAL)

mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, "
      f"MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

# ── SAVE ─────────────────────────────────────────────────────────────────────
save_results(STRATEGY_NAME, SAVE_NAME, list(SECTOR_INDNO.values()), PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"),
    daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")
