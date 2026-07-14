# -*- coding: utf-8 -*-
"""
Turn of Month — Multi-Asset Timing Backtest
===========================================
Tests the turn-of-month calendar signal on individual ETFs across
us_equity_broad + us_sectors baskets.

Signal (no free params — pure calendar):
  Invested: last 3 + first 3 trading days of each calendar month.
  Reference: Ariel (1987); Lakonishok & Smidt (1988).

Each "trade" = one TOM window (entry on close day-3 from month end,
exit on close day+3 from month start).

Per-instrument: compute Sharpe + 3-gate significance (t-test, bootstrap, permutation).
Instruments passing 2/3 or 3/3 gates → included in Implementation as sleeves.

Outputs
-------
  results/turn_of_month_multiasset_per_instrument.csv
  results/turn_of_month_multiasset_summary.json
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

STRATEGY_NAME    = "Turn of Month (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical params
N_DAYS_BEFORE = 3   # last N trading days of prior month
N_DAYS_AFTER  = 3   # first N trading days of new month

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
}

print("=" * 75)
print("TURN OF MONTH — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"Canonical: last_{N_DAYS_BEFORE} + first_{N_DAYS_AFTER} trading days of month")
print(f"Period   : {START_DATE} → {END_DATE}\n")


def load_close(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns:
            return None
        return df["close"]
    except Exception:
        return None


def build_tom_mask(dates, n_before, n_after):
    """Return bool Series: True on TOM days (last n_before + first n_after of month)."""
    df_idx   = pd.Series(range(len(dates)), index=dates)
    months   = dates.to_period("M")
    mask     = pd.Series(False, index=dates)

    for m in months.unique():
        m_days = dates[months == m]
        if len(m_days) == 0:
            continue
        # last n_before trading days of this month
        for d in m_days[-n_before:]:
            mask[d] = True
        # first n_after trading days of this month
        for d in m_days[:n_after]:
            mask[d] = True
    return mask


def generate_tom_trades(close, n_before, n_after):
    """
    Per-window trade: entry at close before TOM window starts,
    exit at close after TOM window ends.
    """
    dates  = close.index
    mask   = build_tom_mask(dates, n_before, n_after)
    tc_rt  = 2 * TC_BPS_OW / 10_000

    trades = []
    in_window = False
    entry_price = None
    entry_date  = None

    for i in range(1, len(dates)):
        prev = dates[i-1]
        today = dates[i]

        if not in_window and mask.iloc[i]:
            entry_price = float(close.iloc[i-1])  # entry at prior close
            entry_date  = today
            in_window   = True
        elif in_window and not mask.iloc[i]:
            xp = float(close.iloc[i-1])
            trades.append({
                "entry_time":       entry_date,
                "exit_time":        today,
                "direction":        "long",
                "instrument":       "ETF",
                "entry_price":      round(entry_price, 4),
                "exit_price":       round(xp, 4),
                "pct_return_gross": round((xp - entry_price) / entry_price, 6),
                "exit_reason":      "tom_window_end",
                "stop_price":       np.nan,
            })
            in_window = False

    # Force close if still in window
    if in_window and entry_price is not None:
        xp = float(close.iloc[-1])
        trades.append({
            "entry_time":       entry_date,
            "exit_time":        dates[-1],
            "direction":        "long",
            "instrument":       "ETF",
            "entry_price":      round(entry_price, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round((xp - entry_price) / entry_price, 6),
            "exit_reason":      "end_of_data",
            "stop_price":       np.nan,
        })
    return pd.DataFrame(trades)


def instrument_metrics(trades, ticker):
    if trades.empty or len(trades) < 5:
        return None

    tc_rt = 2 * TC_BPS_OW / 10_000
    r_arr = np.array(trades["pct_return_gross"] - tc_rt)

    dur_days = (trades["exit_time"] - trades["entry_time"]).dt.days.mean()
    ppy      = max(1.0, 365.0 / dur_days) if dur_days > 0 else 12

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
        "ticker":     ticker,
        "n_trades":   len(trades),
        "sharpe":     round(float(sharpe), 4),
        "t_stat":     round(float(tt["t_stat"]), 4),
        "t_p":        round(float(tt["p_value"]), 4),
        "boot_p5":    round(float(bp5), 4),
        "perm_p":     round(float(perm_p), 4),
        "gates_pass": n_pass,
        "verdict":    "PASS" if n_pass >= 2 else "FAIL",
    }


# ── Run per instrument ────────────────────────────────────────────────────────
all_tickers = []
for basket, tickers in BASKETS.items():
    for t in tickers:
        if t not in all_tickers:
            all_tickers.append(t)

print(f"Testing {len(all_tickers)} instruments...\n")
print(f"  {'Ticker':<8}  {'Basket':<15}  {'n_trades':>8}  {'Sharpe':>7}  {'Gates':>5}  Verdict")
print(f"  {'-'*65}")

results = []
for ticker in all_tickers:
    basket_name = next((b for b, ts in BASKETS.items() if ticker in ts), "unknown")
    close = load_close(ticker)
    if close is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (no data)")
        continue
    trades = generate_tom_trades(close, N_DAYS_BEFORE, N_DAYS_AFTER)
    if not trades.empty:
        trades["instrument"] = ticker

    m = instrument_metrics(trades, ticker)
    if m is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (<5 trades)")
        continue
    m["basket"] = basket_name
    results.append(m)
    v = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print(f"  {ticker:<8}  {basket_name:<15}  {m['n_trades']:>8}  "
          f"{m['sharpe']:>7.3f}  [{m['gates_pass']}/3]  {m['verdict']} {v}")

# ── Save outputs ──────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)

results_df = pd.DataFrame(results)
csv_path   = os.path.join(RESULTS_DIR, "turn_of_month_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {"n_days_before": N_DAYS_BEFORE, "n_days_after": N_DAYS_AFTER},
    "baskets_tested":         BASKETS,
    "n_instruments":          len(results),
    "passing_instruments":    passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "turn_of_month_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {csv_path}")
print(f"  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")
