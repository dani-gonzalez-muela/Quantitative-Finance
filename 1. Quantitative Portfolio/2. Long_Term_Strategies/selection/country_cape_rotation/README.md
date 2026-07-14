# Country CAPE Rotation

**Portfolio:** LongTerm | **Status:** ✅ Validated (value proxy) | **Canonical:** `country_cape_rotation_selection_Backtest_multiasset_v2.py`

## 1. Strategy

Faber-style country value rotation: hold the 5 cheapest of 14 countries, monthly rebalance, CRSP world country returns. Cheapness proxy = inverse 12m return (Shiller CAPE download was blocked — todo proxy log).

## 2. Validation & Results

1996–2026 (30 years): net Sharpe 0.41, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 6.7%, MaxDD −48.8%.

## 3. Portfolio role

Candidate, not selected. Upgrade path: real CAPE data would make this a true value signal instead of a long-term-reversal proxy — its OG research (`Backtest_Country_Rotation*` notebooks incl. the annual addendum) is in the archive and belongs in `v1/` here (archive assessment).

## 4. Files

`results/country_cape_rotation_summary.json` + `_multiasset_` + `_v2_multiasset_summary.json` · older generations + archive notebooks → `v1/`.
