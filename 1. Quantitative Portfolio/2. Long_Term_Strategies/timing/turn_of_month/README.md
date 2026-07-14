# Turn of Month

**Portfolio:** Daily (sub-monthly holds) | **Status:** ✅ Active | **Canonical:** `*_v2_multiasset_daily_equity/`

## 1. Strategy

Calendar effect: invested only the last N + first N trading days of each month (v2 canonical N=5/5), cash (risk-free) otherwise. Refs: Ariel (1987), Lakonishok & Smidt (1988).

## 2. Validation

v1 (CRSP SP500, 2000–2025): 2/3 gates, SIGNIFICANT (moderate), Sharpe 0.69 net. v2 multiasset (2016→2026-04): us_equity_broad + us_sectors baskets pass (combined Sharpe 0.80); per-instrument gates weaker (QQQ, XLV, XLRE, XLC pass individually at 3/3-day variant).

## 3. Results

v2 combined: Sharpe 0.80, CAGR 7.7%, MaxDD −17.5%. Monthly Sharpe ≈ 0.91 (Daily-portfolio measurement). Invested ~28.6% of days (v1) — capital-efficient.

## 4. Portfolio role

Daily-portfolio candidate. Selected at step 6 of the 2026-06-28 Daily portfolio (marginal +0.003); not selected in the 2026-07-02 rebuild. ρ=0.48 with IBS (both calendar-adjacent mean reversion).

## 5. Files

| File | Description |
|---|---|
| `results/turn_of_month_v2_multiasset_daily_equity/combined_equity.csv` | Canonical equity (portfolio input) |
| `results/turn_of_month_{multiasset_,}summary.json` | Gates + stats |
| `turn_of_month_timing_backtest.py` | v1 backtest (CRSP; paths fixed to manifest 2026-07-02) |
