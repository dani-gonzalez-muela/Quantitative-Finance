# QMJ — Quality Minus Junk

**Portfolio:** LongTerm | **Status:** ✅ Active (factor proxy) | **Canonical file:** `qmj_long_short_timing_backtest.py`

## 1. Strategy

Market-neutral quality long/short via FF factor proxy: `RMW + 0.5×CMA` (long profitable/conservative, short unprofitable/aggressive). Monthly. True Compustat GP construction was OOM (5.4GB zip) — proxy documented in todo log.

## 2. Validation

3-gate on monthly returns (1990–2026): **2/3, SIGNIFICANT (moderate)**, Sharpe 0.49.

## 3. Results

CAGR 4.7%, MaxDD −45.3% (long-sample factor drawdowns; market-neutral so uncorrelated with equity beta).

## 4. Portfolio role

**Selected in the 2026-07-02 LongTerm portfolio** (step 2) — its negative correlation to momentum is the diversification engine, not its standalone Sharpe.

## 5. Files

| File | Description |
|---|---|
| `results/qmj_long_short_daily_equity/qmj_long_short_daily_equity.csv` | Canonical equity |
| `results/qmj_long_short_summary.json` | Gates + stats |
| `qmj_long_short_timing_backtest.py` | Backtest (paths fixed to manifest 2026-07-02) |
