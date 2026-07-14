# Fair Value Gap

**Portfolio:** Short-Term | **Status:** ❌ Research stalled — never validated | **Canonical:** none (research notebooks only)

## 1. Strategy

Price-action strategy on "fair value gaps": 3-candle imbalance zones where the middle
candle's move leaves a gap between candle 1's high and candle 3's low (or vice versa);
the hypothesis is that price returns to "fill" the gap. Intraday/daily timeframe.

## 2. Status & verdict

Research reached a first backtest (`v1/FVG_Backtest.ipynb`, trade log in `v1/results/`)
but never entered the v2 multi-asset pipeline — no basket grid search, no 3-gate
significance test, no fee-modeled implementation. FVG is popular in discretionary
trading but thinly evidenced academically; if ever revived, the standard pipeline
(us_equity_broad basket at 5-min bars, real fees) is exactly the right filter.

## 3. Files

| File | Description |
|---|---|
| `v1/FVG_Backtest.ipynb` | First backtest attempt |
| `v1/OG_Research/` | Original exploration notebook |
| `v1/results/fvg_trades.csv` | Trade log from the first backtest |

Reference: "fair value gap" / imbalance concepts from discretionary ICT-style trading; no academic source.
