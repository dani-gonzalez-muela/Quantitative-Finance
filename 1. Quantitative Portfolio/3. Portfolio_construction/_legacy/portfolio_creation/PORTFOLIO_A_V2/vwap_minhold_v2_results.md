# VWAP Trend — MinHold=10min Multiasset Results (v2)

**Date:** 2026-06-27  
**Status:** ❌ REJECTED — Fails significance on all 7 baskets

---

## Background

The original VWAP Trend strategy (v2, zero slippage) had net Sharpe = −0.40 due to excessive round-trips (~4,129/year). A minimum hold time of 10 minutes was applied to suppress rapid VWAP-cross flips, reducing round-trips to ~1,206/year and improving net Sharpe to +0.538 on QQQ at 0.5% slippage — but this only passed 1 of 3 significance gates on its best instrument. This document formally records the full multiasset expansion of that minhold fix.

---

## Methodology

| Parameter | Value |
|---|---|
| Min hold time | 10 minutes |
| Slippage assumption | 0.5% per side |
| Fees | SEC fee + FINRA TAF + slippage via `shared/fees.py` |
| Data | 5-min intraday bars, 2016–2026 |
| Canonical params | Same as v2 grid-search winners (see note below) |
| Significance gates | 3-gate: t-test p<0.05, bootstrap Sharpe 5th pct >0, permutation p<0.05 |

**Note on canonical params:** To isolate the effect of the minhold fix from re-optimisation, the v2 canonical parameters (vwap_threshold, exit_time) were used directly for each basket. This is conservative — if anything, re-optimising for minhold would produce marginally different params, but the conclusion is unlikely to change given the magnitude of the failures.

**Script:** `short_term/vwap_trend/vwap_trend_Backtest_multiasset_v2_minhold.py`  
**Results CSV:** `short_term/vwap_trend/results/vwap_trend_v2_minhold_backtest_results.csv`

---

## Results by Basket

### us_equity_broad
Tickers: SPY, QQQ, IWM, DIA, MDY, IVV, VOO | Params: threshold=0.001, exit=15:55

| Ticker | Sharpe |
|---|---|
| SPY | 0.269 |
| QQQ | 0.409 |
| IWM | −1.085 |
| DIA | −0.138 |
| MDY | 0.228 |
| IVV | 0.184 |
| VOO | 0.423 |

Median Sharpe: **+0.228** | k significant: 0/7 | Binomial p: 1.000 | Gate: **FAIL**

---

### us_factor
Tickers: IWF, IWD, MTUM, USMV, VTV, VUG, DVY, QUAL | Params: threshold=0.001, exit=15:55

| Ticker | Sharpe |
|---|---|
| IWF | −0.471 |
| IWD | −0.275 |
| MTUM | +0.475 |
| USMV | −0.822 |
| VTV | −0.184 |
| VUG | −0.596 |
| DVY | −0.045 |
| QUAL | −0.160 |

Median Sharpe: **−0.230** | k significant: 0/8 | Binomial p: 1.000 | Gate: **FAIL**

*(Note: us_factor was the only basket to show gate_pass=True in v2 without minhold. The minhold fix reverses this.)*

---

### us_sectors
Tickers: XLK, XLC, XLI, XLV, XLY, XLF, XLE, XLU, XLB, XLP, XLRE | Params: threshold=0.001, exit=15:55

| Ticker | Sharpe |
|---|---|
| XLK | −0.131 |
| XLC | −0.109 |
| XLI | −0.624 |
| XLV | −0.351 |
| XLY | −0.413 |
| XLF | −2.291 |
| XLE | −2.238 |
| XLU | −1.936 |
| XLB | −2.170 |
| XLP | −1.556 |
| XLRE | −1.748 |

Median Sharpe: **−1.556** | k significant: 0/11 | Binomial p: 1.000 | Gate: **FAIL**

*(Severe degradation. Sector ETFs are less liquid intraday; 0.5% slippage combined with minhold holding losing positions longer is highly destructive here.)*

---

### bonds_us
Tickers: TLT, IEF, SHY, HYG, LQD | Params: threshold=0.002, exit=15:55

| Ticker | Sharpe |
|---|---|
| TLT | −0.391 |
| IEF | +0.130 |
| SHY | +0.309 |
| HYG | −0.100 |
| LQD | +0.479 |

Median Sharpe: **+0.130** | k significant: 0/5 | Binomial p: 1.000 | Gate: **FAIL**

---

### commodities
Tickers: GLD, SLV, USO, GDX | Params: threshold=0.002, exit=15:30

| Ticker | Sharpe |
|---|---|
| GLD | −0.245 |
| SLV | −1.269 |
| USO | −0.628 |
| GDX | −0.718 |

Median Sharpe: **−0.673** | k significant: 0/4 | Binomial p: 1.000 | Gate: **FAIL**

---

### em_regional
Tickers: EEM, EWZ, INDA, EWW | Params: threshold=0.002, exit=15:55

| Ticker | Sharpe |
|---|---|
| EEM | +0.196 |
| EWZ | −1.320 |
| INDA | −0.387 |
| EWW | −0.259 |

Median Sharpe: **−0.323** | k significant: 0/4 | Binomial p: 1.000 | Gate: **FAIL**

---

### intl_liquid
Tickers: EFA, EZU, EWJ, EWG, EWU | Params: threshold=0.002, exit=15:55

| Ticker | Sharpe |
|---|---|
| EFA | +0.768 |
| EZU | +0.047 |
| EWJ | −0.406 |
| EWG | −0.282 |
| EWU | +0.343 |

Median Sharpe: **+0.047** | k significant: 1/5 | Binomial p: 0.226 | Gate: **FAIL**

---

## Summary Table

| Basket | Tickers | Median Sharpe | k/N sig | Binom p | Gate |
|---|---|---|---|---|---|
| us_equity_broad | 7 | +0.228 | 0/7 | 1.000 | ❌ FAIL |
| us_factor | 8 | −0.230 | 0/8 | 1.000 | ❌ FAIL |
| us_sectors | 11 | −1.556 | 0/11 | 1.000 | ❌ FAIL |
| bonds_us | 5 | +0.130 | 0/5 | 1.000 | ❌ FAIL |
| commodities | 4 | −0.673 | 0/4 | 1.000 | ❌ FAIL |
| em_regional | 4 | −0.323 | 0/4 | 1.000 | ❌ FAIL |
| intl_liquid | 5 | +0.047 | 1/5 | 0.226 | ❌ FAIL |

**Result: 0/7 baskets pass. Strategy rejected.**

---

## Interpretation

**Why minhold hurts instead of helps:** The 10-minute minimum hold was designed to reduce fee drag from excessive flips. It partially succeeds (1,206 vs 4,129 round-trips/year on QQQ), but introduces a new problem: it forces the strategy to hold losing positions longer. VWAP crossings that occur within 10 minutes of the last flip are real market signals; suppressing them locks in losses that would have been cut.

**Why sectors are the worst:** Sector ETFs experience larger intraday directional moves relative to their liquidity. A 0.5% slippage assumption is significant for these instruments, and the minhold forces the strategy to ride out intraday trends against its position before being allowed to flip. This is mechanically destructive.

**The slippage cliff:** The minhold rebuild analysis showed that Sharpe declines sharply with slippage — from 0.947 (0% slip) to 0.536 (0.5% slip) to 0.128 (1.0% slip) on QQQ alone. Most baskets are less liquid than QQQ, so 0.5% slip is likely an *underestimate* of real execution costs.

**Comparison with v2 (no minhold, 0% slip):** The only basket showing gate_pass=True in v2 was us_factor. With minhold at 0.5% slippage, us_factor degrades to median Sharpe −0.230, gate=FAIL. The minhold fix does not rescue any basket.

---

## Verdict

VWAP Trend with min-hold=10min is **not viable as a portfolio component** under realistic cost assumptions. The strategy's alpha (if any) exists only in a zero-slippage regime with rapid execution, which is inconsistent with the execution model. No further parameter optimisation is recommended without a fundamentally different execution approach (e.g., limit orders at VWAP, avoiding crossing the spread entirely).

**Not included in PORTFOLIO_A_V2.**
