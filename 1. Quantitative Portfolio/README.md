# Systematic Trading Research — Two-Portfolio Book

End-to-end systematic strategy research: **38 candidate strategies** researched on
multi-asset ETF baskets, backtested with realistic transaction costs, filtered through
a two-tier statistical validation pipeline, and assembled by greedy diversification
into **two final portfolios**.

| Portfolio | Holding horizon | Members | Sharpe(m) | CAGR | MaxDD |
|---|---|---|---|---|---|
| **SHORT-TERM** | minutes → few days | ema_crossover, overnight, IBS, ORB, congress_momentum (top-5 of 9) | 6.21 | 31.4% | −0.3% |
| **LONG-TERM** | 30+ days | quality_profitability, congress_trade_for_trade, turn_of_month, QMJ, bond_trend, commodity_carry, bollinger_band, credit_carry, yield_curve_duration (top-9 of 29) | 1.68 | 6.3% | −4.9% |
| **Combined (50/50)** | reporting view | both books (corr ~0.19) | 5.83 | 19.5% | −0.3% |

*In-sample, net of modeled fees (SEC + FINRA TAF + $0.005/share slippage on intraday legs).
Read Sharpes as upper bounds.*

## The pipeline (per strategy)

1. **Signal research** — economic rationale + bounded parameter grid, fixed before testing.
2. **Multi-asset backtest** — grid search per basket of related ETFs; canonical params =
   best *median* Sharpe across the basket's instruments; binomial test on the count of
   individually significant tickers.
3. **3-gate significance** — t-test (p<0.05) + bootstrap (5th-pct Sharpe>0) + sign-permutation
   (p<0.05) on the basket composite; failed baskets get a per-instrument **Bonferroni rescue**
   (α = 0.05/N).
4. **Implementation** — three sizing variants across the full validated universe;
   best-by-Sharpe becomes the strategy's canonical curve.
5. **Portfolio assembly** — greedy forward selection on monthly returns
   (each step adds the candidate that maximizes the blend's Sharpe).

## Repository layout

| Folder | Contents |
|---|---|
| `0. Data/` | Datasets + loaders + store registry in its README (machine-read by `_shared/paths.py`). Gitignored except the README. |
| `1. Short_Term_Strategies/` | The 9 short-term strategies (backtest + implementation + README each) |
| `2. Long_Term_Strategies/` | `timing/` + `selection/` long-term candidates |
| `3. Portfolio_construction/` | Candidate tables, greedy selection, the two final books |
| `4. Dashboard/` | Interactive Dash app (see below) |
| `_shared/` | Shared package: fees, sizing, significance, paths resolver |
| `TODO.md` | Optional future work + proxy-data appendix |

Every folder has its own README with details. Data sources: Alpaca 5-minute bars (~44 ETFs,
10y), daily ETF histories incl. VIX ETNs, WRDS/CRSP + Compustat fundamentals and ratios,
CBOE VIX term structure, FRED rates, QuiverQuant congressional disclosures.

## Run the dashboard

```
cd "4. Dashboard"
pip install -r requirements.txt
python app.py        # http://127.0.0.1:7860
```

Overview tab has the full end-to-end methodology write-up; Short-Term / Long-Term tabs
drill into each book; Archived Strategies shows every candidate that didn't make the cut.

---
*Backtest research — not investment advice.*
