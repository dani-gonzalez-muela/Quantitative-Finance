
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME = "Cross-Asset Carry"
SAVE_NAME     = "cross_asset_carry"
STARTING_CAPITAL = 100_000
TOP_N = 3
PARAMS = {"top_n": 3,
           "carry_proxy": "trailing_12m_return / trailing_12m_vol (return-to-risk ratio)",
           "signal": "rank by carry, long top 3 of 5 assets",
           "data_note": "SPY+TLT from prices_validated.parquet; gold+oil from commodities_daily.csv; bonds=bonds_yahoo proxy. UUP/EEM/GLD/DBC ETF download blocked. Period: 2016-2025."}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)

print("Loading cross-asset data...")
ARCH = os.path.join(os.path.dirname(BASE_DIR), "archived_strategies", "output")  # fable fix: archived_strategies sits under long_term/, not selection/
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

prices_val = pd.read_parquet(f"{ARCH}/prices_validated.parquet")
comm       = pd.read_csv(f"{COMM}/commodities_daily.csv", parse_dates=["date"], index_col="date").sort_index()
macro      = pd.read_csv(f"{COMM}/macros_daily.csv",      parse_dates=["date"], index_col="date").sort_index()

spy = prices_val["SPY"].dropna()
tlt = prices_val["TLT"].dropna()
gold = comm["gold"].dropna()
gold = gold[~gold.index.duplicated(keep="last")]
oil  = comm["oil"].dropna()
oil  = oil[~oil.index.duplicated(keep="last")]

# Bonds_yahoo as corporate bond proxy
corp_bond = macro["bonds_yahoo"].dropna()
corp_bond = corp_bond[~corp_bond.index.duplicated(keep="last")]

# Align all to common index (trading days from 2016)
raw = pd.DataFrame({"SPY":spy,"TLT":tlt,"Gold":gold,"Oil":oil,"CorpBond":corp_bond})
raw = raw.resample("B").last().ffill().dropna(how="all")
raw = raw[(raw.index >= "2016-01-01") & (raw.index <= "2026-01-01")]
raw = raw.dropna(how="any")   # need all 5 on same dates
print(f"Data: {raw.index[0].date()} -> {raw.index[-1].date()}, {len(raw)} rows")

monthly = raw.resample("ME").last()
instruments = list(raw.columns)

# Carry proxy: trailing 12m return / trailing 12m volatility (Sharpe-like carry)
weights_list = []
for i in range(len(monthly)):
    if i < 12:
        weights_list.append(pd.Series(0.0, index=instruments))
        continue
    ret_12m = monthly.iloc[i] / monthly.iloc[i-12] - 1
    # Monthly returns over past 12m
    monthly_rets = monthly.iloc[i-12:i].pct_change().dropna()
    vol_12m = monthly_rets.std() * np.sqrt(12) + 1e-9
    carry = ret_12m / vol_12m
    carry_valid = carry.dropna()
    if len(carry_valid) >= TOP_N:
        top3 = carry_valid.nlargest(TOP_N).index.tolist()
        w = pd.Series(0.0, index=instruments)
        w[top3] = 1.0 / TOP_N
        weights_list.append(w)
    else:
        weights_list.append(pd.Series(0.0, index=instruments))

weights = pd.DataFrame(weights_list, index=monthly.index)
weights_applied = weights.shift(1).dropna(how="all")
print(f"Avg instruments held: {weights_applied.sum(axis=1).mean():.2f}")

daily_equity = build_equity_from_weights(raw, weights_applied, STARTING_CAPITAL)
monthly_ret_gross = build_monthly_returns(daily_equity)
monthly_ret_net = monthly_ret_gross - 0.0003
trades_df = build_trades(raw, weights_applied, daily_equity, STARTING_CAPITAL)
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

save_results(STRATEGY_NAME, SAVE_NAME, instruments, PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")

# ── Save signal.csv for cross_asset_carry_Implementation.py ──
# Signal: carry proxy (12m return / 12m vol) per asset, recomputed from monthly
carry_scores = pd.DataFrame(index=monthly.index, columns=instruments, dtype=float)
for i in range(len(monthly)):
    if i < 12:
        continue
    ret_12m = monthly.iloc[i] / monthly.iloc[i - 12] - 1
    monthly_rets = monthly.iloc[i - 12:i].pct_change().dropna()
    vol_12m = monthly_rets.std() * np.sqrt(12) + 1e-9
    carry_scores.iloc[i] = ret_12m / vol_12m
carry_scores.index.name = "date"
signal_long = carry_scores.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
