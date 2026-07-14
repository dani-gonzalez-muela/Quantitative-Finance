# US Cross-Sectional Momentum

**Portfolio:** LongTerm | **Status:** ✅ Validated (factor proxy) | **Canonical:** `us_cross_sectional_momentum_timing_Backtest_multiasset.py`

## 1. Strategy

Classic 12-1 momentum (Jegadeesh & Titman 1993), long-only top-decile proxy: FF `Mkt+0.5×Mom`. Monthly, 5bps/side. (Jensen/Kelly per-stock dataset is 68GB — factor proxy per todo log.)

## 2. Validation & Results

1990–2026: net Sharpe 0.86, **3/3 gates, SIGNIFICANT (strong)**. CAGR 13.9%, MaxDD −44.8% (momentum crashes included).

## 3. Portfolio role

Candidate; on the 2017-08→2025-01 common window it was the first past-peak exclusion (step 7 of the greedy path — high correlation with the selected quality/earnings-momentum pair). First substitute if either factor leg is demoted.

## 4. Files

`results/us_cross_sectional_momentum_summary.json` · `results/us_cross_sectional_momentum_daily_equity/` · v1 → `v1/`.
