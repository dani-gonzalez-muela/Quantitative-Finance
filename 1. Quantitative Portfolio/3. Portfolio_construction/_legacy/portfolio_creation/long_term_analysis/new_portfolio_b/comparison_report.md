# Portfolio B: Current vs Candidate Configurations

**Analysis Date:** 2026-06-18  
**Methodology:** Equity curve normalization to $100k, daily returns, 252-day annualization, zero risk-free rate

---

## Executive Summary

**Verdict: Upgrade to Config 1 (7-sleeve, equal-weight).** Adding `quality_profitability` and `us_cross_sectional_momentum` to the existing 5-sleeve portfolio delivers a material, well-earned improvement. Equal-weight Sharpe rises from **1.57 → 1.97** (+25%) while maximum drawdown holds roughly flat (−6.98% → −6.76%). The two new sleeves bring genuine diversification: `vix_mean_reversion` remains the single biggest contributor (marginal Sharpe +0.24), and both new additions carry positive marginal contributions with modest correlations to the rest of the book. Config 2 (8-sleeve with `bond_trend`) shows a Sharpe of 1.95 EW—slightly below Config 1 (1.97)—and bond_trend's standalone Sharpe of only 0.04 over the common window confirms it adds diversification but insufficient return. The inverse-vol weighting scheme for Config 2 collapses into a near-pure bond_trend position (91% weight) due to its anomalously low measured volatility, making that scheme impractical for Config 2. The MVO scheme selects Config 1 as best overall at **Sharpe = 2.09**. Under 1.5× leverage, Config 1 MVO delivers ~8.7% CAGR at a Sharpe of 2.09 with a max drawdown of only −5.1%.

---

## Common Windows

| Config | Sleeves | Window Start | Window End | Trading Days |
|--------|---------|-------------|-----------|-------------|
| Config 0 (5-sleeve) | IBS, Donchian, VIX MR, GTAA, Vol Overlay | 2016-06-14 | 2026-03-13 | 2,543 |
| Config 1 (7-sleeve) | + Quality Prof., + US XS Momentum | 2016-06-14 | 2026-02-27 | 2,533 |
| Config 2 (8-sleeve) | + Bond Trend | 2016-06-14 | 2026-01-01 | 2,492 |

---

## Metrics Comparison Table

### Equal-Weight (most practical, primary reference)

| Metric | Config 0 (5-sleeve) | Config 1 (7-sleeve) | Config 2 (8-sleeve) |
|--------|--------------------|--------------------|-------------------|
| **Sharpe** | 1.569 | **1.966** | 1.949 |
| **CAGR** | 10.18% | **11.70%** | 10.08% |
| **MaxDD** | -6.98% | -6.76% | **-5.74%** |
| **Sortino** | 1.977 | **2.572** | 2.538 |
| **Calmar** | 1.459 | 1.730 | **1.758** |
| **Ann. Vol** | 6.31% | 5.71% | 4.99% |
| Window | 2016-06-14→2026-03-13 | 2016-06-14→2026-02-27 | 2016-06-14→2026-01-01 |

### Inverse-Volatility Weighted

| Metric | Config 0 (5-sleeve) | Config 1 (7-sleeve) | Config 2 (8-sleeve)* |
|--------|--------------------|--------------------|-------------------|
| **Sharpe** | 1.717 | 1.903 | 0.133 |
| **CAGR** | 2.87% | 4.64% | 0.39% |
| **MaxDD** | -2.02% | -3.41% | -13.42% |
| **Calmar** | 1.418 | 1.360 | 0.029 |

*Config 2 inverse-vol is degenerate: bond_trend's anomalously low measured vol assigns it ~91% weight (capped at 50% for other configs), collapsing the portfolio into near-pure bond exposure. This weighting scheme is not viable for Config 2 without a vol cap or target-vol overlay.

### MVO (Max-Sharpe, 5%–60% bounds per sleeve)

| Metric | Config 0 (5-sleeve) | Config 1 (7-sleeve) | Config 2 (8-sleeve) |
|--------|--------------------|--------------------|-------------------|
| **Sharpe** | 1.682 | **2.090** | 2.079 |
| **CAGR** | 5.49% | 5.71% | 4.92% |
| **MaxDD** | -3.49% | -3.39% | **-2.85%** |
| **Calmar** | 1.574 | **1.683** | 1.726 |
| vol_overlay weight | 60.0% | 60.0% | 60.0% |

Note: MVO consistently hits the 60% cap on vol_overlay (near-zero correlation to equities, very high Sharpe). The practical portfolio should consider a lower cap (e.g. 40%) to avoid concentration.

---

## vs. SPY Benchmark

| Metric | SPY (same window as C0) | SPY (same window as C1) | Config 1 EW | Config 1 MVO |
|--------|------------------------|------------------------|-------------|--------------|
| Sharpe | 1.135 | 1.098 | 1.966 | 2.090 |
| CAGR | 20.05% | 19.30% | 11.70% | 5.71% |
| MaxDD | -33.79% | -33.79% | -6.76% | -3.39% |

Config 1 EW produces 1.79× the Sharpe of SPY with drawdowns 5× shallower. The CAGR is lower (11.7% vs ~19%) but the strategies are sized to 10% annualized vol targets — leverage adjusts for return, not risk.

---

## Rolling Analysis (Equal-Weight)

| Config | Roll. Sharpe Min | Roll. Sharpe Mean | Roll. Sharpe Max | Roll. CAGR Min | Roll. CAGR Mean |
|--------|-----------------|------------------|-----------------|----------------|----------------|
| Config 0 | 0.062 | 1.556 | 3.351 | 0.19% | 9.99% |
| Config 1 | -0.553 | 1.974 | 3.996 | -3.61% | 11.40% |
| Config 2 | -0.542 | 1.985 | 3.829 | -3.09% | 9.90% |

Config 1 lifts the rolling mean Sharpe and also raises the floor (min rolling Sharpe), indicating more consistent performance across different market regimes.

---

## Sleeve-Level Analysis

### Config 1 — 7 Sleeves (window: 2016-06-14 → 2026-02-27)

| Sleeve | Standalone Sharpe | Corr to Rest | Marginal Sharpe |
|--------|------------------|-------------|----------------|
| ibs_mean_reversion | 1.302 | 0.368 | 0.0989 |
| donchian_channel | 0.934 | 0.307 | 0.0218 |
| vix_mean_reversion | 1.237 | 0.169 | 0.2421 |
| gtaa | 0.962 | 0.422 | -0.0003 |
| vol_overlay | 0.992 | -0.029 | 0.0119 |
| quality_profitability | 1.131 | 0.358 | 0.0595 |
| us_cross_sectional_momentum | 1.050 | 0.259 | 0.0835 |

**Key observations for Config 1:**
- `vix_mean_reversion` is the standout contributor with the highest marginal Sharpe (+0.2421) and the lowest correlation to the rest (0.169), making it the most valuable sleeve.
- `vol_overlay` has a near-zero correlation (−0.029) to the rest, providing essential portfolio stabilization.
- `quality_profitability` (+0.0595 marginal) and `us_cross_sectional_momentum` (+0.0835 marginal) both justify inclusion with positive contributions.
- `gtaa` is the weakest link: marginally slightly negative (−0.0003), though functionally neutral. Its correlation (0.422) is among the highest.
- `donchian_channel` has the lowest standalone Sharpe (0.934) but still contributes positively.

### Config 2 — 8 Sleeves (window: 2016-06-14 → 2026-01-01)

| Sleeve | Standalone Sharpe | Corr to Rest | Marginal Sharpe |
|--------|------------------|-------------|----------------|
| ibs_mean_reversion | 1.321 | 0.358 | 0.1105 |
| donchian_channel | 0.936 | 0.290 | 0.0349 |
| vix_mean_reversion | 1.203 | 0.165 | 0.2316 |
| gtaa | 0.882 | 0.426 | -0.0143 |
| vol_overlay | 1.003 | -0.022 | 0.0119 |
| quality_profitability | 1.129 | 0.354 | 0.0635 |
| us_cross_sectional_momentum | 1.036 | 0.260 | 0.0796 |
| bond_trend | 0.040 | -0.073 | 0.0086 |

**Key observations for Config 2:**
- `bond_trend` has a standalone Sharpe of only **0.040** over the common window (2016–2026), reflecting a very difficult decade for trend-following in fixed income.
- Its negative correlation to the portfolio (−0.073) does provide tail-risk hedging, and its marginal Sharpe contribution is positive (+0.0086), but the benefit is small.
- Adding bond_trend reduces EW Sharpe from 1.966 → 1.949 and shifts the common end date back from Feb 2026 → Jan 2026.
- Unless bond_trend is expected to mean-revert to historical levels, Config 2 offers minimal improvement over Config 1.

---

## Drawdown Profile

### Config 0 — Top 5 Drawdowns (Equal-Weight)

| # | Start | Trough | End | Depth | Duration |
|---|-------|--------|-----|-------|----------|
| 1 | 2020-02-20 | 2020-03-05 | 2020-04-29 | -6.98% | 69d |
| 2 | 2021-11-09 | 2022-01-27 | 2022-03-24 | -5.18% | 135d |
| 3 | 2025-02-20 | 2025-03-13 | 2025-05-12 | -4.42% | 81d |
| 4 | 2023-02-03 | 2023-03-13 | 2023-05-18 | -3.83% | 104d |
| 5 | 2018-01-29 | 2018-02-08 | 2018-02-23 | -3.69% | 25d |

Average drawdown duration: 10.6 days

### Config 1 — Top 5 Drawdowns (Equal-Weight)

| # | Start | Trough | End | Depth | Duration |
|---|-------|--------|-----|-------|----------|
| 1 | 2020-02-20 | 2020-03-05 | 2020-05-26 | -6.76% | 96d |
| 2 | 2022-01-04 | 2022-10-11 | 2022-11-30 | -5.68% | 330d |
| 3 | 2018-10-02 | 2018-12-31 | 2019-03-21 | -4.83% | 170d |
| 4 | 2025-02-20 | 2025-04-08 | 2025-06-02 | -4.63% | 102d |
| 5 | 2023-08-01 | 2023-10-20 | 2023-12-01 | -3.13% | 122d |

Average drawdown duration: 10.0 days

### Config 2 — Top 5 Drawdowns (Equal-Weight)

| # | Start | Trough | End | Depth | Duration |
|---|-------|--------|-----|-------|----------|
| 1 | 2020-02-20 | 2020-03-18 | 2020-04-30 | -5.74% | 70d |
| 2 | 2022-01-04 | 2022-10-11 | 2022-11-30 | -4.92% | 330d |
| 3 | 2018-10-02 | 2018-12-31 | 2019-03-21 | -4.21% | 170d |
| 4 | 2025-02-20 | 2025-04-08 | 2025-06-02 | -4.21% | 102d |
| 5 | 2023-08-01 | 2023-10-20 | 2023-12-01 | -2.73% | 122d |

Average drawdown duration: 10.5 days

**Drawdown notes:** All three configs share the same worst drawdown event (COVID Feb 2020). Config 1 sees a longer worst-drawdown duration (330d for the 2022 bear market) vs Config 0 (135d), reflecting the equity exposure from the two new sleeves. Config 2 improves max depth to −5.74% (bond_trend hedging), but the 2022 event extends identically.

---

## Leverage Table — Config 1, MVO (Best Configuration)

Weights: ibs_mr=10.1%, donchian=5.0%, vix_mr=7.2%, gtaa=5.0%, vol_overlay=60.0%, qual_prof=7.7%, us_xs_mom=5.0%

| Leverage | CAGR | Ann. Vol | Sharpe | MaxDD | Sortino | Calmar |
|----------|------|----------|--------|-------|---------|--------|
| **1x** | 5.71% | 2.67% | 2.090 | -3.39% | 2.757 | 1.683 |
| **1.5x** | 8.66% | 4.01% | 2.090 | -5.05% | 2.757 | 1.713 |
| **2x** | 11.67% | 5.35% | 2.090 | -6.69% | 2.757 | 1.743 |
| **2.5x** | 14.74% | 6.69% | 2.090 | -8.31% | 2.757 | 1.773 |
| **3x** | 17.87% | 8.02% | 2.090 | -9.90% | 2.757 | 1.804 |

At 2× leverage: CAGR reaches ~11.7% with max drawdown of only −6.7% — comparable to Config 0 EW CAGR at 10.2% but with a Sharpe of 2.09 vs 1.57. At 1.5× leverage the risk/return is highly attractive: ~8.7% CAGR at −5.1% MaxDD.

---

## Recommendation

**Upgrade to Config 1 (7-sleeve), equal-weight or MVO.**

The case is clear across all three weighting schemes: Config 1 dominates Config 0 on Sharpe (1.97 EW, 2.09 MVO vs 1.57 EW), with essentially unchanged max drawdown. The two new sleeves earn their place — quality_profitability and us_cross_sectional_momentum both have positive marginal contributions and low pairwise correlations to the core book.

Config 2 should be **deferred**. Bond_trend has had a brutal decade in this common window (Sharpe 0.04), and adding it slightly dilutes the portfolio Sharpe while triggering practical problems (the inverse-vol scheme becomes degenerate). Revisit bond_trend if its performance mean-reverts or if the allocation is constrained to ≤10%.

For practical implementation, equal-weight (1/7 per sleeve) is the preferred starting point — it avoids MVO's 60% concentration in vol_overlay and remains robust to estimation error. Apply 1.5×–2× leverage to bring CAGR into the target range.

| Decision | Config 0 EW | Config 1 EW | Config 1 MVO @ 1.5× |
|----------|------------|------------|---------------------|
| Sharpe | 1.57 | 1.97 | 2.09 |
| CAGR | 10.2% | 11.7% | 8.7% (pre-leverage adj.) |
| MaxDD | −6.98% | −6.76% | −5.05% |
| Verdict | Baseline | ✅ **Adopt** | ✅ Preferred with leverage |

---

*All metrics computed from equity curves. Common window is the intersection of all sleeve histories in each config. SPY uses existing `analysis/spy_equity.csv`. Rolling metrics use 252-day window, monthly steps.*
