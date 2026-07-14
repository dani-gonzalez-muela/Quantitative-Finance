# Portfolio Classification Report

**Date:** 2026-06-19  
**Author:** Strategy audit — automated analysis  
**Scope:** All systematic strategies in `algo_trading/long_term_portfolio/`

---

## Section 1: Strategy Classification Table

Classification rule: **holding period ≤ 2 weeks OR daily execution** → SHORT TERM (Portfolio A). **Monthly rebalancing OR avg hold > 2 weeks** → LONG TERM (Portfolio B).

| Strategy | Signal / Rebalancing | Avg Hold | Classification | Status | Notes |
|---|---|---|---|---|---|
| **ibs_mean_reversion** | IBS < 0.2 entry, IBS > 0.8 exit | **2.9 days** | 🔴 SHORT TERM | Backtested | Daily OHLC signal; exits within 1–5 days. Currently misclassified in Portfolio B. |
| **vix_mean_reversion** | VIX spike entry, EMA7 declining exit | **5.5 days** | 🔴 SHORT TERM | Backtested | Max hold 200d but typical exit in under a week. Currently misclassified in Portfolio B. |
| **vix_etn_dual** | eVRP + contango/backwardation, drift-triggered rebalance | Daily | 🔴 SHORT TERM | Backtested | Daily signal; holds SVXY or VXX based on volatility regime. |
| **overnight_premium** | Always long overnight, cash intraday | 1 day (overnight) | 🔴 SHORT TERM | Backtested | Harvests overnight return premium; no multi-day hold. |
| **turn_of_month** | Calendar: last 3 + first 3 trading days/month | ~6 trading days/month | 🔴 SHORT TERM | Backtested | Invested ~28% of days. Avg hold reported as 28 days because backtest groups full monthly window as one trade, but actual exposure is 6 trading days (~8–9 calendar days). |
| **bollinger_band** | Close ≤ lower band entry, ≥ upper band exit, min_hold=30d | **83.8 days** | 🟢 LONG TERM | Backtested | bb_period=30, bb_std=2.0, min_hold=30d. Mean reversion with forced long hold. |
| **donchian_channel** | 20-day breakout, min_hold=30d | **94 days** | 🟢 LONG TERM | Backtested | Trend-following. Default params: channel_period=20, min_hold=30d. |
| **gtaa** | Price vs 200-day SMA per ETF, monthly rebalance | Monthly | 🟢 LONG TERM | Backtested | Faber (2007). 5 ETFs (SPY, EFA, IEF, DBC, VNQ). Monthly preferred over weekly. |
| **vol_overlay** | HAR-RV 20d forward vol forecast, daily rebalance | Daily | ⚠️ UNCERTAIN | Backtested | Daily exposure adjustment on SPY, not a standalone long-short. Classified here as a Portfolio B *modifier* rather than directional hold. See notes. |
| **quality_profitability** | 12m cumulative RMW signal, monthly | Monthly | 🟢 LONG TERM | Backtested | FF5 RMW factor. Long Mkt+half_RMW when signal positive. |
| **us_cross_sectional_momentum** | 12-1m price momentum, monthly rebalance | Monthly | 🟢 LONG TERM | Backtested | Fama-French UMD factor-based. Monthly TC ~10bps round-trip. |
| **bond_duration_carry** | DFII10 real yield + T10Y2Y slope, monthly | Monthly | 🟢 LONG TERM | Backtested | Rotates between 20yr, 10yr, 2yr Treasuries. |
| **sentiment_timing** | VIX end-of-month level, monthly rebalance | Monthly | 🟢 LONG TERM | Backtested | VIX>25→150% SPY, VIX<15→50% SPY, else 100%. |
| **industry_trend** | 12-1m sector momentum, top 3 sectors, monthly | Monthly | 🟢 LONG TERM | Backtested | FF 48-industry or ETF sectors. Monthly rebalance. |
| **low_volatility** | Always long low-beta (large cap decile 10) | Monthly | 🟢 LONG TERM | Backtested | Buy-and-hold of low-vol factor proxy. Monthly accounting. |
| **bab_long_short** | Vasicek-shrunk beta ranking, monthly | Monthly | 🟢 LONG TERM | Backtested | Frazzini-Pedersen BAB factor replica. Monthly rebalance. |
| **bond_trend** | 12m return > 0 → long; else flat, monthly | Monthly | 🟢 LONG TERM | Backtested | Applied to Treasury ETFs. Monthly rebalance. |
| **commodity_carry** | Carry rank (1m vs 3m return), top 3, monthly | Monthly | 🟢 LONG TERM | Backtested | Commodity futures carry. Monthly rebalance. |
| **commodity_trend** | 12m return > 0 → long; else flat, monthly | Monthly | 🟢 LONG TERM | Backtested | Commodity momentum. Monthly rebalance. |
| **country_cape_rotation** | 12m return (cheapest 5 countries), monthly | Monthly | 🟢 LONG TERM | Backtested | Value/mean-reversion signal on country ETFs. Monthly rebalance. |
| **credit_carry** | HG bonds 12m return vs treasury proxy, monthly | Monthly | 🟢 LONG TERM | Backtested | Relative momentum credit carry. Monthly rebalance. |
| **cross_asset_carry** | Carry rank top 3 of 5 assets, monthly | Monthly | 🟢 LONG TERM | Backtested | Vol-adjusted carry across equity/bond/commodity/FX. Monthly. |
| **em_dm_carry** | EM vs DM carry spread > 1%, monthly | Monthly | 🟢 LONG TERM | Backtested | Binary EM/DM rotation. Monthly rebalance. |
| **insider_buying** | VIX spike vs 3m avg (insider buy proxy), monthly | Monthly | 🟢 LONG TERM | Backtested | VIX spike → 130% SPY exposure. Fallback proxy for real insider data. |
| **pead_earnings_drift** | Top-quartile SUE stocks after earnings, hold 1 month | ~1 month | 🟢 LONG TERM | Backtested | Post-Earnings Announcement Drift. Uses next calendar month as holding period. |
| **qmj_long_short** | FF RMW + 0.5×CMA factor, monthly | Monthly | 🟢 LONG TERM | Backtested | Quality-minus-Junk long-short. Monthly rebalance. |
| **quantitative_momentum** | 12m return + FIP quality filter, quarterly rebalance | Quarterly | 🟢 LONG TERM | Backtested | Gray & Vogel QM. Rebalances Feb/May/Aug/Nov. |
| **regime_factor_rotation** | GMM macro regime → top-K factor ETFs, monthly | Monthly | 🟢 LONG TERM | Backtested | Walk-forward GMM on 32 FRED-MD features. Monthly rebalance. |
| **reit_dividend_carry** | REIT dividend yield vs 24m avg carry signal, monthly | Monthly | 🟢 LONG TERM | Backtested | CRSP income return-based carry. Monthly rebalance. |
| **sector_momentum** | Top 5 sectors by 6m return, monthly | Monthly | 🟢 LONG TERM | Backtested | SPX sector ETF momentum. Monthly rebalance. |
| **short_interest_contrarian** | Cross-rank short interest, long bottom quintile, monthly | Monthly | 🟢 LONG TERM | Backtested | Low-short-interest contrarian. Monthly rebalance. |
| **us_earnings_momentum** | avg_rank(ret_1_0, ret_3_1), monthly | Monthly | 🟢 LONG TERM | Backtested | Earnings revision momentum via FF factor implementation. |
| **us_return_seasonality** | Same-calendar-month avg return (5yr lookback), monthly | Monthly | 🟢 LONG TERM | Backtested | SEAS_1_1AN factor. Monthly rebalance. |
| **us_shareholder_yield** | Dividend yield (div12m_me), monthly | Monthly | 🟢 LONG TERM | Backtested | Faber Shareholder Yield proxy. Monthly rebalance. |
| **yield_curve_duration** | T10Y2Y spread → bond duration tilt, monthly | Monthly | 🟢 LONG TERM | Backtested | Rotates 2yr / 10yr / 20yr based on yield curve slope. |
| **congress_s2** (trade-for-trade D180) | Replicates congress trades, hold up to 180d, min 30d | ~30–180 days | 🟢 LONG TERM | Backtested | D180 = positions closed 180 days after congress trade or at exit signal. Monthly-ish natural turnover. |
| **Congress Strategy 1** (1-day SEC hold) | Hold 1 day after disclosure | 1 day | 🔴 SHORT TERM | Pending | Not yet implemented as systematic backtest. |
| **Congress Strategy 3** (Quiver Open) | Same-day execution on disclosure | Same day | 🔴 SHORT TERM | Pending | Not yet implemented. |

### Notes on Vol Overlay Classification

`vol_overlay` uses a HAR-RV model to forecast 20-day forward realized volatility, adjusting SPY exposure daily (range: 0% to 150%). Technically this is **daily rebalancing**, which would make it SHORT TERM by hold-period logic. However, it functions as a **portfolio-level exposure overlay** (not a directional bet), the signal horizon is 20 days forward, and it was specifically designed as a Portfolio B complement. Classification: kept in Portfolio B with an "uncertain" flag. If strict hold-period rules are applied, it should be reclassified or treated as an execution wrapper rather than a standalone strategy.

---

## Section 2: Congress Strategy 2 Greedy Test

### Setup

Congress Strategy 2 equity curve found at:
```
congress_trade_for_trade/results/congress_trade_for_trade_daily_equity/total_nav_3pct_d180_min30d_1x.csv
```
Period: 2015-09-04 → 2025-07-02 (2,564 trading days)

The equity curve was loaded as a daily return series (pct_change) and added as a 25th candidate to the greedy forward selection optimizer.

**Common window (inner join of all 25 candidates):** 2016-06-15 → 2025-07-02 (~9.0 years)

### Congress S2 Standalone Metrics (common window)

| Metric | Value |
|---|---|
| Sharpe | 1.276 |
| CAGR | 10.74% |
| Max Drawdown | −9.62% |
| Period | 2016-06-15 → 2025-07-02 (9.0 yrs) |

### Greedy Results: 24-Strategy Baseline (on congress window)

| Step | Strategy Added | Sharpe Before | Sharpe After | Δ |
|---|---|---|---|---|
| 1 | ibs_mean_reversion (seed) | — | 1.3192 | — |
| 2 | vol_overlay | 1.3192 | 1.8051 | +0.4859 |
| 3 | vix_mean_reversion | 1.8051 | 1.9388 | +0.1337 |
| 4 | us_cross_sectional_momentum | 1.9388 | 2.0142 | +0.0754 |
| 5 | turn_of_month__real_assets | 2.0142 | 2.0803 | +0.0661 |
| 6 | bond_duration_carry__bonds_us | 2.0803 | 2.1534 | +0.0731 |
| Stop | best delta = 0.0088 < 0.02 | | 2.1534 | |

**Baseline final portfolio Sharpe: 2.1534** | CAGR: 10.49% | MaxDD: −6.70%

### Greedy Results: 25-Strategy Run (with Congress S2)

| Step | Strategy Added | Sharpe Before | Sharpe After | Δ | Corr w/ portfolio |
|---|---|---|---|---|---|
| 1 | ibs_mean_reversion (seed) | — | 1.3192 | — | — |
| 2 | **congress_s2** | 1.3192 | 1.8785 | **+0.5593** | **0.0046** |
| 3 | vol_overlay | 1.8785 | 2.1208 | +0.2423 | — |
| 4 | vix_mean_reversion | 2.1208 | 2.2432 | +0.1224 | — |
| 5 | us_cross_sectional_momentum | 2.2432 | 2.3099 | +0.0667 | — |
| 6 | turn_of_month__real_assets | 2.3099 | 2.3723 | +0.0624 | — |
| 7 | bond_duration_carry__bonds_us | 2.3723 | 2.4090 | +0.0367 | — |
| Stop | best delta = 0.0000 < 0.02 | | 2.4090 | |

**Extended final portfolio Sharpe: 2.4090** | CAGR: 10.58% | MaxDD: −6.44%

### Key Findings

- **Congress S2 was selected at step 2** — the second slot after the seed strategy, displacing vol_overlay from its previous step-2 position.
- **Correlation with portfolio at selection: 0.0046** — essentially zero. Congress S2 is near-orthogonal to ibs_mean_reversion.
- **Full-period correlation with 24-strategy portfolio: 0.0256** — also near-zero. This is a fundamentally uncorrelated alpha source.
- The Sharpe improvement from adding Congress S2 (+0.5593) is the largest single-step improvement observed, larger than any step in the 24-strategy run.
- Portfolio Sharpe improves from 2.1534 → 2.4090 (+0.256) by adding Congress S2 to the universe, with slightly lower max drawdown (−6.44% vs −6.70%).

**Conclusion: Congress S2 is a high-value Portfolio B sleeve.** Its near-zero correlation with existing strategies and strong standalone Sharpe (1.28) make it the single best addition to the portfolio.

---

## Section 3: Portfolio A — Short-Term Strategies

### Composition

| Strategy | Status | Sharpe | CAGR | MaxDD | Hold Period |
|---|---|---|---|---|---|
| ibs_mean_reversion | ✅ Backtested | 1.316 | 10.62% | −7.86% | 2.9d avg |
| vix_mean_reversion | ✅ Backtested | 1.204 | 17.88% | −19.82% | 5.5d avg |
| turn_of_month | ✅ Backtested | 0.633 | 5.96% | −21.20% | 6 trading days/month |
| overnight_premium | ✅ Backtested | 0.555 | 6.38% | −38.29% | Overnight only |
| vix_etn_dual | ✅ Backtested | 0.848 | 14.86% | −33.11% | Daily (drift-triggered) |
| Congress Strategy 1 | ⏳ Pending | — | — | — | 1 day |
| Congress Strategy 3 | ⏳ Pending | — | — | — | Same day |

### Combined Portfolio A Metrics (EW, common window 2016-06-15 → 2025-12-31)

*5 backtested strategies, equal-weight on common window*

| Metric | Value |
|---|---|
| Sharpe | **1.56** |
| CAGR | **13.03%** |
| Max Drawdown | **−7.00%** |
| Period | 9.5 years |

Portfolio A is **high-Sharpe, low-drawdown** because IBS MR, VIX MR, and VIX ETN Dual are roughly uncorrelated with each other and have modest individual drawdowns. The short-term nature of positions means low market exposure per trade.

**Note:** Turn of Month and Overnight Premium have large standalone drawdowns (−21% and −38%) because they carry long equity exposure across market crashes. In the combined portfolio these are diluted. Consider sizing them more conservatively.

---

## Section 4: Portfolio B — Long-Term Strategies

### Previous vs. New Composition

The **previous Portfolio B** (7 sleeves from the greedy optimizer) incorrectly included two short-term strategies: `ibs_mean_reversion` (2.9d hold) and `vix_mean_reversion` (5.5d hold). These are reclassified to Portfolio A.

**Previous Portfolio B (7 sleeves — INCORRECT):**
ibs_mean_reversion ❌, vix_mean_reversion ❌, donchian_channel ✓, gtaa ✓, vol_overlay ⚠️, quality_profitability ✓, us_cross_sectional_momentum ✓

**New Portfolio B (7 sleeves — CORRECTED):**
donchian_channel ✓, bollinger_band ✓ (new), gtaa ✓, vol_overlay ⚠️, quality_profitability ✓, us_cross_sectional_momentum ✓, **congress_s2 ✓** (new — greedy-selected)

### New Portfolio B Composition

| Strategy | Status | Sharpe | CAGR | MaxDD | Hold / Rebal |
|---|---|---|---|---|---|
| donchian_channel | ✅ Backtested | 0.919 | 9.10% | −16.08% | ~94d avg hold |
| bollinger_band | ✅ Backtested | 0.729 | 8.72% | −23.75% | ~84d avg hold |
| gtaa | ✅ Backtested | 1.003 | 6.11% | −8.11% | Monthly |
| vol_overlay | ✅ Backtested ⚠️ | 0.948 | 10.71% | −17.66% | Daily (overlay) |
| quality_profitability | ✅ Backtested | 0.777 | 10.43% | −44.39% | Monthly |
| us_cross_sectional_momentum | ✅ Backtested | 0.774 | 9.57% | −44.78% | Monthly |
| congress_s2 | ✅ Backtested | 1.124 | 9.00% | −12.15% | 30–180d |

### Combined Portfolio B Metrics

| Metric | New B (corrected) | Old B (w/ IBS & VIX MR) |
|---|---|---|
| Sharpe | **1.773** | 1.914 |
| CAGR | **10.09%** | 11.44% |
| Max Drawdown | **−12.86%** | −10.20% |
| Period | 2016-06-15 → 2025-07-02 (9.0 yrs) | 2016-06-15 → 2025-12-31 (9.5 yrs) |

The new Portfolio B has modestly lower Sharpe (1.77 vs 1.91) and higher drawdown (−12.9% vs −10.2%) compared to the old version that had IBS MR and VIX MR in it — those two strategies boosted Portfolio B's numbers but were misclassified. The new composition is **conceptually correct**: all strategies have genuine multi-week to multi-month holding periods. The Bollinger Band and Congress S2 additions partially offset the loss of IBS MR and VIX MR.

### Note on Quality and XS Momentum Metrics

`quality_profitability` and `us_cross_sectional_momentum` report drawdowns of −44% because they use very long backtests (63 years and 36 years respectively, including multiple market crashes). On the 10-year common window used for Portfolio B metrics, these are less severe. The combined portfolio diversifies away most of this risk.

---

## Section 5: Action Items

### Immediate

1. **Reclassify IBS Mean Reversion and VIX Mean Reversion into Portfolio A.** They are short-term strategies (2.9d and 5.5d avg hold). Remove from Portfolio B definition. They continue to be the highest-Sharpe individual components in Portfolio A.

2. **Add Congress S2 as a Portfolio B sleeve.** The equity curve exists (`total_nav_3pct_d180_min30d_1x.csv`). The greedy optimizer selects it at step 2 with a +0.56 Sharpe improvement and near-zero correlation to the existing portfolio. No backtest work needed — just add to Portfolio B's sleeve list.

3. **Add Bollinger Band as a Portfolio B sleeve.** It replaces IBS MR in the long-term cluster. Min hold = 30 days, avg hold = 84 days. Equity curve exists (`simple_bet_85pct_1x.csv`).

4. **Update `greedy_optimizer.py` PORTFOLIO_B_SLEEVES dict** to reflect new composition:
   - Remove: `ibs_mean_reversion`, `vix_mean_reversion`
   - Add: `bollinger_band`, `congress_trade_for_trade`

### Near-term

5. **Implement Congress Strategy 1 (1-day SEC hold) and Strategy 3 (Quiver Open).** Both are short-term and belong in Portfolio A. Once backtested, they can be added to Portfolio A's equity pool for combined metrics.

6. **Investigate vol_overlay classification.** Decide whether it is (a) a standalone strategy in Portfolio B, (b) an execution layer applied on top of Portfolio B, or (c) reclassified to SHORT TERM due to daily rebalancing. Currently retained in Portfolio B as an overlay.

7. **Run Portfolio A greedy selection.** Once Congress S1 and S3 are implemented, run the greedy optimizer on Portfolio A candidates (IBS MR, VIX MR, Turn of Month, Overnight Premium, VIX ETN Dual, Congress S1, Congress S3) to find the optimal short-term sub-portfolio.

### Medium-term

8. **Evaluate additional long-term strategies for Portfolio B inclusion.** Candidates not yet in any portfolio with solid standalone Sharpes:
   - `regime_factor_rotation` (Sharpe 0.81, −7.94% MaxDD, monthly) — low drawdown, interesting diversifier
   - `sector_momentum` (Sharpe 0.76, −10.90% MaxDD, monthly) — low drawdown
   - `vix_etn_dual` — if reclassified as long-term (it isn't), would be a strong candidate

9. **Resolve data issues for basket strategies.** Several basket strategies (`cross_asset_carry`, `credit_carry`, `commodity_carry`, etc.) have weak standalone Sharpes (<0.5) or large drawdowns (−58% for commodity_carry) and were not selected by the greedy optimizer. Review whether these should remain in the candidate universe.

10. **Build combined Portfolio A+B allocation layer.** Once both portfolios are correctly classified and implemented, design the cross-portfolio allocation (e.g., 50/50 A/B, or inverse-volatility weighted).

---

*Report generated: 2026-06-19. Source files: strategy backtest notebooks and .py files in `algo_trading/long_term_portfolio/`. Greedy optimizer re-run with Congress S2 as 25th candidate on common window 2016-06-15 → 2025-07-02.*
