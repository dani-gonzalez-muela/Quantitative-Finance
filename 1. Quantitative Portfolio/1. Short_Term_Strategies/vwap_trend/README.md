# VWAP Trend

**Portfolio:** Intraday | **Status:** Active (narrow — 2 instruments) | **Canonical file:** `vwap_trend_Implementation_multiasset_v2.py`

---

## 1. Strategy

VWAP-cross on 5-minute intraday bars. Enters long at 09:30 if close > VWAP*(1+threshold), short if close < VWAP*(1-threshold). Flips position whenever price crosses VWAP, but flips are suppressed for a minimum hold window (debounces whipsaws). Exits at a fixed time-of-day close.

- **Entry:** 09:30 bar, vs. VWAP with a threshold band
- **Exit:** VWAP-cross flip (after min-hold) or 15:55 time exit
- **Direction:** Long and short
- **Session:** 09:30–16:00 ET
- **Fees:** `shared/fees.py`, `calculate_fees_pct` with `slippage=0` — VWAP-cross entries/exits are modeled as limit orders filling exactly at VWAP/close, so only SEC fee + FINRA TAF apply. This is the "proper fees" / optimistic-fill assumption, chosen as canonical over a 0.5% flat-slippage alternative (see §3).

---

## 2. v2 Procedure

### Backtest (`vwap_trend_Backtest_multiasset_v2.py`)

**Phase 1 — Basket-level significance:**

For each basket, a grid search over `vwap_threshold` ∈ {0.0, 0.001, 0.002} (exit fixed at 15:55, min-hold fixed at 10 minutes) finds the canonical threshold that maximizes **median Sharpe across all tickers in the basket**.

The basket then passes a **3-gate significance test** on the equal-weight composite daily returns:
- Gate 1: one-sided t-test `p < 0.05` (on monthly returns)
- Gate 2: bootstrap 5th-percentile Sharpe > 0 (1000 draws, on daily returns)
- Gate 3: sign-randomization permutation test `p < 0.05` (1000 draws, on daily returns)

If all three gates pass, all tickers in the basket are included at the canonical threshold and trade-level CSVs are emitted.

**Phase 2 — Bonferroni rescue (failed baskets only):**

For baskets that fail Phase 1 (all 7 did, in the current run — see §4), each ticker is individually grid-searched and tested at Bonferroni-corrected α = 0.05/N (N = tickers in that basket). Only tickers passing all 3 gates at the stricter alpha are rescued. Trade CSVs are emitted for rescued tickers.

### Implementation (`vwap_trend_Implementation_multiasset_v2.py`)

Loads both result JSONs and the trade-level CSVs directly (no signal recompute). Equal-weights 1/N across all validated instruments. Runs three sizing variants:
1. **simple_bet** — fixed 85% of sleeve equity per trade
2. **intraday_asset_vol** — 2% daily vol target on underlying asset, 4× max leverage (paper method)
3. **vol_targeting** — 10% annualized strategy-return vol target, 2× max leverage

The variant with the highest portfolio Sharpe is selected and written as `results/equity/combined_equity_final.csv`. The choice is recorded in `results/vwap_trend_v2_implementations.json` under `selected_variant`. Trades and equity curves are written directly to `results/trades/` and `results/equity/` — no staging directory.

Note (resolved 2026-07-10): the sizing/Implementation step now uses `SLIPPAGE=0` by default, consistent with the Phase 1/2 slippage-0 significance assumption (previously it silently applied the shared $0.01 default, which is why the old portfolio table looked so much worse). The $0.005 sensitivity lives in `results/_slip0p005/`.

---

## 3. Methodology decisions (locked in 2026-07-01)

This version consolidates what had been three separate, non-aligned scripts (`Backtest_multiasset_v2.py`, `Backtest_multiasset_v2_minhold.py`, `v2_proper_fees_expansion.py`) into one canonical two-phase Backtest script, matching `ema_crossover`'s pattern. Two judgment calls were made explicitly by the user rather than assumed:

- **Canonical basis:** the multi-asset, 5-minute-bar, 10-minute-minhold, full-Bonferroni framework — **not** the older single-ticker QQQ, 1-minute-bar, 45-minute-minhold reconstruction documented in the now-superseded `STATUS.md`. QQQ was re-tested under this framework and **fails** every gate (net Sharpe 0.60, t_p=0.05, boot5 negative, perm_p=0.12) — it is not part of the validated instrument set below, despite `STATUS.md` calling it tradeable under a different, lower-rigor methodology.
- **Slippage/fee assumption:** $0 slippage, exact VWAP fills, SEC + FINRA TAF only (the "proper fees" methodology from the superseded `v2_proper_fees_expansion.py`), chosen over a 0.5% flat-slippage alternative.

Also fixed as part of this consolidation:
- **ROOT path bug**: all four legacy scripts computed `ROOT` two directories up instead of three, causing `DATA_DIR` to resolve to a doubled `short_term/short_term/...` path and `shared.fees` imports to potentially fail depending on execution context. Fixed to match `ema_crossover`'s 3-level `..`.
- **Basket/ticker mismatch**: the old Implementation script's `BASKETS` dict was missing VOO, dropped `em_regional` entirely, and had `EEM`/`EWZ` misfiled into `intl_liquid`. Now matches the Backtest script's `BASKETS` exactly.
- **Unguarded dict comprehension**: `canonical.items()` filtering now checks `isinstance(p, dict)`, matching `ema_crossover`'s existing guard.
- **DST-safe trade loading**: trade CSV timestamps are parsed with `pd.to_datetime(..., utc=True)`, matching `ema_crossover`'s fix for the same mixed-offset (-04:00/-05:00) hazard.

---

## 4. Basket Results (v2)

**Run date:** 2026-07-02 | **Data:** 5-min intraday, ~10.5 years (2016–2026)

All 7 baskets **fail** Phase 1 (no basket passes the 3-gate test at the basket level):

| Basket | Canonical threshold | Median Sharpe | Binomial k/N | Gate |
|---|---|---|---|---|
| us_equity_broad | 0.001 | 0.34 | 2/7 (p=0.044, binom pass) | fail (t_p=0.22, boot5<0, perm_p=0.28) |
| us_factor | 0.001 | 0.16 | 1/8 | fail |
| us_sectors | 0.001 | −0.05 | 2/11 | fail |
| bonds_us | 0.002 | 0.28 | 0/5 | fail |
| commodities | 0.002 | −0.13 | 0/4 | fail |
| em_regional | 0.002 | 0.28 | 1/4 | fail (t_p=0.27, boot5<0, perm_p=0.31) |
| intl_liquid | 0.002 | 0.39 | 1/5 | fail (perm_p=0.019, but boot5 marginal) |

**Phase 2 Bonferroni rescue** was run for all 44 tickers across the 7 failed baskets. Exactly **2 of 44** pass all three gates at their basket's Bonferroni-corrected α:

| Ticker | Basket | Threshold | Sharpe | Bonferroni α | t_p | boot5 | perm_p |
|---|---|---|---|---|---|---|---|
| **MTUM** | us_factor | 0.001 | 0.798 | 0.00625 | 0.0058 | 0.28 | 0.006 |
| **EWW** | em_regional | 0.0 | 1.077 | 0.0125 | <0.001 | 0.55 | 0.000 |

No other ticker in any basket passes its Bonferroni threshold (several come close — QQQ, EFA, SHY, LQD — but none clear all 3 gates).

---

## 5. Validated Instruments — and an important caveat on EWW

Total: **2 instruments**, both via Bonferroni rescue (no basket passes outright).

| Source | Basket | Ticker |
|---|---|---|
| Bonferroni rescued | us_factor | MTUM |
| Bonferroni rescued | em_regional | EWW |

**EWW's statistical pass does not survive realistic position sizing.** EWW trades very frequently under this signal (~1,591 trades/year, 26.8% win rate, mean edge only +0.0154 bps/trade) — the edge is real and statistically distinguishable from zero over 16,651 trades (hence the Bonferroni pass), but it is thin and low-win-rate, which is exactly the profile that suffers badly under fixed-fraction compounding sizing. Under `simple_bet` (85% of equity) and `vol_targeting` (up to 2× leverage), EWW's sleeve equity curve loses **99.4% and 99.9%** of capital respectively over the backtest. Even under `intraday_asset_vol` (the gentlest variant, capped at 4× daily leverage but resized once per day rather than per trade), EWW still draws down **88%**.

MTUM does not have this problem — lower trade frequency (~436/year), and positive Sharpe under all three variants (0.18 / 0.72 / 0.13).

This is a real tension worth flagging rather than quietly netting out: EWW passed the significance framework (using the $0-slippage assumption, on non-compounding daily-additive returns) but is not safely tradeable at any of the three standard sizing variants used here. The portfolio numbers below **include EWW** per the canonical-basis decision in §3 (go with the full Bonferroni-rescued set), but you may want to reconsider EWW specifically — either exclude it, or size it far more conservatively than these three standard variants — before trading this sleeve live.

---

## 6. Portfolio Results (v2 — all sizing variants)

Equal-weight 1/N across 2 instruments. Sleeve per instrument = $100,000 / 2 = $50,000.

| Variant | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| simple (85% fixed bet) | 1.18 | 12.7% | −15.5% |
| **asset_vol (2% daily, 4× max)** ⭐ selected | **1.58** | **33.7%** | **−25.5%** |
| vol_target (10% ann, 2× max) | 1.13 | 18.0% | −24.1% |

*Fee rerun 2026-07-10: canonical regenerated at true **slippage-0** (limit-order-at-VWAP rationale; the old table had inadvertently applied per-share costs in the sizing layer). ⚠ At $0.005/share the strategy collapses (asset_vol 0.28, others negative — `results/_slip0p005/`): do NOT trade with marketable orders. See `../_fee_sensitivity.md`. Per-ticker tables below predate the rerun (relative rankings unchanged).*

**asset_vol** was selected automatically (highest portfolio Sharpe) and is saved as `results/equity/combined_equity_final.csv`. Given the EWW drawdown profile in §5, the portfolio-level MaxDD of −42.8% even under the best variant is substantially EWW-driven — a 2-instrument, 1/N-weighted sleeve has no room to diversify away a single bad actor.

Per-instrument Sharpe by variant:

| Ticker | simple | asset_vol | vol_target |
|---|---|---|---|
| MTUM (Bonf) | 0.18 | 0.72 | 0.13 |
| EWW (Bonf) | −2.80 | −0.45 | −2.95 |

---

## 7. Conclusions

VWAP-trend, standardized to the same 5-min-bar / two-phase / Bonferroni-rescue framework as the rest of this family, validates a **much narrower edge than the pre-standardization artifacts implied**: 2 instruments (MTUM, EWW) out of 44 tested, versus a stale `canonical_params.json` that (on a wrong/outdated schema) suggested a whole 8-ticker basket passing, and a `STATUS.md` that recommended a QQQ-based single-ticker reconstruction which fails outright under this framework.

**What works:** MTUM (momentum factor ETF) — modest but positive and consistent across sizing variants (Sharpe 0.13–0.72).

**What's questionable:** EWW (Mexico ETF) passes the statistical significance bar but its very high trade frequency and low per-trade win rate make it fragile under realistic position sizing — two of three sizing variants produce a near-total capital loss. Worth a second look before including it in a live book (see §5).

**What doesn't work:** every basket fails at the basket level, and QQQ — the ticker the pre-standardization `STATUS.md` called "tradeable" — fails outright under this more rigorous, higher-multiple-comparisons-burden framework.

This is the weakest, narrowest sleeve in the family by a wide margin (2 instruments vs. 15–20 for `ema_crossover`), and one of those two instruments has a real sizing-fragility problem. Treat this strategy's inclusion in a live portfolio as a genuinely open question, not a settled "it passed validation" result.

---

## 8. Files

| File | Description |
|---|---|
| `results/vwap_trend_v2_canonical_params.json` | Canonical threshold + 3-gate stats for all 7 baskets (all fail) |
| `results/vwap_trend_v2_bonferroni_results.json` | Per-ticker Bonferroni results for all 44 tickers across the 7 failed baskets |
| `results/vwap_trend_v2_backtest_results.csv` | Per-ticker Sharpe at each basket's canonical threshold |
| `results/trades/vwap_trend_v2_trades_bonferroni_{basket}_{ticker}.csv` | Trade-level CSVs (Bonferroni rescued tickers: MTUM, EWW) |
| `results/equity/combined_equity_simple.csv` | Daily equity curve — simple_bet variant |
| `results/equity/combined_equity_asset_vol.csv` | Daily equity curve — intraday_asset_vol variant |
| `results/equity/combined_equity_vol_target.csv` | Daily equity curve — vol_targeting variant |
| `results/equity/combined_equity_final.csv` | Daily equity curve — **selected** variant (highest Sharpe; currently asset_vol) |
| `results/vwap_trend_v2_implementations.json` | Per-variant portfolio stats + per-instrument Sharpe + `selected_variant` |

## 9. Superseded files (historical reference only — not read by any current script)

- `STATUS.md` — pre-dates the multi-asset framework (2026-06-16/17). Describes a QQQ-only, 1-minute-bar, 45-minute-minhold reconstruction that was never tested under the Bonferroni multi-asset framework and whose "tradeable" verdict on QQQ is contradicted by §4/§5 above. Kept for history; marked superseded at the top of the file.
- `vwap_trend_Backtest_multiasset_v2_minhold.py`, `vwap_trend_v2_proper_fees_expansion.py` — folded into the single canonical `vwap_trend_Backtest_multiasset_v2.py` described in §2–3. Left on disk but no longer the source of truth.
- `vwap_trend_trades.csv`, `vwap_trend_minhold10_trades.csv`, `vwap_trend_minhold45_trades.csv` — orphaned single-ticker (QQQ), 1-minute-bar trade logs from the pre-multiasset era. Not reusable as a starting trades layer for this framework (wrong bar granularity, single ticker, inconsistent timezone conventions between files, no basket/ticker CSV-per-file convention). Superseded by `results/trades/`.
- `vwap_trend_v2_canonical_params.json` (pre-2026-07-02 version), `vwap_trend_v2_minhold_canonical_params.json`, `vwap_trend_v2_minhold_backtest_results.csv`, `vwap_trend_v2_minhold_proper_fees_results.csv`, `vwap_trend_v2_per_ticker_bonferroni_results.json`, `vwap_trend_v2_per_ticker_equity/` — outputs of the superseded scripts above, on an older/inconsistent schema. `results/vwap_trend_v2_canonical_params.json` and `results/vwap_trend_v2_backtest_results.csv` have been overwritten by this run; the other files are left in place as historical record.
