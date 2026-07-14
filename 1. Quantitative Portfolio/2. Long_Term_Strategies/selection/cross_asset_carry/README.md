# Cross-Asset Carry

**Portfolio:** LongTerm | **Status:** ❌ NOT significant (0/3) | **Canonical:** `cross_asset_carry_selection_Backtest_multiasset_v2.py`

## 1. Strategy

Rank 5 asset-class sleeves (SPY, TLT, gold, oil, corp bonds) by carry proxy (12m return / 12m vol), long top 3. Monthly.

## 2. Validation & Results

2016–2025: net Sharpe **0.15, 0/3 gates**. CAGR 1.5%, MaxDD −38.2%, only 27 rebalances. Also flagged weak by the family Bonferroni layer.

## 3. Portfolio role

**Excluded.** Two honest problems: the "carry" proxy is return-to-risk (i.e., trailing Sharpe momentum), not true carry (spot/futures basis or yield differentials); and 5 sleeves × 9 years is underpowered. Revive only with real carry inputs (futures basis for commodities, yield spreads for bonds/FX) — otherwise retire.

## 4. Files

`results/cross_asset_carry_summary.json` + `_multiasset_` + `_v2_multiasset_summary.json` · older generations → `v1/`.
