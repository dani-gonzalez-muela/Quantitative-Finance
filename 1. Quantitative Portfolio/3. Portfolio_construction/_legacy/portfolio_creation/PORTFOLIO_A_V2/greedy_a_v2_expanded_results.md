# Greedy Forward Selection — Portfolio A v2 Expanded

**Analysis date:** 2026-06-27  
**Common window:** 2016-06-14 → 2025-07-03 (2276 trading days)  
**Threshold:** delta >= -0.05  
**New in v2 expanded:** Phase 1 multi-asset (IBS v2, VIX MR v2) + Phase 3 multi-asset if data available  

---

## Section 1: All Candidates — Standalone Sharpe

| Strategy | Sharpe | t-stat | N days | Available |
|---|---|---|---|---|
| ema_crossover_v2 | 3.8514 | 11.57 | 2276 | ✓ |
| ema_crossover | 2.9669 | 9.08 | 2362 | ✓ |
| ibs_mean_reversion_v2 | 2.0023 | 6.02 | 2276 | ✓ |
| intraday_momentum | 1.4703 | 4.50 | 2362 | ✓ |
| ibs_mean_reversion | 1.3542 | 4.15 | 2362 | ✓ |
| vix_mean_reversion | 1.1807 | 3.61 | 2362 | ✓ |
| vix_mean_reversion_v1 | 1.1717 | 3.59 | 2362 | ✓ |
| congress_s3_quiver | 0.8865 | 2.71 | 2362 | ✓ |
| vix_etn_dual | 0.8708 | 2.62 | 2276 | ✓ |
| vwap_trend | 0.8015 | 2.45 | 2362 | ✓ |
| intraday_momentum_v2 | 0.8008 | 2.41 | 2276 | ✓ |
| orb | 0.7933 | 2.43 | 2362 | ✓ |
| overnight | 0.7536 | 2.31 | 2362 | ✓ |
| overnight_v2 | 0.5849 | 1.76 | 2276 | ✓ |
| vwap_trend_v2 | 0.1308 | 0.39 | 2276 | ✓ |

---

## Section 2: Greedy Selection Trace

**Seed:** `ema_crossover_v2` (Sharpe=3.8514)  

| Step | Strategy Added | Sharpe Before | Sharpe After | delta | N | Corr |
|---|---|---|---|---|---|---|
| 1 | ibs_mean_reversion_v2 | 3.8514 | 4.3198 | +0.4684 | 2 | -0.011 |

---

## Section 3: Final Portfolio

### Strategies (2)

| Strategy | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| ema_crossover_v2 | 3.8514 | 40.58% | -4.78% |
| ibs_mean_reversion_v2 | 2.0023 | 13.47% | -5.38% |

### Combined EW Portfolio

| Metric | Value |
|---|---|
| Sharpe  | 4.3198 |
| CAGR    | 26.50% |
| MaxDD   | -2.37% |
| Sortino | 11.5670 |

---

## Section 4: Rejected Strategies

| Strategy | Standalone | delta if Added | Corr | Verdict |
|---|---|---|---|---|
| overnight | 0.7536 | -0.2438 | 0.095 | Hurts (>0.10) |
| ema_crossover | 2.9669 | -0.2984 | 0.575 | Hurts (>0.10) |
| congress_s3_quiver | 0.8865 | -0.3101 | -0.062 | Hurts (>0.10) |
| orb | 0.7933 | -0.3842 | 0.093 | Hurts (>0.10) |
| intraday_momentum_v2 | 0.8008 | -0.5392 | 0.361 | Hurts (>0.10) |
| intraday_momentum | 1.4703 | -0.5517 | 0.434 | Hurts (>0.10) |
| ibs_mean_reversion | 1.3542 | -0.7458 | 0.404 | Hurts (>0.10) |
| overnight_v2 | 0.5849 | -1.0089 | 0.085 | Hurts (>0.10) |
| vix_mean_reversion | 1.1807 | -1.1458 | 0.205 | Hurts (>0.10) |
| vwap_trend_v2 | 0.1308 | -1.2513 | 0.351 | Hurts (>0.10) |
| vix_mean_reversion_v1 | 1.1717 | -1.3140 | 0.203 | Hurts (>0.10) |
| vix_etn_dual | 0.8708 | -1.4414 | 0.053 | Hurts (>0.10) |
| vwap_trend | 0.8015 | -1.6578 | 0.324 | Hurts (>0.10) |

---

## Section 5: Comparison

| Metric | Old Portfolio A (greedy_a_v2) | New v2 Expanded | delta |
|---|---|---|---|
| Sharpe  | 3.2284 | 4.3198 | +1.0914 |
| CAGR    | 14.39% | 26.50% | +12.11% |
| MaxDD   | -2.77% | -2.37% | +0.39% |
| Sortino | 6.1080 | 11.5670 | +5.4590 |

**Old strategies:** ema_crossover, ibs_mean_reversion, congress_s3_quiver, overnight, intraday_momentum  
**New strategies:** ema_crossover_v2, ibs_mean_reversion_v2  
