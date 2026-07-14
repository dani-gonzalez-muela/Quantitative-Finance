# Greedy Forward Selection — Portfolio A (Short-Term Strategies)

**Analysis date:** 2026-06-19  
**Common date range (inner join):** 2016-06-15 → 2025-08-13 (2304 trading days)  
**Significance filter:** Sharpe ≥ 0.4 AND t-stat ≥ 1.5  
**Greedy improvement threshold:** Δ Sharpe ≥ 0.02  

---

## Section 1: All Candidates — Standalone Sharpe

| Strategy | Sharpe | t-stat | Filter |
|---|---|---|---|
| ema_crossover | 2.0307 | 6.1402 | ✅ PASS |
| ibs_mean_reversion | 1.3761 | 4.1611 | ✅ PASS |
| vix_mean_reversion | 1.2134 | 3.6691 | ✅ PASS |
| intraday_momentum | 1.1407 | 3.4493 | ✅ PASS |
| overnight_premium | 0.9207 | 2.7838 | ✅ PASS |
| vix_etn_dual | 0.8857 | 2.6782 | ✅ PASS |
| congress_s3_quiver | 0.8525 | 2.5777 | ✅ PASS |
| orb | 0.8109 | 2.4521 | ✅ PASS |
| overnight | 0.7945 | 2.4024 | ✅ PASS |
| vwap_trend | 0.7724 | 2.3355 | ✅ PASS |
| turn_of_month | 0.7224 | 2.1844 | ✅ PASS |

---

## Section 2: Greedy Selection Trace

**Seed strategy:** `ema_crossover` (highest standalone Sharpe among filtered candidates)  

| Step | Strategy Added | Sharpe Before | Sharpe After | Δ Sharpe | N Sleeves | Corr w/ Portfolio |
|---|---|---|---|---|---|---|
| 1 | ibs_mean_reversion | 2.0307 | 2.4839 | 0.4532 | 2 | -0.027 |
| 2 | congress_s3_quiver | 2.4839 | 2.5555 | 0.0717 | 3 | 0.004 |

**Greedy stopped:** no remaining strategy improved Sharpe by ≥ 0.02


---

## Section 3: Final Portfolio A

**Selected strategies (3):** `ema_crossover`, `ibs_mean_reversion`, `congress_s3_quiver`

### Per-Strategy Metrics (on aligned period)

| Strategy | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| ema_crossover | 2.0307 | 24.79% | -8.30% |
| ibs_mean_reversion | 1.3761 | 11.43% | -7.86% |
| congress_s3_quiver | 0.8525 | 7.07% | -10.53% |

### Combined EW Portfolio Metrics

| Metric | Value |
|---|---|
| Sharpe  | 2.5555 |
| CAGR    | 14.52% |
| MaxDD   | -3.81% |
| Sortino | 4.9220 |

### Correlation Matrix (Selected Strategies)

| Strategy | ema_crossover | ibs_mean_reversion | congress_s3_quiver |
|---|---|---|---|
| ema_crossover | 1.000 | -0.027 | 0.024 |
| ibs_mean_reversion | -0.027 | 1.000 | -0.026 |
| congress_s3_quiver | 0.024 | -0.026 | 1.000 |

---

## Section 4: Strategies Not Selected

| Strategy | Reason |
|---|---|
| vix_mean_reversion | Failed greedy threshold (δ=-0.0434 < 0.02) |
| intraday_momentum | Failed greedy threshold (δ=-0.0181 < 0.02) |
| overnight_premium | Failed greedy threshold (δ=-0.2747 < 0.02) |
| vix_etn_dual | Failed greedy threshold (δ=-0.2557 < 0.02) |
| orb | Failed greedy threshold (δ=-0.0145 < 0.02) |
| overnight | Failed greedy threshold (δ=-0.0096 < 0.02) |
| vwap_trend | Failed greedy threshold (δ=-0.4669 < 0.02) |
| turn_of_month | Failed greedy threshold (δ=-0.1465 < 0.02) |

---

## Section 5: Comparison to Existing Portfolio A

**Comparison period (common dates):** 2016-06-15 → 2025-08-13  

| Metric | Existing Portfolio A | Greedy Portfolio A | Δ |
|---|---|---|---|
| Sharpe  | 2.6610 | 2.5555 | -0.1055 |
| CAGR    | 23.74% | 14.52% | -9.22% |
| MaxDD   | -3.59% | -3.81% | -0.23% |
| Sortino | 5.6091 | 4.9220 | -0.6871 |

**Existing Portfolio A strategies:** see `portfolio_a_1.0x.csv` equity curve  
**Greedy Portfolio A strategies:** `ema_crossover`, `ibs_mean_reversion`, `congress_s3_quiver`  
