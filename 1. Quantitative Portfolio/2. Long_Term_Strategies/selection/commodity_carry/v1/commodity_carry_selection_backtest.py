
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME = "Commodity Carry"
SAVE_NAME     = "commodity_carry"
STARTING_CAPITAL = 100_000
TOP_N = 3
PARAMS = {"top_n": 3,
           "carry_proxy": "1m_return - 3m_return/3 (roll yield differential proxy)",
           "signal": "rank by carry, long top 3 commodities",
           "data_note": "Futures price proxies from commodities_daily.csv. True carry = spot/futures spread unavailable for ETFs. USO/CORN/WEAT/SOYB/DBA download blocked. Period: 2001-2025."}
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

COMMODITIES = ["gold", "oil", "corn", "wheat", "soybeans"]
available = [c for c in COMMODITIES if c in comm.columns]
comm_dedup = comm[~comm.index.duplicated(keep="last")]
raw = comm_dedup[available].dropna(how="all")
raw = raw.resample("B").last().ffill().dropna(how="all")
raw = raw[(raw.index >= "2002-01-01") & (raw.index <= "2026-01-01")]
print(f"Available: {available}")
print(f"Data: {raw.index[0].date()} -> {raw.index[-1].date()}, {len(raw)} rows")

monthly = raw.resample("ME").last()
carry_1m = monthly.pct_change(1)
carry_3m = monthly.pct_change(3) / 3
carry_signal = carry_1m - carry_3m

weights_list = []
for i in range(len(monthly)):
    if i < 4:
        weights_list.append(pd.Series(0.0, index=available))
        continue
    carry = carry_signal.iloc[i].dropna()
    if len(carry) >= TOP_N:
        top3 = carry.nlargest(TOP_N).index.tolist()
        w = pd.Series(0.0, index=available)
        w[top3] = 1.0 / TOP_N
        weights_list.append(w)
    else:
        weights_list.append(pd.Series(0.0, index=available))

weights = pd.DataFrame(weights_list, index=monthly.index)
weights_applied = weights.shift(1).dropna(how="all")
print(f"Avg instruments held: {weights_applied.sum(axis=1).mean():.2f}")

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

# ── Save signal.csv for commodity_carry_Implementation.py ──
# Signal: carry proxy (1m_return - 3m_return/3) per commodity
carry_signal.index.name = "date"
signal_long = carry_signal.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
