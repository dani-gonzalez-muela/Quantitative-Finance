# Portfolio Deploy Guide
**Version:** 2026-06-19  
**Status:** Live-ready reference — all strategies backtested 2016–2025 (~9.5 years)

---

## Overview

| Portfolio | Strategies | Sharpe | CAGR (1x) | MaxDD | Rebalance |
|---|---|---|---|---|---|
| **A — Short-Term** | 5 | 3.14 | 14.4% | -2.8% | Daily |
| **B — Long-Term** | 9 | 1.98 | 9.2% | -9.4% | Monthly |
| **A+B Combined (A2x / B1x, 50/50)** | 14 | **3.50** | **16.7%** | **-2.9%** | — |

**Capital allocation:** 50% to Portfolio A, 50% to Portfolio B.  
**Portfolio A leverage:** Run at 2x (internal vol-targeting, not margin). CAGR ~28% at 2x.  
**Portfolio B leverage:** 1x recommended. Bond Carry and Congress S2 are sizing-sensitive.

---

## Portfolio A — Short-Term Strategies

*All strategies trade US equities intraday or overnight. Daily management required.*

---

### A1 · EMA Crossover
**Type:** Intraday Trend Following  
**Instrument:** QQQ (5-min bars)  
**Capital allocation:** 20% of Portfolio A  
**Recommended sizing:** `intraday_asset_vol_2pct_14d` — sizes to 2% daily vol using 14-day realized vol. Apply 2x cap.

**Signal:**
- Long: 13-EMA > 48-EMA > 200-EMA AND price breaks above prior-day high
- Short: All three EMAs inverted AND price breaks below prior-day low
- Always flat at 15:55 ET

**Entry:** Market order at signal bar's next open (5-min)  
**Exit:** ATR-based stop (5% of 14-period ATR) OR 15:55 ET flat  
**Stop:** Hard stop at ATR threshold; no overnight holds

**Performance (1x):** Sharpe 2.89 | CAGR 41% | MaxDD -5.6%  
**Notebook:** `short_term_portfolio/ema_crossover/EMA_Backtest.ipynb`  
**Equity file:** `ema_crossover/results/ema_crossover_daily_equity/intraday_asset_vol_2pct_14d_2x_max.csv` (2x)

---

### A2 · IBS Mean Reversion
**Type:** Daily Mean Reversion  
**Instrument:** SPY (daily bars)  
**Capital allocation:** 20% of Portfolio A  
**Recommended sizing:** 85% of capital per trade (simple bet)

**Signal:** Internal Bar Score (IBS) = (Close - Low) / (High - Low)
- Long: IBS < 0.2 (close near day's low → oversold)
- Short: IBS > 0.8 (close near day's high → overbought)
- Enter at today's close; exit at next day's close

**Entry:** MOC (Market On Close) order  
**Exit:** MOC next day — hold exactly 1 day  
**Stop:** None (mean-reversion, tight 1-day hold is the risk control)  
**Avg hold:** ~2.9 trading days (some signals chain)

**Performance (1x):** Sharpe 1.38 | CAGR 11.9% | MaxDD -7.9%  
**Notebook:** `long_term_portfolio/ibs_mean_reversion/IBS_Backtest.ipynb`  
**Equity file:** `ibs_mean_reversion/results/ibs_mean_reversion_daily_equity/simple_bet_85pct_1x.csv`

---

### A3 · Congress Momentum (Strategy 3)
**Type:** Event-Driven Political Alpha  
**Instrument:** Individual stocks (multi)  
**Capital allocation:** 20% of Portfolio A  
**Recommended sizing:** 10% of capital per trade (max ~10 concurrent positions)

**Signal:** Filter: Purchase disclosures where `Annualized_Traded_To_File > 1.5` (stock already up strongly before Quiver published). Buy at OPEN on Quiver upload day, sell at CLOSE same day (1-day hold). Long only.

**Data source:** Quiver Quantitative congressional trading API  
**Entry:** Open of Quiver upload day  
**Exit:** Close of same day  
**Hold:** Same-day (intraday)  
**Filter:** Only Purchase transactions, not Sales

**Performance (1x):** Sharpe 0.85 | CAGR 7.3% | MaxDD -10.5%  
**Notebook:** `short_term_portfolio/congress_momentum/congress_momentum_Backtest.ipynb`  
**Equity file:** `congress_momentum/results/congress_momentum_quiver_open_daily_equity/quiver_open_10pct_1x.csv`

---

### A4 · Overnight Carry
**Type:** Overnight Carry / Mean Reversion  
**Instrument:** SPY  
**Capital allocation:** 20% of Portfolio A  
**Recommended sizing:** 85% of capital per trade

**Signal:** If SPY's intraday session return (Open→Close) was negative today → go long at 15:55 ET close. Exit at next morning open (9:30 ET).
- Statistical basis: market-vs-overnight return correlation r = −0.08 (p < 0.0001)
- Only trades on down-session days (~40% of days)

**Entry:** MOO (Market On Open) next morning or limit at prior close  
**Exit:** 9:30 ET open  
**Stop:** None (overnight hold, small position)

**Performance (1x):** Sharpe 0.82 | CAGR 3.6% | MaxDD -7.2%  
**Notebook:** `short_term_portfolio/overnight/Overnight_Backtest.ipynb`  
**Equity file:** `overnight/results/overnight_daily_equity/simple_85pct_bet.csv`

---

### A5 · Intraday Momentum
**Type:** Intraday Momentum  
**Instrument:** SPY (30-min bars)  
**Capital allocation:** 20% of Portfolio A  
**Recommended sizing:** `intraday_asset_vol_2pct_14d` — 2% daily vol target (paper's exact method)

**Signal:** Time-varying Noise Area at 30-min checkpoints (14-day lookback).
- Long: SPY breaks above upper noise boundary
- Short: SPY breaks below lower noise boundary
- Fast Alpha overlay for better entry fills

**Entry:** At breakout bar's next 30-min open  
**Exit:** Trailing stop = max(current noise band, VWAP). Flat at 15:55 ET.  
**Reference:** Zarattini, Aziz & Barbon (2024)

**Performance (1x):** Sharpe 1.31 | CAGR 8.7% | MaxDD -6.6%  
**Notebook:** `short_term_portfolio/intraday_momentum/Intraday_Momentum_Backtest.ipynb`  
**Equity file:** `intraday_momentum/results/intraday_momentum_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv`

---

## Portfolio B — Long-Term Strategies

*Monthly rebalancing unless otherwise noted. Daily monitoring sufficient.*

---

### B1 · Congress Trade-for-Trade (Strategy 2)
**Type:** Political Alpha — Trade Mirroring  
**Instrument:** Individual stocks (multi)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** 3% of total NAV per position (`TOTAL_NAV_PCT = 0.03`)

**Signal:** Mirror active politicians' stock purchases. Filter: ≥15 historical trades, ≥4 active years, ≥50% win rate → 58 qualifying politicians.
- Buy at close when qualifying politician files a purchase disclosure
- Hold cap: 180 days (`HOLDING_CAP_DAYS = 180`)
- Minimum hold: 30 days (`MIN_HOLD_DAYS = 30`)
- Purchases only (not sales)

**Entry:** Close on filing date  
**Exit:** After 180 days OR minimum 30 days hold  
**Rebalance:** Continuous (new filings drive entries)

**Performance:** Sharpe 1.27 | CAGR 10.7% | MaxDD -9.6%  
**Notebook:** `long_term_portfolio/congress_trade_for_trade/congress_trade_for_trade_Backtest.ipynb`  
**Equity file:** `congress_trade_for_trade/results/congress_trade_for_trade_daily_equity/total_nav_3pct_d180_min30d_1x.csv`

---

### B2 · GTAA (Global Tactical Asset Allocation)
**Type:** Global Macro / Tactical AA  
**Instrument:** Multi-asset ETFs (global equity, bonds, commodities, REITs)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Asset vol target 10% annual (`asset_vol_10pct_1x`)

**Signal:** Faber-style GTAA — monthly momentum + trend filter across 5 global asset classes. Hold top N assets that are above their 10-month moving average. Move to cash if below SMA.

**Entry/Exit:** Monthly rebalance on last trading day of month  
**Rebalance:** Monthly

**Performance:** Sharpe 1.02 | CAGR ~8% | MaxDD ~-12%  
**Notebook:** `long_term_portfolio/gtaa/GTAA_Backtest.ipynb`  
**Equity file:** `gtaa/results/gtaa_daily_equity/asset_vol_10pct_1x.csv`

---

### B3 · Vol Overlay
**Type:** Volatility Regime Overlay  
**Instrument:** Overlaid on existing equity/bond portfolio  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** 1x overlay (`overlay_1p0x`)

**Signal:** Vol regime detection (GMM or XGBoost). Reduces equity exposure in high-vol regimes, increases in low-vol. Functions as portfolio insurance / dynamic hedge.

**Entry/Exit:** Daily signal, positions adjusted at open  
**Rebalance:** Daily signal, but monthly bulk rebalance sufficient

**Performance:** Sharpe 0.99 | CAGR ~8% | MaxDD ~-10%  
**Notebook:** `long_term_portfolio/vol_overlay/Vol_Overlay_Backtest.ipynb`  
**Equity file:** `vol_overlay/results/vol_overlay_daily_equity/overlay_1p0x.csv`

---

### B4 · Quality Profitability
**Type:** Quality Factor  
**Instrument:** US Equities (large-cap)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Equal-weight among selected stocks

**Signal:** Long high-quality/high-profitability stocks (high ROE, low accruals, stable earnings). Monthly rebalance.

**Entry/Exit:** Monthly rebalance  
**Rebalance:** Monthly

**Performance:** Sharpe 0.79 | CAGR ~7% | MaxDD ~-15%  
**Notebook:** `long_term_portfolio/quality_profitability/Quality_Profitability_Backtest.ipynb`  
**Equity file:** `quality_profitability/results/quality_profitability_daily_equity/quality_profitability_daily_equity.csv`

---

### B5 · Turn of Month — Real Assets Basket
**Type:** Calendar Seasonality  
**Instrument:** Real Asset ETFs (GLD, TLT, VNQ, DJP, SLV, IAU — basket)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Equal-weight across basket instruments

**Signal:** Go long real assets on last 4 trading days + first 3 trading days of each month (Turn-of-Month effect). Strong seasonal pattern in commodities, gold, REITs.

**Entry:** Day −4 before month end close  
**Exit:** Day +3 after month start close  
**Rebalance:** Monthly rhythm (automatic)

**Performance (basket):** Sharpe 0.84 | CAGR ~6% | MaxDD ~-8%  
**Basket returns file:** `multi_asset_expansion/results/basket_returns.csv` (col: `turn_of_month__real_assets`)

---

### B6 · Bond Duration Carry
**Type:** Bond Carry  
**Instrument:** US Bond ETFs (TLT, IEF, SHY, BIL — basket, EW)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Equal-weight (NOT inverse-vol — BIL distorts)

**Signal:** Hold longer-duration bonds when the yield curve is positively sloped (carry trade). Reduce duration in inverted or flat curve environments.

**Entry/Exit:** Monthly rebalance  
**Rebalance:** Monthly  
**Note:** Use EW weighting, not inverse-vol. BIL near-zero vol artificially dominates inverse-vol weighting.

**Performance (basket EW):** Sharpe 0.63 | CAGR ~4% | MaxDD ~-6%  
**Basket returns file:** `multi_asset_expansion/results/basket_returns.csv` (col: `bond_duration_carry__bonds_us`)

---

### B7 · Donchian Channel Trend
**Type:** Trend Following  
**Instrument:** Multi-asset ETFs (US equity, bonds, commodities)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Asset vol target 10% annual

**Signal:** Classic Donchian Channel breakout — long when price breaks above N-day high, short/flat when below N-day low. Monthly signal check.

**Entry/Exit:** Monthly rebalance  
**Rebalance:** Monthly

**Performance:** Sharpe 0.94 | CAGR ~7% | MaxDD ~-12%  
**Notebook:** `long_term_portfolio/donchian_channel/Donchian_Backtest.ipynb`  
**Equity file:** `donchian_channel/results/donchian_channel_daily_equity/asset_vol_10pct_1x.csv`

---

### B8 · Cross-Sectional Momentum
**Type:** Cross-Sectional Momentum  
**Instrument:** US ETFs (sectors, factors)  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Equal-weight among top N momentum ETFs

**Signal:** Rank ETFs by trailing 12-1 month momentum. Long top decile, short (or flat) bottom decile. Monthly rebalance.

**Entry/Exit:** Monthly rebalance  
**Rebalance:** Monthly  
**Note:** High correlation with Quality Profitability (r=0.81) — watch combined exposure.

**Performance:** Sharpe 0.85 | CAGR ~7% | MaxDD ~-12%  
**Notebook:** `long_term_portfolio/us_cross_sectional_momentum/XSMomentum_Backtest.ipynb`  
**Equity file:** `us_cross_sectional_momentum/results/us_cross_sectional_momentum_daily_equity/us_cross_sectional_momentum_daily_equity.csv`

---

### B9 · Bollinger Band Mean Reversion
**Type:** Mean Reversion  
**Instrument:** US Equity ETFs  
**Capital allocation:** ~11% of Portfolio B  
**Sizing:** Asset vol target 10% annual

**Signal:** Buy at lower Bollinger Band, sell at upper band or midline. Works on monthly/weekly bars for ETFs.

**Entry/Exit:** Monthly rebalance  
**Rebalance:** Monthly

**Performance:** Sharpe 0.77 | CAGR ~6% | MaxDD ~-13%  
**Notebook:** `long_term_portfolio/bollinger_band/Bollinger_Backtest.ipynb`  
**Equity file:** `bollinger_band/results/bollinger_band_daily_equity/asset_vol_10pct_1x.csv`

---

## Operational Checklist

### Daily (Portfolio A)
- [ ] Pre-market: compute yesterday's IBS score → queue A2 order if IBS < 0.2 or > 0.8
- [ ] Pre-market: check if last session was negative → queue A4 overnight entry
- [ ] 9:30 ET: A4 overnight EXIT at open
- [ ] 9:30 ET: check A5 (IntradayMom) — is SPY above/below noise boundary?
- [ ] 9:35 ET: monitor A1 (EMA) 5-min bar alignment, execute if signal fires
- [ ] 15:55 ET: flatten all intraday positions (A1, A5)
- [ ] 15:55 ET: check A4 entry signal (if session return negative)
- [ ] EOD: check Quiver for new congress disclosures → queue A3 entries for tomorrow open

### Monthly (Portfolio B)
- [ ] Last trading day of month: rebalance B2 (GTAA), B7 (Donchian), B8 (XS Momentum), B9 (Bollinger)
- [ ] Last 4 days of month: B5 (Turn of Month) — enter real assets basket
- [ ] First 3 days of month: B5 — exit real assets basket
- [ ] Monthly: review B4 (Quality) stock rankings, rebalance if needed
- [ ] Monthly: check B6 (Bond Carry) yield curve slope, adjust duration
- [ ] Daily monitor: B3 (Vol Overlay) — check vol regime signal, adjust if regime changes
- [ ] Continuous: B1 (Congress S2) — check new filings daily, enter on qualifying disclosures

### Risk Limits
| Limit | Value |
|---|---|
| Max single strategy loss/month | -5% of portfolio |
| Portfolio A max drawdown trigger | -8% → reduce to 50% sizing |
| Portfolio B max drawdown trigger | -15% → reduce to 50% sizing |
| Combined max drawdown trigger | -10% → review all positions |
| Congress S2 max concurrent positions | ~15 (3% NAV × ~5 avg active) |
| Congress S3 max concurrent positions | 10 (10% capital per trade) |

---

## Backtest Equity Files — Quick Reference

| Strategy | File Path | 1x Sharpe |
|---|---|---|
| A1: EMA | `short_term_portfolio/ema_crossover/results/.../intraday_asset_vol_2pct_14d_2x_max.csv` | 2.89 |
| A2: IBS MR | `long_term_portfolio/ibs_mean_reversion/results/.../simple_bet_85pct_1x.csv` | 1.38 |
| A3: Congress S3 | `short_term_portfolio/congress_momentum/results/.../quiver_open_10pct_1x.csv` | 0.85 |
| A4: Overnight | `short_term_portfolio/overnight/results/.../simple_85pct_bet.csv` | 0.82 |
| A5: Intraday Mom | `short_term_portfolio/intraday_momentum/results/.../intraday_asset_vol_2pct_14d_1x_max.csv` | 1.31 |
| B1: Congress S2 | `long_term_portfolio/congress_trade_for_trade/results/.../total_nav_3pct_d180_min30d_1x.csv` | 1.27 |
| B2: GTAA | `long_term_portfolio/gtaa/results/.../asset_vol_10pct_1x.csv` | 1.02 |
| B3: Vol Overlay | `long_term_portfolio/vol_overlay/results/.../overlay_1p0x.csv` | 0.99 |
| B4: Quality | `long_term_portfolio/quality_profitability/results/.../quality_profitability_daily_equity.csv` | 0.79 |
| B5: Turn of Month | `long_term_portfolio/multi_asset_expansion/results/basket_returns.csv` (col) | 0.84 |
| B6: Bond Carry | `long_term_portfolio/multi_asset_expansion/results/basket_returns.csv` (col) | 0.63 |
| B7: Donchian | `long_term_portfolio/donchian_channel/results/.../asset_vol_10pct_1x.csv` | 0.94 |
| B8: XS Momentum | `long_term_portfolio/us_cross_sectional_momentum/results/.../us_cross_sectional_momentum_daily_equity.csv` | 0.85 |
| B9: Bollinger | `long_term_portfolio/bollinger_band/results/.../asset_vol_10pct_1x.csv` | 0.77 |

---

## Strategy Correlation Notes

**A portfolio:** Near-zero correlations across all pairs except A1↔A5 (r=0.49 — both intraday trend on US large-cap). Acceptable overlap.  
**B portfolio:** Quality (B4) ↔ XS Momentum (B8) at r=0.81 — highest correlation pair. Both are US equity factor strategies. Monitor combined US factor exposure.  
**A vs B:** r=0.20 — genuine diversification. A is intraday/event-driven; B is monthly systematic.  

---

## Strategies Evaluated But Not Selected

*(Kept in codebase for future research)*

| Strategy | Reason Not Selected |
|---|---|
| VWAP Trend (intraday) | r=0.48 with EMA — redundant trend signal on same instrument |
| ORB (intraday) | Δ=-0.07 Sharpe when added to Portfolio A — marginal improvement |
| VIX Mean Reversion | Δ=-0.09 vs Portfolio A — small drag on combined Sharpe |
| VIX ETN Dual | Δ=-0.19 — hurts more than it helps |
| Turn of Month (intraday) | Δ=-0.14 in Portfolio A context |
| Congress S1 (1-day SEC) | Infrastructure not built — needs EDGAR scraping |
| Archived strategies (seasonal, PEAD, etc.) | Did not pass significance filter (Sharpe < 0.40 or t-stat < 1.5) |

---

*Generated by greedy_optimizer_a_v2.py + portfolio_b_greedy + combined_portfolio_analysis.md*  
*Next review: after 6 months of live data*
