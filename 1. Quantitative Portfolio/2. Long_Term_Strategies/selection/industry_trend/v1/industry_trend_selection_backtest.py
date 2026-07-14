
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME = "Industry Trend Following"
SAVE_NAME     = "industry_trend"
STARTING_CAPITAL = 100_000
PARAMS = {"top_n": 3, "mom_window_months": 12, "skip_last_month": True,
           "signal": "12-1m momentum, long top 3 sectors",
           "data_note": "FF49 download blocked; using SPDR sector ETFs (XLE/XLK/XLY/XLP/XLU/XLF/XLI/XLV/XLB) from prices_validated.parquet. Period: 2016-2025. Spirit matches Zarattini & Antonacci (Dow 2025)."}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)
TOP_N = 3

print("Loading sector ETF data...")
ARCH = os.path.join(os.path.dirname(BASE_DIR), "archived_strategies", "output")  # fable fix: archived_strategies sits under long_term/, not selection/
prices = pd.read_parquet(f"{ARCH}/prices_validated.parquet")

SECTORS = ["XLE","XLK","XLY","XLP","XLU","XLF","XLI","XLV","XLB"]
available = [s for s in SECTORS if s in prices.columns]
raw = prices[available].dropna(how="all")
print(f"Sectors: {available}")
print(f"Data: {raw.index[0].date()} -> {raw.index[-1].date()}, {len(raw)} rows")

# 12-1 month momentum (skip last month)
monthly = raw.resample("ME").last()

weights_list = []
for i in range(len(monthly)):
    if i < 13:
        weights_list.append(pd.Series(0.0, index=available))
        continue
    # Return from 13 months ago to 1 month ago (skip last month)
    past_price = monthly.iloc[i-13]
    recent_price = monthly.iloc[i-1]
    mom = (recent_price / past_price) - 1
    mom_valid = mom.dropna()
    if len(mom_valid) >= TOP_N:
        top_sectors = mom_valid.nlargest(TOP_N).index.tolist()
        w = pd.Series(0.0, index=available)
        w[top_sectors] = 1.0 / TOP_N
        weights_list.append(w)
    else:
        weights_list.append(pd.Series(0.0, index=available))

weights = pd.DataFrame(weights_list, index=monthly.index)
weights_applied = weights.shift(1).dropna(how="all")
print(f"Avg sectors held: {weights_applied.sum(axis=1).mean():.2f}")

daily_equity = build_equity_from_weights(raw, weights_applied, STARTING_CAPITAL)
monthly_ret_gross = build_monthly_returns(daily_equity)
monthly_ret_net = monthly_ret_gross - 0.0005
trades_df = build_trades(raw, weights_applied, daily_equity, STARTING_CAPITAL)
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

save_results(STRATEGY_NAME, SAVE_NAME, available, PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")

# ── Save signal.csv for industry_trend_Implementation.py ──
# Signal: 12-1m momentum per sector (recomputed from monthly data, same as in loop)
signal_scores = pd.DataFrame(index=monthly.index, columns=available, dtype=float)
for i in range(len(monthly)):
    if i < 13:
        continue
    past_price   = monthly.iloc[i - 13]
    recent_price = monthly.iloc[i - 1]
    mom_row = (recent_price / past_price) - 1
    signal_scores.iloc[i] = mom_row
signal_scores.index.name = "date"
signal_long = signal_scores.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
