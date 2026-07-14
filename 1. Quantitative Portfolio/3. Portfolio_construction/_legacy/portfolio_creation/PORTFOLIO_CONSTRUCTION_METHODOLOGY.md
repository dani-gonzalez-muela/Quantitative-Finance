# Portfolio Construction Methodology

**Last updated:** 2026-07-02 (v5 — fable alignment: three portfolios canonical, Portfolio A/B names fully retired, rebuilt on regenerated strategy curves)

Previous version (v4, 2026-06-28) remains in the original `algo_trading/portfolio_creation/` folder. v5 changes: canonical builder is now `long_term/portfolio_construction/build_portfolios.py`; Daily/LongTerm rebuilt on fable-regenerated curves (notably the rewritten vix_mean_reversion and improved ibs); LongTerm portfolio assembled for the first time (was TODO in v4).

---

## 1. Overview

Three portfolios, one per time horizon, run as independent sleeves with separate capital:

| Portfolio | Horizon | Assembly method |
|---|---|---|
| **Intraday** | Sub-daily + overnight | **Fixed additive structure** (not greedy): capital works two non-overlapping sessions/day, so `portfolio = mean(EMA, IMOM, ORB, VWAP) + overnight` |
| **Daily** | Days to weeks (sub-monthly) | Greedy forward selection on EW monthly Sharpe, **full path inspected, natural-peak stop** |
| **LongTerm** | Weeks to months (monthly rebalance) | Same greedy |

**Classification is by rebalance/holding frequency, not folder location** — e.g. Bollinger, Turn-of-Month, Donchian and Congress-TFT live under `long_term/timing/` but are Daily candidates.

## 2. Strategy validation (unchanged from v4)

Two-tier inclusion: Tier 2 basket test (binomial + 3-gate on composite) → Tier 3 per-ticker Bonferroni rescue (α=0.05/N); single-asset/alt-data strategies via plain 3-gate. 3 gates: one-sided t-test, bootstrap 5th-pct Sharpe > 0, sign-randomization permutation. Fees per `shared/fees.py` / 5bps for daily+.

## 3. Curve convention for portfolio mixing (new in v5)

Portfolio assembly mixes each strategy's **simple full-notional curve** (`combined_equity_simple.csv`, or the base-fraction variant), NOT the risk-tuned best-by-Sharpe `final` curves. Rationale: EW-of-returns implicitly weights strategies by return volatility; mixing curves with very different vol scales (e.g. a 3%-vol vol-target curve against 10%-vol curves) silently concentrates the portfolio in the lowest-vol sleeve. Sizing variants remain per-strategy deliverables; sizing of the *portfolio* is a separate decision applied after assembly.

## 4. Current portfolios (built 2026-07-02)

### Intraday — Sharpe(d) 4.03 | CAGR 50.8% | MaxDD −8.3%

Components (each = v2 best-by-Sharpe combined equity across its validated instruments): EMA crossover, Intraday Momentum, ORB, VWAP Trend (daytime composite) + Overnight (additive). Numbers are higher than v4's 3.52 because the components are the 2026-06-30 v2 multiasset curves (e.g. EMA asset-vol Sharpe 5.84) rather than the older v1-window curves — capacity/slippage sanity checks apply before sizing real capital (see ema_crossover README §6).

### Daily — natural peak: IBS only — Sharpe(m) 2.29 | CAGR 13.5% | MaxDD −3.5%

Full-path greedy over 8 candidates (IBS_v2, VIX_MR_v2, VIX_ETN_Dual, Congress_Quiver, Congress_TFT, Bollinger, Turn_of_Month, Donchian). **Finding:** the regenerated IBS curve alone (2.29) out-Sharpes v4's six-strategy Daily portfolio (2.23); every addition lowers Sharpe, so the natural peak is a single strategy. Two structural drivers vs v4: the rewritten VIX_MR is weaker-but-honest (the old curve came from the WRONG regime script), and the IBS curve improved. **Diversified alternative (judgment option):** IBS + VIX_MR + Congress_TFT + Turn_of_Month — Sharpe(m) 2.13, CAGR 9.0%, MaxDD −3.3% (0.16 Sharpe give-up for 4× diversification). Both equity curves are saved; the choice is a risk-appetite call, not a statistical one.

### LongTerm — Sharpe(m) 1.36 | CAGR 7.8% | MaxDD −7.0% (first assembly; was TODO in v4)

Common window 2017-08 → 2025-01 (90 months — same as the retired Portfolio-B-v2 run). Greedy over 24 monthly-rebalance candidates (sentiment_timing excluded — known bug; bab_long_short dropped as stale, equity ends 2019-12). Selected 6: **quality_profitability** (seed — Sharpe 1.118, identical to B v2's seed value, confirming curve/window alignment), bond_trend, us_earnings_momentum, commodity_carry, qmj_long_short, credit_carry. Comparison with B v2 (Sharpe 1.61, MaxDD −4.9%, 9 members): the gap is fully structural — B v2's universe included congress_s2 (+0.30 Sharpe at its step 2) and vol_overlay, which now belong to Daily/overlay under the three-portfolio rules. Caveats: earnings-momentum/QMJ are FF-factor proxies; bond_trend/credit_carry flagged weak by the family Bonferroni layer (IEF re-benchmark pending).

**Window handling (v5 rule):** greedy and stats run on the candidates' common window; union-window mixing is forbidden (it produced an artifact −20.7% MaxDD dated Feb-2009 when only the two 1990+ proxy curves existed). Stale candidates (equity ending >18m before the family's typical end) are dropped rather than allowed to truncate the window.

## 5. Canonical artifacts

| Output | Location |
|---|---|
| Builder (one script, all three) | `long_term/portfolio_construction/build_portfolios.py` |
| Results docs + equity curves | `long_term/portfolio_construction/results/{intraday,daily,longterm}_portfolio_*` |
| Family-level significance layer | `long_term/basket_bonferroni_validation.py` + results |
| Strategy READMEs (canonical structure) | every Intraday, Daily and portfolio-member strategy folder |

## 6. Open items

1. Re-run Daily after the IEF re-benchmark and once Congress_TFT/VIX curves are refreshed with new data.
2. Replace FF-factor proxies in earnings-momentum/QMJ when real data sources land (todo log).
3. Fix sentiment_timing equity construction, then re-admit as LongTerm candidate.
4. Decide Daily portfolio: natural peak (IBS only) vs diversified alternative — user judgment.
