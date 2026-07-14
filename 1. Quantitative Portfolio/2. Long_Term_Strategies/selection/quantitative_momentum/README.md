# Quantitative Momentum

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** `quantitative_momentum_selection_Backtest_multiasset.py`

## 1. Strategy

Gray & Vogel (2016) *Quantitative Momentum* (book in folder): S&P 500 point-in-time universe (CRSP), 12-1 momentum top decile, FIP filter keeps the "smoothest" half, quarterly rebalance (Feb/May/Aug/Nov). Winner variant: **value-weighted**.

## 2. Validation & Results

2006-11→2025-11: VW Sharpe 0.61, **3/3 gates, SIGNIFICANT (strong)**. CAGR 12.7% vs SPY 10.4%, MaxDD −50.1%. ~24 names/rebalance, 1,813 trades. (EW variant: 0.42, 2/3 — the VW/EW gap is itself informative: the signal concentrates in large caps.)

## 3. Portfolio role

Candidate, not selected (momentum bucket already occupied). Note: this strategy's 1GB private data cache is the `caches/quantitative_momentum` item in the data plan.

## 4. Files

`results/quantitative_momentum_summary.json` + `_multiasset_summary.json` · equity CSVs (ew/vw/spybench) in results/ · older generations → `v1/`.
