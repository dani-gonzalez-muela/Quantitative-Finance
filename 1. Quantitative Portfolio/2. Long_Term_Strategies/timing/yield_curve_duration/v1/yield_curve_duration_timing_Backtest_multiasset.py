# -*- coding: utf-8 -*-
"""
Yield Curve Duration - Multi-Asset Timing Backtest
Signal: T10Y2Y (10yr-2yr spread) -> duration regime.
  steep  (>0.5%) -> favour long-duration ETFs (TLT, IEF)
  flat   (0-0.5%) -> neutral
  inverted (<0%) -> favour short-duration ETFs (SHY, BIL)

FRED data: synthetic series derived from ETF prices (BIL->short rate; IEF->10yr).
Available 2016-01-04 onwards.  Loaded directly (bypasses stale .pyc cache).

Outputs
  results/yield_curve_duration_multiasset_per_instrument.csv
  results/yield_curve_duration_multiasset_summary.json
"""

import sys, os, json, warnings
import numpy as np
import pandas as pd
from scipy import stats

import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d)
    assert _p != _d, ".project_root marker not found - place it at the algo_trading root"
    _d = _p
_ROOT = _d
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test
warnings.filterwarnings("ignore")

# ---------- Config -----------------------------------------------------------
STRATEGY_NAME    = "Yield Curve Duration (Multi-Asset)"
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
BASKET           = ["TLT", "IEF", "SHY", "TIP", "BIL", "LQD", "HYG"]

# Favourable regime per ETF:
#   long-dur ETFs benefit when curve is steep (T10Y2Y > 0.5%)
#   short-dur ETFs benefit when curve is flat/inverted (T10Y2Y <= 0.5%)
REGIME_MAP = {
    "TLT": "long",
    "IEF": "long",
    "LQD": "long",
    "HYG": "long",
    "TIP": "long",
    "SHY": "short",
    "BIL": "short",
}

DATA_DIR    = data_dir("daily_tickers")
SYNTH_CSV   = os.path.join(_ROOT, "data", "wrds", "fred_rates_synthetic.csv")
RESULTS_DIR = os.path.join(_FILE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

print("=" * 70)
print("YIELD CURVE DURATION -- Multi-Asset Timing Backtest")
print("=" * 70)

# ---------- Load synthetic FRED data -----------------------------------------
print("\nLoading synthetic yield curve data from:", SYNTH_CSV)
if not os.path.exists(SYNTH_CSV):
    raise FileNotFoundError("Run data/build_synthetic_fred.py first: " + SYNTH_CSV)

fr = pd.read_csv(SYNTH_CSV, parse_dates=["date"]).set_index("date").sort_index()
fr = fr[(fr.index >= START_DATE) & (fr.index <= END_DATE)]

fr_m       = fr.resample("ME").last()
spread_lag = fr_m["t10y2y"].shift(1)

def classify_regime(spread):
    if pd.isna(spread): return "unknown"
    if spread > 0.5:    return "long"
    if spread < 0.0:    return "short"
    return "flat"

regime = spread_lag.map(classify_regime)
rc     = regime.value_counts().to_dict()
print("  T10Y2Y range: %.2f%% -> %.2f%%" % (fr_m["t10y2y"].min(), fr_m["t10y2y"].max()))
print("  Regimes (lagged 1m):", rc)
print("  Period: %s -> %s\n" % (fr_m.index[0].date(), fr_m.index[-1].date()))

# ---------- ETF loader -------------------------------------------------------
def load_monthly_close(ticker):
    path = os.path.join(DATA_DIR, "%s.csv" % ticker)
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if "close" not in df.columns or len(df) < 200:
            return None
        return df["close"].resample("ME").last()
    except Exception:
        return None

# ---------- Per-instrument significance test ---------------------------------
def run_instrument(ticker, etf_monthly, fav_regime):
    etf_ret  = etf_monthly.pct_change().dropna()
    tc_rt    = 2 * TC_BPS_OW / 10_000
    common   = etf_ret.index.intersection(regime.index)
    r        = etf_ret.loc[common]
    g        = regime.loc[common]
    hold_ret = r[g == fav_regime].dropna()
    if len(hold_ret) < 10:
        return None, []
    net_ret = hold_ret - tc_rt
    tt  = ttest_returns(net_ret)
    bs  = bootstrap_sharpe(net_ret)
    pmt = permutation_test(net_ret)
    gates_pass = int(tt["significant"]) + int(bs["significant"]) + int(pmt["significant"])
    sharpe_ann = (net_ret.mean() / net_ret.std() * np.sqrt(12)
                  if net_ret.std() > 0 else 0.0)
    trades = []
    for dt, ret in hold_ret.items():
        idx = etf_monthly.index.get_loc(dt)
        ep  = float(etf_monthly.iloc[idx - 1]) if idx > 0 else 100.0
        xp  = float(etf_monthly.loc[dt])
        trades.append({
            "entry_time":       etf_monthly.index[max(idx - 1, 0)],
            "exit_time":        dt,
            "direction":        "long",
            "instrument":       ticker,
            "entry_price":      round(ep, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(float(ret), 6),
            "regime":           fav_regime,
            "t10y2y":           round(float(spread_lag.get(dt, float("nan"))), 4),
        })
    return {
        "ticker":         ticker,
        "fav_regime":     fav_regime,
        "n_hold_months":  len(hold_ret),
        "sharpe":         round(float(sharpe_ann), 4),
        "t_stat":         round(float(tt["t_stat"]), 4),
        "t_p":            round(float(tt["p_value"]), 4),
        "boot_p5":        round(float(bs["ci_lower"]), 4),
        "perm_p":         round(float(pmt["p_value"]), 4),
        "mean_ret_pct":   round(float(net_ret.mean() * 100), 4),
        "gates_pass":     gates_pass,
        "verdict":        "PASS" if gates_pass >= 2 else "FAIL",
    }, trades

# ---------- Main loop --------------------------------------------------------
print("  %-6s  %-7s  %6s  %7s  %5s  Verdict" % ("Ticker","Regime","n_hold","Sharpe","Gates"))
print("  " + "-" * 50)

all_results, all_trades = [], []
for ticker in BASKET:
    monthly = load_monthly_close(ticker)
    if monthly is None:
        print("  %-6s  --       SKIP (no data)" % ticker)
        continue
    fav = REGIME_MAP.get(ticker, "long")
    m, trades = run_instrument(ticker, monthly, fav)
    if m is None:
        print("  %-6s  %-7s  SKIP (<10 hold months)" % (ticker, fav))
        continue
    all_results.append(m)
    all_trades.extend(trades)
    star = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print("  %-6s  %-7s  %6d  %7.3f  [%d/3]  %s %s" % (
        ticker, fav, m["n_hold_months"], m["sharpe"], m["gates_pass"], m["verdict"], star))

# ---------- Save results -----------------------------------------------------
results_df = pd.DataFrame(all_results)
csv_path   = os.path.join(RESULTS_DIR, "yield_curve_duration_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

trades_df = pd.DataFrame(all_trades)
if not trades_df.empty:
    trades_df.to_csv(os.path.join(RESULTS_DIR, "yield_curve_duration_multiasset_trades.csv"), index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
strong  = results_df[results_df["gates_pass"] == 3]["ticker"].tolist() if not results_df.empty else []
print("\n  Passing (>=2/3 gates): %s" % passing)
print("  Strong  ( 3/3 gates): %s" % strong)

summary = {
    "strategy":           STRATEGY_NAME,
    "period":             "%s -> %s" % (START_DATE, END_DATE),
    "tc_bps_one_way":     TC_BPS_OW,
    "canonical_params":   {"signal": "T10Y2Y", "lag_months": 1, "rebal": "month-end",
                           "regimes": {"long": ">0.5%", "flat": "0-0.5%", "short": "<0%"}},
    "regime_counts":      rc,
    "data_note":          "FRED synthetic: IEF/BIL/TLT price-derived yields (2016+)",
    "baskets_tested":     {"bonds_us": BASKET},
    "passing_instruments": passing,
    "strong_instruments":  strong,
    "n_instruments":       len(all_results),
    "per_instrument":      {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                            for r in all_results},
}
json_path = os.path.join(RESULTS_DIR, "yield_curve_duration_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print("\n  CSV  ->", csv_path)
print("  JSON ->", json_path)
print("\n" + "=" * 70 + "\nDone.\n" + "=" * 70)
