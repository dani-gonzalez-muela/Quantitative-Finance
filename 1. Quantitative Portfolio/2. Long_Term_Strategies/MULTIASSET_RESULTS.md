# Multi-Asset Expansion — Results Summary

**Period**: 2016-01-01 → 2026-04-01  
**TC**: 5 bps one-way  
**Significance**: 3-gate test — t-test (p < 0.05), bootstrap Sharpe 5th-pct > 0, permutation p < 0.05  
**Implementation variant shown**: `simple_85` (85% capital deployment)

---

## Architecture Overview

The pipeline has three layers per strategy:

```
Backtest (single-asset / single-universe)
    │
    ├── [Type 2 Selection]  {name}_selection_Backtest_multiasset.py
    │       Grid search over baskets × top_pct × mom_window × freq
    │       3-gate significance per basket; best canonical params saved to JSON
    │
    ├── [Type 1 Timing]     {name}_timing_Backtest_multiasset.py
    │       Canonical params applied to each ETF individually
    │       3-gate significance per instrument; passing list saved to JSON
    │
    └── Implementation      {name}_{type}_Implementation_multiasset.py
            Re-runs signal with canonical params → build_basket_equity()
            One sleeve per passing basket/instrument (85% + 100% variants)
            Combined = 1/N capital per sleeve
```

**Type 1 (Timing)**: signal says WHEN to hold each instrument (e.g. BB entry/exit, calendar window, VIX regime).  
**Type 2 (Selection)**: signal cross-sectionally ranks instruments within a basket (e.g. momentum, carry, contrarian).  
**Universe**: 8 baskets, 68 ETFs total, 2016–2026.

---

## Type 2 — Selection Strategies

| Strategy | Passing Baskets | Sleeves | Sharpe | CAGR | MaxDD | Notes |
|---|---|---|---|---|---|---|
| **industry_trend** | us_sectors, us_factor, em_country | 3 | 0.596 | 8.3% | −30.5% | 12m momentum, 6ME rebal |
| **sector_momentum** | us_sectors, us_factor | 2 | 0.777 | 11.7% | −26.9% | 3m momentum, 6ME rebal; strong XLK/XLF/XLU |
| **bond_trend** | bonds_us, bonds_intl | 2 | 0.703 | 3.4% | −12.1% | 3m momentum, 2ME rebal; low vol bonds |
| **commodity_trend** | commodities, real_assets | 2 | 0.447 | 6.5% | −30.9% | Commodities sleeve weak (0.21 Sharpe); real_assets sleeve strong (0.67) |
| **commodity_carry** | commodities | 1 | 0.554 | 9.7% | −32.3% | sw=2, lw=12, ME rebal; carry beats trend on same basket |
| **cross_asset_carry** | cross_asset | 1 | 0.975 | 11.2% | −17.4% | 13-instrument mixed basket; Sharpe-like carry, 2ME rebal |
| **gtaa** | us_sectors, bonds_us, commodities, real_assets | 4 | 0.810 | 9.7% | −20.8% | SMA-300 filter; all 4 baskets pass; commodities sleeve weakest (0.48) |
| **quality_profitability** | us_equity_broad | 1 | 0.824 | 13.2% | −26.4% | FF5 RMW-gated momentum, 18m window, 6ME; quality timing adds ~0.15 Sharpe vs pure momentum |
| **country_cape_rotation** | em_country | 1 | 0.859 | 17.7% | −34.5% | Contrarian (−return) proxy for CAPE; top_pct=0.10 → 1 ETF at a time |
| **em_dm_carry** | em_dm (combined) | 1 | 0.801 | 14.7% | −30.5% | 9m return spread, thresh=0.05; binary EM vs DM regime switch, 6ME rebal |
| **regime_factor_rotation** | — | 0 | — | — | — | SKIP: SIZE/VLUE/QUAL/COWZ ETFs not in dataset |
| **quantitative_momentum** | — | 0 | — | — | — | SKIP: requires CRSP individual stock data |

---

## Type 1 — Timing Strategies

| Strategy | Passing / Tested | Instruments | Sharpe | CAGR | MaxDD | Notes |
|---|---|---|---|---|---|---|
| **bollinger_band** | 19 / 21 | SPY QQQ IWM MDY XLK XLF XLV XLI XLP XLY XLU XLB XLRE IWF IWD USMV MTUM PKW DVY | 0.671 | 7.9% | −27.4% | XLE, XLC fail; strong mean-reversion edge across most equity ETFs |
| **donchian_channel** | 19 / 21 | SPY QQQ MDY XLK XLE XLV XLI XLP XLY XLU XLB XLRE XLC IWF IWD USMV MTUM PKW DVY | 1.034 | 9.6% | −10.8% | IWM, XLF fail; best combined Sharpe of all timing strategies; low drawdown from diversification |
| **turn_of_month** | 4 / 15 | QQQ XLV XLRE XLC | 0.800 | 6.6% | −7.4% | Calendar anomaly; low drawdown; only selective passes — most ETFs fail significance |
| **overnight_premium** | 0 / 15 | — | — | — | — | All negative Sharpe after TC; overnight edge has reversed in 2016–2026 ETF data |
| **sentiment_timing** | 2 / 15 | QQQ XLK | 0.469 | 6.8% | −32.6% | VIX regime sizing; only tech ETFs pass; high drawdown limits utility |
| **credit_carry** | 1 / 6 | BIL | 4.700 | 0.9% | −0.3% | BIL beats IEF on 12m return ~60% of months; essentially a "cash stays in cash" timing; Sharpe high but CAGR near risk-free rate |
| **reit_dividend_carry** | 0 / 4 | — | — | — | — | ETF total-return proxy too noisy; carry proxy fails significance |
| **bond_duration_carry** | — | — | — | — | — | STUB: FRED ZIP not accessible in current session |
| **yield_curve_duration** | — | — | — | — | — | STUB: FRED ZIP not accessible in current session |
| All stock-level timing | — | — | — | — | — | STUBS: BAB, QMJ, low_vol, PEAD, short_interest, us_csm, us_earn_mom, seasonality, shareholder_yield (need CRSP); congress_trade, insider_buying (need special data) |

---

## Weak Points and Limitations

### 1. Short History (2016–2026 only)
All 68 ETFs launched ≥ 2003; most have clean data from ~2016. With only ~9 years:
- Seasonal strategies (turn_of_month, return_seasonality) have very few observations per calendar slot.
- Momentum strategies are trained entirely in a low-rate, QE-dominant regime.
- The 2020 COVID crash and 2022 rate-hike cycle are the only major stress tests.

### 2. Commodity Sleeve Weakness
The commodities basket underperforms across both trend (0.21 Sharpe) and carry (0.55 Sharpe) strategies. Raw commodities (USO, UNG) are highly mean-reverting at momentum frequencies; the cross-sectional signal picks up sector-specific trends not genuine momentum.

### 3. CAPE Proxy Flaw
`country_cape_rotation` uses inverse trailing return as a CAPE proxy. This is mechanically a contrarian signal, not a fundamental valuation signal. A proper implementation requires Shiller CAPE data per country ETF from an external source (e.g. StarCapital, CAPE-Rank API).

### 4. VIX Sizing Adds Little Value
`sentiment_timing` VIX-sized Sharpe (0.47) is materially lower than the raw buy-and-hold Sharpe (0.92) for QQQ and (1.11) for XLK. The contrarian VIX sizing (high VIX → overweight) hurts performance in 2022 when both VIX and losses peaked simultaneously.

### 5. Overnight Premium Has Reversed
The classic Cooper et al. (2008) overnight premium shows negative edge across all 15 ETFs in 2016–2026. This is consistent with recent literature showing HFT and index arbitrage have arbitraged away the premium since ~2010.

### 6. Type 1 Timing: Combination Problem
The bollinger_band and donchian_channel combined implementations average 19 sleeves. With 1/N equal weighting across SPY, QQQ, IWM, XLK, etc., the strategy is essentially a broadly diversified equity exposure with selective entry timing — not pure alpha generation.

### 7. FRED/CRSP Dependencies Block Key Strategies
Nine strategies are stubs due to missing data:
- FRED ZIP (bond_duration_carry, yield_curve_duration): fixable by downloading directly from `api.stlouisfed.org`.
- CRSP individual stocks (BAB, QMJ, low_vol, PEAD, short_interest, us_csm, us_earn_mom, seasonality, shareholder_yield): requires building a full stock-level backtest infrastructure.
- Congressional/insider data: requires external API subscriptions.

---

## Next Steps

| Priority | Action |
|---|---|
| **HIGH** | Download FRED DGS10 + DGS2 directly (`requests` or `fredapi`) → enable bond_duration_carry + yield_curve_duration |
| **HIGH** | Download missing factor ETFs (SIZE, VLUE, QUAL, COWZ) via Alpaca → enable regime_factor_rotation |
| **HIGH** | Replace commodity_trend commodities sleeve (Sharpe 0.21) with commodity_carry (0.55) in any portfolio construction |
| **MED** | Add Shiller CAPE data per country ETF → rebuild country_cape_rotation with true valuation signal |
| **MED** | Extend ETF history pre-2016 using Alpaca or synthetic proxies → fix seasonality and reduce regime bias |
| **MED** | Build stock-level backtest infrastructure using CRSP + Compustat → enable 9 stubs |
| **MED** | Add portfolio-level construction: combine non-overlapping strategy sleeves with risk-parity weights |
| **LOW** | Re-investigate overnight_premium with intraday ETF data (not just daily open/close) — ETF open prices may not reflect true overnight return |
| **LOW** | Investigate VIX-sized strategies with a 1-month lag (avoid buying into volatility spikes same-period) |

---

## File Index

```
long_term/
├── selection/
│   ├── industry_trend/           industry_trend_selection_{Backtest,Implementation}_multiasset.py
│   ├── sector_momentum/          sector_momentum_selection_{Backtest,Implementation}_multiasset.py
│   ├── bond_trend/               bond_trend_selection_{Backtest,Implementation}_multiasset.py
│   ├── commodity_trend/          commodity_trend_selection_{Backtest,Implementation}_multiasset.py
│   ├── commodity_carry/          commodity_carry_selection_{Backtest,Implementation}_multiasset.py
│   ├── cross_asset_carry/        cross_asset_carry_selection_{Backtest,Implementation}_multiasset.py
│   ├── gtaa/                     gtaa_selection_{Backtest,Implementation}_multiasset.py
│   ├── quality_profitability/    quality_profitability_selection_{Backtest,Implementation}_multiasset.py
│   ├── country_cape_rotation/    country_cape_rotation_selection_{Backtest,Implementation}_multiasset.py
│   ├── em_dm_carry/              em_dm_carry_selection_{Backtest,Implementation}_multiasset.py
│   ├── regime_factor_rotation/   regime_factor_rotation_selection_Backtest_multiasset.py  [STUB]
│   └── quantitative_momentum/    quantitative_momentum_selection_Backtest_multiasset.py   [STUB]
│
└── timing/
    ├── bollinger_band/           bollinger_band_timing_{Backtest,Implementation}_multiasset.py
    ├── donchian_channel/         donchian_channel_timing_{Backtest,Implementation}_multiasset.py
    ├── turn_of_month/            turn_of_month_timing_{Backtest,Implementation}_multiasset.py
    ├── overnight_premium/        overnight_premium_timing_Backtest_multiasset.py  [0 pass]
    ├── sentiment_timing/         sentiment_timing_timing_{Backtest,Implementation}_multiasset.py
    ├── credit_carry/             credit_carry_timing_{Backtest,Implementation}_multiasset.py
    ├── reit_dividend_carry/      reit_dividend_carry_timing_Backtest_multiasset.py  [0 pass]
    ├── bond_duration_carry/      bond_duration_carry_timing_Backtest_multiasset.py  [STUB]
    ├── yield_curve_duration/     yield_curve_duration_timing_Backtest_multiasset.py [STUB]
    └── [11 × stock/special data] *_timing_Backtest_multiasset.py  [STUBS]
```
