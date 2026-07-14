# VIX ETN Dual

**Portfolio:** Daily | **Status:** ✅ Active (scripted) | **Canonical file:** `vix_etn_dual_Implementation_multiasset_v2.py`

**Paper:** Zarattini, Mele & Aziz (2025), "The Volatility Edge: A Dual Approach for VIX ETNs Trading" (SFI N°25-91)

---

## 1. Strategy

Rotates between a short-vol proxy (VIXSHORT = 2× SVXY − 80bps/yr) and a long-vol proxy (VIXLONG = VXX − 50bps/yr) using two signals: **eVRP** (VIX − 10d realized SPY vol; positive = vol risk premium sellable) and **term structure** (contango = VIX < VIX3M). Canonical variant **eVRP+BoC+Sizing**: short vol at VIX/100 weight in contango, half-weight when eVRP ≤ 0, flip to long vol in backwardation. Rebalance only on >2% weight drift or instrument switch.

## 2. Standardization decisions (fable run 2026-07-02)

- **Which of the 5 experimental equity variants is canonical** (plan Phase B item 3): resolved from the notebook itself — `CANONICAL_STRATEGY = "eVRP+BoC+Sizing"` was already declared and significance-tested (3/3 gates, bootstrap Sharpe 0.848). The evrp/evrp_boc/passive/spybench CSVs are the paper's incremental-lift progression, not competing candidates.
- **Basket+Bonferroni does not apply**: scalar-exposure rotation on a fixed ETN pair (refactor_discussion_points §2.1 category 2). Validation = 3-gate on the canonical variant.
- **Sizing variants** = leverage sweep (1.0×/1.5×/2.0×), since per-trade share sizing is meaningless for a weight-driven rotation. Best-by-Sharpe auto-selected.
- **Private VIX data** (`VIXCLS.csv`, `VIX3M_History.csv`) now accessed via the shared data manifest (`data_dir('vix')`) — files stay in the original folder, not duplicated (Phase E).

## 3. Run status

`vix_etn_dual_Implementation_multiasset_v2.py` **runs offline** from existing backtest artifacts — verified 2026-07-02, reproduces the notebook (canonical 1.0× Sharpe 0.85, CAGR 14.8%, MaxDD −33.1%).

`vix_etn_dual_Backtest_multiasset_v2.py` is a faithful notebook conversion (engine copied verbatim) but **needs SPY/SVXY/VXX daily prices**: Alpaca is network-blocked in this sandbox and no local copy exists. It looks for `results/_price_cache.csv` (columns date,spy,svxy,vxx) first, then Alpaca, and self-caches after a successful fetch. Until re-run, the notebook-produced `results/` artifacts (2016-01-19 → 2026-03-31) remain canonical. **Data TODO:** add SVXY + VXX/VIXY daily CSVs to the shared store (same bucket as the 5 missing ETFs).

## 4. Results (canonical run, from notebook 2016→2026-03)

| Variant | Trades | CAGR | Sharpe | MaxDD |
|---|---|---|---|---|
| Passive (always 20% short-vol) | 78 | 6.4% | 0.31 | −57.2% |
| eVRP | 81 | 5.8% | 0.30 | −52.7% |
| eVRP+BoC | 117 | 12.3% | 0.81 | −19.9% |
| **eVRP+BoC+Sizing** (canonical) | 158 | 14.9% | 0.81 | −33.1% |
| SPY B&H | — | 14.8% | 0.84 | −33.8% |

Leverage sweep (Implementation): Sharpe is leverage-invariant (0.85); 1.0× selected. eVRP+BoC is the max-risk-efficiency point (−19.9% DD at 12.3% CAGR); the Sizing layer adds CAGR at the cost of DD. Significance (canonical): t-p=0.003, bootstrap CI [0.26, 1.43], perm p=0.003 — 3/3 strong.

## 5. Files

| File | Description |
|---|---|
| `vix_etn_dual_Backtest_multiasset_v2.py` | Notebook→script conversion (needs price data to re-run) |
| `vix_etn_dual_Implementation_multiasset_v2.py` | Leverage sweep + selection (runs offline) |
| `results/vix_etn_dual_trades.csv` / `_trades_extended.csv` | Canonical trades (158, with entry_weight) |
| `results/equity/combined_equity_{1p0x,1p5x,2p0x,final}.csv` | Leverage variants + selected |
| `results/vix_etn_dual_daily_equity_*.csv` | Incremental-lift progression curves (notebook) |
| `results/vix_etn_dual_{summary,implementations}.json` | Stats + `_recommended` |
| `vix_etn_dual_{Backtest,Implementation}.ipynb` | Original notebooks (kept until script re-run with fresh data) |
| `fetch_vix_data.py` | VIX/VIX3M refresher (writes to the shared vix store) |
