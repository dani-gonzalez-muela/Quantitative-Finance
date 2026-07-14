# Portfolio B — New Strategy Impact Analysis

## Baseline
**5 sleeves**: IBS MR, Donchian, VIX MR, GTAA, Vol Overlay
**Window**: 2016-06-14 → 2026-03-13 (9.74 yrs)
**Sharpe**: 1.7814 | **CAGR**: 11.86% | **MaxDD**: -9.8% | **Sortino**: 2.2305

## 6-Sleeve Tests

| Configuration | Sleeves | Window | Sharpe | CAGR | MaxDD | Sortino | Corr(new,port) | ΔSharpe | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Baseline** | 5 | 2016-06-14→2026-03-13 | **1.7814** | 11.86% | -9.8% | 2.2305 | — | — | — |
| ★ + Industry Trend v2 | 6 | 2016-06-14 → 2025-12-31 | 1.5667 | 12.24% | -13.55% | 1.9616 | 0.589 | -0.2147 | ✗ HURTS | MaxDD OK |
| ★ + Quality v2 | 6 | 2016-06-14 → 2025-12-31 | 1.9593 | 12.31% | -9.2% | 2.4497 | 0.006 | +0.1779 | ✓ IMPROVES | MaxDD OK |
| ★ + Low Vol v2 | 6 | 2016-06-14 → 2025-12-31 | 1.3205 | 11.86% | -14.59% | 1.8289 | 0.551 | -0.4609 | ✗ HURTS | MaxDD OK |
| ★ + Commodity Carry | 6 | 2016-06-14 → 2025-05-12 | 1.6318 | 10.74% | -9.72% | 2.1723 | 0.097 | -0.1496 | ✗ HURTS | MaxDD OK |
|   + Commodity Trend | 6 | 2016-06-14 → 2025-05-12 | 1.5368 | 10.38% | -12.91% | 1.9453 | 0.077 | -0.2446 | ✗ HURTS | MaxDD OK |

## Batch: All Significant Strategies Together

**9 sleeves**: IBS MR, Donchian, VIX MR, GTAA, Vol Overlay, Industry Trend v2, Quality v2, Low Vol v2, Commodity Carry
**Window**: 2016-06-14 → 2025-05-12 (8.91 yrs)

| Configuration | Sleeves | Window | Sharpe | CAGR | MaxDD | Sortino | ΔSharpe | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Baseline** | 5 | 2016-06-14→2026-03-13 | 1.7814 | 11.86% | -9.8% | 2.2305 | — | — |
| **All Significant** | 9 | 2016-06-14 → 2025-05-12 | **1.2838** | 11.01% | -15.31% | 1.727 | -0.4976 | ✗ HURTS | MaxDD WARNING |

---
★ = 3/3 significance tests passed
*Generated: 2026-06-18*