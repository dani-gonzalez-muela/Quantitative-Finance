# Portfolio B Greedy Optimizer v2

**Date:** 2026-06-23  
**Universe:** 21 strategies (18 target, 0 skipped)  
**Common window:** 2017-08-31 → 2025-01-31 (90 months, ~7.5 yrs)  
**Sharpe annualisation:** monthly returns × sqrt(12)  
**Threshold:** Δ ≥ -0.05 (include unless strongly hurts)  


---

## Section 1: All Candidates — Standalone Sharpe

| Strategy | Sharpe | t-stat | Type |
|---|---|---|---|
| quality_profitability ★ | 1.1179 | 3.06 | borderline |
| turn_of_month ★ | 1.0969 | 3.00 | v2_timing |
| xs_momentum | 1.0569 | 2.89 | single_sleeve |
| bollinger_band ★ | 0.9586 | 2.63 | v2_timing |
| regime_factor_rotation ★ | 0.9211 | 2.52 | trusted |
| vol_overlay | 0.9196 | 2.52 | single_sleeve |
| quantitative_momentum | 0.9192 | 2.52 | trusted |
| sector_momentum | 0.8706 | 2.38 | v2_selection |
| gtaa | 0.8653 | 2.37 | v2_selection |
| donchian_channel | 0.8618 | 2.36 | v2_timing |
| industry_trend | 0.8402 | 2.30 | trusted |
| congress_s2 ★ | 0.7875 | 2.16 | single_sleeve |
| em_dm_carry | 0.6316 | 1.73 | borderline |
| sentiment_timing | 0.5985 | 1.64 | v2_timing |
| commodity_carry ★ | 0.5502 | 1.51 | borderline |
| country_cape_rotation | 0.4993 | 1.37 | borderline |
| credit_carry ★ | 0.4585 | 1.26 | v2_timing |
| cross_asset_carry | 0.1885 | 0.52 | borderline |
| bond_trend ★ | 0.1760 | 0.48 | borderline |
| commodity_trend | 0.0908 | 0.25 | borderline |
| yield_curve_duration ★ | 0.0290 | 0.08 | v2_timing |
★ = selected by greedy


---

## Section 2: Greedy Selection Trace

**Seed:** `quality_profitability` (Sharpe=1.1179)  

| Step | Strategy Added | Before | After | Δ | N | Corr |
|---|---|---|---|---|---|---|
| 2 | congress_s2 | 1.1179 | 1.4180 | +0.3001 | 2 | -0.092 |
| 3 | turn_of_month | 1.4180 | 1.5743 | +0.1563 | 3 | 0.316 |
| 4 | bond_trend | 1.5743 | 1.6273 | +0.0530 | 4 | -0.151 |
| 5 | commodity_carry | 1.6273 | 1.6644 | +0.0371 | 5 | -0.043 |
| 6 | regime_factor_rotation | 1.6644 | 1.6613 | -0.0031 | 6 | 0.631 |
| 7 | bollinger_band | 1.6613 | 1.6539 | -0.0074 | 7 | 0.477 |
| 8 | credit_carry | 1.6539 | 1.6445 | -0.0094 | 8 | 0.303 |
| 9 | yield_curve_duration | 1.6445 | 1.6055 | -0.0390 | 9 | 0.267 |


---

## Section 3: Final Portfolio B v2 (9 strategies)

### Per-Strategy Metrics

| Strategy | Standalone Sharpe | CAGR | MaxDD | Type |
|---|---|---|---|---|
| quality_profitability | 1.1179 | 13.02% | -13.48% | borderline |
| congress_s2 | 0.7875 | 8.54% | -11.71% | single_sleeve |
| turn_of_month | 1.0969 | 9.66% | -8.86% | v2_timing |
| bond_trend | 0.1760 | 0.67% | -13.84% | borderline |
| commodity_carry | 0.5502 | 7.38% | -41.2% | borderline |
| regime_factor_rotation | 0.9211 | 0.5% | -0.88% | trusted |
| bollinger_band | 0.9586 | 8.29% | -15.84% | v2_timing |
| credit_carry | 0.4585 | 1.19% | -5.95% | v2_timing |
| yield_curve_duration | 0.0290 | 0.04% | -9.88% | v2_timing |

### Combined EW Portfolio

| Metric | Value |
|---|---|
| Sharpe  | 1.6055 |
| CAGR    | 5.7% |
| MaxDD   | -4.92% |
| Sortino | 2.7797 |
| Window  | 2017-08-31 → 2025-01-31 (7.5 yrs) |


---

## Section 4: Correlation Matrix (Selected Strategies)

| |quality_profitability|congress_s2|turn_of_month|bond_trend|commodity_carry|regime_factor_rotation|bollinger_band|credit_carry|yield_curve_duration|
|---|---|---|---|---|---|---|---|---|---|
| quality_profitability |1.0|-0.092|0.546|-0.163|0.023|0.9|0.832|0.219|0.353|
| congress_s2 |-0.092|1.0|-0.133|-0.066|-0.044|-0.004|-0.111|-0.026|-0.041|
| turn_of_month |0.546|-0.133|1.0|-0.043|-0.023|0.583|0.44|0.221|0.273|
| bond_trend |-0.163|-0.066|-0.043|1.0|-0.098|-0.183|-0.237|0.518|0.058|
| commodity_carry |0.023|-0.044|-0.023|-0.098|1.0|0.039|0.001|0.048|-0.164|
| regime_factor_rotation |0.9|-0.004|0.583|-0.183|0.039|1.0|0.87|0.329|0.402|
| bollinger_band |0.832|-0.111|0.44|-0.237|0.001|0.87|1.0|0.199|0.339|
| credit_carry |0.219|-0.026|0.221|0.518|0.048|0.329|0.199|1.0|0.449|
| yield_curve_duration |0.353|-0.041|0.273|0.058|-0.164|0.402|0.339|0.449|1.0|


---

## Section 5: Rejected Strategies

| Strategy | Standalone | Δ if Added | Corr | Reason |
|---|---|---|---|---|
| donchian_channel | 0.8618 | -0.1080 | 0.759 | Strongly hurts |
| sentiment_timing | 0.5985 | -0.3073 | 0.776 | Strongly hurts |
| gtaa | 0.8653 | -0.0934 | 0.627 | Below threshold |
| sector_momentum | 0.8706 | -0.1457 | 0.753 | Strongly hurts |
| industry_trend | 0.8402 | -0.1846 | 0.757 | Strongly hurts |
| quantitative_momentum | 0.9192 | -0.1157 | 0.58 | Strongly hurts |
| commodity_trend | 0.0908 | -0.4279 | 0.281 | Strongly hurts |
| cross_asset_carry | 0.1885 | -0.3082 | 0.517 | Strongly hurts |
| em_dm_carry | 0.6316 | -0.1732 | 0.695 | Strongly hurts |
| country_cape_rotation | 0.4993 | -0.2314 | 0.666 | Strongly hurts |
| vol_overlay | 0.9196 | -0.0956 | 0.705 | Below threshold |
| xs_momentum | 1.0569 | -0.0734 | 0.691 | Below threshold |