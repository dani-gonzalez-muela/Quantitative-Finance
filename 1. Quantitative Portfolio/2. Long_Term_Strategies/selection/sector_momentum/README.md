# Sector Momentum

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** `sector_momentum_selection_Backtest_multiasset_v2.py`

## 1. Strategy

Rank 10 sector ETFs by 126-day momentum, hold top 5, periodic rebalance. Basket architecture.

## 2. Validation & Results

2014→2026-04: net Sharpe 0.65, **3/3 gates, SIGNIFICANT (strong)**. 127 trades. v2 multiasset: both baskets (us_sectors, us_factor) pass.

## 3. Portfolio role

Candidate, not selected on the common window (its curve ends 2025-01, and the momentum bucket was filled; step 12 on the path). Overlaps industry_trend (6m/top-3 vs 126d/top-5 on near-identical universes) — **a consolidation decision between the two is warranted**: keep one as canonical sector-rotation, archive the other as a parameter variant.

## 4. Files

`results/sector_momentum_summary.json` + `_multiasset_` + `_v2_multiasset_summary.json` · older generations → `v1/`.

## 5. Related archive

`sector_rotation_hybrid` (failed_strategies/) was the composite-signal prototype this strategy superseded — its hybrid idea remains untested (see the recovery README there).
