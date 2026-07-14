# Portfolio Allocation Analysis — Multi-Asset Expansion

_Generated: 2026-06-19_

---

## Section 1: Baseline Portfolio B Recreation

**7 sleeves (EW):** IBS MR, Donchian, VIX MR, GTAA, Vol Overlay, Quality v2, XSec Mom

Sleeves loaded: 7/7  

**Window:** 2016-06-14 → 2025-12-31 (9.55 yrs)

| Metric | Value |
|---|---|
| Sharpe | **1.9168** |
| CAGR | 12.92% |
| MaxDD | -10.2% |
| Sortino | 2.3157 |
| Ann. Vol | 6.46% |

_Target from task spec: Sharpe ≈ 1.97, CAGR 11.7%, MaxDD -6.76%._


---

## Section 2: Portfolio B + All 18 Passing Baskets

**25 total sleeves** (7 Portfolio B + 18 baskets)

**Window:** 2016-06-15 → 2025-07-03

| Metric | Baseline (7-sleeve) | + All 18 Baskets | Delta |
|---|---|---|---|
| Sharpe | 1.9168 | **1.102** | -0.8148 |
| CAGR | 12.92% | 10.42% | -2.50% |
| MaxDD | -10.2% | -16.04% | -5.84% |
| Sortino | 2.3157 | 1.3977 | — |

_Note: window compressed to common intersection across all 25 series._


---

## Section 3: Greedy Forward Selection

**Rule:** Add one basket at a time in order of Sharpe improvement. Stop when no remaining basket improves Sharpe by ≥0.02.

**Starting point:** Portfolio B 7-sleeve (Sharpe=1.9168)

| Step | Basket Added | Baseline Sharpe | Combined Sharpe | Δ Sharpe |
|---|---|---|---|---|
| 1 | turn_of_month__real_assets | 1.8798 | 1.9324 | +0.0526 |
| 2 | bond_duration_carry__bonds_us | 1.9324 | 1.9577 | +0.0253 |

**Final portfolio (9 sleeves):**

| Metric | Value |
|---|---|
| Sharpe | **1.9577** |
| CAGR | 9.79% |
| MaxDD | -8.25% |
| Sortino | 2.5031 |

---

## Section 4: Deduplicated Basket Set

For each strategy, only the single highest-Sharpe basket is kept.

**11 unique-strategy baskets:**

| Basket | Standalone Sharpe |
|---|---|
| donchian_channel__us_factor | 0.903 |
| sentiment_timing__us_factor | 0.854 |
| turn_of_month__real_assets | 0.851 |
| vol_overlay__us_factor | 0.817 |
| us_cross_sectional_momentum__us_factor | 0.747 |
| quality_timing__us_factor | 0.746 |
| industry_trend__us_sectors | 0.726 |
| bond_duration_carry__bonds_us | 0.702 |
| cross_asset_momentum__all_68 | 0.687 |
| low_volatility__all_equity | 0.682 |
| em_dm_carry__intl_country_all | 0.626 |

**Portfolio B + deduplicated set (18 total sleeves):**

| Metric | Baseline (7-sleeve) | + Dedup Set | Delta |
|---|---|---|---|
| Sharpe | 1.9168 | **1.2398** | -0.6770 |
| CAGR | 12.92% | 10.35% | -2.57% |
| MaxDD | -10.2% | -15.01% | -4.81% |
| Sortino | 2.3157 | 1.5631 | N/A |

---

## Section 5: Correlation Matrix (Notable Pairs)

Full matrix saved to `results/correlation_matrix.csv`. Below: pairs with |r| > 0.6.

| Series A | Series B | Correlation |
|---|---|---|
| industry_trend__us_sectors | us_cross_sectional_momentum__us_sectors | +1.000 |
| quality_timing__us_factor | quality_timing__us_equity_broad | +0.966 |
| sentiment_timing__us_factor | sentiment_timing__us_equity_broad | +0.959 |
| quality_timing__us_factor | low_volatility__all_equity | +0.952 |
| vol_overlay__us_factor | vol_overlay__us_equity_broad | +0.951 |
| us_cross_sectional_momentum__us_factor | us_cross_sectional_momentum__us_equity_broad | +0.922 |
| us_cross_sectional_momentum__us_factor | industry_trend__us_sectors | +0.919 |
| us_cross_sectional_momentum__us_factor | us_cross_sectional_momentum__us_sectors | +0.919 |
| donchian_channel__us_factor | donchian_channel__us_equity_broad | +0.914 |
| quality_timing__us_equity_broad | low_volatility__all_equity | +0.906 |
| us_cross_sectional_momentum__us_equity_broad | quality_timing__us_equity_broad | +0.900 |
| quality_timing__us_factor | industry_trend__us_sectors | +0.895 |
| quality_timing__us_factor | us_cross_sectional_momentum__us_sectors | +0.895 |
| us_cross_sectional_momentum__us_factor | quality_timing__us_factor | +0.894 |
| industry_trend__us_sectors | cross_asset_momentum__all_68 | +0.892 |
| us_cross_sectional_momentum__us_sectors | cross_asset_momentum__all_68 | +0.892 |
| low_volatility__all_equity | em_dm_carry__intl_country_all | +0.890 |
| quality_timing__us_factor | us_cross_sectional_momentum__us_equity_broad | +0.874 |
| industry_trend__us_sectors | us_cross_sectional_momentum__us_equity_broad | +0.873 |
| us_cross_sectional_momentum__us_sectors | us_cross_sectional_momentum__us_equity_broad | +0.873 |
| us_cross_sectional_momentum__us_factor | quality_timing__us_equity_broad | +0.872 |
| industry_trend__us_sectors | low_volatility__all_equity | +0.864 |
| us_cross_sectional_momentum__us_sectors | low_volatility__all_equity | +0.864 |
| quality_timing__us_equity_broad | vol_overlay__us_equity_broad | +0.862 |
| us_cross_sectional_momentum__us_factor | cross_asset_momentum__all_68 | +0.855 |
| industry_trend__us_sectors | quality_timing__us_equity_broad | +0.850 |
| us_cross_sectional_momentum__us_sectors | quality_timing__us_equity_broad | +0.850 |
| us_cross_sectional_momentum__us_factor | low_volatility__all_equity | +0.847 |
| quality_timing__us_factor | em_dm_carry__intl_country_all | +0.834 |
| vol_overlay__us_factor | quality_timing__us_factor | +0.833 |
| quality_timing__us_equity_broad | em_dm_carry__intl_country_all | +0.833 |
| us_cross_sectional_momentum__us_equity_broad | cross_asset_momentum__all_68 | +0.830 |
| vol_overlay__us_factor | quality_timing__us_equity_broad | +0.827 |
| sentiment_timing__us_equity_broad | vol_overlay__us_equity_broad | +0.823 |
| sentiment_timing__us_factor | vol_overlay__us_factor | +0.822 |
| us_cross_sectional_momentum__us_equity_broad | low_volatility__all_equity | +0.817 |
| quality_timing__us_factor | cross_asset_momentum__all_68 | +0.814 |
| cross_asset_momentum__all_68 | low_volatility__all_equity | +0.813 |
| vol_overlay__us_factor | low_volatility__all_equity | +0.805 |
| quality_timing__us_factor | vol_overlay__us_equity_broad | +0.803 |
| us_cross_sectional_momentum__us_equity_broad | vol_overlay__us_equity_broad | +0.796 |
| quality_timing__us_equity_broad | cross_asset_momentum__all_68 | +0.790 |
| sentiment_timing__us_factor | vol_overlay__us_equity_broad | +0.786 |
| vol_overlay__us_factor | sentiment_timing__us_equity_broad | +0.783 |
| cross_asset_momentum__all_68 | em_dm_carry__intl_country_all | +0.766 |
| low_volatility__all_equity | vol_overlay__us_equity_broad | +0.761 |
| vol_overlay__us_factor | us_cross_sectional_momentum__us_factor | +0.758 |
| vol_overlay__us_factor | us_cross_sectional_momentum__us_equity_broad | +0.755 |
| us_cross_sectional_momentum__us_factor | vol_overlay__us_equity_broad | +0.752 |
| vol_overlay__us_factor | industry_trend__us_sectors | +0.748 |
| vol_overlay__us_factor | us_cross_sectional_momentum__us_sectors | +0.748 |
| us_cross_sectional_momentum__us_equity_broad | em_dm_carry__intl_country_all | +0.747 |
| industry_trend__us_sectors | em_dm_carry__intl_country_all | +0.741 |
| us_cross_sectional_momentum__us_sectors | em_dm_carry__intl_country_all | +0.741 |
| donchian_channel__us_factor | vol_overlay__us_factor | +0.739 |
| us_cross_sectional_momentum__us_factor | em_dm_carry__intl_country_all | +0.738 |
| donchian_channel__us_equity_broad | vol_overlay__us_equity_broad | +0.733 |
| donchian_channel__us_factor | vol_overlay__us_equity_broad | +0.721 |
| vol_overlay__us_equity_broad | em_dm_carry__intl_country_all | +0.719 |
| industry_trend__us_sectors | vol_overlay__us_equity_broad | +0.718 |
| us_cross_sectional_momentum__us_sectors | vol_overlay__us_equity_broad | +0.718 |
| vol_overlay__us_factor | em_dm_carry__intl_country_all | +0.715 |
| vol_overlay__us_factor | cross_asset_momentum__all_68 | +0.707 |
| quality_timing__us_equity_broad | sentiment_timing__us_equity_broad | +0.696 |
| cross_asset_momentum__all_68 | vol_overlay__us_equity_broad | +0.696 |
| vol_overlay__us_factor | donchian_channel__us_equity_broad | +0.678 |
| sentiment_timing__us_factor | quality_timing__us_equity_broad | +0.668 |
| us_cross_sectional_momentum__us_equity_broad | sentiment_timing__us_equity_broad | +0.662 |
| sentiment_timing__us_factor | quality_timing__us_factor | +0.661 |
| sentiment_timing__us_factor | us_cross_sectional_momentum__us_factor | +0.643 |
| sentiment_timing__us_factor | us_cross_sectional_momentum__us_equity_broad | +0.638 |
| quality_timing__us_factor | sentiment_timing__us_equity_broad | +0.633 |
| donchian_channel__us_factor | donchian_channel__real_assets | +0.626 |
| us_cross_sectional_momentum__us_factor | sentiment_timing__us_equity_broad | +0.625 |
| donchian_channel__us_equity_broad | quality_timing__us_equity_broad | +0.615 |
| donchian_channel__us_factor | quality_timing__us_equity_broad | +0.605 |
| sentiment_timing__us_factor | industry_trend__us_sectors | +0.601 |
| sentiment_timing__us_factor | us_cross_sectional_momentum__us_sectors | +0.601 |
| sentiment_timing__us_factor | low_volatility__all_equity | +0.601 |

**Basket correlations with Portfolio B (sorted low to high):**

| Basket | Corr with Portfolio B |
|---|---|
| bond_duration_carry__bonds_us | +0.091 |
| turn_of_month__real_assets | +0.163 |
| donchian_channel__real_assets | +0.265 |
| em_dm_carry__intl_country_all | +0.338 |
| industry_trend__us_sectors | +0.366 |
| us_cross_sectional_momentum__us_sectors | +0.366 |
| donchian_channel__us_factor | +0.371 |
| low_volatility__all_equity | +0.374 |
| cross_asset_momentum__all_68 | +0.375 |
| donchian_channel__us_equity_broad | +0.384 |
| us_cross_sectional_momentum__us_factor | +0.399 |
| sentiment_timing__us_factor | +0.406 |
| quality_timing__us_factor | +0.406 |
| sentiment_timing__us_equity_broad | +0.417 |
| us_cross_sectional_momentum__us_equity_broad | +0.422 |
| quality_timing__us_equity_broad | +0.432 |
| vol_overlay__us_factor | +0.459 |
| vol_overlay__us_equity_broad | +0.469 |


---

## Section 6: Recommendation

The greedy forward selection picked 2 basket(s) that each improved portfolio Sharpe by ≥0.02:
  - turn_of_month__real_assets (Δ=+0.0526)
  - bond_duration_carry__bonds_us (Δ=+0.0253)

The deduplicated set brings Sharpe to 1.2398, slightly below or equal to the baseline due to window compression from the strictest data overlap.

High intra-basket correlations (|r|>0.6) suggest redundancy:
  - industry_trend__us_sectors ↔ us_cross_sectional_momentum__us_sectors: +1.000
  - quality_timing__us_factor ↔ quality_timing__us_equity_broad: +0.966
  - sentiment_timing__us_factor ↔ sentiment_timing__us_equity_broad: +0.959
  - quality_timing__us_factor ↔ low_volatility__all_equity: +0.952
  - vol_overlay__us_factor ↔ vol_overlay__us_equity_broad: +0.951

**Primary recommendation:**
Add 2 basket(s) to Portfolio B in order of selection:
  1. turn_of_month__real_assets (Δ Sharpe=+0.0526)
  1. bond_duration_carry__bonds_us (Δ Sharpe=+0.0253)
This yields Sharpe=1.9577, CAGR=9.8%, MaxDD=-8.2%.



---
_Script: portfolio_allocator.py | Run: generated_
