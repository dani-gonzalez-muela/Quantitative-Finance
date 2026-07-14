# Intraday Momentum (IMOM)

**Portfolio:** Intraday | **Status:** ✅ Active | **Canonical file:** `intraday_momentum_Implementation_multiasset_v2.py`

**Reference papers:** `reference/`

---

## 1. Strategy

Intraday momentum based on checkpoint breaks (every 30 minutes from 10:00 to 15:30 ET) against a rolling volatility-scaled noise band around the day's open/prior-close reference range. A break above the upper band signals long, a break below the lower band signals short; positions trail a VWAP/band-based stop and can reverse intraday. Exit at EOD (15:55 ET) if still open.

- **Signal:** Checkpoint price vs. `ref ± vol_mult × rolling_sigma` noise band
- **Entry:** Next-bar pullback fill after a checkpoint break (fast-alpha execution)
- **Exit:** Trailing stop (max/min of band and VWAP) or EOD close; can reverse intraday
- **Direction:** Long and short
- **Session:** 09:30–15:55 ET
- **Fees:** `shared/fees.py` (SEC + FINRA TAF + slippage; canonical **$0.005/share per side** since 2026-07-10, `SLIPPAGE` env-overridable)

---

## 2. v2 Procedure

### Backtest (`intraday_momentum_Backtest_multiasset_v2.py`)

**Phase 1 — Basket-level significance:**

For each basket, a grid search (lookback ∈ {8, 10, 14, 21}, vol_mult ∈ {0.5, 1.0, 1.5, 2.0}) finds the canonical params that maximize the **median Sharpe ratio across all tickers in the basket** (fast approximation, no pullback simulation — used only for parameter selection). The basket then passes a **3-gate significance test** on the equal-weight composite monthly returns, computed with the full accurate (pullback-aware) signal:

- Gate 1: one-sided t-test `p < 0.05`
- Gate 2: bootstrap 5th-percentile Sharpe > 0 (1000 draws)
- Gate 3: sign-randomization permutation test `p < 0.05` (1000 draws)

If all three gates pass → basket passes. All tickers in the basket are included at the canonical params. Trade-level CSVs are emitted for the passing basket's instruments.

**Phase 2 — Bonferroni rescue (failed baskets only):**

For baskets that fail Phase 1, each ticker is individually grid-searched and tested at Bonferroni-corrected α = 0.05/N (where N = tickers in that basket). Only tickers that pass all 3 gates at the stricter alpha are rescued. Trade CSVs are emitted for rescued tickers.

### Implementation (`intraday_momentum_Implementation_multiasset_v2.py`)

Loads both result JSONs. Equal-weights 1/N across all validated instruments (basket-passing tickers + Bonferroni rescues). Runs three sizing variants:

1. **simple_bet** — fixed 85% of sleeve equity per trade
2. **intraday_asset_vol** — 2% daily vol target on underlying asset, 4× max leverage (paper method)
3. **vol_targeting** — 10% annualized strategy-return vol target, 2× max leverage

After all three are computed, the variant with the highest portfolio Sharpe is selected automatically and written as `results/equity/combined_equity_final.csv` (the other two are kept alongside it for comparison/audit). The choice is recorded in `results/intraday_momentum_v2_implementations.json` under `selected_variant`.

Trades and equity curves are written directly to `results/trades/` and `results/equity/` — no staging directory.

---

## 3. v2 vs v1

Signal logic is **identical** to v1 (intentionally matched). Changes in v2:

- Multi-asset basket framework with shared canonical params
- Two-tier significance framework (basket 3-gate + Bonferroni rescue) — the pre-standardization script had no rescue pass at all
- Backtest now emits trade-level CSVs → Implementation uses `shared/implementations.py` sizing instead of recomputing signals from raw price data
- Replaced flat TC constant with `shared/fees.py`
- Trade-level `entry_time`/`exit_time` are captured from the actual tz-aware 5-min bar timestamps (not reconstructed from date + time-of-day), so DST offsets are handled correctly
- Fixed a `ROOT` path resolution bug: the folder is nested one level deeper (`Intraday/intraday_momentum/`) than the original 2-level `..`/`..` assumed, which silently pointed `DATA_DIR` at a nonexistent path
- Basket definitions reconciled between Backtest and Implementation (previously mismatched — Implementation was missing VOO from `us_equity_broad` and had a different `intl_liquid`/`em_regional` split)
- Removed the staging-directory output pattern (`results/intraday_momentum_v2_multiasset_daily_equity/`) in favor of writing directly to `results/trades/` and `results/equity/`

---

## 4. Basket Results (v2)

**Run date:** 2026-07-01 | **Data:** 5-min intraday, ~10 years (2016–2026)

### ✅ us_equity_broad — PASS (marginal)
**Canonical params:** lookback=21, vol_mult=1.5 | **Median Sharpe:** 0.34 | **k=4/7** | binom_p=0.0002 | perm_p=0.015

| Ticker | Sharpe |
|--------|--------|
| SPY | 0.76 |
| QQQ | 1.35 |
| IWM | −0.03 |
| DIA | 0.21 |
| MDY | 0.03 |
| IVV | 0.83 |
| VOO | 0.82 |

### ❌ us_factor — FAIL (Median Sharpe: −0.67)
Bonferroni α = 0.05/8 = 0.00625. Rescued: **MTUM** (Sharpe 1.23). Not rescued: IWF, IWD, USMV, VTV, VUG, DVY, QUAL.

### ❌ us_sectors — FAIL (Median Sharpe: −0.95)
Bonferroni α = 0.05/11 = 0.0045 — rescued: **none** (best individual Sharpe: XLK 0.59)

### ❌ bonds_us — FAIL (Median Sharpe: −1.20)
Bonferroni α = 0.05/5 = 0.01 — rescued: **none**. Intraday momentum is strongly negative across bond ETFs (SHY Sharpe = −4.57).

### ❌ commodities — FAIL (Median Sharpe: −0.30)
Bonferroni α = 0.05/4 = 0.0125 — rescued: **none** (GDX best individual Sharpe 0.45, doesn't clear the corrected alpha)

### ❌ em_regional — FAIL (Median Sharpe: −1.15)
Bonferroni α = 0.05/4 = 0.0125 — rescued: **none**

### ❌ intl_liquid — FAIL (Median Sharpe: −0.73)
Bonferroni α = 0.05/5 = 0.01 — rescued: **none**

---

## 5. Validated Instruments

Total: **8 instruments** — 7 basket-passing + 1 Bonferroni rescued

| Source | Basket | Tickers |
|--------|--------|---------|
| Basket PASS | us_equity_broad | SPY, QQQ, IWM, DIA, MDY, IVV, VOO |
| Bonferroni rescued | us_factor | MTUM |

---

## 6. Portfolio Results (v2 — all sizing variants)

Equal-weight 1/N across 8 instruments. Sleeve per instrument = $100,000 / 8 = $12,500.

| Variant | Sharpe | CAGR | MaxDD |
|---------|--------|------|-------|
| simple (85% fixed bet) | 1.05 | 4.4% | −7.0% |
| **asset_vol (2% daily, 4× max)** ⭐ selected | **1.46** | **13.7%** | **−11.5%** |
| vol_target (10% ann, 2× max) | 1.20 | 6.9% | −6.5% |

*Fee rerun 2026-07-10: canonical slippage now **$0.005/share per side**, all variants unified. Frictionless Sharpe 1.69 — low turnover, barely fee-sensitive. See `../_fee_sensitivity.md`. Per-ticker tables below predate the rerun (relative rankings unchanged).*

**asset_vol** was selected automatically (highest portfolio Sharpe) and is saved as `results/equity/combined_equity_final.csv`. All three variants are retained in `results/equity/` for comparison.

Per-instrument Sharpe by variant:

| Ticker | simple | asset_vol | vol_target |
|--------|--------|-----------|------------|
| SPY | 0.75 | 1.22 | 0.90 |
| QQQ | 1.35 | 1.59 | 1.40 |
| IWM | −0.02 | 0.56 | 0.13 |
| DIA | 0.22 | 0.50 | 0.32 |
| MDY | 0.05 | 0.34 | 0.14 |
| IVV | 0.83 | 1.29 | 0.98 |
| VOO | 0.81 | 1.27 | 0.95 |
| MTUM (Bonf) | 1.22 | 1.70 | 1.21 |

MTUM, the Bonferroni-rescued momentum-factor ETF, has the second-highest Sharpe of the whole portfolio under every sizing variant — a genuine diversification win from the rescue pass, not just a marginal add.

---

## 7. Conclusions

The intraday momentum (checkpoint-break) strategy shows a **much narrower edge than EMA crossover** on the same instrument universe. Only the broad US equity basket clears the 3-gate significance test, and it does so marginally (perm_p=0.015).

**What works:** Broad US equity ETFs (SPY, QQQ, IVV, VOO — Sharpe 0.8–1.4) and the momentum factor ETF MTUM (Sharpe 1.2, Bonferroni-rescued). QQQ is the standout at Sharpe 1.35–1.59 across sizing variants.

**What doesn't work:** Every other basket — factor (ex-MTUM), sectors, bonds, commodities, EM, and international equity — fails both the basket-level gate and individual Bonferroni rescue. Bonds are particularly poor (SHY Sharpe −4.57), consistent with a low-volatility instrument getting chopped up by a volatility-band-breakout signal with real transaction costs.

**Basket-level cost:** us_equity_broad passes only marginally (binom_p=0.0002 on the binomial test, but perm_p=0.015 is close to the 0.05 cutoff). Two of seven tickers (IWM, MDY) have near-zero or negative Sharpe under simple sizing and are only rescued into positive territory by asset-vol sizing.

**Bonferroni rescue delivers one real win:** MTUM survives individual testing at the strict corrected alpha (0.05/8 = 0.00625) despite its basket (us_factor) failing outright. This is exactly the scenario the two-tier framework is designed to catch — a genuinely useful individual signal masked by a noisy basket average.

**Portfolio Sharpe of 0.90–1.48** (depending on sizing variant) is meaningfully lower than EMA crossover's 3.68–5.84 on the same instrument universe. asset_vol sizing's daily leverage cap is again the biggest lever, roughly 1.6–1.9× the Sharpe of fixed/vol-target sizing, but the absolute level suggests this signal is a much weaker standalone edge — worth treating as a smaller sleeve or a diversifier alongside EMA crossover rather than a primary allocation.

---

## 8. Files

| File | Description |
|------|-------------|
| `results/intraday_momentum_v2_canonical_params.json` | Canonical params + 3-gate stats for all 7 baskets |
| `results/intraday_momentum_v2_bonferroni_results.json` | Per-ticker Bonferroni results for failed baskets |
| `results/trades/intraday_momentum_v2_trades_{basket}_{ticker}.csv` | Trade-level CSVs (basket-passing tickers) |
| `results/trades/intraday_momentum_v2_trades_bonferroni_{basket}_{ticker}.csv` | Trade-level CSVs (Bonferroni rescued tickers) |
| `results/equity/combined_equity_simple.csv` | Daily equity curve — simple_bet variant |
| `results/equity/combined_equity_asset_vol.csv` | Daily equity curve — intraday_asset_vol variant |
| `results/equity/combined_equity_vol_target.csv` | Daily equity curve — vol_targeting variant |
| `results/equity/combined_equity_final.csv` | Daily equity curve — **selected** variant (highest Sharpe; currently asset_vol) |
| `results/intraday_momentum_v2_implementations.json` | Per-variant portfolio stats + per-instrument Sharpe + `selected_variant` |
| `results/intraday_momentum_v2_multiasset_daily_equity/` | Legacy staging-pattern output from the pre-standardization script; superseded by `results/equity/`, kept only because it could not be deleted in this session |
| `v1/` | Original single-asset implementations archived here |
| `reference/` | Source papers for the strategy |
