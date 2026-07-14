# -*- coding: utf-8 -*-
"""
Sentiment Timing (VIX) — Multi-Asset Timing Backtest
=====================================================
Tests the VIX-regime sizing signal on individual ETFs across
us_equity_broad + us_sectors baskets.

Signal (canonical from sentiment_timing_Backtest.py):
  VIX > 25 (fear)      → 150% exposure (contrarian overweight)
  VIX < 15 (complacency) → 50%  exposure (contrarian underweight)
  15 ≤ VIX ≤ 25       → 100% exposure (neutral)
  Reference: Baker & Wurgler (2006); Da, Engelberg & Gao (2015).

Data: CBOE VIX from data/wrds/15_cboe_vix.parquet (duckdb).
      ETF daily close from long_term/multi_asset_expansion/data/tickers/.

Per-instrument "trades": monthly periods, each sized by avg monthly VIX regime.
3-gate significance on VIX-sized monthly returns vs uninvested (sized=0 periods excluded).

Outputs
-------
  results/sentiment_timing_multiasset_per_instrument.csv
  results/sentiment_timing_multiasset_summary.json
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
import duckdb

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "Sentiment Timing VIX (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical VIX thresholds
VIX_LOW  = 15.0   # below → 50% exposure
VIX_HIGH = 25.0   # above → 150% exposure
EXP_LOW  = 0.50
EXP_MID  = 1.00
EXP_HIGH = 1.50

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
DATA_DIR     = data_dir('daily_tickers')
VIX_PARQUET  = os.path.join(_ROOT, "data", "wrds", "15_cboe_vix.parquet")
OUTPUT_BASE  = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
}

print("=" * 75)
print("SENTIMENT TIMING (VIX) — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"VIX thresholds: <{VIX_LOW} → {EXP_LOW}x; [{VIX_LOW},{VIX_HIGH}] → {EXP_MID}x; "
      f">{VIX_HIGH} → {EXP_HIGH}x")
print(f"Period: {START_DATE} → {END_DATE}\n")


# ── Load VIX ────────────────────────────────────────────────────────────────
def load_vix():
    con = duckdb.connect()
    try:
        vix = con.execute(
            f"SELECT date, vix_close FROM read_parquet('{VIX_PARQUET}') ORDER BY date"
        ).fetchdf()
        vix["date"] = pd.to_datetime(vix["date"])
        vix = vix.set_index("date").sort_index()
        vix = vix[(vix.index >= START_DATE) & (vix.index <= END_DATE)]
        return vix["vix_close"]
    except Exception as e:
        # Try column name variants
        cols = con.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name='read_parquet'").fetchdf() if False else None
        df = con.execute(
            f"SELECT * FROM read_parquet('{VIX_PARQUET}') LIMIT 5").fetchdf()
        date_col  = [c for c in df.columns if "date" in c.lower()][0]
        vix_col   = [c for c in df.columns if "vix" in c.lower() or "close" in c.lower()][-1]
        vix = con.execute(
            f"SELECT {date_col}, {vix_col} FROM read_parquet('{VIX_PARQUET}') ORDER BY {date_col}"
        ).fetchdf()
        vix["date"] = pd.to_datetime(vix[date_col])
        vix = vix.set_index("date").sort_index()
        vix = vix[(vix.index >= START_DATE) & (vix.index <= END_DATE)]
        return vix[vix_col]


print("Loading VIX...")
try:
    vix_daily = load_vix()
    print(f"  VIX loaded: {len(vix_daily)} daily observations, "
          f"{vix_daily.index.min().date()} → {vix_daily.index.max().date()}")
except Exception as e:
    print(f"  ERROR loading VIX: {e}")
    vix_daily = None


def vix_exposure(vix_val):
    if pd.isna(vix_val):
        return EXP_MID
    if vix_val < VIX_LOW:
        return EXP_LOW
    elif vix_val > VIX_HIGH:
        return EXP_HIGH
    else:
        return EXP_MID


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


def generate_vix_trades(close, vix_daily):
    """
    Monthly periods: for each month, compute plain return,
    then scale by avg VIX exposure for that month.
    Each month = one 'trade' with vix-scaled return.
    """
    monthly = close.resample("ME").last()
    monthly_ret = monthly.pct_change().dropna()

    if vix_daily is None:
        return pd.DataFrame()

    # Monthly avg VIX → exposure
    monthly_vix = vix_daily.resample("ME").mean()

    trades = []
    for i in range(len(monthly_ret)):
        period_end = monthly_ret.index[i]
        if i == 0:
            continue
        period_start = monthly_ret.index[i-1]

        vix_val = float(monthly_vix.get(period_end, EXP_MID * 15))
        exp     = vix_exposure(vix_val)
        raw_ret = float(monthly_ret.iloc[i])
        sized_ret = raw_ret * exp

        trades.append({
            "entry_time":       period_start,
            "exit_time":        period_end,
            "direction":        "long",
            "instrument":       "ETF",
            "entry_price":      round(float(monthly.iloc[i-1]), 4),
            "exit_price":       round(float(monthly.iloc[i]), 4),
            "pct_return_gross": round(float(sized_ret), 6),
            "raw_return":       round(float(raw_ret), 6),
            "vix_exposure":     exp,
            "exit_reason":      "month_end",
            "stop_price":       np.nan,
        })
    return pd.DataFrame(trades)


def instrument_metrics(trades, ticker):
    if trades.empty or len(trades) < 12:
        return None

    tc_rt = 2 * TC_BPS_OW / 10_000
    r_arr = np.array(trades["pct_return_gross"] - tc_rt)
    ppy   = 12.0

    sharpe = float(r_arr.mean() / r_arr.std() * np.sqrt(ppy)) if r_arr.std() > 0 else 0.0

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

    # Also compute unscaled Sharpe for reference
    if "raw_return" in trades.columns:
        r_raw  = np.array(trades["raw_return"] - tc_rt)
        sh_raw = float(r_raw.mean() / r_raw.std() * np.sqrt(ppy)) if r_raw.std() > 0 else 0.0
    else:
        sh_raw = sharpe

    n_pass = int(tt["significant"]) + int(bp5 > 0) + int(perm_p < 0.05)

    return {
        "ticker":          ticker,
        "n_months":        len(trades),
        "sharpe_vix_sized": round(float(sharpe), 4),
        "sharpe_raw":       round(float(sh_raw), 4),
        "t_stat":           round(float(tt["t_stat"]), 4),
        "t_p":              round(float(tt["p_value"]), 4),
        "boot_p5":          round(float(bp5), 4),
        "perm_p":           round(float(perm_p), 4),
        "gates_pass":       n_pass,
        "verdict":          "PASS" if n_pass >= 2 else "FAIL",
    }


# ── Run per instrument ────────────────────────────────────────────────────────
all_tickers = []
for basket, tickers in BASKETS.items():
    for t in tickers:
        if t not in all_tickers:
            all_tickers.append(t)

print(f"\nTesting {len(all_tickers)} instruments...\n")
print(f"  {'Ticker':<8}  {'Basket':<15}  {'n_mo':>5}  {'Sh(vix)':>8}  "
      f"{'Sh(raw)':>7}  {'Gates':>5}  Verdict")
print(f"  {'-'*70}")

results = []
for ticker in all_tickers:
    basket_name = next((b for b, ts in BASKETS.items() if ticker in ts), "unknown")
    close = load_close(ticker)
    if close is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (no data)")
        continue
    trades = generate_vix_trades(close, vix_daily)
    if trades.empty:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (no VIX data or no trades)")
        continue
    trades["instrument"] = ticker

    m = instrument_metrics(trades, ticker)
    if m is None:
        print(f"  {ticker:<8}  {basket_name:<15}  SKIP (<12 months)")
        continue
    m["basket"] = basket_name
    results.append(m)
    v = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print(f"  {ticker:<8}  {basket_name:<15}  {m['n_months']:>5}  "
          f"{m['sharpe_vix_sized']:>8.3f}  {m['sharpe_raw']:>7.3f}  "
          f"[{m['gates_pass']}/3]  {m['verdict']} {v}")

# ── Save outputs ──────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)

results_df = pd.DataFrame(results)
csv_path   = os.path.join(RESULTS_DIR, "sentiment_timing_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {
        "vix_low":    VIX_LOW,
        "vix_high":   VIX_HIGH,
        "exp_low":    EXP_LOW,
        "exp_mid":    EXP_MID,
        "exp_high":   EXP_HIGH,
    },
    "baskets_tested":      BASKETS,
    "n_instruments":       len(results),
    "passing_instruments": passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "sentiment_timing_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {csv_path}")
print(f"  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")
