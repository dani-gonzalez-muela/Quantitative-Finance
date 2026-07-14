# Industry Trend

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** `industry_trend_selection_Backtest_multiasset.py` (+ v2 grid outputs)

## 1. Strategy

Sector trend selection: rank 9 sector ETFs by 6m momentum, hold top 3, monthly rebalance. Grid-searched (120 combos: top_pct × freq × window).

## 2. Validation & Results

2016-08→2025-04: Sharpe 0.88, **3/3 gates, SIGNIFICANT (strong)**. CAGR 13.1%, MaxDD −17.1%, 80% year-over-year hit rate, 104 monthly cohorts.

## 3. Portfolio role

Candidate, not selected (step 13 on the greedy path — correlated with the momentum exposures already in). Solid substitute within the equity-selection bucket.

## 4. Housekeeping (from the long-standing §3.1 flag)

The intermediate drafts `industry_trend_v2_selection_Implementation.py`, `industry_trend_v2_selection_backtest.py`, `industry_trend_selection_Implementation_v2.py` are superseded by the `_multiasset` pair → moved to `v1/` by the refactor tool. `industry_trend_v2_summary.json` documents that intermediate era — keep in results as history.

## 5. Files

`results/industry_trend_summary.json` (+ `_v2_`, `_multiasset_` variants) · drafts → `v1/`.
