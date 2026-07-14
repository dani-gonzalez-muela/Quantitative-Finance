# US Return Seasonality

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** `us_return_seasonality_timing_Backtest_multiasset.py`

## 1. Strategy

Same-calendar-month seasonality (Heston-Sadka style): market exposure scaled ±20% by the rolling 5-year same-month average return's sign. FF Mkt, monthly, 5bps/side.

## 2. Validation & Results

1996–2026: net Sharpe 0.57, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 9.7%, MaxDD −54.4% (the ±20% tilt keeps it ~beta).

## 3. Portfolio role

Candidate, not selected. Note: its OG research notebooks (`Backtest_Seasonality*` v1→v3) live in the archive and should move to `v1/` here per the archive assessment — genuinely different research iterations worth keeping.

## 4. Files

`results/us_return_seasonality_summary.json` · `results/us_return_seasonality_daily_equity/` · v1 scripts + archive notebooks → `v1/`.
