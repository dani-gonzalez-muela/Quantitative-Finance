# Portfolio Candidate Tables & Greedy Selection

Threshold **0.1** (greedy keeps adding past the strict Sharpe peak while cumulative Sharpe stays within 0.1 of it). Gates = 3-gate test (t-test / bootstrap Sharpe / sign-permutation) at alpha=0.05, seed=42, on each candidate's monthly combined-equity curve — same test as basket_significance.py; reproduces basket_bonferroni_validation.json for LT names.  NOTE: scipy not installed - gate1 p uses a normal approximation.

## SHORT-TERM portfolio (one merged pool — 5 intraday session + overnight + 3 daily)

| Strategy | Sharpe(m) | Sharpe(d) | t-stat | Gates | CAGR % | MaxDD % | Months | Start | End | Note |
|---|---|---|---|---|---|---|---|---|---|---|
| ema_crossover | 5.129 | 5.678 | 16.55 | 3/3 | 130.62 | -3.04 | 125 | 2016-02-29 | 2026-06-30 |  |
| IBS_v2 | 2.288 | 2.256 | 7.36 | 3/3 | 13.51 | -3.48 | 124 | 2016-02-29 | 2026-05-31 |  |
| orb | 2.052 | 2.196 | 6.62 | 3/3 | 16.24 | -3.44 | 125 | 2016-02-29 | 2026-06-30 |  |
| intraday_momentum | 1.632 | 1.459 | 5.27 | 3/3 | 13.79 | -9.72 | 125 | 2016-02-29 | 2026-06-30 |  |
| vwap_trend | 1.590 | 1.583 | 5.13 | 3/3 | 33.56 | -25.35 | 125 | 2016-02-29 | 2026-06-30 |  |
| overnight | 1.488 | 1.655 | 4.80 | 3/3 | 12.14 | -11.42 | 125 | 2016-02-29 | 2026-06-30 |  |
| VIX_MR_v2 | 1.345 | 1.196 | 4.20 | 3/3 | 19.76 | -13.83 | 117 | 2016-07-31 | 2026-03-31 |  |
| VIX_ETN_Dual | 0.795 | 0.850 | 2.55 | 3/3 | 14.49 | -13.83 | 123 | 2016-02-29 | 2026-04-30 |  |
| Congress_Quiver | 0.791 | 0.874 | 2.45 | 3/3 | 7.32 | -8.37 | 115 | 2016-02-29 | 2025-08-31 |  |

**SHORT-TERM (merged pool, overnight = normal member) greedy** (threshold 0.1, common window 2016-07-31 -> 2025-08-31, 110m)  
Selected **4/9**: ema_crossover, overnight, IBS_v2, orb  
Portfolio Sharpe(m) **6.444** | CAGR 37.99% | MaxDD -0.29%

| Step | Added | Cumulative Sharpe |
|---|---|---|
| 1 | ema_crossover | 5.143 |
| 2 | overnight | 6.060 |
| 3 | IBS_v2 | 6.329 |
| 4 | orb | 6.444 (strict peak) <- selected stop |
| 5 | Congress_Quiver | 6.208 |
| 6 | intraday_momentum | 5.917 |
| 7 | vwap_trend | 5.649 |
| 8 | VIX_MR_v2 | 5.389 |
| 9 | VIX_ETN_Dual | 5.214 |

**Correlation matrix (monthly, common window):**

|                   |   ema_crossover |   intraday_momentum |   orb |   vwap_trend |   overnight |   IBS_v2 |   VIX_MR_v2 |   VIX_ETN_Dual |   Congress_Quiver |
|:------------------|----------------:|--------------------:|------:|-------------:|------------:|---------:|------------:|---------------:|------------------:|
| ema_crossover     |            1    |                0.42 |  0.12 |         0.08 |       -0.32 |    -0.02 |        0.13 |          -0.04 |             -0.17 |
| intraday_momentum |            0.42 |                1    |  0.18 |        -0.05 |       -0.21 |     0.1  |        0.15 |          -0.18 |             -0.16 |
| orb               |            0.12 |                0.18 |  1    |         0.06 |       -0.06 |    -0.03 |        0.02 |          -0.15 |              0.02 |
| vwap_trend        |            0.08 |               -0.05 |  0.06 |         1    |       -0.1  |    -0.17 |        0.01 |          -0.05 |             -0.04 |
| overnight         |           -0.32 |               -0.21 | -0.06 |        -0.1  |        1    |     0.2  |        0.15 |           0.23 |              0.19 |
| IBS_v2            |           -0.02 |                0.1  | -0.03 |        -0.17 |        0.2  |     1    |        0.23 |           0.38 |              0.17 |
| VIX_MR_v2         |            0.13 |                0.15 |  0.02 |         0.01 |        0.15 |     0.23 |        1    |          -0.02 |             -0.14 |
| VIX_ETN_Dual      |           -0.04 |               -0.18 | -0.15 |        -0.05 |        0.23 |     0.38 |       -0.02 |           1    |              0.05 |
| Congress_Quiver   |           -0.17 |               -0.16 |  0.02 |        -0.04 |        0.19 |     0.17 |       -0.14 |           0.05 |              1    |

**Selected blend (4 strats):** Sharpe(m) 6.444 | Sharpe(d) 6.365 | CAGR 35.99% | MaxDD(d) -1.61%

## LongTerm portfolio
### LongTerm - TIMING candidates (19)

| Strategy | Sharpe(m) | t-stat | Gates | CAGR % | MaxDD % | #Baskets | #Instr | Months | Start | End | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Bollinger | 1.079 | 3.31 | 3/3 | 8.66 | -15.84 | 3 | 21 | 113 | 2016-03-31 | 2025-07-31 |  ex-daily |
| us_earnings_momentum | 1.038 | 6.23 | 3/3 | 14.66 | -40.41 | - | - | 433 | 1990-02-28 | 2026-02-28 |  |
| us_cross_sectional_momentum | 0.965 | 5.79 | 3/3 | 14.20 | -44.78 | - | - | 433 | 1990-02-28 | 2026-02-28 |  |
| Donchian | 0.941 | 2.90 | 3/3 | 8.47 | -16.19 | 3 | - | 114 | 2016-02-29 | 2025-07-31 |  ex-daily |
| Turn_of_Month | 0.906 | 2.79 | 3/3 | 7.87 | -16.80 | 2 | - | 114 | 2016-02-29 | 2025-07-31 |  ex-daily |
| Congress_TFT | 0.905 | 2.84 | 3/3 | 9.41 | -11.71 | - | - | 118 | 2015-10-31 | 2025-07-31 |  ex-daily |
| us_shareholder_yield | 0.818 | 4.91 | 3/3 | 12.10 | -56.57 | - | - | 433 | 1990-02-28 | 2026-02-28 |  |
| pead_earnings_drift | 0.752 | 4.47 | 3/3 | 11.84 | -47.23 | - | - | 424 | 1990-03-31 | 2025-06-30 |  |
| low_volatility | 0.725 | 5.42 | 3/3 | 10.02 | -50.72 | - | - | 671 | 1970-02-28 | 2025-12-31 |  |
| insider_buying | 0.722 | 4.33 | 3/3 | 10.45 | -54.57 | - | - | 433 | 1990-02-28 | 2026-02-28 |  |
| overnight_premium | 0.694 | 3.53 | 3/3 | 6.51 | -34.67 | - | - | 311 | 2000-02-29 | 2025-12-31 |  |
| short_interest_contrarian | 0.684 | 2.99 | 3/3 | 10.74 | -50.54 | - | - | 229 | 2006-08-31 | 2025-08-31 |  |
| us_return_seasonality | 0.635 | 3.48 | 3/3 | 9.61 | -54.44 | - | - | 361 | 1996-02-29 | 2026-02-28 |  |
| reit_dividend_carry | 0.609 | 2.67 | 3/3 | 5.46 | -33.08 | - | - | 230 | 2006-01-31 | 2025-02-28 |  |
| credit_carry | 0.579 | 1.75 | 3/3 | 1.49 | -5.95 | 1 | - | 110 | 2016-06-30 | 2025-07-31 |  |
| qmj_long_short | 0.494 | 2.97 | 3/3 | 4.76 | -45.32 | - | - | 433 | 1990-02-28 | 2026-02-28 |  |
| bab_long_short | 0.342 | 1.87 | 3/3 | 5.60 | -78.19 | - | - | 358 | 1990-03-31 | 2019-12-31 |  |
| yield_curve_duration | 0.154 | 0.47 | 0/3 | 0.37 | -9.88 | 1 | - | 111 | 2016-03-31 | 2025-05-31 |  |
| bond_duration_carry | 0.111 | 0.34 | 0/3 | 0.53 | -21.76 | 0 | - | 113 | 2016-03-31 | 2025-07-31 |  |

### LongTerm - SELECTION candidates (10)

| Strategy | Sharpe(m) | t-stat | Gates | CAGR % | MaxDD % | #Baskets | #Instr | Months | Start | End | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| quality_profitability | 0.895 | 7.07 | 3/3 | 9.10 | -43.47 | - | - | 750 | 1963-09-30 | 2026-02-28 |  |
| sector_momentum | 0.891 | 2.52 | 3/3 | 11.76 | -14.84 | 2 | - | 96 | 2017-02-28 | 2025-01-31 |  |
| em_dm_carry | 0.843 | 4.31 | 3/3 | 11.64 | -54.61 | - | - | 313 | 2000-02-29 | 2026-02-28 |  |
| gtaa | 0.827 | 2.42 | 3/3 | 9.74 | -15.22 | 4 | - | 103 | 2017-08-31 | 2026-02-28 |  |
| industry_trend | 0.724 | 2.21 | 3/3 | 10.19 | -20.09 | - | - | 112 | 2016-02-29 | 2025-05-31 |  |
| commodity_carry | 0.543 | 2.62 | 3/3 | 9.04 | -56.63 | - | - | 280 | 2002-02-28 | 2025-05-31 |  |
| country_cape_rotation | 0.470 | 2.57 | 3/3 | 6.50 | -48.84 | - | - | 360 | 1996-03-31 | 2026-02-28 |  |
| commodity_trend | 0.380 | 1.85 | 3/3 | 5.63 | -58.33 | - | - | 284 | 2001-10-31 | 2025-05-31 |  |
| bond_trend | 0.186 | 0.93 | 0/3 | 0.78 | -14.14 | - | - | 300 | 2001-02-28 | 2026-01-31 |  |
| cross_asset_carry | 0.181 | 0.55 | 0/3 | 1.51 | -30.33 | - | - | 113 | 2016-02-29 | 2025-06-30 |  |

_Greedy runs over the combined timing+selection pool, as in build_portfolios.py._

**LongTerm greedy** (threshold 0.1, common window 2017-08-31 -> 2025-01-31, 90m)  
Selected **9/28**: quality_profitability, Congress_TFT, Turn_of_Month, qmj_long_short, bond_trend, commodity_carry, Bollinger, credit_carry, yield_curve_duration  
Portfolio Sharpe(m) **1.684** | CAGR 6.28% | MaxDD -4.92%

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
| 9 | yield_curve_duration | 1.684 <- threshold stop |
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
