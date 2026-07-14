# Portfolio B refinement test — 2026-06-16
*Read-only exploration. Your originals (`portfolio_b_metrics.json`, `Portfolio_B_Analysis.ipynb`) are untouched. This folder only adds new files.*

Sleeve curves used = the committed selections: `simple_bet_85pct_1x` for each sleeve, `overlay_1p0x` for Vol Overlay. Common window 2016-06 → 2026-03 (9.7 yrs). Method reproduces the saved baseline (Sharpe 1.53 ≈ saved 1.50).

## Weighting & sleeve variants (1×)

| Variant | Sharpe | CAGR | MaxDD | Vol | Sortino |
|---|---|---|---|---|---|
| 6 sleeves, equal-weight (current) | 1.53 | 13.0% | −11.3% | 8.2% | 2.09 |
| 6 sleeves, inverse-vol | 1.67 | 11.1% | −8.3% | 6.5% | 2.26 |
| **5 sleeves (drop Sector Hybrid), equal** | **1.87** | 11.5% | −8.8% | 5.9% | 2.48 |
| 5 sleeves (drop Sector Hybrid), inverse-vol | 1.81 | 10.5% | −7.4% | 5.6% | 2.42 |

**Finding:** dropping Sector Hybrid is the single biggest improvement — Sharpe 1.53 → **1.87**, drawdown −11.3% → −8.8%. It was the weakest sleeve (Sharpe 0.80), highest-vol (25%), and correlated 0.5–0.6 with IBS/Donchian/GTAA, so it added risk without diversification. For the 5-sleeve book, equal-weight slightly beats inverse-vol (inverse-vol overweights low-Sharpe GTAA).

Trade-off: you give up some raw CAGR (Sector Hybrid had 19% CAGR), but the risk-adjusted and drawdown improvement is large.

## Leverage sweep — winner (5 sleeves, equal-weight)
Sharpe is leverage-invariant (1.87 throughout); leverage is purely a target-drawdown choice.

| Leverage | CAGR | MaxDD |
|---|---|---|
| 1.0× | 11.5% | −8.8% |
| 1.5× | 17.6% | −13.0% |
| 2.0× | 23.9% | −17.0% |
| 2.5× | 30.5% | −20.8% |
| 3.0× | 37.2% | −24.5% |

- **Matched-return to SPY (14.8% CAGR):** ~1.25× → drawdown only **−10.9%** (vs SPY −33.8%), Sharpe 1.87.
- **Matched-DD to SPY (−33.8%):** could lever to ~4× for ~51% CAGR — but that's leverage theater; not recommended.

**Reference — SPY B&H:** CAGR 14.8%, MaxDD −33.8%, Sharpe 0.85.

## Suggested book to actually trade
**5 sleeves equal-weight (IBS MR, Donchian, VIX MR, GTAA, Vol Overlay) at ~1.5×** → ~17.6% CAGR at −13% drawdown, Sharpe 1.87. Beats SPY's return with roughly one-third of its drawdown. If you want to match SPY's return exactly with minimal risk, ~1.25× gives 14.5% CAGR at −10.9%.

*Caveat: 9.7-yr backtest, mostly a bull regime. VIX MR carries short-vol tail risk (watch in a fast crash). Don't stack more short-vol (VIX ETN Dual) on top.*
