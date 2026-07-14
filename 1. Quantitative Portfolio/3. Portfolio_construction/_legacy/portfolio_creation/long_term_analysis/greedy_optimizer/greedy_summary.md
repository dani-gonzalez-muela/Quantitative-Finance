# Greedy Portfolio Optimizer — Full Results
**Date:** 2026-06-18
**Universe:** 35 strategies loaded ( failed)

---

## Data Summary

| Strategy | Start | End | Trading Days |
|---|---|---|---|
| bab_long_short | 1990-02-28 | 2019-12-31 | 7785 |
| bollinger_band | 2016-05-02 | 2026-03-31 | 2587 |
| bond_duration_carry | 2003-02-28 | 2025-02-28 | 5741 |
| bond_trend | 2001-01-01 | 2026-01-01 | 6524 |
| commodity_carry | 2002-01-01 | 2025-05-12 | 6095 |
| commodity_trend | 2001-09-21 | 2025-05-12 | 6167 |
| country_cape_rotation | 1996-02-29 | 2026-02-27 | 7827 |
| credit_carry | 2001-01-01 | 2025-06-30 | 6391 |
| cross_asset_carry | 2016-01-04 | 2025-06-03 | 2457 |
| donchian_channel | 2016-02-23 | 2026-03-13 | 2624 |
| em_dm_carry | 2000-01-31 | 2026-02-27 | 6805 |
| gtaa | 2016-01-04 | 2026-03-31 | 2672 |
| ibs_mean_reversion | 2016-01-08 | 2026-03-31 | 2668 |
| industry_trend | 2016-01-04 | 2025-05-01 | 2434 |
| insider_buying | 1990-01-31 | 2026-02-27 | 9413 |
| low_volatility | 1970-01-30 | 2025-12-31 | 14589 |
| overnight_premium | 2000-01-03 | 2025-12-31 | 6783 |
| pead_earnings_drift | 1990-02-28 | 2025-06-30 | 9219 |
| qmj_long_short | 1990-01-31 | 2026-02-27 | 9413 |
| quality_profitability | 1963-08-30 | 2026-02-27 | 16306 |
| quantitative_momentum | 2006-11-30 | 2025-11-28 | 4957 |
| regime_factor_rotation | 2016-01-04 | 2026-03-31 | 2672 |
| reit_dividend_carry | 2005-12-30 | 2025-02-28 | 5001 |
| sector_momentum | 2016-08-01 | 2026-03-31 | 2522 |
| sentiment_timing | 1990-01-31 | 2026-02-27 | 9413 |
| short_interest_contrarian | 2006-07-31 | 2025-08-29 | 4980 |
| turn_of_month | 2000-01-03 | 2025-12-31 | 6783 |
| us_cross_sectional_momentum | 1990-01-31 | 2026-02-27 | 9413 |
| us_earnings_momentum | 1990-01-31 | 2026-02-27 | 9413 |
| us_return_seasonality | 1996-01-31 | 2026-02-27 | 7848 |
| us_shareholder_yield | 1990-01-31 | 2026-02-27 | 9413 |
| vix_etn_dual | 2016-01-19 | 2026-03-31 | 2661 |
| vix_mean_reversion | 2016-06-14 | 2026-03-31 | 2556 |
| vol_overlay | 2016-01-05 | 2026-03-30 | 2670 |
| yield_curve_duration | 2003-02-28 | 2025-02-28 | 5741 |

---

## Analysis 1: Greedy Forward Selection (Full Universe)

### Equal Weight (EW)

**Final Sharpe:** 1.9777

**Selection sequence:**

| Step | Strategy | Sharpe |
|---|---|---|
| 1 | ibs_mean_reversion | 1.3193 |
| 2 | quality_profitability | 1.7153 |
| 3 | vix_mean_reversion | 1.8837 |
| 4 | vol_overlay | 1.9045 |
| 5 | donchian_channel | 1.9135 |
| 6 | us_cross_sectional_momentum | 1.9513 |
| 7 | qmj_long_short | 1.9746 |
| 8 | gtaa | 1.9777 |

**Final weights:**

| Strategy | Weight |
|---|---|
| ibs_mean_reversion | 12.5% |
| quality_profitability | 12.5% |
| vix_mean_reversion | 12.5% |
| vol_overlay | 12.5% |
| donchian_channel | 12.5% |
| us_cross_sectional_momentum | 12.5% |
| qmj_long_short | 12.5% |
| gtaa | 12.5% |

### Inverse Volatility (IV)

**Final Sharpe:** 2.4049

**Selection sequence:**

| Step | Strategy | Sharpe |
|---|---|---|
| 1 | ibs_mean_reversion | 1.3193 |
| 2 | quality_profitability | 1.7337 |
| 3 | vol_overlay | 2.0187 |
| 4 | vix_mean_reversion | 2.2229 |
| 5 | bab_long_short | 2.2236 |
| 6 | country_cape_rotation | 2.3030 |
| 7 | donchian_channel | 2.3668 |
| 8 | us_cross_sectional_momentum | 2.3754 |
| 9 | bond_trend | 2.3910 |
| 10 | gtaa | 2.4049 |

**Final weights:**

| Strategy | Weight |
|---|---|
| vol_overlay | 70.3% |
| bond_trend | 7.4% |
| gtaa | 5.1% |
| ibs_mean_reversion | 3.5% |
| country_cape_rotation | 3.0% |
| donchian_channel | 3.0% |
| quality_profitability | 2.7% |
| us_cross_sectional_momentum | 2.2% |
| vix_mean_reversion | 1.8% |
| bab_long_short | 1.0% |

### Max Sharpe / MVO

**Final Sharpe:** 2.4263

**Selection sequence:**

| Step | Strategy | Sharpe |
|---|---|---|
| 1 | ibs_mean_reversion | 1.3193 |
| 2 | quality_profitability | 1.7153 |
| 3 | vix_mean_reversion | 1.9397 |
| 4 | vol_overlay | 2.0051 |
| 5 | bab_long_short | 2.0544 |
| 6 | us_earnings_momentum | 2.2166 |
| 7 | donchian_channel | 2.3184 |
| 8 | bond_trend | 2.3707 |
| 9 | country_cape_rotation | 2.4072 |
| 10 | commodity_carry | 2.4221 |
| 11 | us_cross_sectional_momentum | 2.4252 |
| 12 | gtaa | 2.4263 |

**Final weights:**

| Strategy | Weight |
|---|---|
| vol_overlay | 50.0% |
| bond_trend | 9.7% |
| vix_mean_reversion | 7.8% |
| donchian_channel | 6.3% |
| country_cape_rotation | 5.1% |
| ibs_mean_reversion | 4.5% |
| us_cross_sectional_momentum | 4.0% |
| gtaa | 3.4% |
| us_earnings_momentum | 3.1% |
| quality_profitability | 2.0% |
| bab_long_short | 2.0% |
| commodity_carry | 2.0% |

---

## Analysis 2: Efficient Frontier (MVO)

| Step | Strategy Added | Sharpe | CAGR | Max DD | Window |
|---|---|---|---|---|---|
| 1 | ibs_mean_reversion | 1.3193 | 12.6% | -9.2% | 2016-01-08 – 2026-03-31 |
| 2 | quality_profitability | 1.7153 | 12.8% | -6.5% | 2016-01-08 – 2026-02-27 |
| 3 | vix_mean_reversion | 1.9397 | 14.8% | -7.3% | 2016-06-14 – 2026-02-27 |
| 4 | vol_overlay | 2.0051 | 7.4% | -3.8% | 2016-06-14 – 2026-02-27 |
| 5 | bab_long_short | 2.0544 | 6.7% | -3.1% | 2016-06-14 – 2019-12-31 |
| 6 | us_earnings_momentum | 2.2166 | 7.6% | -3.0% | 2016-06-14 – 2019-12-31 |
| 7 | donchian_channel | 2.3184 | 7.3% | -2.7% | 2016-06-14 – 2019-12-31 |
| 8 | bond_trend | 2.3707 | 5.6% | -2.0% | 2016-06-14 – 2019-12-31 |
| 9 | country_cape_rotation | 2.4072 | 5.4% | -1.9% | 2016-06-14 – 2019-12-31 |
| 10 | commodity_carry | 2.4221 | 5.4% | -1.9% | 2016-06-14 – 2019-12-31 |
| 11 | us_cross_sectional_momentum | 2.4252 | 5.4% | -2.0% | 2016-06-14 – 2019-12-31 |
| 12 | gtaa | 2.4263 | 5.3% | -2.0% | 2016-06-14 – 2019-12-31 |

---

## Analysis 3: 10-Year History Constraint

**Excluded (< 2500 trading days):** cross_asset_carry, industry_trend

**Included (33 strategies):** bab_long_short, bollinger_band, bond_duration_carry, bond_trend, commodity_carry, commodity_trend, country_cape_rotation, credit_carry, donchian_channel, em_dm_carry, gtaa, ibs_mean_reversion, insider_buying, low_volatility, overnight_premium, pead_earnings_drift, qmj_long_short, quality_profitability, quantitative_momentum, regime_factor_rotation, reit_dividend_carry, sector_momentum, sentiment_timing, short_interest_contrarian, turn_of_month, us_cross_sectional_momentum, us_earnings_momentum, us_return_seasonality, us_shareholder_yield, vix_etn_dual, vix_mean_reversion, vol_overlay, yield_curve_duration

### EW (10yr)

Final portfolio: ['ibs_mean_reversion', 'quality_profitability', 'vix_mean_reversion', 'vol_overlay', 'donchian_channel', 'us_cross_sectional_momentum', 'qmj_long_short', 'gtaa']

Final Sharpe: 1.9777

### IV (10yr)

Final portfolio: ['ibs_mean_reversion', 'quality_profitability', 'vol_overlay', 'vix_mean_reversion', 'bab_long_short', 'country_cape_rotation', 'donchian_channel', 'us_cross_sectional_momentum', 'bond_trend', 'gtaa']

Final Sharpe: 2.4049

### MVO (10yr)

Final portfolio: ['ibs_mean_reversion', 'quality_profitability', 'vix_mean_reversion', 'vol_overlay', 'bab_long_short', 'us_earnings_momentum', 'donchian_channel', 'bond_trend', 'country_cape_rotation', 'commodity_carry', 'us_cross_sectional_momentum', 'gtaa']

Final Sharpe: 2.4263

---

## Analysis 4: Correlation Structure

**Common window:** 2016-08-01 → 2019-12-31 (1247 days)

### Top 10 Most Correlated Pairs

| Strategy A | Strategy B | Correlation |
|---|---|---|
| us_shareholder_yield | reit_dividend_carry | 1.000 |
| us_cross_sectional_momentum | us_earnings_momentum | 0.992 |
| short_interest_contrarian | insider_buying | 0.981 |
| us_return_seasonality | insider_buying | 0.980 |
| low_volatility | insider_buying | 0.972 |
| regime_factor_rotation | overnight_premium | 0.967 |
| us_return_seasonality | short_interest_contrarian | 0.967 |
| low_volatility | us_return_seasonality | 0.956 |
| low_volatility | short_interest_contrarian | 0.949 |
| quality_profitability | sentiment_timing | 0.945 |

### Top 10 Least Correlated Pairs (Best Diversifiers)

| Strategy A | Strategy B | Correlation |
|---|---|---|
| us_shareholder_yield | bond_duration_carry | -0.518 |
| bond_duration_carry | reit_dividend_carry | -0.518 |
| us_shareholder_yield | yield_curve_duration | -0.453 |
| yield_curve_duration | reit_dividend_carry | -0.453 |
| short_interest_contrarian | bond_duration_carry | -0.340 |
| us_cross_sectional_momentum | qmj_long_short | -0.330 |
| us_return_seasonality | bond_duration_carry | -0.320 |
| low_volatility | bond_duration_carry | -0.317 |
| pead_earnings_drift | bond_duration_carry | -0.302 |
| insider_buying | bond_duration_carry | -0.295 |

---

## Key Findings

### Consensus Picks (in ALL three schemes)

- **donchian_channel** ← **Portfolio B**
- **gtaa** ← **Portfolio B**
- **ibs_mean_reversion** ← **Portfolio B**
- **quality_profitability**
- **us_cross_sectional_momentum**
- **vix_mean_reversion** ← **Portfolio B**
- **vol_overlay** ← **Portfolio B**

### Two-Scheme Picks

- **bab_long_short** (IV, MVO)
- **bond_trend** (IV, MVO)
- **country_cape_rotation** (IV, MVO)

### Unanimous Rejects (no scheme selected them)

- bollinger_band
- bond_duration_carry
- commodity_trend
- credit_carry
- cross_asset_carry
- em_dm_carry
- industry_trend
- insider_buying
- low_volatility
- overnight_premium
- pead_earnings_drift
- quantitative_momentum
- regime_factor_rotation
- reit_dividend_carry
- sector_momentum
- sentiment_timing
- short_interest_contrarian
- turn_of_month
- us_return_seasonality
- us_shareholder_yield
- vix_etn_dual
- yield_curve_duration

### Portfolio B Sleeve Survival

| Strategy | EW | IV | MVO | Verdict |
|---|---|---|---|---|
| donchian_channel | ✓ | ✓ | ✓ | KEEP (all) |
| gtaa | ✓ | ✓ | ✓ | KEEP (all) |
| ibs_mean_reversion | ✓ | ✓ | ✓ | KEEP (all) |
| vix_mean_reversion | ✓ | ✓ | ✓ | KEEP (all) |
| vol_overlay | ✓ | ✓ | ✓ | KEEP (all) |

### Recommendation

**Add to Portfolio B (consensus):**
- quality_profitability
- us_cross_sectional_momentum

**Consider adding (2 of 3 schemes):**
- bab_long_short
- bond_trend
- country_cape_rotation
