# Congress Trade-for-Trade (TFT)

**Portfolio:** Daily | **Status:** ✅ Active | **Canonical file:** `congress_trade_for_trade_timing_Backtest_multiasset.py`

## 1. Strategy

Mirrors individual US Congressional purchase disclosures trade-for-trade: each disclosed purchase is copied at 3% of total NAV, capped at 180 open positions, minimum 30-day hold. Medium-term equity exposure driven by insider-informed flow.

## 2. Validation

Single-signal alternative-data strategy — basket testing does not apply (methodology special case); validated via the 3-gate significance test. Canonical variant `total_nav_3pct_d180_min30d_1x`.

## 3. Results

| Variant | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| 3% NAV, D180 cap, min 30d hold (1×) | 1.12 | 10.4% | −12.1% |

## 4. Portfolio role

Daily-portfolio candidate (sub-monthly holding frequency; filed under `long_term/timing/` for historical reasons). Its near-zero/negative correlation to the other Daily strategies made it the primary diversifier in the 2026-06-28 Daily portfolio. In the 2026-07-02 rebuild its marginal addition no longer beats the improved standalone ibs curve — see `portfolio_construction/results/daily_portfolio_results.md`.

## 5. Files

| File | Description |
|---|---|
| `congress_trade_for_trade_timing_Backtest_multiasset.py` | Backtest |
| `results/congress_trade_for_trade_daily_equity/total_nav_3pct_d180_min30d_1x.csv` | Canonical equity |
| `results/congress_trade_for_trade_implementations.json` | Variant stats |
| `*_timing_{Backtest,Implementation}.ipynb` | Original notebooks |
