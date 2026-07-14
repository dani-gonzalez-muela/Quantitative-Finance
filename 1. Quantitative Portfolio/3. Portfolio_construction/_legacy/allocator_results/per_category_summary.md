# Per-Category Asset Class Summary

*Period: 2016-01-04 to 2025-07-03 | TC: 5 bps one-way*


## Bonds Intl

**Instruments:** EMB

**Avg Sharpe across 4 strategies:** 0.476

**Best combo:** bond_duration_carry × EMB — Sharpe 0.787, CAGR 5.8%, MaxDD -14.5%

**Worst combo:** bond_trend × EMB — Sharpe 0.279, CAGR 1.9%, MaxDD -26.5%


| Strategy | Avg Sharpe |
|---|---|
| bond_duration_carry | 0.787 |
| vol_overlay | 0.444 |
| donchian_channel | 0.395 |
| bond_trend | 0.279 |


## Bonds Us

**Instruments:** TLT, IEF, SHY, TIP, LQD, HYG

**Avg Sharpe across 6 strategies:** 0.255

**Best combo:** bond_trend × SHY — Sharpe 1.422, CAGR 1.6%, MaxDD -1.4%

**Worst combo:** ibs_mean_reversion × SHY — Sharpe -2.883, CAGR -2.7%, MaxDD -22.6%


| Strategy | Avg Sharpe |
|---|---|
| bond_duration_carry | 0.531 |
| bond_trend | 0.487 |
| vol_overlay | 0.469 |
| yield_curve_duration | 0.354 |
| donchian_channel | 0.323 |
| ibs_mean_reversion | -0.568 |


## Commodities

**Instruments:** GLD, SLV, USO, GDX, PDBC

**Avg Sharpe across 4 strategies:** 0.289

**Best combo:** vol_overlay × GLD — Sharpe 0.854, CAGR 9.2%, MaxDD -18.1%

**Worst combo:** ibs_mean_reversion × SLV — Sharpe -0.234, CAGR -4.6%, MaxDD -63.1%


| Strategy | Avg Sharpe |
|---|---|
| vol_overlay | 0.422 |
| donchian_channel | 0.316 |
| commodity_trend | 0.269 |
| ibs_mean_reversion | 0.150 |


## Currencies

**Instruments:** FXB, FXC

**Avg Sharpe across 2 strategies:** -0.077

**Best combo:** vol_overlay × FXC — Sharpe 0.061, CAGR 0.1%, MaxDD -21.4%

**Worst combo:** donchian_channel × FXB — Sharpe -0.281, CAGR -2.1%, MaxDD -29.0%


| Strategy | Avg Sharpe |
|---|---|
| vol_overlay | -0.012 |
| donchian_channel | -0.141 |


## Em Country

**Instruments:** INDA, EWW

**Avg Sharpe across 6 strategies:** 0.340

**Best combo:** turn_of_month × INDA — Sharpe 0.661, CAGR 6.0%, MaxDD -25.4%

**Worst combo:** donchian_channel × EWW — Sharpe -0.038, CAGR -2.0%, MaxDD -40.8%


| Strategy | Avg Sharpe |
|---|---|
| ibs_mean_reversion | 0.459 |
| quality_timing | 0.414 |
| turn_of_month | 0.369 |
| sentiment_timing | 0.360 |
| vol_overlay | 0.262 |
| donchian_channel | 0.177 |


## Em Regional

**Instruments:** EEM

**Avg Sharpe across 6 strategies:** 0.329

**Best combo:** quality_timing × EEM — Sharpe 0.425, CAGR 6.6%, MaxDD -38.5%

**Worst combo:** ibs_mean_reversion × EEM — Sharpe 0.099, CAGR 0.5%, MaxDD -37.6%


| Strategy | Avg Sharpe |
|---|---|
| quality_timing | 0.425 |
| donchian_channel | 0.421 |
| turn_of_month | 0.395 |
| sentiment_timing | 0.372 |
| vol_overlay | 0.261 |
| ibs_mean_reversion | 0.099 |


## Intl Developed Regional

**Instruments:** EFA, EZU

**Avg Sharpe across 6 strategies:** 0.305

**Best combo:** quality_timing × EFA — Sharpe 0.480, CAGR 7.0%, MaxDD -35.5%

**Worst combo:** ibs_mean_reversion × EZU — Sharpe 0.017, CAGR -0.7%, MaxDD -35.2%


| Strategy | Avg Sharpe |
|---|---|
| quality_timing | 0.471 |
| sentiment_timing | 0.432 |
| donchian_channel | 0.314 |
| vol_overlay | 0.295 |
| turn_of_month | 0.211 |
| ibs_mean_reversion | 0.110 |


## Multi Asset

**Instruments:** gtaa_us_sectors, gtaa_em_countries, gtaa_bonds, gtaa_commodities, gtaa_real_assets, gtaa_full_universe, industry_trend_us_sectors, industry_trend_em...

**Avg Sharpe across 7 strategies:** 0.598

**Best combo:** cross_asset_momentum × cross_asset_mom_top10 — Sharpe 0.781, CAGR 14.1%, MaxDD -27.4%

**Worst combo:** gtaa × gtaa_em_countries — Sharpe 0.434, CAGR 5.4%, MaxDD -40.6%


| Strategy | Avg Sharpe |
|---|---|
| cross_asset_momentum | 0.724 |
| low_volatility | 0.722 |
| industry_trend | 0.621 |
| cross_asset_carry | 0.607 |
| gtaa | 0.560 |
| em_dm_carry | 0.543 |
| country_cape_rotation | 0.444 |


## Real Assets

**Instruments:** VNQ, VNQI, AMLP

**Avg Sharpe across 5 strategies:** 0.336

**Best combo:** turn_of_month × AMLP — Sharpe 0.835, CAGR 9.7%, MaxDD -11.9%

**Worst combo:** ibs_mean_reversion × VNQI — Sharpe -0.142, CAGR -2.0%, MaxDD -34.4%


| Strategy | Avg Sharpe |
|---|---|
| turn_of_month | 0.639 |
| donchian_channel | 0.474 |
| reit_dividend_carry | 0.223 |
| ibs_mean_reversion | 0.204 |
| vol_overlay | 0.142 |


## Us Equity Broad

**Instruments:** SPY, QQQ, IWM, MDY

**Avg Sharpe across 7 strategies:** 0.556

**Best combo:** vol_overlay × QQQ — Sharpe 0.983, CAGR 11.1%, MaxDD -15.2%

**Worst combo:** turn_of_month × IWM — Sharpe 0.158, CAGR 1.1%, MaxDD -24.8%


| Strategy | Avg Sharpe |
|---|---|
| donchian_channel | 0.721 |
| quality_timing | 0.665 |
| sentiment_timing | 0.661 |
| vol_overlay | 0.627 |
| vix_mean_reversion | 0.523 |
| turn_of_month | 0.351 |
| ibs_mean_reversion | 0.344 |


## Us Factor

**Instruments:** IWD, IWF, USMV, MTUM, DVY, PKW

**Avg Sharpe across 7 strategies:** 0.596

**Best combo:** vol_overlay × IWF — Sharpe 1.018, CAGR 11.5%, MaxDD -14.7%

**Worst combo:** ibs_mean_reversion × DVY — Sharpe 0.166, CAGR 1.2%, MaxDD -33.5%


| Strategy | Avg Sharpe |
|---|---|
| sentiment_timing | 0.776 |
| vol_overlay | 0.740 |
| donchian_channel | 0.727 |
| quality_timing | 0.690 |
| ibs_mean_reversion | 0.427 |
| vix_mean_reversion | 0.423 |
| turn_of_month | 0.392 |


## Us Sectors

**Instruments:** XLK, XLF, XLE, XLV, XLI, XLP, XLY, XLU...

**Avg Sharpe across 8 strategies:** 0.457

**Best combo:** vol_overlay × XLK — Sharpe 1.013, CAGR 11.6%, MaxDD -12.5%

**Worst combo:** donchian_channel × XLU — Sharpe -0.153, CAGR -2.6%, MaxDD -40.0%


| Strategy | Avg Sharpe |
|---|---|
| sentiment_timing | 0.597 |
| quality_timing | 0.575 |
| vol_overlay | 0.546 |
| turn_of_month | 0.463 |
| donchian_channel | 0.394 |
| vix_mean_reversion | 0.354 |
| ibs_mean_reversion | 0.329 |
| reit_dividend_carry | 0.129 |
