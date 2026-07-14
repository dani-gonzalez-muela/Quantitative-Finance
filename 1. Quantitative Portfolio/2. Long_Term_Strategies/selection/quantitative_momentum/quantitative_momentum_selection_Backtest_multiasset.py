# -*- coding: utf-8 -*-
"""
Quantitative Momentum -- Multi-Asset Pipeline Wrapper
======================================================
quantitative_momentum is a STOCK-SELECTION strategy that runs on individual
S&P 500 constituents using CRSP data (top decile by 12-1m momentum, FIP filter,
quarterly rebalance). A genuine "multi-asset expansion" is not applicable --
the only meaningful universe is S&P 500 stocks, and the full CRSP backtest
already covers that universe.

This file:
  1. Loads existing CRSP backtest results from results/
  2. Runs the 3-gate significance battery (t-test, bootstrap Sharpe,
     permutation test) on the daily VW equity curve
  3. Saves results/quantitative_momentum_multiasset_summary.json

Basket : sp500_stocks (single sleeve -- the CRSP backtest IS the result)
Period : 2006-11-30 -> 2025-11-28
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

import json
import numpy as np
import pandas as pd

from _shared._backtest_utils import (
    ttest_returns,
    bootstrap_sharpe,
    permutation_test,
)

# -- Paths --
RESULTS_DIR  = os.path.join(_FILE_DIR, "results")
EQUITY_CSV   = os.path.join(RESULTS_DIR, "quantitative_momentum_daily_equity_vw.csv")
SUMMARY_JSON = os.path.join(RESULTS_DIR, "quantitative_momentum_summary.json")
IMPL_JSON    = os.path.join(RESULTS_DIR, "quantitative_momentum_implementations.json")
OUT_JSON     = os.path.join(RESULTS_DIR, "quantitative_momentum_multiasset_summary.json")

STRATEGY_NAME = "Quantitative Momentum"
BASKET        = "sp500_stocks"

print("=" * 70)
print("QUANTITATIVE MOMENTUM -- Multi-Asset Pipeline (CRSP backtest results)")
print("=" * 70)

# -- 1. Load existing results --
with open(SUMMARY_JSON) as f:
    summary = json.load(f)

with open(IMPL_JSON) as f:
    implementations = json.load(f)

key_impl = implementations.get("qmom_vw_1p0x", {})
print(f"\nLoaded CRSP backtest: CAGR={key_impl.get('cagr')}%  "
      f"Sharpe={key_impl.get('sharpe')}  MaxDD={key_impl.get('max_dd')}%")

# -- 2. Load daily equity curve --
eq_raw = pd.read_csv(EQUITY_CSV, index_col=0, parse_dates=True)
# Column may be '0' (unnamed) or 'equity'
eq = eq_raw.iloc[:, 0].dropna()
eq.index = pd.to_datetime(eq.index)
eq.name = "equity"

print(f"Equity curve: {eq.index[0].date()} -> {eq.index[-1].date()}  "
      f"({len(eq)} rows)")

# -- 3. Build monthly returns for significance tests --
monthly_eq  = eq.resample("ME").last()
monthly_ret = monthly_eq.pct_change().dropna()

print(f"Monthly returns: {len(monthly_ret)} observations")

# -- 4. Run 3-gate significance battery --
print("\nRunning significance tests ...")

tt   = ttest_returns(monthly_ret)
bs   = bootstrap_sharpe(monthly_ret)
perm = permutation_test(monthly_ret)

passes = sum([tt["significant"], bs["significant"], perm["significant"]])
label  = (
    "STRONG"   if passes == 3 else
    "MODERATE" if passes == 2 else
    "WEAK"     if passes == 1 else
    "NOT SIG"
)

print(f"  t-test      : p={tt['p_value']}  sig={tt['significant']}")
print(f"  bootstrap   : CI_lo={bs['ci_lower']}  sig={bs['significant']}")
print(f"  permutation : p={perm['p_value']}  sig={perm['significant']}")
print(f"  Gates       : {passes}/3  =>  {label}")

# -- 5. Key metrics from summary --
vw_stats  = summary["variants"]["value_weight"]["stats"]
spy_bench = summary.get("spy_benchmark", {})

# -- 6. Save multiasset_summary.json --
output = {
    "strategy": STRATEGY_NAME,
    "pipeline_note": (
        "Stock-selection strategy. Multi-asset expansion = single universe "
        "(S&P 500 constituents, CRSP). Existing CRSP backtest IS the result."
    ),
    "basket": BASKET,
    "period": summary.get("period", "2006-11-30 -> 2025-11-28"),
    "params": summary.get("params", {}),
    "key_metrics": {
        "cagr_pct":         vw_stats.get("cagr"),
        "total_return_pct": vw_stats.get("total_return"),
        "sharpe":           vw_stats.get("sharpe"),
        "max_dd_pct":       vw_stats.get("max_dd"),
    },
    "spy_benchmark": spy_bench,
    "significance_tests": {
        "ttest":       tt,
        "bootstrap":   bs,
        "permutation": perm,
    },
    "gates_passed": f"{passes}/3",
    "label":        label,
    "implementations": {
        k: v for k, v in implementations.items()
        if not k.startswith("_")
    },
}

os.makedirs(RESULTS_DIR, exist_ok=True)
with open(OUT_JSON, "w") as f:
    json.dump(output, f, indent=2)

print(f"\nSaved -> {OUT_JSON}")
print(f"Final label : {label}  ({passes}/3 gates)")
print(f"CAGR        : {vw_stats.get('cagr')}%")
print(f"Sharpe      : {vw_stats.get('sharpe')}")
print(f"MaxDD       : {vw_stats.get('max_dd')}%")


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
                    ticker_data[_t]["close"], generate_quantitative_momentum_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "quantitative_momentum_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
