# Commodity Carry

**Portfolio:** LongTerm — **SELECTED** (step 4 of the greedy) | **Status:** ✅ Validated | **Canonical:** `commodity_carry_selection_Backtest_multiasset_v2.py`

## 1. Strategy

Rank 5 commodities (gold, oil, corn, wheat, soybeans) by carry proxy (1m return − 3m return/3 ≈ roll-yield differential), long top 3, monthly. Futures-price proxies from `commodities_daily.csv` (ETF downloads blocked; true spot/futures spread pending).

## 2. Validation & Results

2002–2025 (23 years): net Sharpe 0.51, **3/3 gates, SIGNIFICANT (strong)**. CAGR 9.0%, MaxDD −58.4% (commodity vol — sized down at portfolio level).

## 3. Portfolio role

**In the LongTerm portfolio** — near-zero correlation to every equity/bond member (ρ ≤ 0.08) makes it the portfolio's real-asset diversifier. Related: `Portfolio_construction/commodity_combined.py` blends this with commodity_trend's real-assets sleeve (50/50) — kept as an optional composite candidate.

## 4. Files

`results/commodity_carry_summary.json` + `_multiasset_` + `_v2_multiasset_summary.json` · older generations → `v1/`.
