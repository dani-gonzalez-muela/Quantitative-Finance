# -*- coding: utf-8 -*-
"""
Bollinger Band — Multi-Asset Timing Backtest
=============================================
Tests the BB mean-reversion timing signal on individual ETFs across
us_equity_broad + us_sectors + us_factor baskets.

Canonical params (from bollinger_band_summary.json):
  bb_period = 30, bb_std = 2.0, min_hold_days = 30

Signal:
  Entry : next open after close <= lower band (lower = SMA - bb_std * σ)
  Exit  : close >= upper band AND days_held >= min_hold_days

Per-instrument: compute Sharpe + 3-gate significance (t-test, bootstrap, permutation).
Instruments passing 2/3 or 3/3 gates → included in Implementation as sleeves.

Outputs
-------
  results/bollinger_band_multiasset_per_instrument.csv
  results/bollinger_band_multiasset_summary.json
"""

import sys, os

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "Bollinger Band (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical params
BB_PERIOD     = 30
BB_STD        = 2.0
MIN_HOLD_DAYS = 30

DATA_DIR    = os.path.join(_ROOT, "long_term", "multi_asset_expansion", "data", "tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
    "us_factor":       ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"],
}

print("=" * 75)
print("BOLLINGER BAND — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"Canonical: bb_period={BB_PERIOD}, bb_std={BB_STD}, min_hold={MIN_HOLD_DAYS}")
print(f"Period   : {START_DATE} → {END_DATE}\n")


def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns:
            return None
        return df
    except Exception:
        return None


def generate_bb_trades(df, bb_period, bb_std, min_hold_days):
    """BB mean-reversion: entry on open after close ≤ lower band; exit on close ≥ upper band."""
    close  = df["close"]
    sma    = close.rolling(bb_period).mean()
    sigma  = close.rolling(bb_period).std()
    upper  = sma + bb_std * sigma
    lower  = sma - bb_std * sigma

    trades = []
    in_trade = False
    entry_date = entry_price = entry_idx = None

    for i in range(1, len(df)):
        today = df.index[i]
        prev  = df.index[i-1]

        if not in_trade:
            if close.iloc[i-1] <= lower.iloc[i-1] and not pd.isna(lower.iloc[i-1]):
                ep = df["open"].iloc[i] if "open" in df.columns else close.iloc[i]
                if pd.isna(ep):
                    ep = close.iloc[i]
                in_trade    = True
                entry_date  = today
                entry_price = ep
                entry_idx   = i
        else:
            days_held = i - entry_idx
            if days_held >= min_hold_days and close.iloc[i] >= upper.iloc[i] and not pd.isna(upper.iloc[i]):
                xp = close.iloc[i]
                trades.append({
                    "entry_time":       entry_date,
                    "exit_time":        today,
                    "direction":        "long",
                    "instrument":       df.columns[0] if len(df.columns) > 0 else "ETF",
                    "entry_price":      round(float(entry_price), 4),
                    "exit_price":       round(float(xp), 4),
                    "pct_return_gross": round(float((xp - entry_price) / entry_price), 6),
                    "exit_reason":      "upper_band",
                    "stop_price":       np.nan,
                })
                in_trade = False

    # Force-close open trade at end
    if in_trade and entry_price is not None:
        xp = close.iloc[-1]
        trades.append({
            "entry_time":       entry_date,
            "exit_time":        df.index[-1],
            "direction":        "long",
            "instrument":       "ETF",
            "entry_price":      round(float(entry_price), 4),
            "exit_price":       round(float(xp), 4),
            "pct_return_gross": round(float((xp - entry_price) / entry_price), 6),
            "exit_reason":      "end_of_data",
            "stop_price":       np.nan,
        })
    return pd.DataFrame(trades)


def instrument_metrics(trades, ticker):
    """Compute Sharpe + 3-gate tests from trades."""
    if trades.empty or len(trades) < 5:
        return None

    tc_rt     = 2 * TC_BPS_OW / 10_000
    r_arr     = np.array(trades["pct_return_gross"] - tc_rt)

    # Calendar days between trades
    dur_days  = (trades["exit_time"] - trades["entry_time"]).dt.days.mean()
    ppy       = max(1.0, 365.0 / dur_days) if dur_days > 0 else 12

    sharpe = float(r_arr.mean() / r_arr.std() * np.sqrt(ppy)) if r_arr.std() > 0 else 0.0

    from long_term._backtest_utils import ttest_returns
    r_series = pd.Series(r_arr, index=trades["entry_time"].values)
    tt   = ttest_returns(r_series)

    rng  = np.random.RandomState(42)
    bs   = [rng.choice(r_arr, size=len(r_arr), replace=True) for _ in range(1000)]
    ann  = np.sqrt(ppy)
    bp5  = float(np.percentile([b.mean()/b.std()*ann if b.std()>0 else 0.0 for b in bs], 5))

    rng2 = np.random.RandomState(42)
    abs_r = np.abs(r_arr); cnt = 0
    for _ in range(1000):
        sh2 = abs_r * rng2.choice([-1,1], size=len(abs_r))
        if (sh2.mean()/sh2.std()*ann if sh2.std()>0 else 0.0) >= sharpe: cnt += 1
    perm_p = cnt / 1000

    n_pass = int(tt["significant"]) + int(bp5 > 0) + int(perm_p < 0.05)

    return {
        "ticker":    ticker,
        "n_trades":  len(trades),
        "sharpe":    round(float(sharpe), 4),
        "t_stat":    round(float(tt["t_stat"]), 4),
        "t_p":       round(float(tt["p_value"]), 4),
        "boot_p5":   round(float(bp5), 4),
        "perm_p":    round(float(perm_p), 4),
        "gates_pass": n_pass,
        "verdict":   "PASS" if n_pass >= 2 else "FAIL",
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
    df = load_ohlc(ticker)
    if df is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (no data)")
        continue
    # Store instrument name in df for use in trades
    trades = generate_bb_trades(df, BB_PERIOD, BB_STD, MIN_HOLD_DAYS)
    if trades.empty:
        trades["instrument"] = ticker
    else:
        trades["instrument"] = ticker

    m = instrument_metrics(trades, ticker)
    if m is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (<5 trades)")
        continue
    m["basket"] = basket_name
    results.append(m)
    verdict_str = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print(f"  {ticker:<8}  {basket_name:<15}  {m['n_trades']:>8}  "
          f"{m['sharpe']:>7.3f}  [{m['gates_pass']}/3]  {m['verdict']} {verdict_str}")

# ── Save outputs ──────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)

results_df = pd.DataFrame(results)
csv_path   = os.path.join(RESULTS_DIR, "bollinger_band_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {"bb_period": BB_PERIOD, "bb_std": BB_STD, "min_hold_days": MIN_HOLD_DAYS},
    "baskets_tested": BASKETS,
    "n_instruments":  len(results),
    "passing_instruments": passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "bollinger_band_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {csv_path}")
print(f"  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")
