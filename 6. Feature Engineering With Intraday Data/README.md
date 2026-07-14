# Feature Engineering With Intraday Data
*A QuantConnect Research project: from 1,000+ engineered intraday features to 14
validated signals and one deployable trading rule (BTC, 15-minute horizon)*

## What this is

A systematic **feature-engineering and selection pipeline** for high-frequency data,
built entirely in **QuantConnect Research** (QuantBook supplies 1-minute bars for
crypto, futures, forex and indices — no local data management). The test case:
predict whether Bitcoin will be up 15 minutes from now. The deliverables: a validated
14-feature set, and one explicit, human-readable trading rule with measured
out-of-sample performance.

## The steps, in order

**Step 1 — Collect** (notebooks 1–7): 1-minute bars via QuantBook for BTC spot and
futures, commodity/index/currency futures (GC, NG, CL, ES, NQ, VIX…), major forex
pairs and cash indices.

**Step 2 — Merge & engineer** (notebook 8): align everything on common timestamps
(separate 24/7 vs market-hours datasets to avoid look-ahead from forward-filling),
then engineer **1,000+ features**: volatility (realized vol, vol ratios, Bollinger
width), price position (distance to 1h/2h/4h/1d highs and lows, close position within
bar), trend patterns, volume, and cross-asset signals.

**Step 3 — Filter** (notebook 8): variance + correlation filters (|ρ|>0.85 dropped)
→ ~600; then mutual information computed against **7 different target definitions**
(raw return, Sharpe and Sortino thresholds) with stability screening across 10 random
runs → ~250. Features that predict several definitions of "good trade" are more likely
real.

**Step 4 — Model & select** (notebooks 9–11): XGBoost per target with 5-fold
**time-series CV** (expanding window, no look-ahead); consensus feature selection =
intersection of SHAP and gain-importance top-25 → **14 final features**. Selection
improved the model: ROC-AUC 0.52 → 0.54–0.56, overfit gap 6% → 2–3%.

**Step 5 — Extract the rule** (notebooks 12–13): shallow decision trees on the 14
features yield IF–THEN rules (kept only if test accuracy >55%, train–test gap <10%);
independently, profiling what XGBoost "sees" at >75% confidence yields threshold rules.
Both methods converge on the same pattern: **volatility breakout continuation**.

## THE RESULT — the extracted signal and its performance

**The rule** (this is the deliverable — three conditions, no model needed at runtime):

```
IF   rvol_3      > 0.000959   — 15-min realized vol is spiking
AND  hl_range    > 0.001293   — the current bar has a wide high-low range
AND  bb_width_4h > 0.009114   — the 4-hour volatility regime is elevated
THEN long BTC for the next 15 minutes
```

*How it was extracted:* train XGBoost on the engineered features → take only the test
samples where it predicts with >75% confidence → compare the feature distributions of
those samples against the population → the three features above are where the
high-confidence samples deviate most, and the thresholds are their typical values.

**Its out-of-sample performance** (BTC 1-minute bars, chronological 80/20 split,
test window ≈ 5 months, model-confidence filter applied):

| Confidence filter | Trades | Win rate | Avg return / 15-min trade |
|---|---|---|---|
| >50% | 12,847 | 52.1% | +0.041% |
| >70% | 1,892 | 56.8% | +0.142% |
| **>80%** | **377** | **59.2%** | **+0.204%** |

**The three numbers that matter:**

1. **59.2% win rate over 377 trades is statistically significant** — vs the 52.1%
   unfiltered baseline: z = 2.8, **p ≈ 0.003**. The model's confidence genuinely ranks
   opportunities (win rate rises monotonically with confidence — noise doesn't do that).
2. **≈ +0.10% net per trade** after a 0.10% round-trip taker fee →
   **≈ +39% net over the 5-month test window**, in the market only ~3% of the time.
3. **Not headlined on purpose:** annualized Sharpe (~29 as computed per-trade) and
   annualized CAGR — extrapolating 15-minute holds to a year assumes signal frequency,
   fills and capacity persist, which is untested.

## Honest limits

Marginal edge typical of crypto microstructure (ROC-AUC 0.54–0.56 — and ~985 of 1,000
candidate features did NOT survive the pipeline, which is the point). Fees make or
break it: maker execution or wider thresholds would be the first deployment test.
BTC's own features dominated; cross-asset signals added only marginal lift.

## Files & reproducing

Notebooks run inside **QuantConnect Research** (data lives in QC's cloud — create a QC
project and upload them; not runnable locally). `FEATURES.docx` documents each final
feature with its exact pandas construction; `XGBoost Project_1.docx` and
`XGBoost Project_2.pdf` are the original write-ups with full methodology detail.

| Step | Files |
|---|---|
| Collect | `1. BTC_Price_Data` … `7. CashIndices` |
| Merge + engineer + filter | `8. Mega_Merge` |
| Model + select | `9. Model_Crypto`, `10/11. Model_MarketHours` |
| Extract rule | `12. Rule_Extraction`, `13. Getting Features` |
