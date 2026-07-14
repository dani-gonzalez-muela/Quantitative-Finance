# US Shareholder Yield

**Portfolio:** LongTerm | **Status:** ✅ Validated (factor proxy) | **Canonical:** `us_shareholder_yield_timing_Backtest_multiasset.py`

## 1. Strategy

High-shareholder-yield tilt, proxied as FF `Mkt+0.5×HML` (high book-to-market ≈ high-dividend cohort). Monthly, 5bps/side. True div12m_me per-stock construction pending real data (todo proxy log).

## 2. Validation & Results

1990–2026: net Sharpe 0.72, **2/3 gates, SIGNIFICANT (moderate)** (gross 3/3). CAGR 11.9%, MaxDD −56.6%.

## 3. Portfolio role

Candidate, not selected — the HML proxy makes it near-duplicate of the value/quality exposures already selected. Distinct only after a true shareholder-yield construction.

## 4. Files

`results/us_shareholder_yield_summary.json` · `results/us_shareholder_yield_daily_equity/` · v1 → `v1/`.
