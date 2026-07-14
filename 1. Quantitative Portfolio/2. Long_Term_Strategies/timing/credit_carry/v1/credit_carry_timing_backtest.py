
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from _backtest_utils import (build_equity_from_weights, build_monthly_returns,
    build_trades, portfolio_metrics, save_results)

STRATEGY_NAME = "Credit Carry"
SAVE_NAME     = "credit_carry"
STARTING_CAPITAL = 100_000
PARAMS = {"mom_window_months": 12,
           "signal": "long bonds_yahoo when its 12m return > treasury_proxy 12m return; else hold treasury_proxy",
           "data_note": "bonds_yahoo=corporate bond ETF proxy (HYG-like); treasury_proxy=price series from 10yr yields. HYG/LQD/IEF ETF download blocked."}
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(OUTPUT_BASE)

print("Loading credit carry data...")
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
macro = pd.read_csv(f"{COMM}/macros_daily.csv", parse_dates=["date"], index_col="date").sort_index()

bonds_hg = macro["bonds_yahoo"].dropna()   # HYG-like proxy
bonds_hg = bonds_hg[~bonds_hg.index.duplicated(keep="last")]

# Treasury proxy from 10yr yield (duration ~7.5yr)
ir = macro["interest_rates_yahoo"].dropna()
ir = ir[~ir.index.duplicated(keep="last")]
ir_monthly = ir.resample("ME").last()
ir_ret = -7.5 * ir_monthly.diff() / 100
tsy_price = 100.0 * (1 + ir_ret.fillna(0)).cumprod()
tsy_daily = tsy_price.resample("D").ffill()

raw = pd.DataFrame({"bonds_hg": bonds_hg, "tsy_proxy": tsy_daily})
raw = raw.resample("B").last().ffill().dropna(how="all")
raw = raw[(raw.index >= "2001-01-01") & (raw.index <= "2026-01-01")]
print(f"Data: {raw.index[0].date()} -> {raw.index[-1].date()}, {len(raw)} rows")

monthly = raw.resample("ME").last()
hg_ret  = monthly["bonds_hg"].pct_change(12)
tsy_ret = monthly["tsy_proxy"].pct_change(12)
rel_mom = hg_ret - tsy_ret

# Signal: long bonds_hg when relative momentum > 0, else hold treasury
hg_signal  = (rel_mom > 0).astype(float)
tsy_signal = 1 - hg_signal
weights = pd.DataFrame({"bonds_hg": hg_signal, "tsy_proxy": tsy_signal}, index=monthly.index)
weights_applied = weights.shift(1).dropna(how="all")
print(f"HYG-like periods: {hg_signal.shift(1).dropna().sum():.0f} / {len(weights_applied)}")

daily_equity = build_equity_from_weights(raw, weights_applied, STARTING_CAPITAL)
monthly_ret_gross = build_monthly_returns(daily_equity)
monthly_ret_net = monthly_ret_gross - 0.0002
trades_df = build_trades(raw, weights_applied, daily_equity, STARTING_CAPITAL)
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%, Trades={len(trades_df)}")

save_results(STRATEGY_NAME, SAVE_NAME, ["bonds_hg_proxy","tsy_proxy"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"), daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")

# ── Save signal.csv for credit_carry_Implementation.py ──
# Signal: relative momentum (bonds_hg vs tsy_proxy). Per instrument:
#   bonds_hg  score = rel_mom (positive = buy credit)
#   tsy_proxy score = -rel_mom (defensive when rel_mom < 0)
signal_df_raw = pd.DataFrame(
    {"bonds_hg": rel_mom, "tsy_proxy": -rel_mom},
    index=monthly.index
)
signal_df_raw.index.name = "date"
signal_long = signal_df_raw.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
