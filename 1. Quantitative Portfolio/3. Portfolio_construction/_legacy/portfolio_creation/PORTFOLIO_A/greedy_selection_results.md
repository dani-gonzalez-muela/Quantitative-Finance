# Greedy Forward Selection — Portfolio A v2 (Correct Variants)

**Analysis date:** 2026-06-19  
**Common window:** 2016-06-15 -> 2025-08-13 (2304 trading days)  
**Threshold:** delta >= -0.05 (include unless it strongly hurts)  
**Fix from v1:** Correct sizing variants per strategy (matching Portfolio_A_Analysis.ipynb)  


---

## Section 0: Variant Fix vs v1

| Strategy | v1 (wrong) | v2 (correct) | Sharpe v1 | Sharpe v2 |
|---|---|---|---|---|
| ema_crossover | simple_85pct_bet | intraday_asset_vol_2pct_14d_1x_max | 1.94 | 3.0055 |
| intraday_momentum | simple_85pct_bet | intraday_asset_vol_2pct_14d_1x_max | 0.98 | 1.4894 |
| vwap_trend | simple_85pct_bet | vol_target_10pct_ann_1x_max_lev | 0.61 | 0.8077 |
| orb | simple_85pct_bet | risk-based_1pct_risk_1x_lev | 0.84 | 0.8110 |

---

## Section 1: All Candidates — Standalone Sharpe

| Strategy | Sharpe | t-stat | Variant |
|---|---|---|---|
| ema_crossover | 3.0055 | 9.09 | intraday_asset_vol_2pct_14d_1x_max |
| intraday_momentum | 1.4894 | 4.50 | intraday_asset_vol_2pct_14d_1x_max |
| ibs_mean_reversion | 1.3761 | 4.16 | simple_bet_85pct_1x |
| vix_mean_reversion | 1.2134 | 3.67 | simple_bet_85pct_1x |
| overnight_premium | 0.9207 | 2.78 | overnight_premium_daily_equity |
| vix_etn_dual | 0.8857 | 2.68 | evrp_boc_sizing_1p0x |
| congress_s3_quiver | 0.8525 | 2.58 | quiver_open_10pct_1x |
| orb | 0.8110 | 2.45 | risk-based_1pct_risk_1x_lev |
| vwap_trend | 0.8077 | 2.44 | vol_target_10pct_ann_1x_max_lev |
| overnight | 0.7945 | 2.40 | simple_85pct_bet |
| turn_of_month | 0.7224 | 2.18 | turn_of_month_daily_equity |

---

## Section 2: Greedy Selection Trace

**Seed:** `ema_crossover` (Sharpe=3.0055)  

| Step | Strategy Added | Sharpe Before | Sharpe After | delta | N | Corr |
|---|---|---|---|---|---|---|
| 1 | ibs_mean_reversion | 3.0055 | 3.3319 | +0.3264 | 2 | -0.045 |
| 2 | congress_s3_quiver | 3.3319 | 3.2984 | -0.0335 | 3 | 0.001 |
| 3 | overnight | 3.2984 | 3.2488 | -0.0497 | 4 | 0.182 |
| 4 | intraday_momentum | 3.2488 | 3.2169 | -0.0319 | 5 | 0.362 |

---

## Section 3: Final Portfolio (5 strategies)

### Per-Strategy Metrics

| Strategy | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| ema_crossover | 3.0055 | 42.58% | -5.59% |
| ibs_mean_reversion | 1.3761 | 11.43% | -7.86% |
| congress_s3_quiver | 0.8525 | 7.07% | -10.53% |
| overnight | 0.7945 | 3.44% | -7.23% |
| intraday_momentum | 1.4894 | 9.36% | -6.59% |

### Combined EW Portfolio

| Metric | Value |
|---|---|
| Sharpe  | 3.2169 |
| CAGR    | 14.27% |
| MaxDD   | -2.77% |
| Sortino | 6.1021 |

---

## Section 4: Rejected Strategies

| Strategy | Standalone | delta if Added | Corr | Verdict |
|---|---|---|---|---|
| vwap_trend | 0.8077 | -0.6534 | 0.418 | Strongly hurts (>0.10) |
| orb | 0.8110 | -0.0672 | 0.202 | Below threshold (-0.05) |
| vix_mean_reversion | 1.2134 | -0.0867 | 0.139 | Below threshold (-0.05) |
| vix_etn_dual | 0.8857 | -0.1866 | -0.023 | Strongly hurts (>0.10) |
| turn_of_month | 0.7224 | -0.1363 | 0.136 | Strongly hurts (>0.10) |
| overnight_premium | 0.9207 | -0.3240 | 0.302 | Strongly hurts (>0.10) |

---

## Section 5: Comparison to Existing Portfolio A

**Window:** 2016-06-15 -> 2025-08-13  

| Metric | Existing A (5 strat) | Greedy v2 (5 strat) | delta |
|---|---|---|---|
| Sharpe | 2.6610 | 3.2169 | +0.5559 |
| CAGR | 23.7400 | 14.2730 | -9.4670 |
| MaxDD | -3.5875 | -2.7682 | +0.8193 |
| Sortino | 5.6091 | 6.1021 | +0.4929 |

**Existing strategies:** EMA, VWAP Trend, ORB, Overnight, Intraday Mom  

**Greedy v2 strategies:** ema_crossover, ibs_mean_reversion, congress_s3_quiver, overnight, intraday_momentum  