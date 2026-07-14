# Forecasting Volatility — Project Report
*Comparing volatility-forecasting models, and what a good forecast is worth (2016–2026)*

## 1. The question

Volatility clusters: calm days follow calm days, storms follow storms. This project asks
two questions, in order. **(A) Which forecasting model predicts next-month realized
volatility best, out of sample?** — comparing a simple econometric benchmark against
machine learning with hundreds of features. **(B) What is a good forecast worth in
practice?** — using the winning model's forecast to scale equity exposure.

## 2. Data

- Daily prices for SPY / QQQ / GLD; realized volatility built from returns
- ~28 FRED macro series, commodity futures settles (Yahoo), S&P 500 constituent
  stats and financial ratios (WRDS/Compustat) — merged into one daily feature panel
  by notebooks 01→03 (`data/processed/merged_dataset.csv`)
- Local copies populated by `python setup_data.py`; each collection notebook also
  has an API-download fallback (FRED key / yfinance / WRDS)

## 3. Pipeline

| Step | File | What it does |
|---|---|---|
| 1–3 | `01_Data_Collection` → `03_Merge_and_Explore` | Build the daily macro/market feature panel |
| 4 | `04_Vol_Prediction` | HAR-RV and XGBoost vol models, strictly out-of-sample |
| 5 | `05_Vol_Model_Shootout` | **The core experiment:** 4 models, same data, same validation, same backtest |
| 6 | `06_Multi_Asset_Shootout.py` | Same comparison repeated on SPY / QQQ / GLD |
| 7 | `vol_overlay_Backtest` / `_Implementation` | **The application:** forecast → SPY exposure rule, net of costs |

## 4. Result A — the model comparison (the core of the project)

**Long-history shootout** (notebook 05: ~30 years daily, target = 20-day forward realized
vol, expanding window with monthly retraining and a 60-day embargo, identical
vol-targeting backtest for every model):

| Model | OOS R² | Corr | Sharpe improvement vs SPY B&H | Verdict |
|---|---|---|---|---|
| **HAR-RV** (3 terms) | **0.51** | **0.72** | **+0.11** | best |
| XGBoost (210 features) | 0.25 | 0.50 | +0.08 | 2nd |
| AR (trailing vol) | −0.46 | 0.27 | +0.07 | poor forecast, still helps |
| Ridge (210 features) | −3.71 | 0.19 | +0.06 | worst; only model to worsen drawdown |

**Cross-asset check** (script 06: 2016–2026, leaner model set, same protocol):

| Asset | Best model | OOS R² | Sharpe: vol-target vs B&H | MaxDD: vol-target vs B&H |
|---|---|---|---|---|
| SPY | **HAR-RV** | 0.21 | 1.05 vs 0.89 (+0.16) | −22.3% vs −33.8% |
| QQQ | AR(5) / HAR-RV (≈tied) | 0.15 / 0.21 | 1.07 vs 0.88 (+0.19) | −24.8% vs −35.0% |
| GLD | EWMA | ≈0 | 1.10 vs 1.01 (+0.08) | −22.0% vs −22.0% |

**Three findings.** (1) **Simplicity wins:** 3-term HAR-RV beats XGBoost with 210 macro
features — volatility persistence IS the signal; the extra features add nothing.
(2) **The effect is model-robust in equities:** every model, on both equity tickers,
improves the Sharpe of a vol-targeted position and cuts roughly a third of the drawdown
(12 of 12 model×asset combinations improved Sharpe). (3) **It's an equity phenomenon:**
gold's forward vol is barely predictable (R² ≈ 0) and the benefit there is marginal.

## 5. Result B — the application (what the forecast is worth)

`vol_overlay_Backtest` takes the winning HAR-RV forecast on SPY (2016–2026) and tests
four rules that map the forecast to a daily exposure level, **net of transaction costs**:
*symmetric* (lever calm / delever stormy), *asymmetric-cap*, *binary defensive* (fully
invested unless predicted vol crosses a threshold, then cut), *three-state*. Columns
below: Sharpe / CAGR are net annualized performance of holding SPY at the rule's daily
exposure; MaxDD the worst peak-to-trough loss; turnover the average daily exposure change.

| | SPY B&H | Symmetric | Asym. cap | **Binary defensive** | Three-state |
|---|---|---|---|---|---|
| Sharpe (net) | 0.83 | 0.75 | 0.77 | **0.93** | 0.91 |
| CAGR (net) | 13.9% | 12.2% | 11.2% | **10.5%** | 10.4% |
| Max drawdown | −33.8% | −23.3% | −21.7% | **−17.8%** | −17.8% |
| Avg daily turnover | — | 9.7% | 3.8% | **3.5%** | — |

At 1× the winner looks like it "gives up return" — that's the wrong lens, because the
overlay holds less than full exposure on average. Its Sharpe (0.94) is leverage-
invariant, so compare at **equal risk** (`vol_overlay_Implementation`):

| Position | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| SPY buy & hold 1× | 13.6% | 0.81 | −33.8% |
| **Overlay 2.0×** | **20.7%** | **0.94** | **−33.7%** |

**Headline: at the same −34% max drawdown as holding SPY, the HAR-RV overlay earned
+7.1 percentage points more per year.** Two of the four mapping rules don't beat
buy-and-hold even on Sharpe — reported as-is; only the defensive mappings work.

## 6. Limits

Overlay results are single-instrument (SPY) and one decade; the mapping thresholds were
chosen in-sample across 4 variants (mild selection bias); levered rows assume
frictionless financing (real costs at 2× would trim ~1–2pp); simple per-trade fee model.

## 7. Deliverable

`results/vol_signal.csv` — one row per day: predicted vol + exposure per mapping rule.
Any portfolio can consume it directly as an exposure multiplier.

Reference: Corsi (2009), "A Simple Approximate Long-Memory Model of Realized Volatility"
(HAR-RV). Exposure-mapping rules proprietary.
