# Portfolio B Greedy Optimizer — Corrected Universe

**Date:** 2026-06-19  
**Universe:** 25 strategies (7 sleeves + 18 baskets)  
**Excluded:** ibs_mean_reversion, vix_mean_reversion (reclassified to Portfolio A)  
**Common window:** 2016-05-03 → 2025-07-02 (2305 days)  
**Threshold:** Δ ≥ -0.05 (include unless strongly hurts)  


---

## Section 1: All Candidates — Standalone Sharpe

| Strategy | Sharpe | t-stat | Type |
|---|---|---|---|
| congress_s2 ★ | 1.2673 | 3.83 | sleeve |
| vol_overlay ★ | 0.9929 | 3.00 | sleeve |
| donchian ★ | 0.9430 | 2.85 | sleeve |
| gtaa ★ | 0.9049 | 2.74 | sleeve |
| xs_momentum ★ | 0.8492 | 2.57 | sleeve |
| donchian_channel__us_factor | 0.8408 | 2.54 | basket |
| sentiment_timing__us_factor | 0.8374 | 2.53 | basket |
| turn_of_month__real_assets ★ | 0.8350 | 2.53 | basket |
| vol_overlay__us_factor | 0.8272 | 2.50 | basket |
| quality_profit ★ | 0.7918 | 2.39 | sleeve |
| bollinger_band ★ | 0.7737 | 2.34 | sleeve |
| us_cross_sectional_momentum__us_factor | 0.7542 | 2.28 | basket |
| donchian_channel__us_equity_broad | 0.7519 | 2.27 | basket |
| industry_trend__us_sectors | 0.7347 | 2.22 | basket |
| us_cross_sectional_momentum__us_sectors | 0.7347 | 2.22 | basket |
| low_volatility__all_equity | 0.7252 | 2.19 | basket |
| quality_timing__us_factor | 0.7250 | 2.19 | basket |
| vol_overlay__us_equity_broad | 0.7185 | 2.17 | basket |
| us_cross_sectional_momentum__us_equity_broad | 0.7071 | 2.14 | basket |
| sentiment_timing__us_equity_broad | 0.6947 | 2.10 | basket |
| quality_timing__us_equity_broad | 0.6849 | 2.07 | basket |
| bond_duration_carry__bonds_us ★ | 0.6298 | 1.90 | basket |
| cross_asset_momentum__all_68 | 0.6151 | 1.86 | basket |
| donchian_channel__real_assets | 0.6092 | 1.84 | basket |
| em_dm_carry__intl_country_all | 0.5115 | 1.55 | basket |
★ = selected by greedy


---

## Section 2: Greedy Selection Trace

**Seed:** `congress_s2` (Sharpe=1.2673)  

| Step | Strategy Added | Before | After | Δ | N | Corr |
|---|---|---|---|---|---|---|
| 1 | gtaa | 1.2673 | 1.5392 | +0.2719 | 2 | 0.011 |
| 2 | vol_overlay | 1.5392 | 1.7834 | +0.2442 | 3 | 0.000 |
| 3 | quality_profit | 1.7834 | 1.9201 | +0.1367 | 4 | 0.011 |
| 4 | turn_of_month__real_assets | 1.9201 | 2.0207 | +0.1006 | 5 | 0.106 |
| 5 | bond_duration_carry__bonds_us | 2.0207 | 2.0580 | +0.0373 | 6 | 0.120 |
| 6 | donchian | 2.0580 | 2.0257 | -0.0322 | 7 | 0.292 |
| 7 | xs_momentum | 2.0257 | 1.9833 | -0.0425 | 8 | 0.288 |
| 8 | bollinger_band | 1.9833 | 1.9785 | -0.0047 | 9 | 0.203 |

---

## Section 3: Final Portfolio B (9 strategies)

### Per-Strategy Metrics

| Strategy | Standalone Sharpe | CAGR | MaxDD | Type |
|---|---|---|---|---|
| congress_s2 | 1.2673 | 10.57% | -9.62% | sleeve |
| gtaa | 0.9049 | 6.65% | -9.24% | sleeve |
| vol_overlay | 0.9929 | 11.34% | -17.66% | sleeve |
| quality_profit | 0.7918 | 7.82% | -15.22% | sleeve |
| turn_of_month__real_assets | 0.8350 | 6.26% | -8.50% | basket |
| bond_duration_carry__bonds_us | 0.6298 | 2.66% | -9.06% | basket |
| donchian | 0.9430 | 11.16% | -18.71% | sleeve |
| xs_momentum | 0.8492 | 10.98% | -22.07% | sleeve |
| bollinger_band | 0.7737 | 11.54% | -27.86% | sleeve |

### Combined EW Portfolio

| Metric | Value |
|---|---|
| Sharpe  | 1.9785 |
| CAGR    | 9.22% |
| MaxDD   | -9.40% |
| Sortino | 2.6823 |

---

## Section 4: Rejected Strategies

| Strategy | Standalone | Δ if Added | Corr | Reason |
|---|---|---|---|---|
| donchian_channel__us_factor | 0.8408 | -0.0705 | 0.533 | Below threshold |
| sentiment_timing__us_factor | 0.8374 | -0.0946 | 0.531 | Below threshold |
| vol_overlay__us_factor | 0.8272 | -0.1185 | 0.636 | Strongly hurts |
| donchian_channel__us_equity_broad | 0.7519 | -0.1232 | 0.543 | Strongly hurts |
| us_cross_sectional_momentum__us_factor | 0.7542 | -0.2406 | 0.609 | Strongly hurts |
| quality_timing__us_factor | 0.7250 | -0.2364 | 0.643 | Strongly hurts |
| industry_trend__us_sectors | 0.7347 | -0.2253 | 0.587 | Strongly hurts |
| us_cross_sectional_momentum__us_sectors | 0.7347 | -0.2253 | 0.587 | Strongly hurts |
| donchian_channel__real_assets | 0.6092 | -0.0892 | 0.430 | Below threshold |
| us_cross_sectional_momentum__us_equity_broad | 0.7071 | -0.2940 | 0.636 | Strongly hurts |
| quality_timing__us_equity_broad | 0.6849 | -0.2962 | 0.672 | Strongly hurts |
| sentiment_timing__us_equity_broad | 0.6947 | -0.1662 | 0.545 | Strongly hurts |
| cross_asset_momentum__all_68 | 0.6151 | -0.2258 | 0.580 | Strongly hurts |
| low_volatility__all_equity | 0.7252 | -0.1967 | 0.617 | Strongly hurts |
| vol_overlay__us_equity_broad | 0.7185 | -0.1514 | 0.651 | Strongly hurts |
| em_dm_carry__intl_country_all | 0.5115 | -0.2950 | 0.565 | Strongly hurts |