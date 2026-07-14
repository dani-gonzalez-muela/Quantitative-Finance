# Overnight Premium - Bonferroni Correction: us_equity_broad (Intraday 5-min)

**Date:** 2026-06-28  
**Analysis period:** 2016-01-01 to 2026-04-01

## Methodology

### Why intraday data instead of daily OHLCV?

The previous Bonferroni test used daily OHLCV close-to-open as a proxy for the overnight return, yielding SPY net Sharpe = 0.77. However, the v1 overnight backtest that produced Sharpe ~1.16 used **true intraday overnight returns** extracted from 5-minute bar data. Daily OHLCV open prices include pre-market moves that are not tradeable at the 9:30 open price, and daily close prices include post-market activity. Using close-to-open from daily bars conflates the true overnight period (15:55 to 09:30 next day) with extended-hours moves, understating the signal quality.

### True overnight return construction (5-min bars)

- **Entry price**: close of the **15:55 bar** (last regular-session bar)
- **Exit price**: open of the **09:30 bar** on the next trading day
- **Signal**: enter only when `intraday_return < filter_threshold`
  - `intraday_return = (close_1555 - open_0930) / open_0930`
  - `filter_threshold = 0`: enter on any negative intraday day
- **Fees**: `shared/fees.py` `calculate_fees_pct()` applied per-trade with actual prices
  - Mode: shared/fees.py (per-trade, price-dependent)
- **Grid**: `filter_threshold` in [0, -0.001, -0.002, -0.003, -0.005]
- **Bonferroni threshold**: alpha = 0.05 / 4 = **0.0125**

### Three-gate significance test (all required)

1. One-sided t-test: p < 0.0125
2. Bootstrap 5th-percentile annualised Sharpe > 0 (2000 draws)
3. Sign-randomisation permutation test: p < 0.0125 (2000 permutations)
   - Each trade return multiplied by random +/-1 (shuffling does not change Sharpe)

## Validation

**SPY with `filter_threshold=0` (all negative-intraday days):**

| Metric | Value |
|--------|-------|
| Net Sharpe (annualised) | **0.8330** |
| N trades | 1176 |
| Avg fee per trade | 0.931 bps |
| Target (v1 result) | ~1.16 |
| Match | MISMATCH - investigate |

## Per-Ticker Results

### SPY - FAIL

| Metric | Value |
|--------|-------|
| Optimal threshold | `-0.001` |
| Net Sharpe (annualised) | **0.8491** |
| CAGR | 3.86% |
| Max Drawdown | -16.37% |
| N trades | 982 |
| Avg fee RT | 0.93 bps |

**Gate results (Bonferroni alpha = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 - t-test | p < 0.0125 | p = 0.047006 | FAIL |
| 2 - bootstrap | 5th pct Sharpe > 0 | -0.0355 | FAIL |
| 3 - permutation | p < 0.0125 | p = 0.0385 | FAIL |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.833 | 1176 | 3.913 | 0.5655 |
| -0.001 | 0.8491 | 982 | 4.265 | 0.5631 <- best |
| -0.002 | 0.6533 | 818 | 3.51 | 0.5538 |
| -0.003 | 0.6452 | 673 | 3.698 | 0.5572 |
| -0.005 | 0.748 | 482 | 4.617 | 0.5602 |

### QQQ - FAIL

| Metric | Value |
|--------|-------|
| Optimal threshold | `-0.001` |
| Net Sharpe (annualised) | **0.7128** |
| CAGR | 3.89% |
| Max Drawdown | -17.72% |
| N trades | 1034 |
| Avg fee RT | 1.21 bps |

**Gate results (Bonferroni alpha = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 - t-test | p < 0.0125 | p = 0.074531 | FAIL |
| 2 - bootstrap | 5th pct Sharpe > 0 | -0.1128 | FAIL |
| 3 - permutation | p < 0.0125 | p = 0.0705 | FAIL |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.6814 | 1163 | 3.869 | 0.5563 |
| -0.001 | 0.7128 | 1034 | 4.219 | 0.5629 <- best |
| -0.002 | 0.5108 | 908 | 3.112 | 0.5485 |
| -0.003 | 0.3378 | 798 | 2.096 | 0.5464 |
| -0.005 | 0.6052 | 629 | 3.857 | 0.5612 |

### IWM - FAIL

| Metric | Value |
|--------|-------|
| Optimal threshold | `-0.003` |
| Net Sharpe (annualised) | **0.8459** |
| CAGR | 4.45% |
| Max Drawdown | -17.00% |
| N trades | 941 |
| Avg fee RT | 1.57 bps |

**Gate results (Bonferroni alpha = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 - t-test | p < 0.0125 | p = 0.051232 | FAIL |
| 2 - bootstrap | 5th pct Sharpe > 0 | 0.0401 | PASS |
| 3 - permutation | p < 0.0125 | p = 0.0545 | FAIL |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.8078 | 1261 | 4.635 | 0.5726 |
| -0.001 | 0.8028 | 1155 | 4.709 | 0.5706 |
| -0.002 | 0.8207 | 1044 | 4.89 | 0.5738 |
| -0.003 | 0.8459 | 941 | 5.212 | 0.576 <- best |
| -0.005 | 0.4835 | 751 | 3.178 | 0.5606 |

### MDY - FAIL

| Metric | Value |
|--------|-------|
| Optimal threshold | `-0.003` |
| Net Sharpe (annualised) | **0.3660** |
| CAGR | 1.45% |
| Max Drawdown | -19.29% |
| N trades | 844 |
| Avg fee RT | 0.83 bps |

**Gate results (Bonferroni alpha = 0.0125):**

| Gate | Criterion | Value | Result |
|------|-----------|-------|--------|
| 1 - t-test | p < 0.0125 | p = 0.251574 | FAIL |
| 2 - bootstrap | 5th pct Sharpe > 0 | -0.5572 | FAIL |
| 3 - permutation | p < 0.0125 | p = 0.2415 | FAIL |

**Grid search:**

| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |
|-----------|--------|----------|----------------|----------|
| 0 | 0.2919 | 1208 | 1.553 | 0.5488 |
| -0.001 | 0.2161 | 1085 | 1.19 | 0.5465 |
| -0.002 | 0.2342 | 952 | 1.344 | 0.5473 |
| -0.003 | 0.366 | 844 | 2.192 | 0.5498 <- best |
| -0.005 | 0.145 | 644 | 0.915 | 0.5404 |

## Conclusion

**No tickers pass all three gates at Bonferroni alpha = 0.0125.**

The us_equity_broad basket remains excluded from Portfolio A v2's overnight sleeve.

**Excluded (failed at least 1 gate):** SPY, QQQ, IWM, MDY.

Validation: SPY true-intraday overnight Sharpe at threshold=0 = 0.8330 (MISMATCH - investigate)