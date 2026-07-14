# Portfolio A V2 — File Inventory

**Last updated:** 2026-06-28  
All paths relative to `algo_trading/`.

---

## Portfolio-Level Files

| Path | Description | Key contents |
|------|-------------|--------------|
| `portfolio_creation/PORTFOLIO_A_V2/PORTFOLIO_A_V2_RESEARCH.md` | Master research document | Inclusion decisions, stats, fee model, permutation test, research timeline |
| `portfolio_creation/PORTFOLIO_A_V2/FILE_INVENTORY.md` | This file | Index of all key output files |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_combined_equity_v2.csv` | **Final portfolio equity curve** | Date + equity, 2016-01-27 → 2025-07-02. Sharpe=3.43, CAGR=14.06%, MaxDD=−1.71% |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_bucket_a_equity_v2.csv` | Bucket A equity curve | Intraday bucket combined (EMA+IMOM+ORB+VWAP). Sharpe=2.59 |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_bucket_b_equity_v2.csv` | Bucket B equity curve | Multi-day bucket combined (IBS v2+TFT+Quiver+IBS v1). Sharpe=2.38 |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_strategy_returns_v2.csv` | Per-strategy daily returns | Columns: EMA_voltgt, IMOM_voltgt, ORB_QQQ, ORB_MDY, ORB_MTUM, ORB_composite, VWAP_QQQ, VWAP_MTUM, VWAP_EWW, VWAP_composite, IBS_v1, IBS_v2, TFT, Quiver, Bucket_A, Bucket_B, Portfolio |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_stats_v2.json` | Stats JSON | Per-strategy + bucket + portfolio Sharpe/CAGR/MaxDD/Calmar |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_final_results.md` | Final results summary | Human-readable stats table |
| `portfolio_creation/PORTFOLIO_A_V2/greedy_optimizer_a_v2_expanded.py` | Portfolio assembly script | Loads per-strategy equity CSVs, computes buckets, outputs combined equity + stats |
| `portfolio_creation/PORTFOLIO_A_V2/greedy_a_v2_expanded_results.md` | Greedy optimizer output | Incremental Sharpe gain per strategy added |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_diversified_equity.csv` | Earlier iteration equity | Pre-final diversification run |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_diversified_results.md` | Earlier iteration results | Stats from diversification phase |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_expanded_equity.csv` | Earlier iteration equity | Expanded strategy set run |
| `portfolio_creation/PORTFOLIO_A_V2/portfolio_a_v2_final_equity.csv` | Earlier iteration equity | Pre-v2 final run |
| `portfolio_creation/PORTFOLIO_A_V2/bonferroni_raw.json` | Raw Bonferroni JSON | Gate statistics for Bonferroni-tested tickers |
| `portfolio_creation/PORTFOLIO_A_V2/bonferroni_results.md` | Bonferroni results summary | Pass/fail table for Bonferroni rescue tests |

---

## Supporting Research Notes (PORTFOLIO_A_V2/)

| Path | Description |
|------|-------------|
| `portfolio_creation/PORTFOLIO_A_V2/vwap_minhold_v1params_results.md` | VWAP Tier 1 clean retest results (Sharpe=0.5514, 3/3 gates pass) |
| `portfolio_creation/PORTFOLIO_A_V2/vwap_minhold_v2_results.md` | VWAP v2 multiasset summary |
| `portfolio_creation/PORTFOLIO_A_V2/vwap_v2_expansion_results.md` | VWAP per-ticker Bonferroni (MTUM + EWW pass) |
| `portfolio_creation/PORTFOLIO_A_V2/orb_per_ticker_bonferroni_results.md` | ORB per-ticker Bonferroni summary (QQQ/MDY/MTUM pass) |
| `portfolio_creation/PORTFOLIO_A_V2/overnight_bonferroni_intraday_results.md` | Overnight intraday Bonferroni summary (all fail) |
| `portfolio_creation/PORTFOLIO_A_V2/overnight_bonferroni_results.md` | Overnight daily Bonferroni summary |
| `portfolio_creation/PORTFOLIO_A_V2/SESSION_SUMMARY.md` | Session notes |

---

## Bucket A — Strategy Equity Files

### EMA Crossover (Vol-Targeted)
| Path | Description |
|------|-------------|
| `short_term/ema_crossover/results/ema_crossover_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv` | **Used in portfolio.** EMA v1 params, vol-targeted sizing (1x max). Sharpe=2.98 |
| `short_term/ema_crossover/results/ema_crossover_v2_backtest_results.csv` | EMA v2 grid search results across tickers and param sets |
| `short_term/ema_crossover/results/ema_crossover_v2_multiasset_daily_equity/combined_equity.csv` | EMA v2 multiasset combined equity |
| `short_term/ema_crossover/results/ema_crossover_implementations.json` | All implementation variants tested |
| `short_term/ema_crossover/results/ema_crossover_summary.json` | Summary stats across implementations |
| `short_term/ema_crossover/results/ema_crossover_trades.csv` | Trade log |
| `short_term/ema_crossover/results/ema_crossover_v2_canonical_params.json` | v2 canonical params selected in-sample (NOT used in portfolio — overfit) |

### IMOM (Intraday Momentum)
| Path | Description |
|------|-------------|
| `short_term/intraday_momentum/results/intraday_momentum_daily.csv` | **Used in portfolio.** IMOM daily equity. Sharpe=1.40 |
| `short_term/intraday_momentum/results/intraday_momentum_v2_backtest_results.csv` | IMOM v2 backtest results |
| `short_term/intraday_momentum/results/intraday_momentum_implementations.json` | All implementations tested |
| `short_term/intraday_momentum/results/intraday_momentum_summary.json` | Summary stats |
| `short_term/intraday_momentum/results/intraday_momentum_trades.csv` | Trade log |
| `short_term/intraday_momentum/results/intraday_momentum_v2_canonical_params.json` | v2 canonical params |

### ORB (Opening Range Breakout)
| Path | Description |
|------|-------------|
| `short_term/orb/results/orb_per_ticker_equity/QQQ.csv` | **Used in portfolio.** ORB daily equity — QQQ (window=5min, ATR=5%, threshold=0.02%) |
| `short_term/orb/results/orb_per_ticker_equity/MDY.csv` | **Used in portfolio.** ORB daily equity — MDY (window=10min, ATR=2%) |
| `short_term/orb/results/orb_per_ticker_equity/MTUM.csv` | **Used in portfolio.** ORB daily equity — MTUM (window=5min, ATR=2%, threshold=0%) |
| `short_term/orb/results/orb_per_ticker_bonferroni_results.json` | Per-ticker Bonferroni test results; QQQ/MDY/MTUM pass |
| `short_term/orb/results/orb_v2_backtest_results.csv` | ORB v2 basket backtest (canonical atr=10 — failed basket test) |
| `short_term/orb/results/orb_implementations.json` | All implementations tested |
| `short_term/orb/results/orb_summary.json` | Summary stats |
| `short_term/orb/results/orb_trades.csv` | Trade log |
| `short_term/orb/results/orb_v2_canonical_params.json` | v2 canonical params |
| `short_term/orb/results/orb_per_ticker_partial/us_equity_broad.json` | Per-ticker partial results — us_equity_broad basket |
| `short_term/orb/results/orb_per_ticker_partial/us_factor.json` | Per-ticker partial results — us_factor basket |

### VWAP Trend
| Path | Description |
|------|-------------|
| `short_term/vwap_trend/results/vwap_trend_minhold_v1params_equity.csv` | **Used in portfolio (QQQ leg).** VWAP v1 params + minhold=10min + slippage=0 |
| `short_term/vwap_trend/results/vwap_trend_minhold_v1params_results.json` | VWAP Tier 1 test results: Sharpe=0.5514, all 3 gates pass |
| `short_term/vwap_trend/results/vwap_trend_minhold_rebuild.json` | Rebuild validation: no-fee/no-minhold gives Sharpe=0.947, confirms code correctness |
| `short_term/vwap_trend/results/vwap_trend_v2_minhold_backtest_results.csv` | v2 multiasset test (0/7 baskets pass) |
| `short_term/vwap_trend/results/vwap_trend_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv` | VWAP with vol-targeted sizing (not used — minhold version preferred) |
| `short_term/vwap_trend/results/minhold_run.log` | Run log for minhold tests |

### Overnight (Excluded)
| Path | Description |
|------|-------------|
| `short_term/overnight/results/overnight_bonferroni_intraday_us_equity_broad.json` | Intraday Bonferroni retest — all 4 tickers fail at α=0.0125 |
| `short_term/overnight/results/overnight_bonferroni_us_equity_broad.json` | Daily Bonferroni test results |
| `short_term/overnight/results/overnight_v2_backtest_results.csv` | v2 basket backtest (binom_k=0) |

---

## Bucket B — Strategy Equity Files

### IBS Mean Reversion
| Path | Description |
|------|-------------|
| `short_term/ibs_mean_reversion/results/ibs_mean_reversion_v2_multiasset_daily_equity/combined_equity.csv` | **Used in portfolio as IBS v2.** Combined multiasset equity. Sharpe=2.11 |
| `short_term/ibs_mean_reversion/results/ibs_mean_reversion_daily_equity/simple_bet_85pct_1x.csv` | **Used in portfolio as IBS v1.** Original parameterization. Sharpe=1.44 |
| `short_term/ibs_mean_reversion/results/ibs_mean_reversion_v2_backtest_results.csv` | IBS v2 basket backtest results |
| `short_term/ibs_mean_reversion/results/ibs_mean_reversion_implementations.json` | All implementations tested |
| `short_term/ibs_mean_reversion/results/ibs_mean_reversion_summary.json` | Summary stats |
| `short_term/ibs_mean_reversion/results/ibs_mean_reversion_trades.csv` | Trade log |

### Congress Trade-for-Trade (TFT)
| Path | Description |
|------|-------------|
| `long_term/timing/congress_trade_for_trade/results/congress_trade_for_trade_daily_equity/total_nav_3pct_d180_min30d_1x.csv` | **Used in portfolio.** TFT equity (180-day window, 30-day min hold). Sharpe=1.25 |
| `long_term/timing/congress_trade_for_trade/results/congress_trade_for_trade_implementations.json` | All implementations tested |

### Congress Quiver
| Path | Description |
|------|-------------|
| `short_term/congress_momentum/results/congress_momentum_quiver_open_daily_equity/quiver_open_10pct_1x.csv` | **Used in portfolio.** Congress Quiver equity. Sharpe=0.86 |
| `short_term/congress_momentum/results/congress_momentum_quiver_open_implementations.json` | All implementations tested |

---

## Shared Infrastructure

| Path | Description |
|------|-------------|
| `shared/fees.py` | Fee model: SEC fee + FINRA TAF + slippage (0 for VWAP, $0.01/share for ORB/EMA) |
| `short_term/data/intraday_baskets.json` | Basket definitions (us_equity_broad, us_factor, em_regional, etc.) |
