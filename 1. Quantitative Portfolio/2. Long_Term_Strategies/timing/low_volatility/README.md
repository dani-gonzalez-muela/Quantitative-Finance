# Low Volatility (CRSP Beta Decile 1)

**Portfolio:** LongTerm | **Status:** ✅ Validated | **Canonical:** v2 = `low_vol_v2_timing_backtest.py` outputs (`low_vol_v2_summary.json`)

## 1. Strategy

Buy-and-hold the lowest-beta decile: CRSP NYSE/NYSEMKT Beta Decile 1 portfolio (indno 1000102), monthly rebalance built into CRSP construction. The academic low-vol anomaly in its cleanest benchmark form (v2 replaced the v1 Better-Market-Betas version — that dataset ends 2019; CRSP deciles cover 1925–2025).

## 2. Validation & Results

1970–2025 (56 years): net Sharpe 0.61, **3/3 gates, SIGNIFICANT (strong)**. CAGR 16.1%, MaxDD −74.4% (long-only equity through 1973/2000/2008 — the anomaly is in the risk-adjusted return, not the drawdown).

## 3. Portfolio role

Candidate, not selected by the greedy (overlaps the quality/defensive space already covered by quality_profitability + qmj). Keep validated as substitute.

## 4. Files

`results/low_vol_v2_summary.json` (canonical) · `results/low_volatility_summary.json` + `low_volatility_timing_backtest.py` → v1 (superseded era) · `results/low_vol_v2_daily_equity/`.
