# PEAD — Post-Earnings Announcement Drift

**Portfolio:** LongTerm | **Status:** ✅ Validated (partial data) | **Canonical:** `pead_earnings_drift_timing_Backtest_multiasset.py`

## 1. Strategy

Long top-quartile SUE (standardized unexpected earnings: (EPS − EPS_lag4)/8q-rolling-std) after announcements, 1-month hold, S&P 500 universe via CRSP+CCM. 5bps/side.

## 2. Validation & Results

1990–2025: net Sharpe 0.68, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 11.9%, MaxDD −47.2%, 425 monthly cohorts. **Data caveat:** Compustat quarterly coverage ~50% (5.4GB ZIP streaming limit) — a chunked loader would complete the universe (same todo item as QMJ).

## 3. Portfolio role

Candidate, not selected (drawdown-heavy vs its marginal Sharpe contribution on the common window). Priority re-test after the Compustat loader fix.

## 4. Files

`results/pead_earnings_drift_summary.json` · `results/pead_earnings_drift_daily_equity/` · v1 → `v1/`.
