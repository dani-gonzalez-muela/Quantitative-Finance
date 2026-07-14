# ORB — Opening Range Breakout

**Portfolio:** Intraday | **Status:** ⚠️ Bonferroni-rescued only | **Canonical file:** `orb_Implementation_multiasset_v2.py`

---

## 1. Strategy

Intraday momentum breakout on 5-minute bars. Compares the close vs. open of the opening range (OR) window; enters long if OR_close > OR_open, short if OR_close < OR_open, provided the range exceeds a minimum threshold. Entry at the first bar after the OR window, at the OR boundary price. Stop loss at an ATR-based distance. Exit at EOD if the stop isn't hit.

- **Entry:** First bar after the OR window, at the OR boundary price
- **Exit:** ATR stop hit or EOD close
- **Direction:** Long and short
- **Session:** 09:30–15:55 ET
- **Fees:** `shared/fees.py` (SEC + FINRA TAF + slippage; canonical **$0.005/share per side** since 2026-07-10, `SLIPPAGE` env-overridable)

---

## 2. v2 Procedure

### Backtest (`orb_Backtest_multiasset_v2.py`)

**Phase 1 — Basket-level significance:**

For each basket, a grid search finds the canonical params (`window_size` ∈ {5, 10, 15} min, `atr_percent` ∈ {2, 5, 10}%, `threshold` ∈ {0.0, 0.01, 0.02}% of open) that maximize the **median Sharpe ratio across all tickers in the basket**.

The basket then passes a **3-gate significance test** on the equal-weight composite monthly returns:

- Gate 1: one-sided t-test `p < 0.05`
- Gate 2: bootstrap 5th-percentile Sharpe > 0 (1000 draws)
- Gate 3: sign-randomization permutation test `p < 0.05` (1000 draws)

If all three gates pass → basket passes. All tickers in the basket are included at the canonical params, and trade-level CSVs are emitted for the basket's instruments.

**Phase 2 — Bonferroni rescue (failed baskets only):**

For baskets that fail Phase 1, each ticker is individually grid-searched and tested at Bonferroni-corrected α = 0.05/N (where N = tickers in that basket). Only tickers that pass all 3 gates at the stricter alpha are rescued. Trade CSVs are emitted for rescued tickers.

### Implementation (`orb_Implementation_multiasset_v2.py`)

Loads both result JSONs and the trade CSVs (no signal recomputation). Equal-weights 1/N across all validated instruments (basket-passing tickers + Bonferroni rescues). Runs three sizing variants:

1. **simple_bet** — fixed 85% of sleeve equity per trade
2. **intraday_asset_vol** — 2% daily vol target on underlying asset, 4× max leverage (paper method)
3. **vol_targeting** — 10% annualized strategy-return vol target, 2× max leverage

After all three are computed, the variant with the highest portfolio Sharpe is selected automatically and written as `results/equity/combined_equity_final.csv` (the other two are kept alongside it for comparison/audit). The choice is recorded in `results/orb_v2_implementations.json` under `selected_variant`.

Trades and equity curves are written directly to `results/trades/` and `results/equity/` — no staging directory.

---

## 3. v2 vs v1

Signal logic is **identical** to v1 (intentionally matched — same OR-boundary entry, same Wilder ATR stop). Changes in v2:

- Multi-asset basket framework with shared canonical params
- Two-tier significance framework (basket 3-gate + Bonferroni rescue)
- Backtest now emits trade-level CSVs → Implementation uses `shared/implementations.py` sizing, instead of an independent `run_orb()` reimplementation that recomputed signals from scratch
- Three canonical sizing variants (simple / asset-vol / vol-targeting) added, with automatic best-by-Sharpe selection — v1 and the prior v2 draft had none
- Fixed a `ROOT` path bug (2 levels of `..` instead of 3) that broke both scripts' `shared`/`data` imports
- Fixed basket/ticker mismatches between Backtest and Implementation (see §6)

---

## 4. Basket Results (v2)

**Run date:** 2026-07-01 | **Data:** 5-min intraday, ~10.4 years (2016–2026)

All 7 baskets **fail** the Phase 1 basket-level 3-gate test — none pass at α=0.05. This matches the strategy's known character: ORB's edge here is concentrated in a handful of individual tickers rather than being basket-wide.

| Basket | Median Sharpe | k/N (t-test) | Gate 1 (t-test p) | Gate 2 (boot5 Sharpe) | Gate 3 (perm p) |
|---|---|---|---|---|---|
| us_equity_broad | 0.15 | 1/7 | 0.182 | −1.05 | 0.169 |
| us_factor | −0.22 | 1/8 | 1.000 | −3.34 | 0.660 |
| us_sectors | −1.23 | 0/11 | 1.000 | −16.90 | 1.000 |
| bonds_us | −1.55 | 0/5 | 1.000 | −14.44 | 1.000 |
| commodities | −0.66 | 0/4 | 1.000 | −10.75 | 1.000 |
| em_regional | −1.62 | 0/4 | 1.000 | −14.15 | 1.000 |
| intl_liquid | −1.42 | 0/5 | 1.000 | −14.78 | 1.000 |

us_equity_broad and us_factor come closest (positive median Sharpe / marginal t-test), but both fail gates 2 and 3 — the composite basket return isn't robust to bootstrap resampling or permutation.

---

## 5. Bonferroni Rescue (Phase 2)

Per-ticker grid search + 3-gate test at Bonferroni-corrected α run on all 7 failed baskets.

| Basket | α | Rescued | Best individual Sharpe (non-rescued) |
|---|---|---|---|
| us_equity_broad | 0.00714 | **QQQ** (0.83, w=5/atr=5%/thr=0.02%), **MDY** (0.85, w=10/atr=2%/thr=0.02%) | VOO 0.24, IVV 0.23 |
| us_factor | 0.00625 | **MTUM** (1.23, w=5/atr=2%/thr=0.00%) | QUAL 0.56, DVY 0.14 |
| us_sectors | 0.00455 | None | XLV 0.11 |
| bonds_us | 0.01000 | None | TLT −0.55 |
| commodities | 0.01250 | None | GLD 0.07 |
| em_regional | 0.01250 | None | EWW −0.72 |
| intl_liquid | 0.01000 | None | EFA −0.66 |

Only **QQQ, MDY, MTUM** clear the Bonferroni bar — consistent with prior runs of this pipeline.

---

## 6. Basket/Ticker Definition Fix

Prior to this pass, Backtest and Implementation used **different** basket definitions for the same basket names, which silently changed which tickers were evaluated depending on which script ran:

- Implementation was missing **VOO** from `us_equity_broad` (6 tickers instead of 7)
- Implementation dropped **`em_regional`** entirely
- Implementation folded **EEM/EWZ** into `intl_liquid` (which should only be EFA/EZU/EWJ/EWG/EWU) and dropped **EZU**

Both scripts now share the identical `BASKETS` dict (matching Backtest's original, correct definition). This affects Implementation's sizing only in the case a *passing* basket includes VOO or em_regional tickers — for this run, since only Bonferroni-rescued single tickers are validated, the fix has no effect on the numbers below, but it removes a latent inconsistency that would have surfaced the moment any basket passed Phase 1.

---

## 7. Validated Instruments

Total: **3 instruments** — 0 basket-passing + 3 Bonferroni rescued (QQQ, MDY, MTUM).

| Source | Basket | Ticker | Params | Sharpe |
|---|---|---|---|---|
| Bonferroni rescued | us_equity_broad | QQQ | w=5min, atr=5%, thr=0.02% | 0.83 |
| Bonferroni rescued | us_equity_broad | MDY | w=10min, atr=2%, thr=0.02% | 0.85 |
| Bonferroni rescued | us_factor | MTUM | w=5min, atr=2%, thr=0.00% | 1.23 |

---

## 8. Portfolio Results (v2 — all sizing variants)

Equal-weight 1/N across 3 instruments. Sleeve per instrument = $100,000 / 3 ≈ $33,333.

| Variant | Sharpe | CAGR | MaxDD |
|---------|--------|------|-------|
| simple (85% fixed bet) | 1.78 | 5.5% | −3.3% |
| **asset_vol (2% daily, 4× max)** ⭐ selected | **2.20** | **16.3%** | **−4.7%** |
| vol_target (10% ann, 2× max) | 1.83 | 9.1% | −5.0% |

*Fee rerun 2026-07-10: canonical slippage now **$0.005/share per side**, all variants unified. Frictionless Sharpe 2.61 — low turnover, barely fee-sensitive. See `../_fee_sensitivity.md`. Per-ticker tables below predate the rerun (relative rankings unchanged).*

**asset_vol** was selected automatically (highest portfolio Sharpe) and is saved as `results/equity/combined_equity_final.csv`. All three variants are retained in `results/equity/` for comparison.

Per-instrument Sharpe by variant:

| Ticker | simple | asset_vol | vol_target |
|--------|--------|-----------|------------|
| QQQ | 0.82 | 1.36 | 0.78 |
| MDY | 0.84 | 1.22 | 0.85 |
| MTUM | 1.21 | 1.91 | 1.21 |

As with ema_crossover, asset-vol sizing's daily leverage cap (based on realized asset volatility) lifts Sharpe across the board relative to fixed-fraction or strategy-vol sizing — worth sanity-checking against capacity/slippage assumptions before sizing real capital this way, especially given the small (3-instrument) validated universe here.

---

## 9. Conclusions

Unlike ema_crossover, ORB shows **no basket-wide edge** in this asset universe — every basket fails the 3-gate test at the basket level. The strategy's signal (OR-boundary breakout with EOD/ATR exit) only clears a statistically rigorous bar on a small number of individual, liquid, trend-prone instruments.

**What works:** QQQ, MDY (broad US equity, Bonferroni-rescued) and MTUM (momentum factor, Bonferroni-rescued). All three have Sharpe 0.8–1.2 gross of the sizing variant, improving to 1.2–1.9 under asset-vol sizing.

**What doesn't work:** Every other basket and ticker — sectors, bonds, commodities, EM, international all show negative-to-marginal Sharpe with no individual ticker clearing its Bonferroni bar. Bonds in particular are strongly negative (SHY −4.04, comparable to ema_crossover's bond weakness).

**Small validated universe is a real constraint:** With only 3 instruments, portfolio diversification benefit is limited and the Sharpe/CAGR figures above should be treated as more fragile than ema_crossover's 20-instrument portfolio. A future iteration could explore relaxing the OR grid, testing additional exit logic, or accepting the strategy is narrower in scope than ema_crossover by design.

---

## 10. Files

| File | Description |
|------|--------------|
| `results/orb_v2_canonical_params.json` | Canonical params + 3-gate stats for all 7 baskets |
| `results/orb_per_ticker_bonferroni_results.json` | Per-ticker Bonferroni results for failed baskets |
| `results/orb_v2_backtest_results.csv` | Per-ticker Sharpe at basket canonical params |
| `results/trades/orb_v2_trades_{basket}_{ticker}.csv` | Trade-level CSVs (basket-passing tickers — none this run) |
| `results/trades/orb_v2_trades_bonferroni_{basket}_{ticker}.csv` | Trade-level CSVs (Bonferroni-rescued tickers: QQQ, MDY, MTUM) |
| `results/equity/combined_equity_simple.csv` | Daily equity curve — simple_bet variant |
| `results/equity/combined_equity_asset_vol.csv` | Daily equity curve — intraday_asset_vol variant |
| `results/equity/combined_equity_vol_target.csv` | Daily equity curve — vol_targeting variant |
| `results/equity/combined_equity_final.csv` | Daily equity curve — **selected** variant (highest Sharpe; currently asset_vol) |
| `results/orb_v2_implementations.json` | Per-variant portfolio stats + per-instrument Sharpe + `selected_variant` |
| `reference/` | Original_Paper.pdf, QQQ/TQQQ day-trading paper |
| `v0/` | Early exploratory research (pre-v1) |
| `v1/` | Original single-asset notebooks |

### Orphaned / stale files (flagged, not deleted — deletion is blocked in this workspace)

| Path | Why it's stale |
|---|---|
| `results/orb_implementations.json` | v1-era single-QQQ leftover; not written by any current script |
| `results/orb_summary.json` | v1-era single-QQQ leftover; not written by any current script |
| `results/qqq_daily_prices.csv` | Not referenced by any current script |
| `results/orb_per_ticker_equity/` (QQQ.csv, MDY.csv, MTUM.csv) | Superseded by `results/trades/` + `shared/implementations.py` sizing; the old Backtest script wrote raw equity curves here directly, the new one writes trades instead |
| `results/orb_v2_multiasset_daily_equity/combined_equity.csv` | Superseded by `results/equity/combined_equity_*.csv` (four variants + selected final), matching the ema_crossover pattern |
| `v0/Delete/` (3 notebooks) | Named for deletion by a prior pass; never removed |
