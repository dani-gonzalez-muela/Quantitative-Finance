# Portfolio Construction

**Status:** ✅ 2-portfolio structure (2026-07-10). The 3-sleeve split (Intraday / Daily / LongTerm) is retired.

## Method (2026-07-10)

Two portfolios, each built by `greedy_with_threshold` on monthly returns over the candidates' common window:

- **SHORT-TERM** — ONE merged candidate pool of all 9 short-term strategies (5 intraday session: ema_crossover, intraday_momentum, orb, vwap_trend, overnight — overnight is a *normal* pool member, not additive — plus daily: IBS, VIX_MR, VIX_ETN_Dual, Congress_Quiver). Selection = top-5 on the greedy path (strict peak is 4; the 5th, Congress_Quiver, kept as a cheap diversifier per plan). Intraday legs use the $0.005/share fee rerun (see `1. Short_Term_Strategies/_fee_sensitivity.md`).
- **LONG-TERM** — top-9 on the greedy path over the LT timing+selection pool **+ the 4 ex-daily timing names** (Bollinger, Donchian, Turn_of_Month, Congress_TFT; user decision 2026-07-10) = 29 candidates.
- **Combined 2-book blend** — 50/50 monthly-rebalanced, reporting only (book correlation ~0.19).

## Current portfolios (2026-07-10, post-fee rerun)

| Portfolio | Members | Sharpe(m) | CAGR | MaxDD |
|---|---|---|---|---|
| **SHORT-TERM** | ema_crossover, overnight, IBS_v2, orb, Congress_Quiver | 6.21 | 31.4% | −0.3% |
| **LONG-TERM** | quality_profitability, congress_trade_for_trade, turn_of_month, qmj_long_short, bond_trend, commodity_carry, bollinger_band, credit_carry, yield_curve_duration | 1.68 | 6.3% | −4.9% |
| **Combined (50/50)** | both books | 5.83 | 19.5% | −0.3% |

(Exact current numbers: `results/final_portfolios.md`. In-sample Sharpes are optimistic; never size the short-vol names — VIX_MR, VIX_ETN — aggressively: left-tail risk.)

## Files

| File | Role |
|---|---|
| `portfolio_analysis.py` | Candidate tables (stats/gates per strategy) + greedy paths + correlation matrix -> `results/portfolio_candidate_tables.md` |
| `build_final_portfolios.py` | **Canonical builder for the two portfolios** -> `results/final_portfolios.md` + equity CSVs |
| `build_portfolios.py` | Superseded 3-sleeve builder (kept for reference; do not run) |
| `commodity_combined.py` | 50/50 commodity_trend + commodity_carry blend (pre-existing) |
| `results/short_term_portfolio_equity.csv` | SHORT-TERM monthly equity curve |
| `results/long_term_portfolio_equity.csv` | LONG-TERM monthly equity curve |
| `results/combined_2book_equity.csv` | 50/50 blend (reporting only) |
| `results/_legacy_3sleeve_2026-07-10/` | Retired 3-sleeve outputs |
| `_legacy/` | Older superseded builders (Portfolio-B era) |

Run: `python portfolio_analysis.py` (tables), then `python build_final_portfolios.py` (final books).

See `portfolio_creation/PORTFOLIO_CONSTRUCTION_METHODOLOGY.md` for the general methodology; window/mixing conventions unchanged (common-window greedy, stale candidates dropped rather than truncating the window).
