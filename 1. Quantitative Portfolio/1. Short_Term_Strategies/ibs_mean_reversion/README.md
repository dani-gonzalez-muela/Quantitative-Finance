# IBS Mean Reversion

**Portfolio:** Daily | **Status:** ✅ Active | **Canonical file:** `ibs_mean_reversion_Implementation_multiasset_v2.py`

---

## 1. Strategy

Internal Bar Strength (IBS) mean reversion on daily bars. IBS = (close − low) / (high − low). Enters long at next open when IBS < `ibs_buy` (close near the day's low → oversold); exits at close when IBS > `ibs_sell`, or at a fixed stop. Long only, multi-day holds allowed.

- **Entry:** Open of the day after signal (IBS[t−1] < ibs_buy)
- **Exit:** Close when IBS > ibs_sell, or stop hit
- **Direction:** Long only
- **Fees:** flat 5bps/side at signal level; `shared/fees.py` in sizing layer

## 2. v2 Procedure

### Backtest (`ibs_mean_reversion_Backtest_multiasset_v2.py`)

**Phase 1** — per-basket grid search (ibs_buy ∈ {0.1,0.15,0.2,0.25}, ibs_sell ∈ {0.7,0.75,0.8,0.85}, stop ∈ {−2%,−3%,−5%,None}) maximizing median Sharpe across basket instruments; binomial instrument-count test + 3-gate significance (t-test p<0.05, bootstrap 5th-pct Sharpe>0, sign-permutation p<0.05) on composite monthly returns. Passing baskets emit per-instrument trade CSVs.

**Phase 2** — Bonferroni rescue for failed baskets at α = 0.05/N per ticker.

### Implementation (`ibs_mean_reversion_Implementation_multiasset_v2.py`)

1/N sleeves across all validated instruments. Three sizing variants, **adapted for daily bars** (plan Phase B item 1): the intraday 2%-daily/4×-max asset-vol method is too aggressive for multi-day holds, so:

1. **simple** — fixed 85% of sleeve equity per trade
2. **asset_vol** — underlying-asset vol targeting at **1% daily, 14d lookback, 2× max** (daily-bar analog of the paper method)
3. **vol_target** — 10% annualized strategy-vol target, 2× max

Best-by-Sharpe variant auto-selected → `results/equity/combined_equity_final.csv`.

## 3. v2.1 vs v2 (fable standardization run, 2026-07-02)

Signal logic **identical** (verified: regenerated canonical params match the pre-fable ones exactly for all 7 baskets — see `results/_pre_fable/`). Changes:

- **Fixed ROOT path bug** (§0 class 1): `ROOT` used 2×`..` from `short_term/Daily/<strategy>/`, resolving DATA_DIR to nonexistent `short_term/long_term/...`. Now uses `shared/paths.py` (marker-file discovery + data manifest).
- Backtest now **emits trade-level CSVs** to `results/trades/` (none existed).
- **Phase 2 Bonferroni integrated** into the main backtest loop (was a one-off side file `ibs_v2_bonferroni_rescue_bonds_us.json`; regenerated results agree with it: no bonds rescued).
- Implementation: replaced single 1/N combined curve (custom folder `ibs_mean_reversion_v2_multiasset_daily_equity/`) with **3 sizing variants + best-by-Sharpe selection** in canonical `results/equity/`.
- Trade timestamps parsed `utc=True` (§0 class 2 guard); JSON readers isinstance-guard `_run_info` (§0 class 3).

## 4. Basket Results (v2.1, run 2026-07-02, data 2016–2025)

| Basket | Params (buy/sell/stop) | Median Sharpe | Basket Sharpe | Binom | Result |
|---|---|---|---|---|---|
| us_equity_broad (4/7 avail) | 0.15 / 0.85 / −2% | 1.23 | 1.52 | 4/4 | ✅ PASS |
| us_factor (6/8 avail) | 0.10 / 0.85 / −2% | 1.05 | 1.28 | 6/6 | ✅ PASS |
| us_sectors (11/11) | 0.25 / 0.80 / −2% | 1.24 | 1.87 | 10/11 | ✅ PASS |
| bonds_us (5/5) | 0.15 / 0.80 / None | 0.25 | 0.09 | 0/5 | ❌ FAIL |
| commodities (4/4) | 0.25 / 0.85 / −2% | 1.20 | 1.83 | 4/4 | ✅ PASS |
| em_regional (4/4) | 0.25 / 0.75 / −2% | 0.93 | 1.42 | 4/4 | ✅ PASS |
| intl_liquid (5/5) | 0.15 / 0.85 / −2% | 1.12 | 1.36 | 5/5 | ✅ PASS |

Missing tickers (DIA, IVV, VOO, VTV, VUG) are the 5 known-missing daily ETFs (`todo/_strategy_notes_and_extensions.md`; download blocked by sandbox network).

**Bonferroni rescue (bonds_us, α=0.01):** none rescued. TLT closest (Sharpe 0.56, t-p=0.038 > α). Matches the pre-fable side-file exactly.

## 5. Validated Instruments

**34 instruments**, all from basket passes (0 Bonferroni): us_equity_broad (SPY, QQQ, IWM, MDY), us_factor (IWF, IWD, MTUM, USMV, DVY, QUAL), us_sectors (all 11 XL*), commodities (GLD, SLV, USO, GDX), em_regional (EEM, EWZ, INDA, EWW), intl_liquid (EFA, EZU, EWJ, EWG, EWU).

## 6. Portfolio Results (v2.1 — all sizing variants)

1/N across 34 instruments ($100k / 34 ≈ $2,941 per sleeve).

| Variant | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| simple (85% bet) | 2.26 | 13.3% | −3.9% |
| asset_vol (1% daily, 2×) | 2.03 | 10.3% | −5.3% |
| **vol_target (10% ann, 2×)** ⭐ selected | **2.28** | 7.1% | **−2.5%** |

vol_target wins on Sharpe with the smallest drawdown; simple delivers the highest CAGR if capital efficiency matters more than Sharpe.

## 7. Conclusions

IBS mean reversion is significant nearly everywhere **except US bonds** — a broad, robust daily mean-reversion edge (6/7 baskets pass all gates with k=N binomial counts). Contrast with ema_crossover (trend), which passes only in US equities: the two are natural complements in the Daily/Intraday sleeve structure. Bond ETFs' low intraday ranges make IBS noisy and fee-dominated; do not trade the strategy there.

## 8. Files

| File | Description |
|---|---|
| `results/ibs_mean_reversion_v2_canonical_params.json` | Canonical params + gates (carries `_run_info` — isinstance-guard) |
| `results/ibs_mean_reversion_v2_bonferroni_results.json` | Per-ticker rescue results (bonds_us) |
| `results/trades/ibs_mean_reversion_v2_trades_{basket}_{ticker}.csv` | 34 trade CSVs |
| `results/equity/combined_equity_{simple,asset_vol,vol_target,final}.csv` | Variant + selected equity curves |
| `results/ibs_mean_reversion_v2_implementations.json` | Per-variant stats + `selected_variant` |
| `results/_pre_fable/` | Pre-fable canonical params/results (for diff audit) |
| `IBS_Mean_Reversion*.ipynb` | v1 notebooks (historical) |
