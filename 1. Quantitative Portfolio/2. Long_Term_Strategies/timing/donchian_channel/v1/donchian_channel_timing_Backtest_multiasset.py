# -*- coding: utf-8 -*-
"""
Donchian Channel — Multi-Asset Timing Backtest
===============================================
Tests the Donchian breakout timing signal on individual ETFs across
us_equity_broad + us_sectors + us_factor baskets.

Canonical params (from donchian_channel_summary.json):
  channel_period = 20, min_hold_days = 30, stop_loss = -0.08

Signal:
  Entry : close > highest close of last channel_period days (breakout)
  Exit  : close < lowest close of last channel_period days, OR
          pct_return < stop_loss, OR days_held >= min_hold_days (profit take)

Per-instrument: compute Sharpe + 3-gate significance (t-test, bootstrap, permutation).
Instruments passing 2/3 or 3/3 gates → included in Implementation as sleeves.

Outputs
-------
  results/donchian_channel_multiasset_per_instrument.csv
  results/donchian_channel_multiasset_summary.json
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

STRATEGY_NAME    = "Donchian Channel (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical params
CHANNEL_PERIOD = 20
MIN_HOLD_DAYS  = 30
STOP_LOSS      = -0.08

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
    "us_factor":       ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"],
}

print("=" * 75)
print("DONCHIAN CHANNEL — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"Canonical: channel_period={CHANNEL_PERIOD}, min_hold={MIN_HOLD_DAYS}, "
      f"stop_loss={STOP_LOSS}")
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


def generate_donchian_trades(df, channel_period, min_hold_days, stop_loss):
    """
    Donchian breakout: entry on close > N-day high (trend-following).
    Exit on: close < N-day low, OR stop_loss hit, OR held >= min_hold_days + new signal.
    """
    close = df["close"]
    roll_high = close.shift(1).rolling(channel_period).max()
    roll_low  = close.shift(1).rolling(channel_period).min()

    trades = []
    in_trade = False
    entry_date = entry_price = entry_idx = None

    for i in range(channel_period + 1, len(df)):
        today  = df.index[i]
        cp     = float(close.iloc[i])
        rl     = float(roll_low.iloc[i])

        if not in_trade:
            rh = float(roll_high.iloc[i])
            if not pd.isna(rh) and cp > rh:
                ep          = df["open"].iloc[i] if "open" in df.columns else cp
                if pd.isna(ep):
                    ep = cp
                in_trade    = True
                entry_date  = today
                entry_price = float(ep)
                entry_idx   = i
        else:
            days_held = i - entry_idx
            pct_ret   = (cp - entry_price) / entry_price if entry_price else 0.0
            exit_reason = None

            if pct_ret <= stop_loss:
                exit_reason = "stop_loss"
            elif not pd.isna(rl) and cp < rl and days_held >= min_hold_days:
                exit_reason = "lower_channel"
            elif days_held >= min_hold_days * 3:
                exit_reason = "max_hold"

            if exit_reason:
                trades.append({
                    "entry_time":       entry_date,
                    "exit_time":        today,
                    "direction":        "long",
                    "instrument":       "ETF",
                    "entry_price":      round(entry_price, 4),
                    "exit_price":       round(cp, 4),
                    "pct_return_gross": round(pct_ret, 6),
                    "exit_reason":      exit_reason,
                    "stop_price":       round(entry_price * (1 + stop_loss), 4),
                })
                in_trade = False

    # Force-close at end
    if in_trade and entry_price is not None:
        cp  = float(close.iloc[-1])
        pct = (cp - entry_price) / entry_price
        trades.append({
            "entry_time":       entry_date,
            "exit_time":        df.index[-1],
            "direction":        "long",
            "instrument":       "ETF",
            "entry_price":      round(entry_price, 4),
            "exit_price":       round(cp, 4),
            "pct_return_gross": round(pct, 6),
            "exit_reason":      "end_of_data",
            "stop_price":       round(entry_price * (1 + stop_loss), 4),
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
    df = load_ohlc(ticker)
    if df is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (no data)")
        continue
    trades = generate_donchian_trades(df, CHANNEL_PERIOD, MIN_HOLD_DAYS, STOP_LOSS)
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
csv_path   = os.path.join(RESULTS_DIR, "donchian_channel_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {"channel_period": CHANNEL_PERIOD,
                          "min_hold_days": MIN_HOLD_DAYS,
                          "stop_loss":     STOP_LOSS},
    "baskets_tested":         BASKETS,
    "n_instruments":          len(results),
    "passing_instruments":    passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "donchian_channel_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {csv_path}")
print(f"  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")
