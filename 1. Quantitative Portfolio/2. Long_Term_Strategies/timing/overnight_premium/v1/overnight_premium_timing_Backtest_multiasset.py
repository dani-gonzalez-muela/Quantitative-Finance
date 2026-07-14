# -*- coding: utf-8 -*-
"""
Overnight Premium — Multi-Asset Timing Backtest
===============================================
Tests the overnight-premium timing signal on individual ETFs across
us_equity_broad + us_sectors baskets.

Signal (canonical OVERNIGHT_FRAC=0.65):
  For each trading day, overnight return = open_t / close_{t-1} - 1.
  From Cooper et al. (2008): ~65% of long-run equity return earned overnight.
  Strategy: always hold close→next open; cash during intraday (open→close).
  Each "trade" = one overnight hold (close to next open).

Per-instrument significance test:
  - Compute overnight return series for each ETF
  - 3-gate test: t-test mean > 0, bootstrap Sharpe 5th pct > 0, permutation p < 0.05
  Note: no explicit OVERNIGHT_FRAC applied to ETF returns — we test whether the
  raw overnight edge exists (ETF prices already embed dividend reinvestment).

Outputs
-------
  results/overnight_premium_multiasset_per_instrument.csv
  results/overnight_premium_multiasset_summary.json
"""

import sys, os

import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d)
    assert _p != _d, ".project_root marker not found - place it at the algo_trading root"
    _d = _p
_ROOT = _d
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "Overnight Premium (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical params
OVERNIGHT_FRAC = 0.65   # documented fraction; used as reference, not applied to filter

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
}

print("=" * 75)
print("OVERNIGHT PREMIUM — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"Canonical: overnight_frac={OVERNIGHT_FRAC} (Cooper et al. 2008)")
print(f"Signal   : close_t-1 → open_t return (each day is one trade)")
print(f"Period   : {START_DATE} → {END_DATE}\n")


def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns or "open" not in df.columns:
            return None
        return df
    except Exception:
        return None


def compute_overnight_returns(df):
    """overnight return = open_t / close_{t-1} - 1 for each day."""
    close = df["close"]
    open_ = df["open"]
    overnight = open_ / close.shift(1) - 1
    overnight = overnight.dropna()
    # each observation is a "trade": entry at prior close, exit at today's open
    trades = []
    dates  = overnight.index
    for i in range(len(overnight)):
        if pd.isna(overnight.iloc[i]):
            continue
        entry_date = df.index[i]      # prior close date
        exit_date  = dates[i]         # today (open)
        ep = float(close.iloc[i])
        xp = float(open_.loc[exit_date])
        if ep <= 0 or xp <= 0:
            continue
        trades.append({
            "entry_time":       entry_date,
            "exit_time":        exit_date,
            "direction":        "long",
            "instrument":       "ETF",
            "entry_price":      round(ep, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(float(overnight.iloc[i]), 6),
            "exit_reason":      "next_open",
            "stop_price":       np.nan,
        })
    return pd.DataFrame(trades)


def instrument_metrics(trades, ticker):
    if trades.empty or len(trades) < 50:
        return None

    tc_rt = 2 * TC_BPS_OW / 10_000
    # Overnight hold is ~1 day; TC matters but at 5bps per trip it's small per day
    r_arr = np.array(trades["pct_return_gross"] - tc_rt)

    # Trades are 1-day (overnight), so ~252 per year
    ppy = 252.0

    sharpe = float(r_arr.mean() / r_arr.std() * np.sqrt(ppy)) if r_arr.std() > 0 else 0.0

    from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns
    r_series = pd.Series(r_arr, index=trades["entry_time"].values)
    tt  = ttest_returns(r_series)

    rng = np.random.RandomState(42)
    ann = np.sqrt(ppy)
    bs  = [rng.choice(r_arr, size=len(r_arr), replace=True) for _ in range(1000)]
    bp5 = float(np.percentile([b.mean()/b.std()*ann if b.std()>0 else 0.0 for b in bs], 5))

    rng2  = np.random.RandomState(42)
    abs_r = np.abs(r_arr); cnt = 0
    for _ in range(1000):
        sh2 = abs_r * rng2.choice([-1,1], size=len(abs_r))
        if (sh2.mean()/sh2.std()*ann if sh2.std()>0 else 0.0) >= sharpe: cnt += 1
    perm_p = cnt / 1000

    n_pass = int(tt["significant"]) + int(bp5 > 0) + int(perm_p < 0.05)

    return {
        "ticker":       ticker,
        "n_trades":     len(trades),
        "mean_ret_bps": round(float(r_arr.mean()) * 10000, 2),
        "sharpe":       round(float(sharpe), 4),
        "t_stat":       round(float(tt["t_stat"]), 4),
        "t_p":          round(float(tt["p_value"]), 4),
        "boot_p5":      round(float(bp5), 4),
        "perm_p":       round(float(perm_p), 4),
        "gates_pass":   n_pass,
        "verdict":      "PASS" if n_pass >= 2 else "FAIL",
    }


# ── Run per instrument ────────────────────────────────────────────────────────
all_tickers = []
for basket, tickers in BASKETS.items():
    for t in tickers:
        if t not in all_tickers:
            all_tickers.append(t)

print(f"Testing {len(all_tickers)} instruments...\n")
print(f"  {'Ticker':<8}  {'Basket':<15}  {'n_days':>7}  {'Sharpe':>7}  "
      f"{'mean(bps)':>9}  {'Gates':>5}  Verdict")
print(f"  {'-'*72}")

results = []
for ticker in all_tickers:
    basket_name = next((b for b, ts in BASKETS.items() if ticker in ts), "unknown")
    df = load_ohlc(ticker)
    if df is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (no data)")
        continue
    trades = compute_overnight_returns(df)
    if not trades.empty:
        trades["instrument"] = ticker

    m = instrument_metrics(trades, ticker)
    if m is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (<50 obs)")
        continue
    m["basket"] = basket_name
    results.append(m)
    v = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print(f"  {ticker:<8}  {basket_name:<15}  {m['n_trades']:>7}  "
          f"{m['sharpe']:>7.3f}  {m['mean_ret_bps']:>9.2f}  [{m['gates_pass']}/3]  "
          f"{m['verdict']} {v}")

# ── Save outputs ──────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)

results_df = pd.DataFrame(results)
csv_path   = os.path.join(RESULTS_DIR, "overnight_premium_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {"overnight_frac_reference": OVERNIGHT_FRAC},
    "signal_note":    "Each ETF daily close→next open is one trade; test mean > 0",
    "baskets_tested":      BASKETS,
    "n_instruments":       len(results),
    "passing_instruments": passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "overnight_premium_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {csv_path}")
print(f"  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")
