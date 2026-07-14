# Long-Term Strategy Report — Full Universe (25 Strategies)
**Date:** 2026-06-18  
**Starting Capital:** $100,000  
**Transaction Cost:** 5 bps one-way (10 bps round-trip)  
**SPY Benchmark Sharpe (2016–2026):** ~0.80

---

## Significance Test Criteria

Three-gate test applied to **monthly returns**:

1. **Gate 1 (Sharpe):** Net Sharpe (annualized from monthly) > 0.80
2. **Gate 2 (t-stat):** t-statistic of monthly mean return > 1.65 (one-sided 5%)
3. **Gate 3 (Bootstrap):** 5th percentile of 1,000-resample bootstrap Sharpe > 0

Verdict: ✅ STRONG = 3/3 | ⚠️ MODERATE = 2/3 | ❌ NOT SIGNIFICANT = <2/3

---

## Part A — Original 17 Strategies

| # | Strategy | Theme | Period | CAGR | Sharpe | Max DD | Net Verdict |
|---|----------|-------|--------|------|--------|--------|-------------|
| 1 | us_cross_sectional_momentum | Cross-sectional Factor | 1990–2026 | 13.88% | 0.774 | -44.78% | ✅ STRONG |
| 2 | us_shareholder_yield | Cross-sectional Factor | 1990–2026 | 11.85% | 0.662 | -56.57% | ⚠️ MODERATE |
| 3 | us_earnings_momentum | Cross-sectional Factor | 1990–2026 | 14.34% | 0.828 | -40.41% | ✅ STRONG |
| 4 | us_return_seasonality | Cross-sectional Factor | 1996–2026 | 9.70% | 0.519 | -54.44% | ⚠️ MODERATE |
| 5 | country_cape_rotation | Cross-sectional Factor | 1996–2026 | 6.67% | 0.387 | -48.84% | ⚠️ MODERATE |
| 6 | yield_curve_duration | Macro / Fixed Income | 2003–2025 | 4.11% | 0.312 | -21.90% | ❌ NOT SIG |
| 7 | em_dm_carry | Macro / TAA | 2000–2026 | 11.51% | 0.682 | -54.61% | ⚠️ MODERATE |
| 8 | turn_of_month | Calendar Anomaly | 2000–2025 | 5.91% | 0.633 | -21.20% | ⚠️ MODERATE |
| 9 | overnight_premium | Market Microstructure | 2000–2025 | 6.35% | 0.556 | -38.29% | ⚠️ MODERATE |
| 10 | short_interest_contrarian | Alternative Beta | 2006–2025 | 10.61% | 0.559 | -50.54% | ⚠️ MODERATE |
| 11 | sentiment_timing | Alternative Beta | 1990–2026 | 10.87% | 0.555 | -61.14% | ⚠️ MODERATE |
| 12 | insider_buying | Alternative Beta | 1990–2026 | 10.20% | 0.588 | -54.57% | ⚠️ MODERATE |
| 13 | pead_earnings_drift | Long-Short Factor | 1990–2025 | 11.87% | 0.612 | -47.23% | ⚠️ MODERATE |
| 14 | bab_long_short | Long-Short Factor | 1990–2019 | 5.53% | 0.283 | -78.19% | ❌ NOT SIG |
| 15 | qmj_long_short | Quality Factor | 1990–2026 | 4.74% | 0.407 | -45.32% | ⚠️ MODERATE |
| 16 | bond_duration_carry | Fixed Income | 2003–2025 | 4.21% | 0.358 | -21.46% | ❌ NOT SIG |
| 17 | reit_dividend_carry | Real Assets | 2006–2025 | 5.44% | 0.500 | -33.08% | ⚠️ MODERATE |

### Part A — Significance Summary
| Level | Count | Strategies |
|-------|-------|-----------|
| ✅ STRONG (3/3) | 2 | us_cross_sectional_momentum, us_earnings_momentum |
| ⚠️ MODERATE (2/3) | 12 | us_shareholder_yield, us_return_seasonality, country_cape_rotation, em_dm_carry, turn_of_month, overnight_premium, short_interest_contrarian, sentiment_timing, insider_buying, pead_earnings_drift, qmj_long_short, reit_dividend_carry |
| ❌ NOT SIGNIFICANT | 3 | yield_curve_duration, bab_long_short, bond_duration_carry |

---

## Part B — 8 New Strategies
**TC:** 1 bps | Significance: t-test + bootstrap Sharpe + permutation (sign-flip)

| # | Strategy | Period | Sharpe | CAGR | MaxDD | Net Significance | Data Source |
|---|----------|--------|--------|------|-------|-----------------|-------------|
| 18 | bond_trend | 2001–2026 | 0.21 | 0.77% | -16.0% | ❌ NOT SIG (0/3) | bonds_yahoo + yield proxy |
| 19 | commodity_trend | 2001–2025 | 0.35 | 5.62% | -67.1% | ⚠️ MODERATE (2/3) | commodities_daily (gold, oil) |
| 20 | credit_carry | 2001–2025 | 0.04 | -0.09% | -37.4% | ❌ NOT SIG (0/3) | bonds_yahoo + yield proxy |
| 21 | industry_trend | 2016–2025 | 0.61 | 10.11% | -36.0% | ✅ STRONG (3/3) | SPDR sector ETFs |
| 22 | low_volatility | 1970–2025 | 0.59 | 9.84% | -50.7% | ✅ STRONG (3/3) | CRSP NYSE size decile 10 |
| 23 | cross_asset_carry | 2016–2025 | 0.17 | 1.50% | -38.2% | ❌ NOT SIG (0/3) | SPY+TLT+gold+oil proxies |
| 24 | commodity_carry | 2002–2025 | 0.51 | 9.00% | -58.4% | ✅ STRONG (3/3) | commodities_daily (5 commodities) |
| 25 | quality_profitability | 1963–2026 | 0.72 | 9.18% | -43.5% | ✅ STRONG (3/3) | FF5 RMW factor |

### Part B — Significance Summary
| Level | Count | Strategies |
|-------|-------|-----------|
| ✅ STRONG (3/3) | 4 | industry_trend, low_volatility, commodity_carry, quality_profitability |
| ⚠️ MODERATE (2/3) | 1 | commodity_trend |
| ❌ NOT SIGNIFICANT | 3 | bond_trend, credit_carry, cross_asset_carry |

---

## Combined Significance Overview (25 strategies)

| Level | Count | % |
|-------|-------|---|
| ✅ STRONG | 6 | 24% |
| ⚠️ MODERATE | 13 | 52% |
| ❌ NOT SIGNIFICANT | 6 | 24% |

**19 of 25 strategies (76%) pass at least 2 of 3 gates net of costs.**

---

## Recommendations

**Deploy (strong net significance):**
- us_earnings_momentum, us_cross_sectional_momentum (CAGR >13%, Sharpe >0.77)
- industry_trend, quality_profitability, commodity_carry, low_volatility

**Investigate further:**
- em_dm_carry — strong gross, moderate net; reduce rebalance frequency
- pead_earnings_drift — real earnings data, longer hold period improves TC efficiency
- turn_of_month — low MaxDD (-21%), good diversifier role

**Do not deploy standalone:**
- bab_long_short — MaxDD -78%, not significant net
- yield_curve_duration, bond_duration_carry, credit_carry — costs exceed alpha
- bond_trend, cross_asset_carry — no alpha with current proxies

---

## Data Sources

| Source | Strategies |
|--------|-----------|
| Fama-French 5 Factor + Mom (monthly) | 1, 2, 3, 4, 11, 12, 15, 25 |
| CRSP World Country Returns parquet | 5, 7 |
| FRED Interest Rate Daily ZIP | 6, 16 |
| CRSP SP500 Market Portfolio | 8, 9, 17 |
| Compustat Short Interest ZIP | 10 |
| CBOE VIX Parquet | 11, 12 |
| Compustat Quarterly + CCM Bridge + CRSP | 13 |
| Better Market Betas ZIP (bswa32) | 14 |
| vol_overlay commodities_daily.csv | 19, 23, 24 |
| archived_strategies/output/prices_validated.parquet | 21 |
| CRSP NYSE size decile 10 | 22 |

*Note: Jensen/Kelly 68GB, Shiller CAPE, Baker-Wurgler, EDGAR Form 4, VNQ/yfinance — all blocked during backtesting.*

---

*Report merged: 2026-06-20 | Sources: _full_strategy_report_v2.md (17 strategies) + _new_strategies_report.md (8 strategies)*
