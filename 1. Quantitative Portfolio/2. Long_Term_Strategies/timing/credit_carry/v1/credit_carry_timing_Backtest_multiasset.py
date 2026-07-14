# -*- coding: utf-8 -*-
"""
Credit Carry — Multi-Asset Timing Backtest
==========================================
Tests the credit carry timing signal on individual ETFs in the bonds_us basket.

Original signal (credit_carry_Backtest.py):
  Binary switch: hold HYG-like bonds when their 12m return > treasury proxy 12m return;
  else hold treasury proxy.
  Reference: carry = credit premium (IG bonds earn more than Treasuries over time).

Multi-asset adaptation:
  Benchmark = IEF (7-10yr Treasuries; the main "risk-free" bond proxy in the basket).
  For each non-IEF ETF in bonds_us, each month:
    signal = 1 if ETF 12m return > IEF 12m return (better carry), else 0
  "Trade" = monthly hold when signal = 1.
  Test per-instrument: does holding the ETF when it beats IEF 12m return produce
  significantly positive returns?

Note: Using a "conditional hold" frame: we test whether the periods where the ETF
  wins vs IEF have positive returns (not versus IEF — just vs zero).
  This avoids compounding the L/S comparison with the multiasset expansion.

Canonical: mom_window_months = 12 (from credit_carry PARAMS).

Outputs
-------
  results/credit_carry_multiasset_per_instrument.csv
  results/credit_carry_multiasset_summary.json
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

STRATEGY_NAME    = "Credit Carry (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical params
MOM_WINDOW = 12   # months — comparison window vs IEF

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "bonds_us": ["TLT","IEF","SHY","TIP","BIL","LQD","HYG"],
}

BENCHMARK_TICKER = "IEF"   # 7-10yr Treasury as credit carry benchmark

print("=" * 75)
print("CREDIT CARRY — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"Canonical: mom_window={MOM_WINDOW}m, benchmark={BENCHMARK_TICKER}")
print(f"Signal   : hold ETF when its {MOM_WINDOW}m return > {BENCHMARK_TICKER} {MOM_WINDOW}m return")
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
        return df["close"].resample("ME").last()
    except Exception:
        return None


# ── Load benchmark ────────────────────────────────────────────────────────────
print(f"Loading benchmark ({BENCHMARK_TICKER})...")
bench_monthly = load_close(BENCHMARK_TICKER)
if bench_monthly is None:
    print(f"  ERROR: {BENCHMARK_TICKER} data not found. Cannot run signal.")
    bench_momentum = None
else:
    bench_momentum = bench_monthly.pct_change(MOM_WINDOW).shift(1)  # skip-1 bias
    print(f"  Benchmark: {len(bench_monthly)} monthly observations")


def generate_credit_trades(etf_monthly, bench_mom, ticker, mom_window):
    """
    Each month: hold ETF if ETF mom_window-m return (skip-1) > benchmark.
    One 'trade' per hold-month.
    """
    etf_ret     = etf_monthly.pct_change()
    etf_mom     = etf_monthly.pct_change(mom_window).shift(1)  # skip-1

    trades = []
    for i in range(1, len(etf_monthly)):
        d = etf_monthly.index[i]
        d_prev = etf_monthly.index[i-1]
        em = etf_mom.get(d, np.nan)
        bm = bench_mom.get(d, np.nan) if bench_mom is not None else np.nan

        if pd.isna(em) or pd.isna(bm):
            continue

        signal = 1 if em > bm else 0
        if signal == 0:
            continue

        raw_ret = float(etf_ret.iloc[i]) if not pd.isna(etf_ret.iloc[i]) else 0.0
        ep  = float(etf_monthly.iloc[i-1])
        xp  = float(etf_monthly.iloc[i])

        trades.append({
            "entry_time":       d_prev,
            "exit_time":        d,
            "direction":        "long",
            "instrument":       ticker,
            "entry_price":      round(ep, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(raw_ret, 6),
            "etf_mom":          round(float(em), 6),
            "bench_mom":        round(float(bm), 6),
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
        "ticker":      ticker,
        "n_hold_months": len(trades),
        "sharpe":      round(float(sharpe), 4),
        "t_stat":      round(float(tt["t_stat"]), 4),
        "t_p":         round(float(tt["p_value"]), 4),
        "boot_p5":     round(float(bp5), 4),
        "perm_p":      round(float(perm_p), 4),
        "gates_pass":  n_pass,
        "verdict":     "PASS" if n_pass >= 2 else "FAIL",
    }


# ── Run per instrument ────────────────────────────────────────────────────────
all_tickers = [t for t in BASKETS["bonds_us"] if t != BENCHMARK_TICKER]

print(f"Testing {len(all_tickers)} instruments (excluding benchmark {BENCHMARK_TICKER})...\n")
print(f"  {'Ticker':<8}  {'Basket':<12}  {'n_hold':>7}  {'Sharpe':>7}  {'Gates':>5}  Verdict")
print(f"  {'-'*60}")

results = []
for ticker in all_tickers:
    basket_name = "bonds_us"
    etf_monthly = load_close(ticker)
    if etf_monthly is None:
        print(f"  {ticker:<8}  {basket_name:<12}  SKIP (no data)")
        continue
    if bench_monthly is None:
        print(f"  {ticker:<8}  {basket_name:<12}  SKIP (no benchmark)")
        continue

    trades = generate_credit_trades(etf_monthly, bench_momentum, ticker, MOM_WINDOW)
    m = instrument_metrics(trades, ticker)
    if m is None:
        print(f"  {ticker:<8}  {basket_name:<12}  SKIP (<12 hold months)")
        continue
    m["basket"] = basket_name
    results.append(m)
    v = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print(f"  {ticker:<8}  {basket_name:<12}  {m['n_hold_months']:>7}  "
          f"{m['sharpe']:>7.3f}  [{m['gates_pass']}/3]  {m['verdict']} {v}")

# ── Save outputs ──────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)

results_df = pd.DataFrame(results)
csv_path   = os.path.join(RESULTS_DIR, "credit_carry_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {"mom_window_months": MOM_WINDOW, "benchmark": BENCHMARK_TICKER},
    "signal_note":    f"Hold ETF when its {MOM_WINDOW}m return (skip-1) > {BENCHMARK_TICKER} {MOM_WINDOW}m return",
    "baskets_tested":      BASKETS,
    "n_instruments":       len(results),
    "passing_instruments": passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "credit_carry_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {csv_path}")
print(f"  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")
