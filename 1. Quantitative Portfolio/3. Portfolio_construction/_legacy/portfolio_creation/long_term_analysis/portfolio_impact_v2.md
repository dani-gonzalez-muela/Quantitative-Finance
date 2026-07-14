# Portfolio B — Impact Analysis v2

_Computed: 2026-06-18_

## Baseline Metrics

| Portfolio | Window | Sharpe | CAGR | MaxDD | Sortino |
|---|---|---|---|---|---|
| 5-sleeve (IBS+Donchian+VIX+GTAA+VolOverlay) | 2016-06-15 → 2026-03-13 | 1.832 | 11.07% | -8.80% | 2.380 |
| 6-sleeve (+Quality v2) | 2016-06-15 → 2026-02-27 | 2.147 | 11.65% | -8.11% | 2.882 |

---

## 6th-Sleeve Individual Tests

Ranked by ΔSharpe. Baseline Sharpe is recomputed on the same common window (fair comparison).

| # | Strategy | Window | Baseline Sharpe | 6-sleeve Sharpe | ΔSharpe | CAGR | MaxDD | Sortino | Corr(new,5-port) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | us_earnings_momentum | 2016-06-15 → 2026-02-27 | 1.864 | 2.157 | +0.293 | 12.32% | -8.68% | 2.860 | -0.00 | ✅ IMPROVES |
| 2 | us_cross_sectional_momentum | 2016-06-15 → 2026-02-27 | 1.864 | 2.147 | +0.283 | 12.23% | -8.64% | 2.844 | -0.00 | ✅ IMPROVES |
| 3 | us_return_seasonality | 2016-06-15 → 2026-02-27 | 1.864 | 2.048 | +0.184 | 12.00% | -8.86% | 2.617 | 0.01 | ✅ IMPROVES |
| 4 | insider_buying | 2016-06-15 → 2026-02-27 | 1.864 | 2.043 | +0.179 | 11.96% | -8.62% | 2.607 | 0.01 | ✅ IMPROVES |
| 5 | em_dm_carry | 2016-06-15 → 2026-02-27 | 1.864 | 2.019 | +0.155 | 10.93% | -8.40% | 2.578 | 0.02 | ✅ IMPROVES |
| 6 | us_shareholder_yield | 2016-06-15 → 2026-02-27 | 1.864 | 2.009 | +0.145 | 11.98% | -9.14% | 2.506 | 0.03 | ✅ IMPROVES |
| 7 | sentiment_timing | 2016-06-15 → 2026-02-27 | 1.864 | 2.007 | +0.143 | 12.18% | -8.81% | 2.565 | 0.01 | ✅ IMPROVES |
| 8 | short_interest_contrarian | 2016-06-15 → 2025-08-29 | 1.846 | 1.976 | +0.129 | 11.75% | -8.61% | 2.504 | 0.02 | ✅ IMPROVES |
| 9 | reit_dividend_carry | 2016-06-15 → 2025-02-28 | 1.822 | 1.935 | +0.113 | 10.25% | -8.14% | 2.405 | 0.03 | ✅ IMPROVES |
| 10 | country_cape_rotation | 2016-06-15 → 2026-02-27 | 1.864 | 1.962 | +0.098 | 10.85% | -8.49% | 2.463 | 0.04 | ✅ IMPROVES |
| 11 | pead_earnings_drift | 2016-06-15 → 2025-06-30 | 1.827 | 1.891 | +0.064 | 11.40% | -9.13% | 2.340 | 0.02 | ✅ IMPROVES |
| 12 | qmj_long_short | 2016-06-15 → 2026-02-27 | 1.864 | 1.884 | +0.020 | 9.91% | -7.79% | 2.538 | -0.00 | ➡️ NEUTRAL |
| 13 | bond_duration_carry | 2016-06-15 → 2025-02-28 | 1.822 | 1.819 | -0.003 | 9.25% | -6.89% | 2.348 | 0.03 | ➡️ NEUTRAL |
| 14 | yield_curve_duration | 2016-06-15 → 2025-02-28 | 1.822 | 1.791 | -0.031 | 9.02% | -6.89% | 2.293 | -0.04 | ➡️ NEUTRAL |
| 15 | turn_of_month | 2016-06-15 → 2025-12-31 | 1.847 | 1.797 | -0.051 | 10.44% | -7.33% | 2.263 | 0.39 | ❌ HURTS |
| 16 | overnight_premium | 2016-06-15 → 2025-12-31 | 1.847 | 1.713 | -0.135 | 11.17% | -10.47% | 2.226 | 0.65 | ❌ HURTS |
| 17 | bab_long_short | 2016-06-15 → 2019-12-31 | 2.149 | 1.725 | -0.424 | 10.88% | -4.93% | 2.092 | 0.06 | ❌ HURTS |

---

## Test A — 7th-Sleeve Tests (vs 6-sleeve Quality baseline)

| # | Strategy | Window | Baseline Sharpe | 7-sleeve Sharpe | ΔSharpe | CAGR | MaxDD | Sortino | Corr(new,6-port) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | us_cross_sectional_momentum | 2016-06-15 → 2026-02-27 | 2.141 | 2.160 | +0.019 | 12.36% | -8.07% | 2.860 | 0.29 | ➡️ NEUTRAL |
| 2 | us_earnings_momentum | 2016-06-15 → 2026-02-27 | 2.141 | 2.155 | +0.014 | 12.43% | -8.21% | 2.854 | 0.31 | ➡️ NEUTRAL |
| 3 | qmj_long_short | 2016-06-15 → 2026-02-27 | 2.141 | 2.119 | -0.022 | 10.39% | -7.34% | 2.898 | 0.06 | ➡️ NEUTRAL |
| 4 | bond_duration_carry | 2016-06-15 → 2025-02-28 | 2.081 | 2.059 | -0.022 | 9.74% | -6.56% | 2.725 | 0.07 | ➡️ NEUTRAL |
| 5 | em_dm_carry | 2016-06-15 → 2026-02-27 | 2.141 | 2.112 | -0.029 | 11.25% | -8.03% | 2.705 | 0.28 | ➡️ NEUTRAL |
| 6 | yield_curve_duration | 2016-06-15 → 2025-02-28 | 2.081 | 2.048 | -0.033 | 9.54% | -6.92% | 2.725 | -0.04 | ➡️ NEUTRAL |
| 7 | reit_dividend_carry | 2016-06-15 → 2025-02-28 | 2.081 | 2.009 | -0.073 | 10.58% | -8.16% | 2.506 | 0.34 | ❌ HURTS |
| 8 | country_cape_rotation | 2016-06-15 → 2026-02-27 | 2.141 | 2.068 | -0.073 | 11.18% | -8.33% | 2.633 | 0.27 | ❌ HURTS |
| 9 | turn_of_month | 2016-06-15 → 2025-12-31 | 2.126 | 2.051 | -0.074 | 10.86% | -6.93% | 2.643 | 0.38 | ❌ HURTS |
| 10 | us_return_seasonality | 2016-06-15 → 2026-02-27 | 2.141 | 2.043 | -0.099 | 12.15% | -8.89% | 2.601 | 0.33 | ❌ HURTS |
| 11 | insider_buying | 2016-06-15 → 2026-02-27 | 2.141 | 2.037 | -0.104 | 12.12% | -8.86% | 2.599 | 0.34 | ❌ HURTS |
| 12 | us_shareholder_yield | 2016-06-15 → 2026-02-27 | 2.141 | 2.018 | -0.124 | 12.14% | -9.50% | 2.506 | 0.33 | ❌ HURTS |
| 13 | short_interest_contrarian | 2016-06-15 → 2025-08-29 | 2.109 | 1.965 | -0.144 | 11.88% | -8.81% | 2.481 | 0.34 | ❌ HURTS |
| 14 | sentiment_timing | 2016-06-15 → 2026-02-27 | 2.141 | 1.993 | -0.148 | 12.31% | -9.22% | 2.558 | 0.33 | ❌ HURTS |
| 15 | overnight_premium | 2016-06-15 → 2025-12-31 | 2.126 | 1.957 | -0.169 | 11.49% | -9.65% | 2.599 | 0.62 | ❌ HURTS |
| 16 | pead_earnings_drift | 2016-06-15 → 2025-06-30 | 2.087 | 1.896 | -0.191 | 11.58% | -9.73% | 2.333 | 0.31 | ❌ HURTS |
| 17 | bab_long_short | 2016-06-15 → 2019-12-31 | 2.376 | 1.911 | -0.465 | 10.83% | -4.54% | 2.315 | 0.07 | ❌ HURTS |

---

## Test B — Best-5 Combination

Top-5 strategies by ΔSharpe (6th-sleeve test): **us_earnings_momentum, us_cross_sectional_momentum, us_return_seasonality, insider_buying, em_dm_carry**

| Configuration | Sleeves | Window | Baseline Sharpe | Combined Sharpe | ΔSharpe | CAGR | MaxDD | Sortino |
|---|---|---|---|---|---|---|---|---|
| 5-base + top-5 | 10 | 2016-06-15 → 2026-02-27 | 1.864 | 1.612 | -0.252 | 12.83% | -12.70% | 1.801 |
| 6-base + top-5 | 11 | 2016-06-15 → 2026-02-27 | 2.141 | 1.581 | -0.560 | 12.83% | -12.62% | 1.781 |

---

## Test C — Bond Strategies vs Bond Benchmark

### yield_curve_duration

| Metric | Strategy | Benchmark (equal-weight static) | Δ (dynamic vs passive) |
|---|---|---|---|
| Sharpe | 0.369 | N/A | — |
| CAGR | 3.78% | N/A | — |
| MaxDD | -21.90% | N/A | — |
| Note | — | Constituent ETF curves not separately available. Dynamic strategy Sharpe reported standalone. | — |

### bond_duration_carry

| Metric | Strategy | Benchmark (equal-weight static) | Δ (dynamic vs passive) |
|---|---|---|---|
| Sharpe | 0.423 | N/A | — |
| CAGR | 3.88% | N/A | — |
| MaxDD | -21.46% | N/A | — |
| Note | — | Constituent ETF curves not separately available. Dynamic strategy Sharpe reported standalone. | — |

---

## Notes

- All equity curves normalized to $100,000 starting capital
- Business-day reindex with forward-fill applied (handles weekend/holiday gaps)
- Baseline Sharpe always recomputed on the **same** common window as the test strategy
- Vol Overlay: `overlay_1p0x.csv` (columns: `entry_time`, `pct_return_gross`)
- GTAA: unnamed index column detected and handled automatically
- MaxDD WARNING threshold: < −15%
- ΔSharpe thresholds: IMPROVES > +0.05 | NEUTRAL ±0.05 | HURTS < −0.05