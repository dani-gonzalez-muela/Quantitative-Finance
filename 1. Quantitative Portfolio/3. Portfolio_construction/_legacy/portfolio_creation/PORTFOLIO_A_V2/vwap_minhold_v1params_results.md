# VWAP Trend QQQ — Clean Significance Test (v1 params + minhold)

**Date:** 2026-06-28  
**Instrument:** QQQ  
**Period:** 2016-01-04 → 2026-06-23 (2,632 trading days)

---

## Parameters

| Parameter | Value |
|-----------|-------|
| Signal | Close vs cumulative intraday VWAP |
| Direction | Long when close > VWAP, Short otherwise |
| Min hold | 10 minutes |
| Slippage | 0.0 (limit-order assumption) |
| Fees | SEC fee (0.0000278) + FINRA TAF (0.000166/share) |
| Exit | EOD close at 15:55 |

---

## Performance

| Metric | Value |
|--------|-------|
| Sharpe (annualised) | **0.5514** |
| CAGR | 8.11% |
| Max Drawdown | -17.25% |

---

## Significance Gates (α = 0.05)

| Gate | Test | Result | Pass? |
|------|------|--------|-------|
| Gate 1 | One-sided t-test (H₀: mean ≤ 0) | p = 0.0374 | ✅ PASS |
| Gate 2 | Bootstrap 5th-pct Sharpe (2,000 draws) | 5th pct = 0.0437 > 0 | ✅ PASS |
| Gate 3 | Sign-permutation p-value (2,000 perms) | p = 0.037 | ✅ PASS |

**Verdict: INCLUDE (3/3 gates pass)**

---

## Validation

- No-minhold + zero-fees rebuild: Sharpe = **0.947** ✓ (matches v1 reference)
- Sharpe delta from clean to net: 0.947 → 0.551 (−0.396) attributable to minhold friction + regulatory fees

---

## Result Files

- Equity curve: `short_term/vwap_trend/results/vwap_trend_minhold_v1params_equity.csv`
- Full JSON: `short_term/vwap_trend/results/vwap_trend_minhold_v1params_results.json`
