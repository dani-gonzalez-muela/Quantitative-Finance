"""
Low Volatility v2 — True BAB using CRSP Beta Decile Portfolios (1926-2025)
===========================================================================
Enhancement over v1:
- v1 used CRSP large-cap decile 10 (market-cap proxy for low-beta)
- v2 uses CRSP NYSE/NYSEMKT Beta Decile 1 (actual lowest-beta decile portfolio)
  from 10_crsp_market_portfolios.parquet (indno 1000102)
- Long bottom beta decile only (simple BAB proxy)
- Nearly 100-year history (1926-2025)
- Data: CRSP NYSE/NYSEMKT Beta Decile 1 = lowest beta stocks, monthly rebalanced
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import pyarrow.parquet as pq
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME    = "Low Volatility / BAB v2 (CRSP Beta Decile 1)"
SAVE_NAME        = "low_vol_v2"
STARTING_CAPITAL = 100_000
OUTPUT_BASE      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR         = os.path.dirname(OUTPUT_BASE)

# CRSP Beta Decile indno mapping
# 1000102 = NYSE/NYSEMKT Beta Decile 1 (LOWEST beta)
# 1000111 = NYSE/NYSEMKT Beta Decile 10 (HIGHEST beta)
LOW_BETA_ID  = 1000102
HIGH_BETA_ID = 1000111
MARKET_ID    = 1000040   # NYSE/NYSEMKT Value-Weighted Market Index

PARAMS = {
    "strategy": "long_low_beta_decile",
    "data": "CRSP NYSE/NYSEMKT Beta Decile 1 (lowest beta stocks)",
    "signal": "always long beta decile 1; buy-and-hold low-beta portfolio",
    "note": (
        "CRSP NYSE/NYSEMKT Beta Decile 1 from 10_crsp_market_portfolios.parquet "
        "(indno=1000102). True BAB signal: long 20% lowest-beta stocks on NYSE/NYSEMKT. "
        "Monthly rebalance built into the CRSP portfolio construction. "
        "Better Market Betas zip covers 1986-2019 (individual stock betas); "
        "CRSP beta deciles cover 1925-2025 and are the standard academic benchmark. "
        "Period: 1970-2025."
    )
}

print("Loading CRSP market portfolios...")
mkt_path = os.path.normpath(os.path.join(
    BASE_DIR, "..", "..", "algo_trading", "data", "wrds",
    "10_crsp_market_portfolios.parquet"))
df_all = pq.read_table(mkt_path).to_pandas()

# Pull low-beta decile and market
ids_needed = [LOW_BETA_ID, HIGH_BETA_ID, MARKET_ID]
df = df_all[df_all["indno"].isin(ids_needed)].copy()
df["date"] = pd.to_datetime(df["dlycaldt"])
df = df.sort_values(["indno", "date"])

# Pivot to wide
wide = df.pivot(index="date", columns="indno", values="dlytotret")
wide = wide.rename(columns={
    LOW_BETA_ID:  "low_beta",
    HIGH_BETA_ID: "high_beta",
    MARKET_ID:    "market",
})

# Filter to 1970+ (data exists from 1925 but pre-1970 thinner)
wide = wide.loc["1970-01-01":]
wide = wide.dropna(subset=["low_beta"])
print(f"Data: {wide.index[0].date()} -> {wide.index[-1].date()}, {len(wide)} rows")

# Build price series from returns
prices = pd.DataFrame(index=wide.index)
prices["low_beta"] = (1 + wide["low_beta"].fillna(0)).cumprod() * 100

# ── SIGNAL: always long low-beta decile ──────────────────────────────────────
# Buy-and-hold the low-beta decile portfolio
monthly_dates = prices.resample("ME").last().index

weights_list = []
for dt in monthly_dates:
    weights_list.append(pd.Series({"low_beta": 1.0}))

weights = pd.DataFrame(weights_list, index=monthly_dates)
weights_applied = weights.shift(1).dropna(how="all")

# ── BACKTEST ─────────────────────────────────────────────────────────────────
daily_equity = build_equity_from_weights(prices, weights_applied, STARTING_CAPITAL)
monthly_ret_gross = build_monthly_returns(daily_equity)
monthly_ret_net   = monthly_ret_gross - 0.0002   # low turnover
trades_df = build_trades(prices, weights_applied, daily_equity, STARTING_CAPITAL)

mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, "
      f"MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

# ── SAVE ─────────────────────────────────────────────────────────────────────
save_results(STRATEGY_NAME, SAVE_NAME, ["CRSP_BetaDecile1_NYSE_NYSEMKT"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"),
    daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")
