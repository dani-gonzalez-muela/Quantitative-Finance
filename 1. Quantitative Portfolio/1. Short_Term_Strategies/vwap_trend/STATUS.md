> **SUPERSEDED (2026-07-02).** This document predates the multi-asset v2 Bonferroni framework and describes a single-ticker QQQ reconstruction that was never tested at that rigor. Under the current framework, QQQ fails outright and the validated instrument set is MTUM + EWW (see `README.md`). Kept below for historical reference only — do not use for trading decisions.

# VWAP Trend — status (2026-06-16)

## Original signal — ARCHIVED basis (do not trade)
1-minute VWAP cross, flips long/short on every cross, exits EOD. ~4,129 round-trips/yr.
- Gross edge **0.54 bps/trade**; realistic QQQ cost **~0.5–0.9 bps round-trip**.
- Curve Sharpe 0.62–0.97 only because the saved curves use **zero slippage**.
- Realistic net: **Sharpe −0.40 / curve −1.6 at $0.01** (see `../../NOTE_curve_vs_significance_fees.md`).
- Verdict: not tradeable — fees exceed the edge. The zero-slip curves (`results/*_daily_equity/`, `vwap_trend_summary.json`) are retained only as the archived original; do not use in the tradeable book.

## Rebuilt variant — minimum-hold (lower turnover) ✅ tradeable
Same VWAP-trend entry, but **suppress flips until a minimum hold elapses** (debounce the whipsaws). Real-time-implementable causal rule; reconstructed exactly from the original contiguous cross-point prices, then run through the standard `simple_bet` pipeline + realistic fees. No new data needed.

Swept hold length through the real pipeline; **45-minute minimum hold is the best and is fee-robust** (~797 trades/yr vs 4,129):

| Slippage/side | Net Sharpe (pipeline) | 
|---|---|
| $0.000 (frictionless) | 0.76 |
| **$0.005 (realistic ½-spread)** | **0.54** |
| $0.010 (conservative full-spread) | 0.33 |

Files: `results/vwap_trend_minhold45_trades.csv` (standardized, 14.9k→ collapsed), `results/vwap_trend_minhold_rebuild.json`.
(10-min hold was also tested: better frictionless but fails at conservative cost; 45-min wins net.)

### Honest assessment
The rescue is real: from a money-loser (−0.40) to genuinely positive and **fee-robust across all cost assumptions** (0.33–0.76). But it's still **the weakest short-term sleeve** (others net 0.79–1.16, SPY 0.85).

### Portfolio A impact (equal-weight proxy)
| Book | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| With OLD VWAP (0-slip) | 2.26 | 24.3% | −5.6% |
| With NEW VWAP-45 (0-slip) | 2.58 | 23.8% | −5.9% |
| With NEW VWAP-45 ($0.005) | 2.38 | 21.8% | −6.4% |
| WITHOUT VWAP (4 sleeves) | **2.70** | 24.1% | −3.5% |

The new VWAP is much better than the old, but **still dilutive** — the 4-sleeve book has the highest Sharpe. Reason: VWAP-45 is low-Sharpe (0.54) and partly correlated with EMA/Intraday (intraday QQQ trend), so at equal weight it pulls the portfolio down. Including it is a reasonable choice if you value having more real sleeves and accept Sharpe 2.70→2.38; the math alone favors 4 sleeves.

### Status: original = archived basis; VWAP-45 = the tradeable version. Per user, included in Portfolio A.
