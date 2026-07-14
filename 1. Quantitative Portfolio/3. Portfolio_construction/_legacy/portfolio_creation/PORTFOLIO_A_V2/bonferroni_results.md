# Bonferroni Analysis — Failed Basket Strategies

**Date:** 2026-06-27  
**Purpose:** For strategies where baskets failed the binomial significance test, check each individual ticker at the Bonferroni-corrected threshold p < 0.05/N to rescue any individually significant tickers.

---

## Setup

| Parameter | Value |
|---|---|
| Basket (all strategies) | us_equity_broad |
| Basket definition | SPY, QQQ, IWM, DIA, MDY, IVV, VOO (N=7) |
| Bonferroni threshold | 0.05 / 7 = **0.00714** |
| Test | One-sided t-test (H0: mean=0, HA: mean>0) |
| Normal approx | Used (valid for n > 100; all samples n > 400) |

---

## Strategy 1: Overnight Premium

**Canonical params:** `filter_threshold=0` (enter only if prior intraday return < 0)  
**Return formula:** `(next_open / today_close - 1) - 2 × TC` where TC = 0.0001  
**Data source:** `long_term/multi_asset_expansion/data/tickers/`

| Ticker | Sharpe | Mean (bps) | t-stat | p-value | n | Pass Bonferroni? |
|---|---|---|---|---|---|---|
| SPY | +0.552 | +2.56 | +1.142 | 0.127 | 1079 | ✗ |
| QQQ | +0.490 | +2.82 | +1.013 | 0.156 | 1078 | ✗ |
| IWM | +0.739 | +4.27 | +1.593 | 0.056 | 1172 | ✗ |
| DIA | N/A | N/A | N/A | N/A | N/A | No data |
| MDY | +0.155 | +0.84 | +0.329 | 0.371 | 1129 | ✗ |
| IVV | N/A | N/A | N/A | N/A | N/A | No data |
| VOO | N/A | N/A | N/A | N/A | N/A | No data |

**Result: 0/7 tickers pass Bonferroni.**  
Closest: IWM (p=0.056) — significant at p<0.10 but far from Bonferroni threshold.  
Note: All available tickers have positive mean returns and positive Sharpes, consistent with the overnight premium effect being real but weak in this equity ETF basket.

---

## Strategy 2: ORB (Opening Range Breakout)

**Canonical params:** `window_size=5min, atr_percent=10%, threshold=0.01%`  
**Data source:** `short_term/data/intraday_5min/`

| Ticker | Sharpe | Mean (bps) | t-stat | p-value | n | Pass Bonferroni? |
|---|---|---|---|---|---|---|
| SPY | +0.020 | +0.05 | +0.065 | 0.474 | 2449 | ✗ |
| QQQ | +0.627 | +2.30 | +2.027 | **0.021** | 2497 | ✗ |
| IWM | +0.153 | +0.53 | +0.493 | 0.311 | 2526 | ✗ |
| DIA | −0.193 | −0.51 | −0.624 | 1.000 | 2471 | ✗ |
| MDY | +0.389 | +1.18 | +1.257 | 0.104 | 2501 | ✗ |
| IVV | +0.226 | +0.58 | +0.731 | 0.232 | 2448 | ✗ |
| VOO | −0.113 | −0.28 | −0.365 | 1.000 | 2433 | ✗ |

**Result: 0/7 tickers pass Bonferroni.**  
Closest: QQQ (p=0.021) — passes unadjusted p<0.05 but fails Bonferroni (need p<0.00714).  
The ORB signal appears mostly noise across this basket.

---

## Strategy 3: VWAP Trend

**Canonical params:** `vwap_threshold=0.001, exit_time=15:55`  
**Data source:** `short_term/data/intraday_5min/`

| Ticker | Sharpe | Mean (bps) | t-stat | p-value | n | Pass Bonferroni? |
|---|---|---|---|---|---|---|
| SPY | +0.312 | +4.77 | +1.008 | 0.157 | 665 | ✗ |
| QQQ | +0.575 | +6.86 | +1.858 | **0.032** | 1145 | ✗ |
| IWM | −0.824 | −10.08 | −2.668 | 1.000 | 1283 | ✗ |
| DIA | −0.073 | −1.21 | −0.235 | 1.000 | 536 | ✗ |
| MDY | +0.234 | +3.43 | +0.755 | 0.225 | 697 | ✗ |
| IVV | +0.295 | +6.12 | +0.953 | 0.170 | 446 | ✗ |
| VOO | +0.429 | +9.26 | +1.387 | 0.083 | 423 | ✗ |

**Result: 0/7 tickers pass Bonferroni.**  
Closest: QQQ (p=0.032) — barely passes unadjusted p<0.05 but well above Bonferroni threshold.  
VWAP shows clear dispersion — QQQ and VOO suggest possible trend-following on large-cap tech, but IWM strongly negative, indicating no robust effect across the basket.

---

## Summary

| Strategy | Tickers Rescued | Best Individual p-value |
|---|---|---|
| Overnight | 0/7 | IWM p=0.056 |
| ORB | 0/7 | QQQ p=0.021 |
| VWAP | 0/7 | QQQ p=0.032 |

**No individual tickers were rescued from the failed baskets.** The Bonferroni threshold (p<0.00714) is strict enough that none of the individual ticker signals pass even when considered in isolation from the basket framework. This is consistent with ORB and VWAP being genuinely weak strategies on US equity ETFs (not a data artifact).

**Implication for portfolio construction:** No Bonferroni-rescued ticker equity files to add to either bucket. Proceed with the 6 candidate strategies as specified.
