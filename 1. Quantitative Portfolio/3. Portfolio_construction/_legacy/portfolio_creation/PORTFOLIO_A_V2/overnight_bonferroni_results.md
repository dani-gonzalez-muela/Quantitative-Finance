# Overnight Premium — Bonferroni Correction: us_equity_broad

**Date:** 2026-06-27  
**Analysis period:** 2016-01-01 — 2026-04-01

## Methodology

The overnight v2 multi-asset expansion tested 5 baskets. The `us_equity_broad` basket (SPY, QQQ, IWM, MDY) failed with `binom_k=0` — zero of four tickers cleared the basket-level significance gate. Per the statistical protocol, a failed basket triggers Bonferroni correction: test each ticker individually at a family-wise error-corrected threshold.

**Signal:** Enter long at today's close, exit at the next day's open, when the previous day's intraday return (open→close) is strictly negative. `filter_threshold` sets a minimum magnitude — enter only when `intraday_return < −threshold` (higher thresholds = more selective, fewer trades, potentially higher-quality signals).

- **Grid:** `filter_threshold` ∈ [0, 0.001, 0.002, 0.003, 0.005]
- **Fees:** SPY/QQQ = 0.5 bps/side (1 bps round-trip); IWM/MDY = 1 bps/side (2 bps RT)
- **Bonferroni threshold:** α = 0.05 / 4 = **0.0125**

**Three-gate significance test (all gates required):**
1. One-sided t-test: p < 0.0125
2. Bootstrap (5,000 draws): 5th-percentile annualised Sharpe > 0
3. Permutation test (5,000 sign-flips): p < 0.0125

## Per-Ticker Results

### SPY — ❌ FAIL

| Metric | Value |
|--------|-------|
| Optimal `filter_threshold` | `0` |
| Net Sharpe (annualised) | **0.7675** |
| CAGR | 3.82% |
| Max Drawdown | -17.39% |
| N trades | 1079 |
| Round-trip fees | 1.0 bps |

**Gate results (Bonferroni α = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 — t-test | p < 0.0125 | p = 0.056138 | ❌ |
| 2 — bootstrap | 5th pct Sharpe > 0 | -0.0158 | ❌ |
| 3 — permutation | p < 0.0125 | p = 0.055000 | ❌ |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.7675 | 1079 | 3.56 | 0.5718 ← best |
| 0.001 | 0.6672 | 894 | 3.293 | 0.5694 |
| 0.002 | 0.4159 | 746 | 2.194 | 0.559 |
| 0.003 | 0.2588 | 618 | 1.431 | 0.5615 |
| 0.005 | 0.1781 | 443 | 1.067 | 0.5553 |

### QQQ — ❌ FAIL

| Metric | Value |
|--------|-------|
| Optimal `filter_threshold` | `0.001` |
| Net Sharpe (annualised) | **0.6863** |
| CAGR | 3.74% |
| Max Drawdown | -15.44% |
| N trades | 951 |
| Round-trip fees | 1.0 bps |

**Gate results (Bonferroni α = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 — t-test | p < 0.0125 | p = 0.091218 | ❌ |
| 2 — bootstrap | 5th pct Sharpe > 0 | -0.1803 | ❌ |
| 3 — permutation | p < 0.0125 | p = 0.090600 | ❌ |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.6632 | 1078 | 3.821 | 0.5538 |
| 0.001 | 0.6863 | 951 | 4.118 | 0.5563 ← best |
| 0.002 | 0.4705 | 826 | 2.929 | 0.5472 |
| 0.003 | 0.253 | 734 | 1.597 | 0.5409 |
| 0.005 | 0.3664 | 578 | 2.383 | 0.5502 |

### IWM — ❌ FAIL

| Metric | Value |
|--------|-------|
| Optimal `filter_threshold` | `0` |
| Net Sharpe (annualised) | **0.7386** |
| CAGR | 4.87% |
| Max Drawdown | -18.79% |
| N trades | 1172 |
| Round-trip fees | 2.0 bps |

**Gate results (Bonferroni α = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 — t-test | p < 0.0125 | p = 0.055610 | ❌ |
| 2 — bootstrap | 5th pct Sharpe > 0 | -0.0083 | ❌ |
| 3 — permutation | p < 0.0125 | p = 0.056600 | ❌ |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.7386 | 1172 | 4.274 | 0.5606 ← best |
| 0.001 | 0.7049 | 1071 | 4.195 | 0.5584 |
| 0.002 | 0.6889 | 964 | 4.22 | 0.5622 |
| 0.003 | 0.7238 | 875 | 4.585 | 0.5657 |
| 0.005 | 0.3362 | 695 | 2.249 | 0.5439 |

### MDY — ❌ FAIL

| Metric | Value |
|--------|-------|
| Optimal `filter_threshold` | `0.003` |
| Net Sharpe (annualised) | **0.2042** |
| CAGR | 0.65% |
| Max Drawdown | -17.68% |
| N trades | 790 |
| Round-trip fees | 2.0 bps |

**Gate results (Bonferroni α = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 — t-test | p < 0.0125 | p = 0.358839 | ❌ |
| 2 — bootstrap | 5th pct Sharpe > 0 | -0.7184 | ❌ |
| 3 — permutation | p < 0.0125 | p = 0.369000 | ❌ |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.1554 | 1129 | 0.835 | 0.5465 |
| 0.001 | 0.0573 | 1007 | 0.318 | 0.5432 |
| 0.002 | 0.0867 | 886 | 0.501 | 0.544 |
| 0.003 | 0.2042 | 790 | 1.229 | 0.5481 ← best |
| 0.005 | 0.0245 | 605 | 0.156 | 0.5405 |

## Conclusion

**No tickers pass all three gates at Bonferroni α = 0.0125.** The `us_equity_broad` basket remains excluded from Portfolio A v2.

**Excluded (failed ≥ 1 gate):** SPY, QQQ, IWM, MDY.

_Note: SPY was validated independently in v1 with net Sharpe ≈ 1.16 using `filter_threshold=0`. Results here are consistent with that baseline._
