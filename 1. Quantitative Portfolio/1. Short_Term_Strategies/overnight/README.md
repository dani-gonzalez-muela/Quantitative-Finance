# Overnight Premium

**Portfolio:** Intraday | **Status:** Active | **Canonical file:** `overnight_Implementation_multiasset_v2.py`

---

## 1. Strategy

Long-only overnight-carry strategy. Enters at the after-market session's close (~19:55 ET) if that day's regular-session (09:30-15:55) return was below a threshold; exits at the *next* day's pre-market session's open (~04:00 ET). No intraday position -- only held overnight.

- **Entry:** Actual last-bar price of the after-market session (16:00-19:55 ET), same day
- **Exit:** Actual first-bar price of the pre-market session (04:00-09:25 ET), next trading day
- **Direction:** Long only (long+short was tested in `OG_Research/Overnight.ipynb` and long-only found superior -- shorts added cost, not edge)
- **Signal:** same-day market-session return `< threshold`
- **Fees:** `shared/fees.py` (SEC + FINRA TAF + slippage; canonical **$0.005/share per side** since 2026-07-10, `SLIPPAGE` env-overridable)

---

## 2. v2 Procedure

### Backtest (`overnight_Backtest_multiasset_v2.py`)

**Phase 1 -- Basket-level significance:**

For each basket, a grid search over `threshold` ∈ {0, -0.001, -0.002, -0.003, -0.005} finds the canonical threshold that maximizes the **median Sharpe ratio across all tickers in the basket**.

The basket then passes a **3-gate significance test** on the equal-weight composite monthly returns:

- Gate 1: one-sided t-test `p < 0.05`
- Gate 2: bootstrap 5th-percentile Sharpe > 0 (2000 draws)
- Gate 3: sign-randomization permutation test `p < 0.05` (2000 draws)

Plus a binomial test on how many individual tickers in the basket clear `p < 0.05` on their own. If all three gates pass -> basket passes. All tickers in the basket are included at the canonical threshold. Trade-level CSVs are emitted for the passing basket's instruments.

**Phase 2 -- Bonferroni rescue (failed baskets only):**

For baskets that fail Phase 1, each ticker is individually grid-searched and tested at Bonferroni-corrected α = 0.05/N (where N = tickers in that basket). Only tickers that pass all 3 gates at the stricter alpha are rescued. Trade CSVs are emitted for rescued tickers.

### Implementation (`overnight_Implementation_multiasset_v2.py`)

Loads both result JSONs. Equal-weights 1/N across all validated instruments (basket-passing tickers + Bonferroni rescues). Runs three sizing variants (`shared/implementations.py`):

1. **simple_bet** -- fixed 85% of sleeve equity per trade
2. **intraday_asset_vol** -- 2% daily vol target on underlying asset, 4x max leverage (paper method)
3. **vol_targeting** -- 10% annualized strategy-return vol target, 2x max leverage

After all three are computed, the variant with the highest portfolio Sharpe is selected automatically and written as `results/equity/combined_equity_final.csv` (the other two are kept alongside it for comparison/audit). The choice is recorded in `results/overnight_v2_implementations.json` under `selected_variant`.

Trades and equity curves are written directly to `results/trades/` and `results/equity/` -- no staging directory, and (unlike the prior version) no writes outside this strategy's own `results/` folder.

---

## 3. v2 vs. prior versions

This is a larger rework than a typical v1->v2 bump, done in two stages:

**Stage 1 (archived, `archive/pre_5min_port_2026-07-01/` and `archive/superseded/`):** an earlier v2 attempt approximated the overnight window as daily-close -> next-daily-open using daily OHLCV data (`overnight_Backtest_multiasset_v2_dailyOHLCV.py`, now archived). This understates signal quality because daily "open" bakes in pre-market moves. A separate exploratory script (`overnight_bonferroni_intraday.py`, now archived) and several one-off notebook runs (the `overnight_bonferroni_intraday_*`, `overnight_bonferroni_v1window_*`, and `overnight_v1window_all_baskets.json` files, all archived) prototyped a fix using real 5-min session data, but never converged into a single canonical script -- they used three different, mutually incompatible JSON schemas, covered different basket subsets, and in one case (`overnight_bonferroni_intraday.py`) tested a `us_equity_broad` ticker set that didn't match the Backtest script's own basket definition.

**Stage 2 (this version):** the session-decomposition logic and overnight-window definition from `OG_Research/Overnight.ipynb` and the archived `overnight_v1window_all_baskets.json` prototype were ported into a single script that does Phase 1 + Phase 2 together, matching `ema_crossover`'s structure exactly:

- Real 5-min-bar session decomposition (pre-market/market/after-market), not daily OHLCV
- Entry/exit use actual bar timestamps of each session boundary (robust to holidays/half-days), not fixed clock times
- Single canonical `BASKETS` dict, identical in both scripts (the old ticker-set mismatch is gone)
- Corrected `ROOT` path resolution (3 levels up from the script, not 2) -- the old daily-OHLCV Backtest/Implementation scripts happened to still resolve correctly at 2 levels because their target (`long_term/multi_asset_expansion/data/tickers`) sits one level higher than `short_term/data/`; the old `overnight_bonferroni_intraday.py` was not so lucky and had a broken `DATA_DIR`
- DST-safe trade loading (`pd.to_datetime(col, utc=True)` after initial parse) -- this strategy's own trade data straddles DST twice a year (after-market close ~19:55 ET is EDT in summer, EST in winter), confirmed via real mixed -04:00/-05:00 offsets in the trade CSVs
- JSON dict comprehensions guarded with `isinstance(v, dict)` -- `canonical_params.json` carries a `_run_info` string key alongside the per-basket dicts (deliberately, to match `ema_crossover`'s real on-disk shape and exercise the guard for real, not just in theory)
- Trades and equity write directly to `results/trades/` / `results/equity/`; no external write to `portfolio_creation/PORTFOLIO_A_V2/` (the old `overnight_bonferroni_intraday.py` wrote there -- that script is archived and not part of this pipeline anymore; the pre-existing file(s) at that external path were not touched or deleted and should be reviewed/cleaned up manually if no longer needed)

**Note on scope:** overnight only defines `us_equity_broad`, `us_factor`, `us_sectors`, `em_regional`, and `intl_liquid` -- no `bonds_us` or `commodities` baskets. That was true of every prior version of this strategy and wasn't changed here.

---

## 4. Basket Results (v2, 5-min session-based)

**Run date:** 2026-07-01 | **Data:** 5-min intraday incl. extended hours, ~10 years (2016-2026)

### PASS -- us_equity_broad
**Canonical threshold:** 0.0 | **Binomial:** k=6/7, p≈0.0000

| Metric | Value |
|---|---|
| t-test p | 0.0005 |
| bootstrap 5th-pct Sharpe | 2.41 |
| permutation p | 0.0000 |

### PASS -- us_factor
**Canonical threshold:** 0.0 | **Binomial:** k=6/8, p≈0.0000

| Metric | Value |
|---|---|
| t-test p | 0.0001 |
| bootstrap 5th-pct Sharpe | 2.99 |
| permutation p | 0.0000 |

### PASS -- em_regional
**Canonical threshold:** -0.005 | **Binomial:** k=2/4, p=0.0140

| Metric | Value |
|---|---|
| t-test p | 0.0044 |
| bootstrap 5th-pct Sharpe | 1.51 |
| permutation p | 0.0065 |

### FAIL -- us_sectors
**Canonical threshold:** -0.002 | **Binomial:** k=2/11, p=0.1019 (fail)
Basket composite fails 3-gate (boot5 < 0, perm_p=0.29).
Bonferroni rescue α = 0.05/11 = 0.0045 -- rescued: **XLV** (Sharpe 0.87)

### FAIL -- intl_liquid
**Canonical threshold:** -0.003 | **Binomial:** k=0/5, p=1.00 (fail)
Basket composite fails 3-gate outright (t_p=1.0, perm_p=0.78). No tickers individually significant.
Bonferroni rescue α = 0.05/5 = 0.01 -- rescued: **none**

---

## 5. Validated Instruments

Total: **20 instruments** -- 19 basket-passing + 1 Bonferroni rescued

| Source | Basket | Tickers |
|--------|--------|---------|
| Basket PASS | us_equity_broad | SPY, QQQ, IWM, DIA, MDY, IVV, VOO |
| Basket PASS | us_factor | IWF, IWD, MTUM, USMV, VTV, VUG, DVY, QUAL |
| Basket PASS | em_regional | EEM, EWZ, INDA, EWW |
| Bonferroni rescued | us_sectors | XLV |

---

## 6. Portfolio Results (v2 -- all sizing variants)

Equal-weight 1/N across 20 instruments. Sleeve per instrument = $100,000 / 20 = $5,000. Period: 2016-01-04 to 2026-06-23.

| Variant | Sharpe | CAGR | MaxDD |
|---------|--------|------|-------|
| simple (85% fixed bet) | 1.45 | 5.2% | -6.5% |
| **asset_vol (2% daily, 4x max)** selected | **1.66** | **12.1%** | **-13.9%** |
| vol_target (10% ann, 2x max) | 1.28 | 4.2% | -6.2% |

*Fee rerun 2026-07-10: canonical slippage now **$0.005/share per side**, all variants unified. Frictionless Sharpe 1.88 — ~0.5 trades/day, barely fee-sensitive. See `../_fee_sensitivity.md`. Per-ticker tables below predate the rerun (relative rankings unchanged).*

**asset_vol** was selected automatically (highest portfolio Sharpe) and is saved as `results/equity/combined_equity_final.csv`. All three variants are retained in `results/equity/` for comparison.

Per-instrument Sharpe by variant:

| Ticker | simple | asset_vol | vol_target |
|--------|--------|-----------|------------|
| SPY | 0.76 | 1.10 | 0.76 |
| QQQ | 0.77 | 1.13 | 0.74 |
| IWM | 0.59 | 0.82 | 0.54 |
| DIA | 0.14 | 0.38 | -0.03 |
| MDY | 0.55 | 0.56 | 0.52 |
| IVV | 1.01 | 1.29 | 1.04 |
| VOO | 0.79 | 1.06 | 0.79 |
| IWF | 0.77 | 1.15 | 0.55 |
| IWD | 0.57 | 0.53 | 0.38 |
| MTUM | 0.66 | 0.67 | 0.61 |
| USMV | 0.83 | 0.91 | 0.75 |
| VTV | 1.00 | 0.96 | 0.99 |
| VUG | 0.19 | 0.53 | 0.02 |
| DVY | 0.94 | 0.53 | 0.86 |
| QUAL | 0.42 | 0.66 | 0.30 |
| EEM | -0.06 | 0.14 | 0.07 |
| EWZ | 0.05 | 0.49 | 0.08 |
| INDA | 0.54 | 0.52 | 0.39 |
| EWW | 1.01 | 0.92 | 1.10 |
| XLV (Bonf) | 0.81 | 1.07 | 0.72 |

---

## 7. Conclusions

The overnight-carry effect is real and statistically significant in US broad equity and factor ETFs once measured with the actual session-based overnight window (after-market close -> pre-market open) instead of the daily-OHLCV approximation used previously. `us_equity_broad` and `us_factor` both pass cleanly at threshold=0 (i.e., "enter whenever today's session return was non-positive"), consistent with the original single-instrument SPY research in `OG_Research/Overnight.ipynb`.

**What works:** US broad equity and factor ETFs (median Sharpe 0.77-1.15 under asset-vol sizing), plus EM regionals as a basket (though driven mostly by EWW/INDA -- EEM and EWZ are weak on their own).

**What doesn't work:** Sector ETFs mostly fail individually (only XLV rescued out of 11); international developed-market ETFs (`intl_liquid`) fail outright with zero individually-significant tickers.

**Basket-level cost:** As with the other strategies in this family, basket-level inclusion means some individually weak tickers (EEM, DIA) ride along inside a passing basket. A stricter per-ticker filter within passing baskets is a possible future refinement, consistent with the same caveat noted in `ema_crossover`'s README.

**Known limitation carried over from research:** the long-only design choice was validated on SPY alone in `OG_Research/Overnight.ipynb`; it was not re-tested against long+short at the multi-asset v2 level. If a future iteration wants to revisit that, the session-decomposition code in `build_overnight_pivot()` doesn't need to change -- only `run_overnight()`'s entry-direction logic.

---

## 8. Directory layout

- `overnight_Backtest_multiasset_v2.py`, `overnight_Implementation_multiasset_v2.py` -- canonical pipeline (this README describes their current output)
- `results/` -- canonical outputs: `overnight_v2_canonical_params.json`, `overnight_v2_bonferroni_results.json`, `overnight_v2_backtest_results.csv`, `overnight_v2_implementations.json`, `results/trades/`, `results/equity/`
- `OG_Research/Overnight.ipynb` -- original single-instrument (SPY) research notebook; source of the session-decomposition logic and the long-only design decision
- `Overnight_Backtest.ipynb`, `Overnight_Implementation.ipynb` -- earlier single-instrument (SPY) notebooks, kept for reference, not part of the v2 pipeline
- `archive/pre_5min_port_2026-07-01/` -- snapshot of every script and result file as they stood before this port (daily-OHLCV Backtest/Implementation, the old intraday Bonferroni script, all 5 old Bonferroni JSON variants, the `v1window_all_baskets.json` prototype this port is based on, old trade/equity outputs)
- `archive/superseded/` -- the same superseded files, moved out of the live `results/`/top-level directory (this workspace does not permit file deletion, only moves, so both archive locations exist as a paper trail rather than one being deleted in favor of the other)
- `archive/tooling/` -- a temporary chunked-execution driver used only because this run had to be split into several sub-45-second steps; not part of the pipeline, safe to ignore

**External write removed:** the prior `overnight_bonferroni_intraday.py` wrote output to `portfolio_creation/PORTFOLIO_A_V2/` outside this strategy's folder. That script is archived and no longer runs. Whatever file(s) it left at that external path were not modified or deleted as part of this work (out of scope of this folder, and file deletion isn't available in this workspace regardless) -- worth a manual check if that path is still referenced anywhere downstream.
