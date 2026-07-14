# VIX Mean Reversion

> 2026-07-10: standardized portfolio-facing curve added at `results/equity/combined_equity_final.csv` (copy of `vix_mean_reversion_daily_equity/asset_vol_10pct_1x.csv`); the superseded wrong-version `*_v2_multiasset_daily_equity/` was removed to `_delete_2026-07-10/`.

**Portfolio:** Daily | **Status:** ✅ Active | **Type:** single-instrument (SVXY) | **Canonical files:** `VIX_Mean_Reversion_Backtest.ipynb` + `VIX_Mean_Reversion_Implementation.ipynb`

---

## 1. Strategy

Long **SVXY** (economically short volatility) on VIX spikes, harvesting the variance risk premium as volatility mean-reverts. Daily bars. VIX OHLC from WRDS (`load_vix` → `15_cboe_vix.parquet`); SVXY from Alpaca.

**Spike trigger:** `VIX ≥ 18` **and** `VIX > 1.10 × SMA40(VIX)` — elevated *and* 10% above its 40-day average.

**Regime ladder (entry strictness by VIX level):**

| Regime | VIX | Entry condition |
|---|---|---|
| normal | < 30 | spike |
| vix30 | 30–40 | spike **and** VIX-EMA7 declining |
| vix40 | 40–45 | spike **and** VIX-EMA7 declining |
| autobuy | ≥ 45 | unconditional (buy the panic) |

- **Entry:** next day's open after the condition triggers.
- **Exit:** VIX-EMA7 declining **and** VIX < entry-VIX (vol rolling over below entry), or **−20% stop**, or **200-day max hold**.
- **Whipsaw guards:** immunity after entry (normal 2d / vix30–40 5d), 2-day cooldown + 5-day enhanced-scrutiny window after exit.
- **Pre/post-2018 sizing:** SVXY went −1× → −0.5× after Volmageddon (Feb 2018), so pre-2018 allocation is halved (47.5% vs 95%). Feb 5–9 2018 excluded.
- **Indicators:** EMA7/EMA18 on VIX highs, SMA40 on VIX, Stochastic (K=7, smooth=3, D=3).
- **Params source:** hand-tuned to VIX dynamics (VRP literature: Carr & Wu 2009, Eraker 2009). No grid search — too many interacting regime/EMA/stochastic/cooldown parameters.

## 2. Procedure

- **`VIX_Mean_Reversion_Backtest.ipynb`** — signal research: builds the spike/regime engine, generates standardized 9-column trades, runs 3-gate significance (t-test, bootstrap Sharpe CI, sign-permutation) on mark-to-market daily returns → saves `results/vix_mean_reversion_trades.csv` + `_summary.json`.
- **`VIX_Mean_Reversion_Implementation.ipynb`** — sizing on the saved trades (single instrument, no sleeves): Simple bet, Risk-based (−20% stop), Kelly, Asset-vol; leverage sweep 1×–8× → saves `results/vix_mean_reversion_implementations.json` + `results/vix_mean_reversion_daily_equity/`.
- **`v1/VIX_Mean_Reversion.ipynb`** — original monolithic research notebook (full spike-type derivation and charts; kept for provenance).

## 3. Results (signal: 72 trades, 2016–2026, avg hold 5.5d, 79% win — Sharpe 1.20, 3/3 significance)

Sizing at 1×:

| Sizing | Total Ret | CAGR | Sharpe | MaxDD |
|---|---|---|---|---|
| Simple 85% | +449% | 19.0% | 1.20 | −19.8% |
| Asset-vol 10% | +596% | 21.9% | 1.20 | −23.2% |
| Quarter-Kelly 17% | +42% | 3.6% | 1.20 | −4.0% |
| Risk-based 1% | +11% | 1.1% | 1.20 | −1.2% |

Kelly f\* ≈ 66% (79% win, 1.63 W/L). Safe to ~4× (Full-Kelly 4× → +284%, DD −15.6%); **8× blows up** (Simple 8× → −2,834%, DD −129%). Sizing sets the risk dial, not the edge — Sharpe is flat at ~1.20.

Exit mix: 70 signal exits (81% win, +3.36% avg), 1 stop-loss (−20%), 1 end-of-data. Pre-2018: 6 trades, 100% win; post-2018: 66 trades, 77% win.

**Note:** VIX MR and `vix_etn_dual` are both short-vol and highly correlated — not independent diversifiers; don't double-weight them in a book.

## 4. Files

| File | Description |
|---|---|
| `v1/VIX_Mean_Reversion.ipynb` | Original monolithic research notebook (provenance) |
| `VIX_Mean_Reversion_Backtest.ipynb` | Canonical signal research |
| `VIX_Mean_Reversion_Implementation.ipynb` | Canonical sizing / leverage sweep |
| `results/vix_mean_reversion_trades.csv` | Standardized 9-col trades |
| `results/vix_mean_reversion_summary.json` | Params + significance verdict |
| `results/vix_mean_reversion_implementations.json` | Per-sizing stats + recommended |
| `results/vix_mean_reversion_daily_equity/` | Per-sizing daily equity curves |

*Single-instrument strategy — no `_multiasset_v2.py` (that lineage was the superseded `_WRONG_equity_regime` equity-basket version and was removed).*
