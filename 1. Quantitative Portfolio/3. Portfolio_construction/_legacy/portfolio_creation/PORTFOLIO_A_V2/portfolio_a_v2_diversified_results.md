# Portfolio A v2 — Diversified (No-EMA)

**Date:** 2026-06-27  
**Window:** 2016-06-14 → 2025-07-03  
**EMA strategies excluded** — EMA v2 Sharpe (3.87) is inflated by in-sample basket param selection.  
**Threshold:** delta ≥ -0.05  

---

## Greedy Selection

| Step | Added | Sharpe After | Δ |
|---|---|---|---|
| 0 | ibs_mean_reversion_v2 | 2.0018 | +0.0000 |
| 1 | intraday_momentum | 2.3151 | +0.3133 |
| 2 | congress_s3_quiver | 2.3467 | +0.0316 |
| 3 | overnight | 2.3288 | -0.0179 |
| 4 | ibs_mean_reversion | 2.3099 | -0.0189 |
| 5 | vix_mean_reversion | 2.2810 | -0.0289 |
| 6 | intraday_momentum_v2 | 2.2799 | -0.0011 |
| 7 | vix_etn_dual | 2.2688 | -0.0111 |
| 8 | vwap_trend | 2.3075 | +0.0388 |
| 9 | overnight_v2 | 2.2831 | -0.0244 |

---

## Final Portfolio

**10 strategies (equal weight)**

| Strategy | Sharpe (solo) |
|---|---|
| ibs_mean_reversion_v2 | 2.0023 |
| intraday_momentum | 1.4703 |
| congress_s3_quiver | 0.8865 |
| overnight | 0.7536 |
| ibs_mean_reversion | 1.3542 |
| vix_mean_reversion | 1.1807 |
| intraday_momentum_v2 | 0.8008 |
| vix_etn_dual | 0.8708 |
| vwap_trend | 0.8015 |
| overnight_v2 | 0.5849 |

| Metric | Value |
|---|---|
| Sharpe | 2.2831 |
| CAGR | 10.64% |
| MaxDD | -3.31% |
| Sortino | 3.4016 |

## Annual Returns

| Year | Return |
|---|---|
| 2017 | 4.71% |
| 2018 | 9.73% |
| 2019 | 6.19% |
| 2020 | 23.34% |
| 2021 | 15.47% |
| 2022 | 12.04% |
| 2023 | 7.31% |
| 2024 | 6.52% |
| 2025 | 5.43% |

---

## Correlation Matrix

|                       |   ibs_mean_reversion_v2 |   intraday_momentum |   congress_s3_quiver |   overnight |   ibs_mean_reversion |   vix_mean_reversion |   intraday_momentum_v2 |   vix_etn_dual |   vwap_trend |   overnight_v2 |
|:----------------------|------------------------:|--------------------:|---------------------:|------------:|---------------------:|---------------------:|-----------------------:|---------------:|-------------:|---------------:|
| ibs_mean_reversion_v2 |                   1     |               0.106 |               -0.066 |       0.174 |                0.765 |                0.338 |                  0.123 |          0.215 |        0.053 |          0.209 |
| intraday_momentum     |                   0.106 |               1     |                0.02  |       0.045 |                0.017 |                0.037 |                  0.797 |         -0.169 |        0.35  |          0.057 |
| congress_s3_quiver    |                  -0.066 |               0.02  |                1     |       0.12  |               -0.026 |               -0.024 |                  0.016 |         -0.01  |        0.02  |          0.036 |
| overnight             |                   0.174 |               0.045 |                0.12  |       1     |                0.229 |                0.051 |                  0.06  |          0.026 |        0.064 |          0.56  |
| ibs_mean_reversion    |                   0.765 |               0.017 |               -0.026 |       0.229 |                1     |                0.29  |                  0.023 |          0.236 |        0.045 |          0.227 |
| vix_mean_reversion    |                   0.338 |               0.037 |               -0.024 |       0.051 |                0.29  |                1     |                  0.055 |          0.104 |        0.02  |          0.065 |
| intraday_momentum_v2  |                   0.123 |               0.797 |                0.016 |       0.06  |                0.023 |                0.055 |                  1     |         -0.162 |        0.33  |          0.071 |
| vix_etn_dual          |                   0.215 |              -0.169 |               -0.01  |       0.026 |                0.236 |                0.104 |                 -0.162 |          1     |       -0.082 |         -0.079 |
| vwap_trend            |                   0.053 |               0.35  |                0.02  |       0.064 |                0.045 |                0.02  |                  0.33  |         -0.082 |        1     |          0.035 |
| overnight_v2          |                   0.209 |               0.057 |                0.036 |       0.56  |                0.227 |                0.065 |                  0.071 |         -0.079 |        0.035 |          1     |

---

## Notes

- EMA v2 (combined basket Sharpe=3.87) excluded due to in-sample overfitting: grid-searched params (21/55/0.03 ATR) are specific to the 2016-2026 training window.
- Using v1 EMA params (13/48/0.05) reproduces v1's SPY Sharpe=0.83 exactly — confirming v2 logic is correct but params are optimistic.
- VIX MR: SVXY basket test not feasible (vol ETFs not in daily data; Alpaca blocked). Using v1 SVXY equity directly (Sharpe=1.20, 72 trades, hand-tuned params).
- Overnight v2: locked to filter_threshold=0 (enter only after down days), matching v1 contrarian signal. Passes em_regional basket only.
