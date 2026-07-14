# Multi-Asset ETF Basket Backtest Report

**Generated:** 2026-06-19
**Strategies tested:** 19
**Total (strategy, basket) pairs:** 51
**Passing EW (Sharpe ≥ 0.60 & t-stat ≥ 2.0):** 18
**Passing InvVol:** 22
**Transaction costs:** 5 bps one-way (baked into individual strategy returns)

## Summary Table

Sorted by Sharpe EW descending. ✓ = Sharpe ≥ 0.60 AND t-stat ≥ 2.0.

| Strategy | Category | N | Sharpe EW | Sharpe InvVol | t-stat EW | CAGR EW | MaxDD EW | Pass EW | Pass InvVol |
|---|---|---|---|---|---|---|---|---|---|
| donchian_channel | us_factor | 6 | 0.903 | 0.921 | 2.78 | 8.1% | -14.1% | ✓ | ✓ |
| sentiment_timing | us_factor | 6 | 0.854 | 0.872 | 2.63 | 9.8% | -18.1% | ✓ | ✓ |
| turn_of_month | real_assets | 3 | 0.851 | 0.760 | 2.62 | 6.3% | -8.5% | ✓ | ✓ |
| vol_overlay | us_factor | 6 | 0.817 | 0.844 | 2.51 | 8.1% | -14.6% | ✓ | ✓ |
| donchian_channel | us_equity_broad | 4 | 0.805 | 0.807 | 2.48 | 9.2% | -21.1% | ✓ | ✓ |
| turn_of_month | us_sectors | 11 | 0.753 | 0.767 | 1.99 | 6.2% | -10.3% | ✗ | ✓ |
| us_cross_sectional_momentum | us_factor | 6 | 0.747 | 0.747 | 2.30 | 13.2% | -31.5% | ✓ | ✓ |
| quality_timing | us_factor | 6 | 0.746 | 0.760 | 2.30 | 11.8% | -36.3% | ✓ | ✓ |
| industry_trend | us_sectors | 11 | 0.726 | 0.726 | 2.24 | 12.1% | -30.1% | ✓ | ✓ |
| us_cross_sectional_momentum | us_sectors | 11 | 0.726 | 0.726 | 2.24 | 12.1% | -30.1% | ✓ | ✓ |
| bond_duration_carry | bonds_us | 8 | 0.702 | 2.332 | 2.16 | 3.0% | -9.1% | ✓ | ✓ |
| donchian_channel | real_assets | 3 | 0.702 | 0.516 | 2.16 | 6.7% | -18.1% | ✓ | ✗ |
| us_cross_sectional_momentum | us_equity_broad | 4 | 0.699 | 0.699 | 2.15 | 13.2% | -33.8% | ✓ | ✓ |
| quality_timing | us_equity_broad | 4 | 0.694 | 0.711 | 2.14 | 12.3% | -36.3% | ✓ | ✓ |
| sentiment_timing | us_equity_broad | 4 | 0.694 | 0.713 | 2.14 | 9.3% | -22.8% | ✓ | ✓ |
| cross_asset_momentum | all_68 | 68 | 0.687 | 0.687 | 2.21 | 9.7% | -26.2% | ✓ | ✓ |
| sentiment_timing | us_sectors | 11 | 0.683 | 0.687 | 1.81 | 7.4% | -17.7% | ✗ | ✗ |
| low_volatility | all_equity | 40 | 0.682 | 0.682 | 2.20 | 8.9% | -34.1% | ✓ | ✓ |
| vol_overlay | us_equity_broad | 4 | 0.674 | 0.688 | 2.07 | 6.8% | -16.0% | ✓ | ✓ |
| vol_overlay | us_sectors | 11 | 0.666 | 0.696 | 1.77 | 5.3% | -12.0% | ✗ | ✗ |
| gtaa | gtaa_core | 7 | 0.644 | 0.644 | 1.98 | 7.7% | -26.9% | ✗ | ✗ |
| quality_timing | us_sectors | 11 | 0.641 | 0.638 | 1.70 | 10.6% | -36.3% | ✗ | ✗ |
| em_dm_carry | intl_country_all | 18 | 0.626 | 0.626 | 2.02 | 10.2% | -39.6% | ✓ | ✓ |
| cross_asset_carry | all_68 | 68 | 0.612 | 0.612 | 1.97 | 7.1% | -23.2% | ✗ | ✗ |
| bond_trend | bonds_us | 8 | 0.602 | 1.056 | 1.85 | 1.8% | -8.5% | ✗ | ✓ |
| vol_overlay | bonds_us | 8 | 0.562 | 2.249 | 1.73 | 2.9% | -16.6% | ✗ | ✓ |
| vix_mean_reversion | us_equity_broad | 4 | 0.546 | 0.548 | 1.68 | 7.8% | -33.5% | ✗ | ✗ |
| country_cape_rotation | intl_country_all | 18 | 0.542 | 0.542 | 1.75 | 9.3% | -41.9% | ✗ | ✗ |
| donchian_channel | us_sectors | 11 | 0.537 | 0.518 | 1.42 | 4.6% | -11.9% | ✗ | ✗ |
| em_dm_carry | em_regional | 4 | 0.512 | 0.512 | 1.65 | 7.7% | -39.1% | ✗ | ✗ |
| quality_timing | intl_developed | 12 | 0.508 | 0.518 | 1.56 | 7.9% | -38.4% | ✗ | ✗ |
| ibs_mean_reversion | us_factor | 6 | 0.506 | 0.531 | 1.56 | 4.1% | -22.5% | ✗ | ✗ |
| sentiment_timing | em_regional | 4 | 0.495 | 0.507 | 1.52 | 6.8% | -21.2% | ✗ | ✗ |
| sentiment_timing | intl_developed | 12 | 0.494 | 0.507 | 1.52 | 5.8% | -23.2% | ✗ | ✗ |
| quality_timing | em_regional | 4 | 0.486 | 0.490 | 1.50 | 8.2% | -47.0% | ✗ | ✗ |
| ibs_mean_reversion | us_sectors | 11 | 0.485 | 0.548 | 1.29 | 3.9% | -17.6% | ✗ | ✗ |
| vol_overlay | commodities | 7 | 0.478 | 0.509 | 1.47 | 3.5% | -12.9% | ✗ | ✗ |
| vix_mean_reversion | us_factor | 6 | 0.456 | 0.451 | 1.40 | 5.7% | -35.2% | ✗ | ✗ |
| donchian_channel | em_regional | 4 | 0.438 | 0.526 | 1.35 | 4.6% | -19.5% | ✗ | ✗ |
| vix_mean_reversion | us_sectors | 11 | 0.435 | 0.410 | 1.15 | 6.0% | -34.8% | ✗ | ✗ |
| yield_curve_duration | bonds_us | 8 | 0.432 | 1.482 | 1.33 | 1.6% | -13.2% | ✗ | ✓ |
| turn_of_month | us_factor | 6 | 0.423 | 0.443 | 1.30 | 3.1% | -12.8% | ✗ | ✗ |
| ibs_mean_reversion | us_equity_broad | 4 | 0.405 | 0.428 | 1.25 | 3.8% | -31.3% | ✗ | ✗ |
| turn_of_month | us_equity_broad | 4 | 0.367 | 0.384 | 1.13 | 3.0% | -18.5% | ✗ | ✗ |
| vol_overlay | em_regional | 4 | 0.346 | 0.351 | 1.06 | 2.9% | -20.4% | ✗ | ✗ |
| vol_overlay | intl_developed | 12 | 0.341 | 0.355 | 1.05 | 3.0% | -22.2% | ✗ | ✗ |
| donchian_channel | commodities | 7 | 0.321 | 0.280 | 0.99 | 3.3% | -34.1% | ✗ | ✗ |
| donchian_channel | bonds_us | 8 | 0.318 | 1.386 | 0.98 | 0.9% | -8.8% | ✗ | ✓ |
| donchian_channel | intl_developed | 12 | 0.315 | 0.267 | 0.97 | 2.7% | -25.4% | ✗ | ✗ |
| commodity_trend | commodities | 7 | 0.276 | 0.279 | 0.85 | 2.7% | -32.2% | ✗ | ✗ |
| vol_overlay | real_assets | 3 | 0.164 | 0.179 | 0.51 | 1.1% | -18.2% | ✗ | ✗ |

## Strategy Analysis

For each strategy: which baskets passed, and how EW vs InvVol compare.

### cross_asset_momentum

Eligible baskets: **1** | Passing (EW): **1**

- **all_68**: EW=0.687 | InvVol=0.687 (Δ+0.000)  t=2.21  CAGR=9.7%  MaxDD=-26.2%  [**PASS**]

> **Interpretation:** Consistent edge across all eligible baskets — robust, broad-based alpha.

### cross_asset_carry

Eligible baskets: **1** | Passing (EW): **0**

- **all_68**: EW=0.612 | InvVol=0.612 (Δ+0.000)  t=1.97  CAGR=7.1%  MaxDD=-23.2%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### gtaa

Eligible baskets: **1** | Passing (EW): **0**

- **gtaa_core**: EW=0.644 | InvVol=0.644 (Δ+0.000)  t=1.98  CAGR=7.7%  MaxDD=-26.9%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### low_volatility

Eligible baskets: **1** | Passing (EW): **1**

- **all_equity**: EW=0.682 | InvVol=0.682 (Δ+0.000)  t=2.20  CAGR=8.9%  MaxDD=-34.1%  [**PASS**]

> **Interpretation:** Consistent edge across all eligible baskets — robust, broad-based alpha.

### sentiment_timing

Eligible baskets: **5** | Passing (EW): **2**

- **us_factor**: EW=0.854 | InvVol=0.872 (Δ+0.018)  t=2.63  CAGR=9.8%  MaxDD=-18.1%  [**PASS**]
- **us_equity_broad**: EW=0.694 | InvVol=0.713 (Δ+0.019)  t=2.14  CAGR=9.3%  MaxDD=-22.8%  [**PASS**]
- **us_sectors**: EW=0.683 | InvVol=0.687 (Δ+0.005)  t=1.81  CAGR=7.4%  MaxDD=-17.7%  [FAIL]
- **em_regional**: EW=0.495 | InvVol=0.507 (Δ+0.012)  t=1.52  CAGR=6.8%  MaxDD=-21.2%  [FAIL]
- **intl_developed**: EW=0.494 | InvVol=0.507 (Δ+0.013)  t=1.52  CAGR=5.8%  MaxDD=-23.2%  [FAIL]

> **Interpretation:** Selective edge — strongest in **us_factor**. Consider narrowing deployment to passing baskets.

### quality_timing

Eligible baskets: **5** | Passing (EW): **2**

- **us_factor**: EW=0.746 | InvVol=0.760 (Δ+0.014)  t=2.30  CAGR=11.8%  MaxDD=-36.3%  [**PASS**]
- **us_equity_broad**: EW=0.694 | InvVol=0.711 (Δ+0.016)  t=2.14  CAGR=12.3%  MaxDD=-36.3%  [**PASS**]
- **us_sectors**: EW=0.641 | InvVol=0.638 (Δ-0.003)  t=1.70  CAGR=10.6%  MaxDD=-36.3%  [FAIL]
- **intl_developed**: EW=0.508 | InvVol=0.518 (Δ+0.010)  t=1.56  CAGR=7.9%  MaxDD=-38.4%  [FAIL]
- **em_regional**: EW=0.486 | InvVol=0.490 (Δ+0.005)  t=1.50  CAGR=8.2%  MaxDD=-47.0%  [FAIL]

> **Interpretation:** Selective edge — strongest in **us_factor**. Consider narrowing deployment to passing baskets.

### turn_of_month

Eligible baskets: **4** | Passing (EW): **1**

- **real_assets**: EW=0.851 | InvVol=0.760 (Δ-0.091)  t=2.62  CAGR=6.3%  MaxDD=-8.5%  [**PASS**]
- **us_sectors**: EW=0.753 | InvVol=0.767 (Δ+0.014)  t=1.99  CAGR=6.2%  MaxDD=-10.3%  [FAIL]
- **us_factor**: EW=0.423 | InvVol=0.443 (Δ+0.020)  t=1.30  CAGR=3.1%  MaxDD=-12.8%  [FAIL]
- **us_equity_broad**: EW=0.367 | InvVol=0.384 (Δ+0.017)  t=1.13  CAGR=3.0%  MaxDD=-18.5%  [FAIL]

> **Interpretation:** Selective edge — strongest in **real_assets**. Consider narrowing deployment to passing baskets.

### ibs_mean_reversion

Eligible baskets: **3** | Passing (EW): **0**

- **us_factor**: EW=0.506 | InvVol=0.531 (Δ+0.025)  t=1.56  CAGR=4.1%  MaxDD=-22.5%  [FAIL]
- **us_sectors**: EW=0.485 | InvVol=0.548 (Δ+0.063)  t=1.29  CAGR=3.9%  MaxDD=-17.6%  [FAIL]
- **us_equity_broad**: EW=0.405 | InvVol=0.428 (Δ+0.024)  t=1.25  CAGR=3.8%  MaxDD=-31.3%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### vix_mean_reversion

Eligible baskets: **3** | Passing (EW): **0**

- **us_equity_broad**: EW=0.546 | InvVol=0.548 (Δ+0.002)  t=1.68  CAGR=7.8%  MaxDD=-33.5%  [FAIL]
- **us_factor**: EW=0.456 | InvVol=0.451 (Δ-0.005)  t=1.40  CAGR=5.7%  MaxDD=-35.2%  [FAIL]
- **us_sectors**: EW=0.435 | InvVol=0.410 (Δ-0.024)  t=1.15  CAGR=6.0%  MaxDD=-34.8%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### us_cross_sectional_momentum

Eligible baskets: **3** | Passing (EW): **3**

- **us_factor**: EW=0.747 | InvVol=0.747 (Δ+0.000)  t=2.30  CAGR=13.2%  MaxDD=-31.5%  [**PASS**]
- **us_sectors**: EW=0.726 | InvVol=0.726 (Δ+0.000)  t=2.24  CAGR=12.1%  MaxDD=-30.1%  [**PASS**]
- **us_equity_broad**: EW=0.699 | InvVol=0.699 (Δ+0.000)  t=2.15  CAGR=13.2%  MaxDD=-33.8%  [**PASS**]

> **Interpretation:** Consistent edge across all eligible baskets — robust, broad-based alpha.

### industry_trend

Eligible baskets: **1** | Passing (EW): **1**

- **us_sectors**: EW=0.726 | InvVol=0.726 (Δ+0.000)  t=2.24  CAGR=12.1%  MaxDD=-30.1%  [**PASS**]

> **Interpretation:** Consistent edge across all eligible baskets — robust, broad-based alpha.

### country_cape_rotation

Eligible baskets: **1** | Passing (EW): **0**

- **intl_country_all**: EW=0.542 | InvVol=0.542 (Δ+0.000)  t=1.75  CAGR=9.3%  MaxDD=-41.9%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### em_dm_carry

Eligible baskets: **2** | Passing (EW): **1**

- **intl_country_all**: EW=0.626 | InvVol=0.626 (Δ+0.000)  t=2.02  CAGR=10.2%  MaxDD=-39.6%  [**PASS**]
- **em_regional**: EW=0.512 | InvVol=0.512 (Δ+0.000)  t=1.65  CAGR=7.7%  MaxDD=-39.1%  [FAIL]

> **Interpretation:** Selective edge — strongest in **intl_country_all**. Consider narrowing deployment to passing baskets.

### bond_trend

Eligible baskets: **1** | Passing (EW): **0**

- **bonds_us**: EW=0.602 | InvVol=1.056 (Δ+0.455)  t=1.85  CAGR=1.8%  MaxDD=-8.5%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### bond_duration_carry

Eligible baskets: **1** | Passing (EW): **1**

- **bonds_us**: EW=0.702 | InvVol=2.332 (Δ+1.629)  t=2.16  CAGR=3.0%  MaxDD=-9.1%  [**PASS**]

> **Interpretation:** Consistent edge across all eligible baskets — robust, broad-based alpha.

### yield_curve_duration

Eligible baskets: **1** | Passing (EW): **0**

- **bonds_us**: EW=0.432 | InvVol=1.482 (Δ+1.051)  t=1.33  CAGR=1.6%  MaxDD=-13.2%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### commodity_trend

Eligible baskets: **1** | Passing (EW): **0**

- **commodities**: EW=0.276 | InvVol=0.279 (Δ+0.003)  t=0.85  CAGR=2.7%  MaxDD=-32.2%  [FAIL]

> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. Strategy may lack edge across these asset classes, or signal is too noisy when diversified at basket level.

### vol_overlay

Eligible baskets: **8** | Passing (EW): **2**

- **us_factor**: EW=0.817 | InvVol=0.844 (Δ+0.027)  t=2.51  CAGR=8.1%  MaxDD=-14.6%  [**PASS**]
- **us_equity_broad**: EW=0.674 | InvVol=0.688 (Δ+0.014)  t=2.07  CAGR=6.8%  MaxDD=-16.0%  [**PASS**]
- **us_sectors**: EW=0.666 | InvVol=0.696 (Δ+0.030)  t=1.77  CAGR=5.3%  MaxDD=-12.0%  [FAIL]
- **bonds_us**: EW=0.562 | InvVol=2.249 (Δ+1.687)  t=1.73  CAGR=2.9%  MaxDD=-16.6%  [FAIL]
- **commodities**: EW=0.478 | InvVol=0.509 (Δ+0.030)  t=1.47  CAGR=3.5%  MaxDD=-12.9%  [FAIL]
- **em_regional**: EW=0.346 | InvVol=0.351 (Δ+0.005)  t=1.06  CAGR=2.9%  MaxDD=-20.4%  [FAIL]
- **intl_developed**: EW=0.341 | InvVol=0.355 (Δ+0.014)  t=1.05  CAGR=3.0%  MaxDD=-22.2%  [FAIL]
- **real_assets**: EW=0.164 | InvVol=0.179 (Δ+0.015)  t=0.51  CAGR=1.1%  MaxDD=-18.2%  [FAIL]

> **Interpretation:** Selective edge — strongest in **us_factor**. Consider narrowing deployment to passing baskets.

### donchian_channel

Eligible baskets: **8** | Passing (EW): **3**

- **us_factor**: EW=0.903 | InvVol=0.921 (Δ+0.018)  t=2.78  CAGR=8.1%  MaxDD=-14.1%  [**PASS**]
- **us_equity_broad**: EW=0.805 | InvVol=0.807 (Δ+0.002)  t=2.48  CAGR=9.2%  MaxDD=-21.1%  [**PASS**]
- **real_assets**: EW=0.702 | InvVol=0.516 (Δ-0.186)  t=2.16  CAGR=6.7%  MaxDD=-18.1%  [**PASS**]
- **us_sectors**: EW=0.537 | InvVol=0.518 (Δ-0.019)  t=1.42  CAGR=4.6%  MaxDD=-11.9%  [FAIL]
- **em_regional**: EW=0.438 | InvVol=0.526 (Δ+0.087)  t=1.35  CAGR=4.6%  MaxDD=-19.5%  [FAIL]
- **commodities**: EW=0.321 | InvVol=0.280 (Δ-0.041)  t=0.99  CAGR=3.3%  MaxDD=-34.1%  [FAIL]
- **bonds_us**: EW=0.318 | InvVol=1.386 (Δ+1.067)  t=0.98  CAGR=0.9%  MaxDD=-8.8%  [FAIL]
- **intl_developed**: EW=0.315 | InvVol=0.267 (Δ-0.047)  t=0.97  CAGR=2.7%  MaxDD=-25.4%  [FAIL]

> **Interpretation:** Selective edge — strongest in **us_factor**. Consider narrowing deployment to passing baskets.

## Category Analysis

Which strategies have genuine edge (EW) in each asset class?

### all_68

Strategies tested: **2** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **1**

- cross_asset_momentum: Sharpe EW=0.687  InvVol=0.687  t=2.21  [**PASS**]
- cross_asset_carry: Sharpe EW=0.612  InvVol=0.612  t=1.97  [fail]

> **Verdict:** Edge is concentrated in: **cross_asset_momentum**.

### all_equity

Strategies tested: **1** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **1**

- low_volatility: Sharpe EW=0.682  InvVol=0.682  t=2.20  [**PASS**]

> **Verdict:** Edge is concentrated in: **low_volatility**.

### bonds_us

Strategies tested: **5** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **1**

- bond_duration_carry: Sharpe EW=0.702  InvVol=2.332  t=2.16  [**PASS**]
- bond_trend: Sharpe EW=0.602  InvVol=1.056  t=1.85  [fail]
- vol_overlay: Sharpe EW=0.562  InvVol=2.249  t=1.73  [fail]
- yield_curve_duration: Sharpe EW=0.432  InvVol=1.482  t=1.33  [fail]
- donchian_channel: Sharpe EW=0.318  InvVol=1.386  t=0.98  [fail]

> **Verdict:** Edge is concentrated in: **bond_duration_carry**.

### commodities

Strategies tested: **3** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **0**

- vol_overlay: Sharpe EW=0.478  InvVol=0.509  t=1.47  [fail]
- donchian_channel: Sharpe EW=0.321  InvVol=0.280  t=0.99  [fail]
- commodity_trend: Sharpe EW=0.276  InvVol=0.279  t=0.85  [fail]

> **Verdict:** No strategy shows a statistically reliable edge in this basket.

### em_regional

Strategies tested: **5** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **0**

- em_dm_carry: Sharpe EW=0.512  InvVol=0.512  t=1.65  [fail]
- sentiment_timing: Sharpe EW=0.495  InvVol=0.507  t=1.52  [fail]
- quality_timing: Sharpe EW=0.486  InvVol=0.490  t=1.50  [fail]
- donchian_channel: Sharpe EW=0.438  InvVol=0.526  t=1.35  [fail]
- vol_overlay: Sharpe EW=0.346  InvVol=0.351  t=1.06  [fail]

> **Verdict:** No strategy shows a statistically reliable edge in this basket.

### gtaa_core

Strategies tested: **1** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **0**

- gtaa: Sharpe EW=0.644  InvVol=0.644  t=1.98  [fail]

> **Verdict:** No strategy shows a statistically reliable edge in this basket.

### intl_country_all

Strategies tested: **2** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **1**

- em_dm_carry: Sharpe EW=0.626  InvVol=0.626  t=2.02  [**PASS**]
- country_cape_rotation: Sharpe EW=0.542  InvVol=0.542  t=1.75  [fail]

> **Verdict:** Edge is concentrated in: **em_dm_carry**.

### intl_developed

Strategies tested: **4** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **0**

- quality_timing: Sharpe EW=0.508  InvVol=0.518  t=1.56  [fail]
- sentiment_timing: Sharpe EW=0.494  InvVol=0.507  t=1.52  [fail]
- vol_overlay: Sharpe EW=0.341  InvVol=0.355  t=1.05  [fail]
- donchian_channel: Sharpe EW=0.315  InvVol=0.267  t=0.97  [fail]

> **Verdict:** No strategy shows a statistically reliable edge in this basket.

### real_assets

Strategies tested: **3** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **2**

- turn_of_month: Sharpe EW=0.851  InvVol=0.760  t=2.62  [**PASS**]
- donchian_channel: Sharpe EW=0.702  InvVol=0.516  t=2.16  [**PASS**]
- vol_overlay: Sharpe EW=0.164  InvVol=0.179  t=0.51  [fail]

> **Verdict:** Edge is concentrated in: **turn_of_month + donchian_channel**.

### us_equity_broad

Strategies tested: **8** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **5**

- donchian_channel: Sharpe EW=0.805  InvVol=0.807  t=2.48  [**PASS**]
- us_cross_sectional_momentum: Sharpe EW=0.699  InvVol=0.699  t=2.15  [**PASS**]
- quality_timing: Sharpe EW=0.694  InvVol=0.711  t=2.14  [**PASS**]
- sentiment_timing: Sharpe EW=0.694  InvVol=0.713  t=2.14  [**PASS**]
- vol_overlay: Sharpe EW=0.674  InvVol=0.688  t=2.07  [**PASS**]
- vix_mean_reversion: Sharpe EW=0.546  InvVol=0.548  t=1.68  [fail]
- ibs_mean_reversion: Sharpe EW=0.405  InvVol=0.428  t=1.25  [fail]
- turn_of_month: Sharpe EW=0.367  InvVol=0.384  t=1.13  [fail]

> **Verdict:** Multiple strategies pass — this basket is fertile ground. Consider a multi-strategy allocation here.

### us_factor

Strategies tested: **8** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **5**

- donchian_channel: Sharpe EW=0.903  InvVol=0.921  t=2.78  [**PASS**]
- sentiment_timing: Sharpe EW=0.854  InvVol=0.872  t=2.63  [**PASS**]
- vol_overlay: Sharpe EW=0.817  InvVol=0.844  t=2.51  [**PASS**]
- us_cross_sectional_momentum: Sharpe EW=0.747  InvVol=0.747  t=2.30  [**PASS**]
- quality_timing: Sharpe EW=0.746  InvVol=0.760  t=2.30  [**PASS**]
- ibs_mean_reversion: Sharpe EW=0.506  InvVol=0.531  t=1.56  [fail]
- vix_mean_reversion: Sharpe EW=0.456  InvVol=0.451  t=1.40  [fail]
- turn_of_month: Sharpe EW=0.423  InvVol=0.443  t=1.30  [fail]

> **Verdict:** Multiple strategies pass — this basket is fertile ground. Consider a multi-strategy allocation here.

### us_sectors

Strategies tested: **9** | Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **2**

- turn_of_month: Sharpe EW=0.753  InvVol=0.767  t=1.99  [fail]
- industry_trend: Sharpe EW=0.726  InvVol=0.726  t=2.24  [**PASS**]
- us_cross_sectional_momentum: Sharpe EW=0.726  InvVol=0.726  t=2.24  [**PASS**]
- sentiment_timing: Sharpe EW=0.683  InvVol=0.687  t=1.81  [fail]
- vol_overlay: Sharpe EW=0.666  InvVol=0.696  t=1.77  [fail]
- quality_timing: Sharpe EW=0.641  InvVol=0.638  t=1.70  [fail]
- donchian_channel: Sharpe EW=0.537  InvVol=0.518  t=1.42  [fail]
- ibs_mean_reversion: Sharpe EW=0.485  InvVol=0.548  t=1.29  [fail]
- vix_mean_reversion: Sharpe EW=0.435  InvVol=0.410  t=1.15  [fail]

> **Verdict:** Edge is concentrated in: **us_cross_sectional_momentum + industry_trend**.
