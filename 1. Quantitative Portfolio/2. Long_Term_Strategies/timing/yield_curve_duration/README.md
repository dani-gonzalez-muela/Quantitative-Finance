# Yield Curve Duration

**Portfolio:** LongTerm | **Status:** ❌ NOT significant (0/3) — on the IEF re-benchmark list | **Canonical:** `yield_curve_duration_timing_Backtest_multiasset_v2.py`

## 1. Strategy

Duration timing on the curve slope: T10Y2Y>0.5% → long duration (20yr), <0% → short duration (2yr), else 10yr. Synthetic FRED yields, duration-model price returns, monthly, 5bps/side.

## 2. Validation & Results

2016-02→2025-07: net Sharpe **−0.23, 0/3 gates**. CAGR −1.3%, MaxDD −36.9%. Flagged twice independently (todo notes + family Bonferroni layer) as one of the weakest members.

## 3. Portfolio role

**Excluded** (also dropped as stale/short by the common-window rule in the current build). Disposition pending the **quarterly-rebalance IEF re-benchmark** (unified TODO item 1): the 2016–2025 sample is a uniquely hostile rates regime, so weak absolute performance ≠ dead signal — but it must beat IEF to justify its complexity.

## 4. Files

`results/yield_curve_duration_summary.json` + `_v2_multiasset_summary.json` · older scripts → `v1/`.
