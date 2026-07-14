# BAB — Betting Against Beta

**Portfolio:** LongTerm | **Status:** ⚠️ Validated gross only — NOT significant net | **Canonical:** `bab_long_short_timing_Backtest_multiasset.py`

## 1. Strategy

Frazzini-Pedersen BAB: long bottom-quintile beta, short top-quintile beta, beta-neutral scaling (capped 3×). Betas = Vasicek-shrunk (`bswa32`, Better Market Betas dataset). Monthly, 5bps/side per leg.

## 2. Validation

1990–2019 (data ends 2019 — flagged STALE by the portfolio builder). Gross: 2/3 gates (Sharpe 0.34). **Net: 0/3 — costs consume the edge** (Sharpe 0.26, MaxDD −78%).

## 3. Results

CAGR 5.5%, Sharpe(d) 0.28, MaxDD −78.2%, 357 monthly rebalances.

## 4. Portfolio role

**Excluded** from the LongTerm portfolio: not significant net of costs AND equity curve ends 2019-12 (dropped as stale by the common-window rule). Revival requires refreshed beta data (Better Market Betas covers 1986–2019 only) and a cost-reduction redesign (quintile turnover is brutal at 5bps/leg).

## 5. Files

`results/bab_long_short_summary.json` (stats+gates) · `results/bab_long_short_daily_equity/` · v1 script in `v1/` after refactor.
