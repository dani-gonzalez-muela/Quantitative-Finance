# Final Portfolios — 2-book structure (2026-07-10)

SHORT-TERM: evaluated **9** merged candidates, selected **5** (top-5 on the greedy path; strict Sharpe peak was step 4).  
LONG-TERM: unchanged method, top-9 of 29 candidates.

## SHORT-TERM portfolio

Selected: **ema_crossover, overnight, IBS_v2, orb, Congress_Quiver**

**Sharpe(m) 6.208 | Sharpe(d) 6.1 | CAGR 31.44% | MaxDD -0.26%**  (window 2016-07-31 -> 2025-08-31, 110m)

| Step | Added | Cumulative Sharpe |
|---|---|---|
| 1 | ema_crossover | 5.143 |
| 2 | overnight | 6.060 |
| 3 | IBS_v2 | 6.329 |
| 4 | orb | 6.444 (strict peak) |
| 5 | Congress_Quiver | 6.208 <- selected stop |
| 6 | intraday_momentum | 5.917 |
| 7 | vwap_trend | 5.649 |
| 8 | VIX_MR_v2 | 5.389 |
| 9 | VIX_ETN_Dual | 5.214 |

_Fees: intraday legs at $0.005/share slippage (2026-07-10 rerun); vwap_trend (slippage-0 canonical, cost-fragile) was evaluated in the pool and NOT selected._

## LONG-TERM portfolio

Selected: **quality_profitability, Congress_TFT, Turn_of_Month, qmj_long_short, bond_trend, commodity_carry, Bollinger, credit_carry, yield_curve_duration**

**Sharpe(m) 1.684 | CAGR 6.28% | MaxDD -4.92%**  (window 2017-08-31 -> 2025-01-31, 90m)

| Step | Added | Cumulative Sharpe |
|---|---|---|
| 1 | quality_profitability | 1.118 |
| 2 | Congress_TFT | 1.418 |
| 3 | Turn_of_Month | 1.574 |
| 4 | qmj_long_short | 1.639 |
| 5 | bond_trend | 1.707 |
| 6 | commodity_carry | 1.722 |
| 7 | Bollinger | 1.724 (strict peak) |
| 8 | credit_carry | 1.719 |
| 9 | yield_curve_duration | 1.684 <- selected stop |
| 10 | us_cross_sectional_momentum | 1.620 |
| 11 | gtaa | 1.532 |
| 12 | Donchian | 1.469 |
| 13 | us_earnings_momentum | 1.416 |
| 14 | bond_duration_carry | 1.375 |
| 15 | overnight_premium | 1.340 |
| 16 | sector_momentum | 1.289 |
| 17 | em_dm_carry | 1.243 |
| 18 | industry_trend | 1.203 |
| 19 | reit_dividend_carry | 1.169 |
| 20 | us_return_seasonality | 1.132 |
| 21 | insider_buying | 1.102 |
| 22 | short_interest_contrarian | 1.074 |
| 23 | low_volatility | 1.049 |
| 24 | us_shareholder_yield | 1.027 |
| 25 | country_cape_rotation | 1.006 |
| 26 | pead_earnings_drift | 0.979 |
| 27 | cross_asset_carry | 0.954 |
| 28 | commodity_trend | 0.925 |

_Note: LT includes bond_trend and yield_curve_duration, 0/3 on gates — kept deliberately as low-correlation diversifiers._

## Combined 2-book blend (50/50, monthly rebalanced — reporting only)

**Sharpe(m) 5.825 | CAGR 19.53% | MaxDD -0.33%**  (common window 2017-09-30 -> 2025-01-31, 89m; book correlation 0.19)

_Leverage caveat: never size the short-vol names (VIX_MR, VIX_ETN) aggressively — left-tail risk._
