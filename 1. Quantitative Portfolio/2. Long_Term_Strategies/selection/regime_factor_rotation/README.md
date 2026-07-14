# Regime Factor Rotation

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** `regime_factor_rotation_selection_Backtest_multiasset.py`

## 1. Strategy

GMM macro-regime model (10 PCA components, 3 regimes, refit every 24m, trained on macro data from 1984) rotates among 5 factor ETFs (SIZE, VLUE, QUAL, COWZ, MTUM ↔ SMB/HML/RMW/CMA/Mom), holding the top 3 per regime. Basket architecture.

## 2. Validation & Results

Trading 2016→2026-04 (training from 1984): net Sharpe 0.82, **3/3 gates, SIGNIFICANT (strong)**. 44 trades.

## 3. Portfolio role

Candidate, not selected (factor bucket occupied by quality/momentum legs). Distinctive as the only regime-conditional selector in the family — worth keeping alive. Its private `data/` cache (incl. **ff_factors_monthly.csv, consumed by 8+ other backtests**) is the promotion item in the data plan.

## 4. Files

`results/regime_factor_rotation_summary.json` + `_multiasset_summary.json` · older generations → `v1/`.
