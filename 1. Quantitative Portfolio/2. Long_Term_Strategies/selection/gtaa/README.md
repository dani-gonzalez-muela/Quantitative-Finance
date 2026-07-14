# GTAA — Global Tactical Asset Allocation

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** `gtaa_selection_Backtest_multiasset_v2.py`

## 1. Strategy

Faber (2007) GTAA: 5 asset-class ETFs (SPY, EFA, IEF, DBC, VNQ) at 20% each, each held only when above its 200-day SMA (else to SHV cash). Winner variant: **monthly** rebalance (vs weekly). Reference: Faber 2007 + Concretum QuanTips #1 (papers in folder).

## 2. Validation & Results

2016→2026-04: monthly variant Sharpe 0.93, **3/3 gates, SIGNIFICANT (strong)**. CAGR 6.1%, **MaxDD −8.7%** (vs SPY's −33.8%) — the drawdown control is the whole point. v2 multiasset: 4/4 baskets pass.

## 3. Portfolio role

Candidate; validated on every basket but not selected on the 2017-08→2025-01 common window (its defensive profile overlaps bond_trend + credit_carry). Natural substitute if the bond legs are retired after the IEF re-benchmark. Was "pending inclusion" in methodology v4 — now formally a first-class candidate.

## 4. Files

`results/gtaa_summary.json` + `_multiasset_` + `_v2_multiasset_summary.json` · reference PDFs + Concretum notebook stay in folder root · older generations → `v1/`.
