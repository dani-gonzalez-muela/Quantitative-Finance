# Greedy Forward Selection — Portfolio Optimizer Results

**Date:** 2026-06-19
**Universe:** 24 strategies (7 Portfolio B sleeves + 17 basket strategies)
**Common window:** 2016-06-15 → 2025-07-03 (2276 trading days, ~9.0 yrs)
**Weighting:** Equal-weight throughout
**Stop criterion:** Marginal Sharpe improvement < 0.02

---

## Section 1: Standalone Sharpe Ranking (all 24 strategies)

| Rank | Strategy | Sharpe | Category |
|------|----------|--------|----------|
| 1 | ibs_mean_reversion ★ | 1.3797 | Portfolio B sleeve |
| 2 | vix_mean_reversion ★ | 1.2029 | Portfolio B sleeve |
| 3 | vol_overlay ★ | 0.9894 | Portfolio B sleeve |
| 4 | donchian_channel | 0.9699 | Portfolio B sleeve |
| 5 | gtaa | 0.9053 | Portfolio B sleeve |
| 6 | donchian_channel__us_factor | 0.8657 | Basket strategy |
| 7 | sentiment_timing__us_factor | 0.8475 | Basket strategy |
| 8 | vol_overlay__us_factor | 0.8384 | Basket strategy |
| 9 | us_cross_sectional_momentum ★ | 0.8354 | Portfolio B sleeve |
| 10 | turn_of_month__real_assets ★ | 0.8296 | Basket strategy |
| 11 | donchian_channel__us_equity_broad | 0.7771 | Basket strategy |
| 12 | us_cross_sectional_momentum__us_factor | 0.7649 | Basket strategy |
| 13 | industry_trend__us_sectors | 0.7441 | Basket strategy |
| 14 | low_volatility__all_equity | 0.7344 | Basket strategy |
| 15 | quality_timing__us_factor | 0.7305 | Basket strategy |
| 16 | vol_overlay__us_equity_broad | 0.7304 | Basket strategy |
| 17 | us_cross_sectional_momentum__us_equity_broad | 0.7156 | Basket strategy |
| 18 | sentiment_timing__us_equity_broad | 0.7029 | Basket strategy |
| 19 | quality_timing__us_equity_broad | 0.6900 | Basket strategy |
| 20 | quality_profitability | 0.6268 | Portfolio B sleeve |
| 21 | donchian_channel__real_assets | 0.6226 | Basket strategy |
| 22 | cross_asset_momentum__all_68 | 0.6212 | Basket strategy |
| 23 | bond_duration_carry__bonds_us ★ | 0.5965 | Basket strategy |
| 24 | em_dm_carry__intl_country_all | 0.5571 | Basket strategy |

★ = selected by greedy algorithm

---

## Section 2: Greedy Selection Trace

| Step | Strategy Added | Sharpe Before | Sharpe After | Δ | N Sleeves |
|------|----------------|---------------|--------------|---|-----------|
| 1 | ibs_mean_reversion | — | 1.3797 | — (seed) | 1 |
| 2 | vol_overlay | 1.3797 | 1.6303 | +0.2506 | 2 |
| 3 | vix_mean_reversion | 1.6303 | 1.8865 | +0.2562 | 3 |
| 4 | us_cross_sectional_momentum | 1.8865 | 2.0483 | +0.1618 | 4 |
| 5 | turn_of_month__real_assets | 2.0483 | 2.1173 | +0.0690 | 5 |
| 6 | bond_duration_carry__bonds_us | 2.1173 | 2.1502 | +0.0329 | 6 |

**Stop reason:** Best marginal gain among 18 remaining strategies < 0.02

---

## Section 3: Final Portfolio

**6 strategies selected**

| # | Strategy | Standalone Sharpe | Corr with Portfolio at Selection |
|---|----------|-------------------|----------------------------------|
| 1 | ibs_mean_reversion | 1.3797 | — (seed) |
| 2 | vol_overlay | 0.9894 | -0.0326 |
| 3 | vix_mean_reversion | 1.2029 | 0.1155 |
| 4 | us_cross_sectional_momentum | 0.8354 | -0.0062 |
| 5 | turn_of_month__real_assets | 0.8296 | 0.1454 |
| 6 | bond_duration_carry__bonds_us | 0.5965 | 0.1044 |

### Final Portfolio Metrics (EW, full common window)

| Metric | Value |
|--------|-------|
| Sharpe  | **2.1502** |
| CAGR    | 10.47% |
| MaxDD   | -6.7% |
| Sortino | 2.8711 |
| Window  | 2016-06-15 → 2025-07-03 (9.03 yrs) |

---

## Section 4: Strategies NOT Selected

| Strategy | Standalone Sharpe | Reason Not Selected |
|----------|-------------------|---------------------|
| donchian_channel | 0.9699 | Marginal improvement < 0.02 threshold (corr=0.285, Sharpe=0.970) |
| gtaa | 0.9053 | Marginal improvement < 0.02 threshold (corr=0.393, Sharpe=0.905) |
| quality_profitability | 0.6268 | Marginal improvement < 0.02 threshold (corr=0.419, Sharpe=0.627) |
| donchian_channel__us_factor | 0.8657 | Marginal improvement < 0.02 threshold (corr=0.287, Sharpe=0.866) |
| sentiment_timing__us_factor | 0.8475 | Marginal improvement < 0.02 threshold (corr=0.452, Sharpe=0.848) |
| vol_overlay__us_factor | 0.8384 | Marginal improvement < 0.02 threshold (corr=0.466, Sharpe=0.838) |
| donchian_channel__us_equity_broad | 0.7771 | Marginal improvement < 0.02 threshold (corr=0.279, Sharpe=0.777) |
| us_cross_sectional_momentum__us_factor | 0.7649 | Marginal improvement < 0.02 threshold (corr=0.426, Sharpe=0.765) |
| quality_timing__us_factor | 0.7305 | Marginal improvement < 0.02 threshold (corr=0.451, Sharpe=0.731) |
| industry_trend__us_sectors | 0.7441 | Marginal improvement < 0.02 threshold (corr=0.395, Sharpe=0.744) |
| donchian_channel__real_assets | 0.6226 | Marginal improvement < 0.02 threshold (corr=0.273, Sharpe=0.623) |
| us_cross_sectional_momentum__us_equity_broad | 0.7156 | Marginal improvement < 0.02 threshold (corr=0.438, Sharpe=0.716) |
| quality_timing__us_equity_broad | 0.6900 | Marginal improvement < 0.02 threshold (corr=0.470, Sharpe=0.690) |
| sentiment_timing__us_equity_broad | 0.7029 | Marginal improvement < 0.02 threshold (corr=0.444, Sharpe=0.703) |
| cross_asset_momentum__all_68 | 0.6212 | Marginal improvement < 0.02 threshold (corr=0.397, Sharpe=0.621) |
| low_volatility__all_equity | 0.7344 | Marginal improvement < 0.02 threshold (corr=0.417, Sharpe=0.734) |
| vol_overlay__us_equity_broad | 0.7304 | Marginal improvement < 0.02 threshold (corr=0.458, Sharpe=0.730) |
| em_dm_carry__intl_country_all | 0.5571 | Marginal improvement < 0.02 threshold (corr=0.366, Sharpe=0.557) |

---

## Section 5: Comparison — Greedy Portfolio vs Portfolio B

| Metric | Portfolio B (7-sleeve EW) | Greedy Portfolio |
|--------|--------------------------|-----------------|
| Sleeves | 7 | 6 |
| Sharpe  | 1.8821 | **2.1502** |
| CAGR    | 11.37% | 10.47% |
| MaxDD   | -10.2% | -6.7% |
| Sortino | 2.3483 | 2.8711 |
| ΔSharpe vs Portfolio B | — | +0.2681 |

*Note: Both measured on identical common window (2016-06-15 → 2025-07-03) with EW weighting.*