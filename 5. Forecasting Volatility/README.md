# Forecasting Volatility

**Which model predicts equity volatility best out-of-sample — and what is a good
forecast worth?** Four models (HAR-RV, XGBoost with 210 macro features, AR, Ridge)
compared on identical data, validation and backtest; the winner then applied as an
SPY exposure rule. Full details: `PROJECT_REPORT.md`.

## Result A — the model comparison

Same target (20-day forward realized vol), same expanding-window walk-forward with a
60-day embargo, same vol-targeting backtest for every model (~30 years daily):

| Model | OOS R² | Sharpe improvement vs SPY B&H |
|---|---|---|
| **HAR-RV** (3 terms) | **0.51** | **+0.11** |
| XGBoost (210 features) | 0.25 | +0.08 |
| AR (trailing vol) | −0.46 | +0.07 |
| Ridge (210 features) | −3.71 | +0.06 |

Repeated across assets (2016–2026, `06_Multi_Asset_Shootout.py`): **12 of 12
model×asset combinations improved Sharpe**; strong on SPY and QQQ (~⅓ of the drawdown
cut), weak on GLD (gold vol is barely predictable, R² ≈ 0).

**Takeaway: simplicity wins — the 3-term HAR-RV beats machine learning with 210
features. Volatility persistence IS the signal; the effect is model-robust in equities.**

## Result B — the application

The HAR-RV forecast mapped to a daily SPY exposure rule ("binary defensive": fully
invested unless predicted vol crosses a threshold), 2016–2026, net of costs:

| | SPY buy & hold | HAR-RV overlay (1×) | HAR-RV overlay (2×) |
|---|---|---|---|
| Sharpe | 0.83 | **0.93** | **0.94** |
| CAGR | 13.9% | 10.5% | **20.7%** |
| Max drawdown | −33.8% | **−17.8%** | −33.7% |

**Equal-risk headline: at SPY's own −34% drawdown (the 2× row), the overlay earned
+7.1pp more per year** — the forecast doesn't beat SPY dollar-for-dollar, it beats it
risk-for-risk. Figure: `results/showcase_overlay_vs_spy.png`.

## Run it yourself

1. `python setup_data.py` — populates `data/` from the Quantitative Portfolio repo
   (notebooks also have FRED/yfinance/WRDS download fallbacks).
2. Notebooks in order: `01` → `02` → `03` → `04_Vol_Prediction` → `05_Vol_Model_Shootout`
   → `vol_overlay_Backtest` → `vol_overlay_Implementation`.
3. Cross-asset ranking: `python 06_Multi_Asset_Shootout.py SPY QQQ GLD`.

## Files

| File | Role |
|---|---|
| `01`–`03` notebooks | Data pipeline → daily macro/market feature panel |
| `04_Vol_Prediction.ipynb` | HAR-RV + XGBoost vol models, out-of-sample |
| `05_Vol_Model_Shootout.ipynb` | The 4-model comparison (Result A) |
| `06_Multi_Asset_Shootout.py` | Cross-asset ranking → `results/multi_asset_shootout.md` |
| `vol_overlay_Backtest/Implementation.ipynb` | Exposure-rule application (Result B) |
| `setup_data.py` | One-shot local data setup |
| `results/vol_signal.csv` | Deliverable: daily predicted vol + exposure signal |
| `PROJECT_REPORT.md` | Full write-up |

Reference: Corsi (2009), "A Simple Approximate Long-Memory Model of Realized
Volatility" (HAR-RV). Exposure-mapping rules proprietary.
