# Candidate Statistics (Sharpe / CAGR / MaxDD)

All figures on MONTHLY returns, computed with the same load_returns / stats_monthly logic as build_portfolios.py. This is the per-candidate view the greedy selector ranks over. Candidates with <24 months are dropped by greedy_full_path but shown here for completeness.

## Daily candidates (8)

| Strategy | Sharpe(m) | CAGR % | MaxDD % | Months | Start | End | Note |
|---|---|---|---|---|---|---|---|
| IBS_v2 | 2.288 | 13.51 | -3.48 | 124 | 2016-02-29 | 2026-05-31 |  |
| Bollinger | 1.079 | 8.66 | -15.84 | 113 | 2016-03-31 | 2025-07-31 |  |
| Donchian | 0.941 | 8.47 | -16.19 | 114 | 2016-02-29 | 2025-07-31 |  |
| Turn_of_Month | 0.906 | 7.87 | -16.80 | 114 | 2016-02-29 | 2025-07-31 |  |
| Congress_TFT | 0.905 | 9.41 | -11.71 | 118 | 2015-10-31 | 2025-07-31 |  |
| VIX_ETN_Dual | 0.796 | 14.56 | -13.83 | 122 | 2016-02-29 | 2026-03-31 |  |
| Congress_Quiver | 0.791 | 7.32 | -8.37 | 115 | 2016-02-29 | 2025-08-31 |  |
| VIX_MR_v2 | - | - | - | - | - | - | NO EQUITY FILE |

## LongTerm candidates (25)

| Strategy | Sharpe(m) | CAGR % | MaxDD % | Months | Start | End | Note |
|---|---|---|---|---|---|---|---|
| us_earnings_momentum | 1.038 | 14.66 | -40.41 | 433 | 1990-02-28 | 2026-02-28 |  |
| us_cross_sectional_momentum | 0.965 | 14.20 | -44.78 | 433 | 1990-02-28 | 2026-02-28 |  |
| quality_profitability | 0.895 | 9.10 | -43.47 | 750 | 1963-09-30 | 2026-02-28 |  |
| sector_momentum | 0.891 | 11.76 | -14.84 | 96 | 2017-02-28 | 2025-01-31 |  |
| em_dm_carry | 0.843 | 11.64 | -54.61 | 313 | 2000-02-29 | 2026-02-28 |  |
| gtaa | 0.827 | 9.74 | -15.22 | 103 | 2017-08-31 | 2026-02-28 |  |
| us_shareholder_yield | 0.818 | 12.10 | -56.57 | 433 | 1990-02-28 | 2026-02-28 |  |
| pead_earnings_drift | 0.752 | 11.84 | -47.23 | 424 | 1990-03-31 | 2025-06-30 |  |
| low_volatility | 0.725 | 10.02 | -50.72 | 671 | 1970-02-28 | 2025-12-31 |  |
| industry_trend | 0.724 | 10.19 | -20.09 | 112 | 2016-02-29 | 2025-05-31 |  |
| insider_buying | 0.722 | 10.45 | -54.57 | 433 | 1990-02-28 | 2026-02-28 |  |
| overnight_premium | 0.694 | 6.51 | -34.67 | 311 | 2000-02-29 | 2025-12-31 |  |
| short_interest_contrarian | 0.684 | 10.74 | -50.54 | 229 | 2006-08-31 | 2025-08-31 |  |
| us_return_seasonality | 0.635 | 9.61 | -54.44 | 361 | 1996-02-29 | 2026-02-28 |  |
| reit_dividend_carry | 0.609 | 5.46 | -33.08 | 230 | 2006-01-31 | 2025-02-28 |  |
| credit_carry | 0.579 | 1.49 | -5.95 | 110 | 2016-06-30 | 2025-07-31 |  |
| commodity_carry | 0.543 | 9.04 | -56.63 | 280 | 2002-02-28 | 2025-05-31 |  |
| qmj_long_short | 0.494 | 4.76 | -45.32 | 433 | 1990-02-28 | 2026-02-28 |  |
| country_cape_rotation | 0.470 | 6.50 | -48.84 | 360 | 1996-03-31 | 2026-02-28 |  |
| commodity_trend | 0.380 | 5.63 | -58.33 | 284 | 2001-10-31 | 2025-05-31 |  |
| bab_long_short | 0.342 | 5.60 | -78.19 | 358 | 1990-03-31 | 2019-12-31 |  |
| bond_trend | 0.186 | 0.78 | -14.14 | 300 | 2001-02-28 | 2026-01-31 |  |
| cross_asset_carry | 0.181 | 1.51 | -30.33 | 113 | 2016-02-29 | 2025-06-30 |  |
| yield_curve_duration | 0.154 | 0.37 | -9.88 | 111 | 2016-03-31 | 2025-05-31 |  |
| bond_duration_carry | 0.111 | 0.53 | -21.76 | 113 | 2016-03-31 | 2025-07-31 |  |
