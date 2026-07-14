# -*- coding: utf-8 -*-
"""
Overnight Premium — Multi-Asset Timing Backtest v2
===================================================
Rigorous v2 framework for the overnight-premium timing strategy.

Signal: buy at close_t, sell at open_{t+1}  (one overnight trade per day).
No grid hyperparameters — signal is fixed. "Grid" has 1 combo.

Per-basket binomial test:
  N = number of instruments in basket
  k = instruments passing ≥ 2/3 significance gates
  P(Binomial(N, 0.05) >= k) for "STRATEGY EXISTS"

n_boot = 500 for speed.

Outputs
-------
  results/overnight_premium_v2_multiasset_summary.json
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
from scipy.stats import binom

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "Overnight Premium v2 (Multi-Asset)"
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
N_BOOT           = 500

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
}

DATA_DIR    = data_dir("daily_tickers")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")

print("=" * 75)
print("OVERNIGHT PREMIUM — Multi-Asset Timing Backtest v2")
print("=" * 75)
print(f"Signal : close_t → open_{{t+1}} (one overnight trade per day)")
print(f"Period : {START_DATE} → {END_DATE}")
print(f"TC     : {TC_BPS_OW} bps each way")
print(f"n_boot : {N_BOOT}\n")


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


def compute_overnight_returns(df, ticker):
    """overnight return = open_t / close_{t-1} - 1, net of round-trip TC."""
    tc_rt = 2 * TC_BPS_OW / 10_000
    close = df["close"]
    open_ = df["open"]
    overnight_gross = (open_ / close.shift(1) - 1).dropna()
    overnight_net   = overnight_gross - tc_rt
    return overnight_net


def significance_3gates(r_series, n_boot=N_BOOT):
    """3-gate test: t-test, bootstrap Sharpe 5th-pct > 0, permutation p < 0.05."""
    r = np.array(r_series.dropna())
    if len(r) < 50 or r.std() == 0:
        return 0, {}
    ppy = 252.0
    ann = np.sqrt(ppy)
    sharpe = r.mean() / r.std() * ann

    # Gate 1: one-sided t-test
    from scipy.stats import ttest_1samp
    t_stat, t_p_two = ttest_1samp(r, 0)
    t_p = float(t_p_two / 2) if t_stat > 0 else 1.0
    gate1 = t_p < 0.05

    # Gate 2: bootstrap Sharpe 5th pct > 0
    rng = np.random.RandomState(42)
    boot_sharpes = []
    for _ in range(n_boot):
        s = rng.choice(r, size=len(r), replace=True)
        boot_sharpes.append(s.mean() / s.std() * ann if s.std() > 0 else 0.0)
    boot_p5 = float(np.percentile(boot_sharpes, 5))
    gate2 = boot_p5 > 0

    # Gate 3: permutation p < 0.05
    rng2  = np.random.RandomState(42)
    abs_r = np.abs(r); cnt = 0
    for _ in range(n_boot):
        sh2 = abs_r * rng2.choice([-1, 1], size=len(abs_r))
        if (sh2.mean() / sh2.std() * ann if sh2.std() > 0 else 0.0) >= sharpe:
            cnt += 1
    perm_p = cnt / n_boot
    gate3  = perm_p < 0.05

    n_pass = int(gate1) + int(gate2) + int(gate3)
    return n_pass, {
        "sharpe":  round(float(sharpe), 4),
        "t_stat":  round(float(t_stat), 4),
        "t_p":     round(float(t_p), 4),
        "boot_p5": round(float(boot_p5), 4),
        "perm_p":  round(float(perm_p), 4),
    }


# ── Pre-load data ─────────────────────────────────────────────────────────────

all_tickers = list(dict.fromkeys(t for ts in BASKETS.values() for t in ts))
ticker_data = {}
print("Loading price data...")
for ticker in all_tickers:
    df = load_ohlc(ticker)
    ticker_data[ticker] = df
    status = f"{len(df):>5} rows" if df is not None else " NO DATA"
    print(f"  {ticker:<8} {status}")

os.makedirs(RESULTS_DIR, exist_ok=True)

summary_per_basket = {}

for basket_name, basket_tickers in BASKETS.items():
    print(f"\n{'='*75}")
    print(f"BASKET: {basket_name}  ({len(basket_tickers)} instruments)")
    print(f"{'='*75}")

    available = [(t, ticker_data[t]) for t in basket_tickers if ticker_data.get(t) is not None]
    if not available:
        print("  No data — skipping.")
        continue

    N = len(available)
    tickers_avail = [t for t, _ in available]

    print(f"\n  {'Ticker':<8}  {'n_days':>7}  {'Sharpe':>7}  {'mean_bps':>9}  {'Gates':>5}  Verdict")
    print(f"  {'-'*55}")

    sharpes_list = []
    pass_count   = 0
    per_inst     = {}

    for ticker, df in available:
        ret = compute_overnight_returns(df, ticker)
        if len(ret) < 50:
            print(f"  {ticker:<8}  SKIP (<50 obs)")
            continue

        n_gates, gd = significance_3gates(ret)
        sharpe = gd.get("sharpe", 0.0)
        sharpes_list.append(sharpe)
        if n_gates >= 2:
            pass_count += 1

        verdict = "PASS" if n_gates >= 2 else "FAIL"
        star    = " ***" if n_gates == 3 else (" **" if n_gates == 2 else "")
        mean_bps = float(ret.mean()) * 10000
        print(f"  {ticker:<8}  {len(ret):>7}  {sharpe:>7.3f}  {mean_bps:>9.2f}  [{n_gates}/3]  {verdict}{star}")

        per_inst[ticker] = {
            "n_trades": len(ret),
            "sharpe":   sharpe,
            "mean_bps": round(mean_bps, 2),
            "gates":    n_gates,
            "verdict":  verdict,
            **gd,
        }

    n_valid = len(sharpes_list)
    if n_valid == 0:
        print("  No valid instruments — skipping basket.")
        continue

    median_sharpe = float(np.median(sharpes_list))
    binom_pvalue  = float(binom.sf(pass_count - 1, n_valid, 0.05))
    verdict_str   = "STRATEGY EXISTS" if binom_pvalue < 0.05 else "NO EVIDENCE OF EFFECT"

    print(f"\n  BINOMIAL TEST — {basket_name}")
    print(f"    N instruments      : {n_valid}")
    print(f"    Expected FP (5%)   : {n_valid*0.05:.2f}")
    print(f"    Observed pass count: {pass_count}")
    print(f"    Binomial p-value   : {binom_pvalue:.6f}")
    print(f"    Verdict            : {verdict_str}")
    print(f"    Median Sharpe      : {median_sharpe:.3f}")

    summary_per_basket[basket_name] = {
        "instruments":             tickers_avail,
        "n_instruments":           n_valid,
        "canonical_params":        {"overnight_hold": True, "tc_bps_ow": TC_BPS_OW},
        "canonical_median_sharpe": round(median_sharpe, 4),
        "pass_count_at_canon":     pass_count,
        "binomial_pvalue":         round(binom_pvalue, 6),
        "binomial_significant":    bool(binom_pvalue < 0.05),
        "verdict":                 verdict_str,
        "per_instrument":          per_inst,
    }


# ── Save JSON ────────────────────────────────────────────────────────────────

out = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "n_boot":         N_BOOT,
    "grid":           {"combos": 1, "note": "No hyperparameters — signal fixed"},
    "baskets":        summary_per_basket,
}

json_path = os.path.join(RESULTS_DIR, "overnight_premium_v2_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(out, f, indent=2, default=str)

print(f"\n{'='*75}")
print(f"FINAL SUMMARY")
print(f"{'='*75}")
for bname, bdata in summary_per_basket.items():
    print(f"\n  {bname}")
    print(f"    Verdict    : {bdata['verdict']}")
    print(f"    Med Sharpe : {bdata['canonical_median_sharpe']:.3f}")
    print(f"    Pass count : {bdata['pass_count_at_canon']}/{bdata['n_instruments']}")
    print(f"    Binom p    : {bdata['binomial_pvalue']:.6f}")

print(f"\n  JSON → {json_path}")
print(f"\n{'='*75}\nDone.\n{'='*75}")


# ── Tier 2: INTEGRATED Bonferroni rescue (fable refactor 2026-07-02) ─────────
# Runs after Tier 1 on the NEXT execution of this script; on-disk results
# remain canonical until then. Engine: shared/basket_significance.py.
# Requires: summary_per_basket dict + per-instrument best combos + a
# (ticker, combo) -> monthly returns callable. Wire the lambda below to this
# script's own signal/equity functions if the auto-detected name is wrong.
try:
    from _shared.basket_significance import bonferroni_rescue
    if "summary_per_basket" in dir() and "instrument_best" in dir():
        bonferroni_rescue(
            summary_per_basket=summary_per_basket,
            instrument_best=instrument_best,
            monthly_returns_fn=lambda _t, _c: compute_monthly_returns(
                build_daily_equity_from_trades(
                    ticker_data[_t]["close"], generate_overnight_premium_trades_v2(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "overnight_premium_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
