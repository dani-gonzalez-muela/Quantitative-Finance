# Session Summary — Strategy v1/v2 Audit + Portfolio A Fix

## EMA v2 High Sharpe — Root Cause Found

**Not a coding bug.** The Sharpe of 3.87 comes from in-sample parameter selection:
- Grid search selected 21/55 EMA with 0.03 ATR stop over the 2016–2026 training window
- These params happened to be extremely well-fitted to the bull-market + 2022 bear year combination
- Running v2 logic with v1's actual params (13/48, stop=0.05 ATR) → SPY Sharpe = **0.83** (vs v1's reported 0.84 — exact match)
- Re-entry after stop exists in BOTH v1 and v2 (it's correct behavior, not a bug)

**Conclusion:** v2 EMA logic is correct. Performance is inflated by in-sample param selection.

---

## v1/v2 Mismatch Fixes

| Strategy | Problem | Fix |
|---|---|---|
| **Overnight v2** | Canonical was `filter_threshold=None` (always enter) — v1 only enters after down days | Locked to `filter_threshold=0` in PARAM_GRID. Rerun complete. Passes **em_regional** basket (Sharpe=0.56, CAGR=5.8%, MaxDD=-27.1%) |
| **VIX MR v2** | Entire file was wrong — tested equity ETFs with VIX regime filter, not SVXY VIX spikes | Archived wrong v2 to `_archive/`. VIX MR is inherently single-asset (SVXY). Basket framework N/A. Using v1 SVXY equity (Sharpe=1.20, 72 trades). |
| **EMA v2** | Logic correct, params in-sample | No code change. Flagged for portfolio use. |
| **VWAP / IBS / IMOM v2** | Already correct | No changes. |

---

## Portfolio A — Diversified Build (EMA v2 excluded)

EMA v2's inflated Sharpe (3.87) dominates the greedy selection and stops it at 2 strategies.
With EMA v2 excluded, greedy builds a genuinely diversified 10-strategy portfolio:

| Metric | EMA v2 Dominated (old) | Diversified (new) |
|---|---|---|
| Strategies | 2 | **10** |
| Sharpe | 4.32 | **2.28** |
| CAGR | 26.5% | **10.6%** |
| MaxDD | -2.4% | **-3.3%** |
| Negative years | 0/9 | **0/9** |

### Strategies selected (greedy, threshold delta ≥ -0.05):
1. ibs_mean_reversion_v2 (Sharpe=2.00) — seed
2. intraday_momentum / v1 sizing (Sharpe=1.47) — Δ+0.31
3. congress_s3_quiver (Sharpe=0.89) — Δ+0.03
4. overnight / v1 (Sharpe=0.75) — Δ-0.02
5. ibs_mean_reversion / v1 single-sleeve (Sharpe=1.35) — Δ-0.02
6. vix_mean_reversion v1 / SVXY (Sharpe=1.18) — Δ-0.03
7. intraday_momentum_v2 (Sharpe=0.80) — Δ-0.00
8. vix_etn_dual (Sharpe=0.87) — Δ-0.01
9. vwap_trend v1 (Sharpe=0.80) — Δ+0.04
10. overnight_v2 / em_regional (Sharpe=0.58) — Δ-0.02

### Annual Returns:
2017: +4.71% | 2018: +9.73% | 2019: +6.19% | 2020: +23.34%
2021: +15.47% | 2022: +12.04% | 2023: +7.31% | 2024: +6.52% | 2025: +5.43%

### Files saved:
- `portfolio_a_v2_diversified_results.md` — full report with correlation matrix
- `portfolio_a_v2_diversified_equity.csv` — daily equity curve
- `greedy_a_v2_expanded_results.md` — EMA-dominated version (for reference)

---

## Still Open
- Congress Trade-for-Trade (Strategy 2): Sharpe=0.95, CAGR=10.4% — add to portfolio?
- ORB: All negative Sharpe across all baskets — excluded
- VWAP v2: Sharpe=0.12 combined — too weak, excluded
