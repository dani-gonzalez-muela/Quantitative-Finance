# EM/DM Carry

**Portfolio:** LongTerm | **Status:** ✅ Active (ETF proxy) | **Canonical:** `em_dm_carry_*_multiasset` outputs

## 1. Strategy

Rotates between EM and DM equity baskets on relative carry/momentum: v2 canonical = top 25% by 9m carry, 5% threshold, semi-annual rebalance (grid of 240 combos). ETF proxy universe (EEM/INDA/EWZ/... vs SPY/QQQ/IWM/MDY); true country-level carry needs WRDS country returns (todo log).

## 2. Validation

Grid-search median Sharpe 1.15 at canonical params; v1 country-level version (2000–2026): Sharpe 0.68, CAGR 11.5%.

## 3. Results

v2 combined (2016→2026-04): Sharpe 0.80, CAGR 14.7%, MaxDD −30.5% (simple_85).

## 4. Portfolio role

**Selected in the 2026-07-02 LongTerm portfolio** (step 3) — the EM leg diversifies the US-factor-heavy momentum seed.

## 5. Files

| File | Description |
|---|---|
| `results/em_dm_carry_v2_multiasset_daily_equity/combined_equity.csv` | Canonical equity |
| `results/em_dm_carry_{multiasset_,}summary.json` | Stats + grid |
