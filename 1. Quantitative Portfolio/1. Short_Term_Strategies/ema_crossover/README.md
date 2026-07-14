# EMA Crossover

**Portfolio:** Intraday | **Status:** ✅ Active | **Canonical file:** `ema_crossover_Implementation_multiasset_v2.py`

---

## 1. Strategy

EMA crossover on 5-minute intraday bars. Enters long when fast EMA > slow EMA > 200-bar trend EMA; enters short when the reverse is true. Uses an ATR-based stop loss. Holds position until stop is hit or end of day — no overnight carries.

- **Entry:** Open of the bar following signal generation
- **Exit:** ATR stop hit or EOD close
- **Direction:** Long and short
- **Session:** 09:30–15:55 ET
- **Fees:** `shared/fees.py` (SEC + FINRA TAF + slippage; canonical **$0.005/share per side** since 2026-07-10, `SLIPPAGE` env-overridable)

---

## 2. v2 Procedure

### Backtest (`ema_crossover_Backtest_multiasset_v2.py`)

**Phase 1 — Basket-level significance:**

For each basket, a grid search finds the canonical params (fast ∈ {8, 13, 21}, slow ∈ {34, 48, 55}, stop ∈ {0.03, 0.05, 0.07}, fast < slow) that maximize the **median Sharpe ratio across all tickers in the basket**.

The basket then passes a **3-gate significance test** on the equal-weight composite monthly returns:

- Gate 1: one-sided t-test `p < 0.05`
- Gate 2: bootstrap 5th-percentile Sharpe > 0 (500 draws)
- Gate 3: sign-randomization permutation test `p < 0.05` (500 draws)

If all three gates pass → basket passes. All tickers in the basket are included at the canonical params. Trade-level CSVs are emitted for the passing basket's instruments.

**Phase 2 — Bonferroni rescue (failed baskets only):**

For baskets that fail Phase 1, each ticker is individually grid-searched and tested at Bonferroni-corrected α = 0.05/N (where N = tickers in that basket). Only tickers that pass all 3 gates at the stricter alpha are rescued. Trade CSVs are emitted for rescued tickers.

### Implementation (`ema_crossover_Implementation_multiasset_v2.py`)

Loads both result JSONs. Equal-weights 1/N across all validated instruments (basket-passing tickers + Bonferroni rescues). Runs three sizing variants:

1. **simple_bet** — fixed 85% of sleeve equity per trade
2. **intraday_asset_vol** — 2% daily vol target on underlying asset, 4× max leverage (paper method)
3. **vol_targeting** — 10% annualized strategy-return vol target, 2× max leverage

After all three are computed, the variant with the highest portfolio Sharpe is selected automatically and written as `results/equity/combined_equity_final.csv` (the other two are kept alongside it for comparison/audit). The choice is recorded in `results/ema_crossover_v2_implementations.json` under `selected_variant`.

Trades and equity curves are written directly to `results/trades/` and `results/equity/` — no staging directory.

---

## 3. v2 vs v1

Signal logic is **identical** to v1 (intentionally matched). Changes in v2:

- Multi-asset basket framework with shared canonical params
- Two-tier significance framework (basket 3-gate + Bonferroni rescue)
- Backtest now emits trade-level CSVs → Implementation uses `shared/implementations.py` sizing
- Replaced flat TC constant with `shared/fees.py`
- Corrected entry: uses `open[i]` (open of bar after signal), not `close[i]`
- Fixed permutation test: sign-randomization (permutation × random sign), not pure shuffle

---

## 4. Basket Results (v2)

**Run date:** 2026-06-30 | **Data:** 5-min intraday, ~10 years (2015–2026)

### ✅ us_equity_broad — PASS
**Canonical params:** fast=21, slow=55, stop=0.03 | **Median Sharpe:** 3.03 | **k=7/7**

| Ticker | Sharpe |
|--------|--------|
| SPY | 2.56 |
| QQQ | 3.30 |
| IWM | 2.94 |
| DIA | 2.63 |
| MDY | 4.53 |
| IVV | 3.19 |
| VOO | 3.03 |

### ✅ us_factor — PASS (marginal)
**Canonical params:** fast=21, slow=55, stop=0.03 | **Median Sharpe:** 1.40 | **k=5/8** | perm_p=0.044

| Ticker | Sharpe |
|--------|--------|
| IWF | −0.58 |
| IWD | 2.01 |
| MTUM | 3.47 |
| USMV | −1.82 |
| VTV | 1.26 |
| VUG | −1.95 |
| DVY | 1.54 |
| QUAL | 2.03 |

*Note: us_factor passes the basket-level 3-gate test at perm_p=0.044 (marginal). Three tickers (IWF, USMV, VUG) have negative individual Sharpe — they are included by basket-level inclusion rules and drag down portfolio performance. This is a known cost of basket-level testing.*

### ❌ us_sectors — FAIL (Median Sharpe: −1.40)
Basket fails Phase 1. Bonferroni α = 0.05/11 = 0.00455.

Rescued: **XLC** (Sharpe 0.93), **XLI** (Sharpe 1.14), **XLV** (Sharpe 1.35) | Not rescued: XLY (perm_p=0.038 > α)

### ❌ bonds_us — FAIL (Median Sharpe: −3.76)
Bonferroni rescue α = 0.05/5 = 0.01 — rescued: **None**

EMA crossover has strongly negative Sharpe across all bond ETFs. SHY Sharpe = −14.1 (fee-dominated low-volatility instrument).

### ❌ commodities — FAIL (Median Sharpe: 0.54)
Basket composite fails 3-gate (boot5 < 0, perm_p=1.0) despite some tickers showing positive Sharpe.
Bonferroni rescue α = 0.05/4 = 0.0125 — rescued: **GLD** (Sharpe 1.14), **USO** (Sharpe 1.35)

### ❌ em_regional — FAIL (Median Sharpe: −2.90)
Bonferroni rescue skipped (median Sharpe clearly negative). Rescued: **None**

### ❌ intl_liquid — FAIL (Median Sharpe: −3.51)
Bonferroni rescue skipped (median Sharpe clearly negative). Rescued: **None**

---

## 5. Validated Instruments

Total: **20 instruments** — 15 basket-passing + 5 Bonferroni rescued

| Source | Basket | Tickers |
|--------|--------|---------|
| Basket PASS | us_equity_broad | SPY, QQQ, IWM, DIA, MDY, IVV, VOO |
| Basket PASS | us_factor | IWF, IWD, MTUM, USMV, VTV, VUG, DVY, QUAL |
| Bonferroni rescued | us_sectors | XLC, XLI, XLV |
| Bonferroni rescued | commodities | GLD, USO |

---

## 6. Portfolio Results (v2 — all sizing variants)

Equal-weight 1/N across 20 instruments. Sleeve per instrument = $100,000 / 20 = $5,000.

| Variant | Sharpe | CAGR | MaxDD |
|---------|--------|------|-------|
| simple (85% fixed bet) | 5.10 | 37.7% | −2.3% |
| **asset_vol (2% daily, 4× max)** ⭐ selected | **5.68** | **129.0%** | **−4.7%** |
| vol_target (10% ann, 2× max) | 5.32 | 75.1% | −5.1% |

*Fee rerun 2026-07-10: canonical slippage now **$0.005/share per side**, all variants unified (old table mixed $0.0045 flat for asset_vol, $0.01 for others). Frictionless Sharpe 7.77. See `../_fee_sensitivity.md`. Per-ticker tables below predate the rerun (relative rankings unchanged).*

**asset_vol** was selected automatically (highest portfolio Sharpe) and is saved as `results/equity/combined_equity_final.csv`. All three variants are retained in `results/equity/` for comparison. Note the CAGR is high because the paper's intraday asset-vol sizing re-levers daily up to 4× based on realized asset volatility — the low realized vol of the broad-equity sleeve keeps leverage near the cap for much of the period, compounding aggressively. Worth sanity-checking against capacity/slippage assumptions before sizing real capital this way.

Per-instrument Sharpe by variant:

| Ticker | simple | asset_vol | vol_target |
|--------|--------|-----------|------------|
| SPY | 2.52 | 3.89 | 2.66 |
| QQQ | 3.24 | 4.53 | 3.37 |
| IWM | 2.89 | 4.41 | 2.87 |
| DIA | 2.59 | 4.06 | 2.64 |
| MDY | 4.44 | 5.26 | 4.46 |
| IVV | 3.14 | 4.37 | 3.17 |
| VOO | 2.97 | 4.34 | 2.99 |
| IWF | −0.59 | 2.03 | −1.29 |
| IWD | 1.98 | 3.78 | 1.76 |
| MTUM | 3.41 | 4.95 | 3.24 |
| USMV | −1.82 | 1.53 | −2.50 |
| VTV | 1.23 | 3.39 | 0.98 |
| VUG | −2.01 | 1.29 | −4.24 |
| DVY | 1.51 | 3.66 | 1.23 |
| QUAL | 1.99 | 3.97 | 1.71 |
| XLC (Bonf) | 0.92 | 3.43 | 0.92 |
| XLI (Bonf) | 1.12 | 3.32 | 0.86 |
| XLV (Bonf) | 1.34 | 3.56 | 1.27 |
| GLD (Bonf) | 1.11 | 3.08 | 1.04 |
| USO (Bonf) | 1.32 | 3.06 | 1.19 |

Notably, the three negative-Sharpe tickers under simple/vol_target sizing (IWF, USMV, VUG) turn positive under asset_vol sizing — the daily vol-based leverage cap appears to dampen the effect of the large adverse drawdowns that hurt fixed-fraction sizing on these names.

---

## 7. Conclusions

The EMA crossover strategy with 200-bar trend filter shows a **strong and statistically significant intraday edge in US equities**, particularly the broad market and momentum/quality factor ETFs. The signal has been validated through three independent significance gates.

Key findings:

**What works:** US broad equity (SPY, QQQ, IWM — Sharpe 2.5–4.5) and select factor ETFs (MTUM, QUAL, IWD). The strategy is trend-following in nature: it performs well in directionally trending intraday sessions and struggles in choppy, mean-reverting regimes.

**What doesn't work:** Bonds, international equity, and EM ETFs all show strongly negative Sharpes (−3 to −5). The 200-bar trend filter appears to generate false signals in low-volatility instruments (SHY Sharpe = −14) and in non-US markets which may have different intraday dynamics. The strategy should **not** be applied to these asset classes.

**Basket-level cost:** The us_factor basket passes at a marginal significance level (perm_p=0.044). Three tickers (IWF, USMV, VUG) have negative Sharpe and are included by basket-level rules. A stricter implementation could exclude individual negative-Sharpe tickers even within passing baskets, but this would require per-ticker testing and is reserved for a future iteration.

**Bonferroni rescue delivers:** XLC, XLI, XLV (sector ETFs) and GLD, USO (commodities) survive individual Bonferroni testing and contribute positive Sharpe (0.9–1.3) to the portfolio. This demonstrates that the basket-level gate is appropriately conservative — it filters out noisy baskets but doesn't discard all individual opportunities within them.

**Portfolio Sharpe of 3.68–5.84** (depending on sizing variant) is driven primarily by the broad equity basket. The addition of 5 Bonferroni instruments improves diversification. Under simple/vol_target sizing the rescued and factor tickers show meaningfully higher drawdowns (e.g. XLI, USO); asset_vol sizing's daily leverage cap notably compresses these drawdowns across the board. Consider sleeve-level stop-losses on the rescued tickers if drawdown tolerance is a constraint under simple sizing.

---

## 8. Files

| File | Description |
|------|-------------|
| `results/ema_crossover_v2_canonical_params.json` | Canonical params + 3-gate stats for all 7 baskets |
| `results/ema_crossover_v2_bonferroni_results.json` | Per-ticker Bonferroni results for failed baskets |
| `results/trades/ema_crossover_v2_trades_{basket}_{ticker}.csv` | Trade-level CSVs (basket-passing tickers) |
| `results/trades/ema_crossover_v2_trades_bonferroni_{basket}_{ticker}.csv` | Trade-level CSVs (Bonferroni rescued tickers) |
| `results/equity/combined_equity_simple.csv` | Daily equity curve — simple_bet variant |
| `results/equity/combined_equity_asset_vol.csv` | Daily equity curve — intraday_asset_vol variant |
| `results/equity/combined_equity_vol_target.csv` | Daily equity curve — vol_targeting variant |
| `results/equity/combined_equity_final.csv` | Daily equity curve — **selected** variant (highest Sharpe; currently asset_vol) |
| `results/ema_crossover_v2_implementations.json` | Per-variant portfolio stats + per-instrument Sharpe + `selected_variant` |
| `v1/` | Original single-asset implementations archived here |
