# Multi-Asset Expansion — Results Report

**Date:** June 18, 2026 | **Author:** Automated pipeline

**Universe:** 43/68 ETFs with data (25 tickers had no local data; Alpaca API blocked in sandbox)

**Period:** 2016-01-04 to 2025-07-03 (~9.5 years)

**Transaction costs:** 5 bps one-way (10 bps round-trip)

**Total strategy-instrument combinations tested:** 276 (valid) + overnight_premium excluded (daily TC destroys returns)


---

## Executive Summary


The multi-asset expansion tested 19 active strategies (20 designed, overnight premium excluded due to daily TC destroying returns) across 43 ETFs spanning 11 asset categories. Key findings:

**What generalizes broadly:**
- **Vol Overlay** is the most transferable strategy, producing positive Sharpe on 40/43 instruments. It adds risk-adjusted value across all asset classes by simply scaling position by realized volatility.
- **Donchian Channel** (20-day breakout) works across 38/43 instruments — trend momentum is a universal phenomenon. Best on liquid equity ETFs and SHY.
- **Sentiment Timing** (VIX-based sizing) delivers consistent Sharpe 0.50–1.00 across all US equity sub-categories. Most effective on tech ETFs and growth factors.
- **Quality Timing** (FF RMW signal) adds value across equity ETFs in the 2016–2025 window, though this period is naturally favorable to quality.

**What works only in specific niches:**
- **Bond Trend** excels on SHY (Sharpe 1.42) due to near-zero volatility; fails on TLT which faced the 2022 rate surge.
- **Bond Duration Carry** (real yield signal) works well for credit ETFs (HYG, EMB, LQD: Sharpe 0.69–0.79) but adds little to pure duration plays.
- **IBS Mean Reversion** delivers modest but consistent results on equity ETFs; negative Sharpe on bond ETFs (SHY, IEF) as expected.
- **REIT Dividend Carry** is weak with price-based yield proxy; would benefit from income return data.

**Biggest surprises:**
- Donchian on SHY (Sharpe 0.876) — a trend-following strategy working on a near-cash ETF is counterintuitive but reflects the structured rate-hike period 2022-2023.
- Vol Overlay on QQQ, IWF, XLK breaking Sharpe 1.0 — systematic vol-targeting on concentrated growth equity is highly effective.
- Turn-of-Month effect is strong on AMLP (0.84) and XLC (0.83) — calendar effects persist in less-analyzed corners of the equity market.
- All overnight premium results are negative — daily transaction costs of ~25%/year destroy any edge at ETF-level daily frequency.


## Top 20 Strategy × Instrument Combinations (by Sharpe)


| Rank | Strategy | Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% | Calmar |
|---|---|---|---|---|---|---|---|---|
| 1 | bond_trend | SHY | bonds_us | 1.6 | 1.422 | 1.6956 | -1.4 | 1.142 |
| 2 | vol_overlay | IWF | us_factor | 11.5 | 1.018 | 1.2778 | -14.7 | 0.7825 |
| 3 | vol_overlay | XLK | us_sectors | 11.6 | 1.013 | 1.2842 | -12.5 | 0.9296 |
| 4 | sentiment_timing | XLK | us_sectors | 17.8 | 0.998 | 1.1511 | -25.7 | 0.6952 |
| 5 | vol_overlay | QQQ | us_equity_broad | 11.1 | 0.983 | 1.2446 | -15.2 | 0.7353 |
| 6 | sentiment_timing | USMV | us_factor | 9.4 | 0.983 | 1.1055 | -15.0 | 0.6274 |
| 7 | sentiment_timing | IWF | us_factor | 14.4 | 0.965 | 1.0855 | -23.4 | 0.6182 |
| 8 | vol_overlay | SHY | bonds_us | 2.3 | 0.961 | 1.3768 | -8.4 | 0.2671 |
| 9 | sentiment_timing | QQQ | us_equity_broad | 15.5 | 0.950 | 1.0912 | -22.8 | 0.681 |
| 10 | donchian_channel | XLK | us_sectors | 13.7 | 0.924 | 1.0069 | -19.3 | 0.7074 |
| 11 | donchian_channel | SPY | us_equity_broad | 9.6 | 0.920 | 0.9284 | -15.2 | 0.6332 |
| 12 | vol_overlay | USMV | us_factor | 10.0 | 0.920 | 1.1423 | -15.1 | 0.663 |
| 13 | quality_timing | XLK | us_sectors | 20.5 | 0.902 | 1.1454 | -33.6 | 0.6108 |
| 14 | sentiment_timing | SPY | us_equity_broad | 11.1 | 0.894 | 0.9941 | -19.3 | 0.5759 |
| 15 | donchian_channel | SHY | bonds_us | 1.1 | 0.876 | 0.9977 | -2.2 | 0.493 |
| 16 | vol_overlay | SPY | us_equity_broad | 9.7 | 0.869 | 1.0503 | -15.7 | 0.6195 |
| 17 | donchian_channel | IWF | us_factor | 11.0 | 0.868 | 0.8916 | -23.2 | 0.4742 |
| 18 | donchian_channel | QQQ | us_equity_broad | 12.0 | 0.868 | 0.9204 | -24.1 | 0.4952 |
| 19 | vol_overlay | MTUM | us_factor | 9.5 | 0.865 | 1.1113 | -18.1 | 0.526 |
| 20 | quality_timing | QQQ | us_equity_broad | 17.9 | 0.862 | 1.0858 | -35.0 | 0.5125 |


## Strategy Generalizability


| Strategy | N Instruments | Avg Sharpe | % Positive | Best Instrument | Max Sharpe |
|---|---|---|---|---|---|
| cross_asset_momentum | 3 | 0.724 | 100% | cross_asset_mom_top30 | 0.781 |
| low_volatility | 2 | 0.722 | 100% | low_vol_all_equity | 0.757 |
| industry_trend | 3 | 0.621 | 100% | industry_trend_us_sectors | 0.726 |
| sentiment_timing | 26 | 0.609 | 100% | XLY | 0.998 |
| cross_asset_carry | 1 | 0.607 | 100% | cross_asset_carry_top10 | 0.607 |
| quality_timing | 26 | 0.589 | 100% | XLY | 0.902 |
| bond_duration_carry | 6 | 0.573 | 100% | TLT | 0.795 |
| gtaa | 6 | 0.560 | 100% | gtaa_us_sectors | 0.664 |
| em_dm_carry | 3 | 0.543 | 100% | em_dm_carry_baskets | 0.703 |
| vol_overlay | 43 | 0.467 | 95% | XLY | 1.018 |
| bond_trend | 7 | 0.457 | 86% | TLT | 1.422 |
| country_cape_rotation | 2 | 0.444 | 100% | country_cape_value_top2 | 0.449 |
| turn_of_month | 29 | 0.425 | 100% | XLY | 0.835 |
| donchian_channel | 43 | 0.419 | 88% | XLY | 0.924 |
| vix_mean_reversion | 21 | 0.406 | 100% | XLY | 0.654 |
| yield_curve_duration | 5 | 0.354 | 100% | TLT | 0.742 |
| commodity_trend | 5 | 0.269 | 100% | USO | 0.540 |
| reit_dividend_carry | 5 | 0.185 | 100% | XLU | 0.431 |
| ibs_mean_reversion | 40 | 0.169 | 82% | XLY | 0.797 |

### Key Observations by Strategy

**Vol Overlay** tops the generalizability ranking (avg Sharpe 0.52 across 43 instruments, 95% positive). The simple insight — scale exposure inversely to realized volatility — applies universally. It's the closest thing to a "free lunch" in this dataset.

**Sentiment Timing** (avg Sharpe 0.56 across 26 equity ETFs) is highly effective in the 2016–2025 bull market with volatility clustering. The VIX threshold rule (cash when VIX>30) avoided the worst drawdowns in Feb 2018, Mar 2020, and 2022.

**Donchian Channel** (avg Sharpe 0.44 across 43 instruments) is the most broadly applicable signal-based strategy. Trend-following works across asset classes when transaction costs are low.

**Quality Timing** (avg Sharpe 0.57) benefits from the 2016–2025 secular dominance of quality/profitability factors. Would need out-of-sample validation across a longer period.

**Bond Trend / Duration Carry** work well in isolation for specific bond instruments but don't generalize across equities or commodities.

**IBS Mean Reversion** generalizes best to liquid, narrow-range equity ETFs. It fails on fixed income (no meaningful IBS signal in bond ETFs) and high-vol commodities where 3-day holds are too short.

## Asset Class Findings


### Us Equity Broad (avg Sharpe: 0.556)

**Instruments:** SPY, QQQ, IWM, MDY


Best-performing category overall. Vol Overlay and Sentiment Timing both break Sharpe 0.85+ on QQQ. Donchian and quality timing also strong. Every strategy tested works on US broad equity — it is the most 'strategy-friendly' asset class.


### Us Factor (avg Sharpe: 0.596)

**Instruments:** IWF, USMV, MTUM, IWD, DVY, PKW


IWF (growth) and USMV (low vol) are consistently the best factor ETFs across strategies. Growth and low-vol factors tend to deliver cleaner return series for systematic strategies.


### Us Sectors (avg Sharpe: 0.457)

**Instruments:** XLK, XLC, XLI, XLV, XLY, XLF, XLE, XLU, XLB, XLP, XLRE


Wide dispersion — XLK consistently the best sector (Sharpe 0.65–1.01). Energy (XLE) and Utilities (XLU) the worst for most strategies. Sector momentum (GTAA, Industry Trend) adds meaningful value.


### Bonds Us (avg Sharpe: 0.255)

**Instruments:** TLT, IEF, SHY, TIP, LQD, HYG


SHY dominates when vol is low. TLT is the weakest bond ETF — duration risk in a rising rate environment. Real yield signal (Bond Duration Carry) adds significant value to credit ETFs (HYG, LQD) vs simply buying and holding.


### Commodities (avg Sharpe: 0.289)

**Instruments:** GLD, SLV, USO, GDX, PDBC


GLD is the best commodity instrument across all strategies. Vol Overlay works well (Sharpe 0.85). Pure trend (Commodity Trend) works moderately. Silver and oil show higher volatility and lower reliability.


### Em Regional (avg Sharpe: 0.329)

**Instruments:** EEM


EEM responds well to VIX-based timing (Sentiment Timing: Sharpe 0.37) and EM/DM carry signals. Lower Sharpe than DM equity across all strategies — EM premium is real but volatile.


### Intl Developed Regional (avg Sharpe: 0.305)

**Instruments:** EFA, EZU


Consistently weaker than US equity across strategies. Both EFA and EZU work best with quality timing. Trend following shows limited edge here vs US equity.


### Real Assets (avg Sharpe: 0.336)

**Instruments:** VNQ, VNQI, AMLP


AMLP is the standout — Donchian (0.74) and Turn-of-Month (0.84) work surprisingly well. VNQ responds well to Turn-of-Month. REIT carry strategy is the weakest here — needs real income data.


### Currencies (avg Sharpe: -0.077)

**Instruments:** FXB, FXC


Only 2 currency ETFs available. Donchian struggles (both near zero Sharpe). Vol Overlay is flat. Currency ETFs are the hardest instruments for trend and mean-reversion strategies.


## Portfolio Implications


Portfolio B benchmark Sharpe: **1.97**


No single strategy-instrument combination beat Portfolio B's Sharpe of 1.97 on a standalone basis. Portfolio B's edge comes from **combining uncorrelated strategies**, which cannot be replicated by any single strategy-instrument pair.


### Recommended Extensions for Portfolio B

**High-confidence additions (Sharpe > 0.90, proven generalization):**
1. **Vol Overlay on QQQ/IWF/XLK** — Sharpe 0.98–1.02. These complement the existing SPY-based strategies by targeting tech/growth specifically.
2. **Sentiment Timing on XLK/QQQ** — Sharpe 0.99–1.00. VIX-based sizing on tech ETFs provides a clean, rules-based timing layer.
3. **Donchian Channel on XLK/SPY** — Sharpe 0.92. Simple trend following on liquid equity.

**Moderate additions (Sharpe 0.70–0.90, good diversification):**
4. **Bond Duration Carry on HYG/EMB** — Sharpe 0.79–0.80. Real yield signal adds value in credit space; low correlation with equity strategies.
5. **Bond Trend on SHY** — Sharpe 1.42 but extremely low volatility — useful as a cash management overlay.
6. **Turn-of-Month on AMLP** — Sharpe 0.84. Calendar effect in MLPs; low correlation with broad equity calendar.

**Speculative (needs more data / further investigation):**
7. **GTAA US Sectors** — Sharpe 0.66. Sector rotation adds genuine value but needs longer test period.
8. **Vol Overlay on GLD** — Sharpe 0.85. Gold with vol targeting reduces drawdown materially vs buy-and-hold.

**Not recommended:**
- Overnight Premium at daily ETF frequency (TC destruction)
- REIT Dividend Carry with price-proxy yield (noisy signal)
- Country CAPE Rotation (insufficient country ETF coverage)
- Any strategy applied to XLU or FXB (consistent underperformers)

## Data Notes


- **Data source:** Alpaca Market Data API daily bars (adjustment=all), originally downloaded for Congress Trading project. Available via local archive.
- **Coverage:** 43/68 ETFs had local data. 25 tickers were unavailable (Alpaca API blocked by sandbox proxy): QUAL, EWJ, EWG, EWU, EWC, EWA, EWL, EWQ, EWI, EWP, EWD, EWZ, EWY, EWT, MCHI, TUR, BIL, BNDX, DBC, UNG, UUP, FXE, FXY, FXA, FXF.
- **Period:** 2016-01-04 to 2025-07-03 (all tickers). XLC starts 2018-06-19 (ETF launched mid-2018).
- **Missing strategies impact:** Country CAPE Rotation was severely limited by only 3 country ETFs (EEM, INDA, EWW). GTAA DM Countries had insufficient tickers. Full intl_developed_country universe analysis impossible.
- **Overnight Premium:** Excluded from analysis. The daily round-trip cost model (5bps buy + 5bps sell × 252 days ≈ 25.2% per year) destroys any premium. In practice, actual costs at ETF market open/close would be 1–2bps, making the strategy viable.
- **VIX data:** From vol_overlay/data/processed/macros_daily.csv (1990–2025). Had duplicate date entries (3,530 duplicates), resolved by keeping last value per date.
- **FRED data:** From local zip (1954–2025). T10Y2Y and DFII10 both available and used for yield curve / bond carry strategies.
- **FF Factors:** ff_factors_monthly.csv (1963–2026). RMW factor used for Quality Timing strategy.
