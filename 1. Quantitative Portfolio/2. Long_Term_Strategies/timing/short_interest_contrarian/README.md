# Short Interest Contrarian

**Portfolio:** LongTerm | **Status:** ✅ Validated (proxy return leg) | **Canonical:** `short_interest_contrarian_timing_Backtest_multiasset.py`

## 1. Strategy

Long the LEAST-shorted quintile (log short-interest cross-sectional rank, ~1,800 stocks/quintile, Compustat). Return leg proxied as FF Mkt+0.3×SMB (least-shorted tilts small). Monthly, 5bps/side.

## 2. Validation & Results

2006-07→2025-08: net Sharpe 0.61, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 10.6%, MaxDD −50.5%.

## 3. Portfolio role

Candidate, not selected (beta-dominated proxy return leg limits diversification). Upgrade path: Compustat short interest lacks a shares-outstanding denominator — joining it would enable true SI-ratio ranks and a per-stock return leg instead of the factor proxy.

## 4. Files

`results/short_interest_contrarian_summary.json` · `results/short_interest_contrarian_daily_equity/` · v1 → `v1/`.
