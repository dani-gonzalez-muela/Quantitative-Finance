# US Earnings Momentum

**Portfolio:** LongTerm | **Status:** ✅ Active (factor proxy) | **Canonical file:** `us_earnings_momentum_timing_backtest.py`

## 1. Strategy

Short-term price+earnings momentum composite, implemented as a Fama-French factor proxy: `Mkt + 0.4×Mom + 0.2×RMW`, monthly rebalance. Signal: avg_rank(ret_1_0, ret_3_1). True per-stock earnings data replacement is listed in the todo proxy-data log.

## 2. Validation

3-gate on monthly returns (1990–2026): **3/3, SIGNIFICANT (strong)**, net Sharpe 0.93.

## 3. Results

CAGR 14.3%, Sharpe(d) 0.83, MaxDD −40.4% (36-year sample incl. dot-com and GFC).

## 4. Portfolio role

**Selected — seed of the 2026-07-02 LongTerm portfolio** (highest individual monthly Sharpe in family). Its deep-drawdown profile is diluted by the other four members (portfolio MaxDD −20.7%).

## 5. Files

| File | Description |
|---|---|
| `results/us_earnings_momentum_daily_equity/us_earnings_momentum_daily_equity.csv` | Canonical equity |
| `results/us_earnings_momentum_summary.json` | Gates + stats |
