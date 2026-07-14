# 2. Long_Term_Strategies — the long-term candidate pool

Two families, one folder per strategy:

- `timing/` (20) — e.g. credit_carry, yield_curve_duration, qmj_long_short, low_volatility,
  pead_earnings_drift, bollinger_band, donchian_channel, turn_of_month, congress_trade_for_trade, …
- `selection/` (12) — e.g. gtaa, sector_momentum, bond_trend, commodity_carry/trend,
  quality_profitability, quantitative_momentum, …

## How they're used

`3. Portfolio_construction/portfolio_analysis.py` evaluates a 29-name pool
(LT_TIMING + LT_SELECTION + the 4 ex-daily timing names bollinger_band, donchian_channel,
turn_of_month, congress_trade_for_trade — added by user decision 2026-07-10); 
`build_final_portfolios.py` takes the top-9 on the greedy diversification path as the
**LONG-TERM portfolio** (currently: quality_profitability, congress_trade_for_trade,
turn_of_month, qmj_long_short, bond_trend, commodity_carry, bollinger_band, credit_carry,
yield_curve_duration — Sharpe(m) 1.68). bond_trend + yield_curve_duration are 0/3 on
gates — kept deliberately as diversifiers; donchian evaluated but not selected.

Curves are monthly-marked (stepped-daily in the dashboard). Results conventions
per folder mirror the short-term tree (`results/*_daily_equity/` etc.); see
`MULTIASSET_RESULTS.md` and `STRATEGY_REPORT.md` for cross-strategy summaries.
