# Portfolio A v2 — Final (with Congress TFT)

**Date:** 2026-06-27  
**Window:** 2016-06-14 → 2025-07-02  
**EMA strategies excluded** — Sharpe inflated by in-sample param selection.  

---

## Greedy Selection Trace

| Step | Added | Sharpe After | Δ |
|---|---|---|---|
| 0 | ibs_mean_reversion_v2 | 2.0030 | +0.0000 |
| 1 | intraday_momentum | 2.3150 | +0.3130 |
| 2 | congress_trade_for_trade | 2.5100 | +0.1950 |
| 3 | congress_s3_quiver | 2.6070 | +0.0970 |
| 4 | overnight | 2.6070 | -0.0000 |
| 5 | ibs_mean_reversion | 2.5890 | -0.0180 |

---

## Final Portfolio — 6 Strategies (Equal Weight)

| Strategy | Solo Sharpe | Type |
|---|---|---|
| ibs_mean_reversion_v2 | 2.0031 | Daily mean-rev (multi-asset) |
| intraday_momentum | 1.4698 | Intraday momentum |
| congress_trade_for_trade | 1.1710 | Medium-term equity (Congress) |
| congress_s3_quiver | 0.8867 | Same-day Quiver signal |
| overnight | 0.7538 | Overnight premium (contrarian) |
| ibs_mean_reversion | 1.3545 | Daily mean-rev (v1) |

| Metric | Value |
|---|---|
| **Sharpe** | **2.5893** |
| **CAGR** | **9.43%** |
| **MaxDD** | **-3.04%** |
| **Sortino** | **4.3680** |

## Annual Returns

| Year | Return |
|---|---|
| 2017 | 6.12% |
| 2018 | 7.16% |
| 2019 | 5.50% |
| 2020 | 20.19% |
| 2021 | 13.67% |
| 2022 | 7.14% |
| 2023 | 7.93% |
| 2024 | 6.04% |
| 2025 | 6.42% |

---

## Correlation Matrix

                          ibs_mean_reversion_v2  intraday_momentum  congress_trade_for_trade  congress_s3_quiver  overnight  ibs_mean_reversion
ibs_mean_reversion_v2                     1.000              0.106                    -0.007              -0.066      0.174               0.765
intraday_momentum                         0.106              1.000                    -0.001               0.020      0.045               0.017
congress_trade_for_trade                 -0.007             -0.001                     1.000              -0.004     -0.005               0.005
congress_s3_quiver                       -0.066              0.020                    -0.004               1.000      0.120              -0.026
overnight                                 0.174              0.045                    -0.005               0.120      1.000               0.229
ibs_mean_reversion                        0.765              0.017                     0.005              -0.026      0.229               1.000

---

## Notes

- **EMA excluded**: v2 basket Sharpe=3.87 is in-sample overfit. v1 QQQ equity also shows ~2.97 (inflated — needs investigation).
- **Congress TFT**: 3% NAV per trade, 180d cap, 30d min hold. CAGR=9.3%, Sharpe=1.12. Adds +0.195 Sharpe to portfolio.
- **Congress Quiver**: same-day open on Quiver publish date, filtered by prior momentum. Adds +0.097.
- **VIX MR v1 (SVXY)** and **IMOM v2** fell below the -0.05 threshold after Congress TFT was added.
