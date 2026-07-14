# ORB Per-Ticker Optimization — Bonferroni-Corrected Results

**Date:** 2026-06-27  
**Script:** `short_term/orb/orb_per_ticker_bonferroni.py`  
**Depends on:** ORB Multi-Asset Backtest v2 (all 7 baskets failed at basket level)

---

## Methodology

### Signal (identical to v1/v2)
- **Opening Range:** first `window_size` minutes of the trading day (09:30 to 09:30+window)
- `OR_open` = first bar open; `OR_close` = close of last bar in the OR window
- **Long signal:** `OR_close > OR_open × (1 + threshold/100)`
- **Short signal:** `OR_close < OR_open × (1 − threshold/100)`
- **Entry:** next bar open after OR window ends
- **Exit:** end-of-day close, or ATR stop loss if triggered intraday
- **Stop:** `entry_price ± (atr_percent/100) × ATR14` (Wilder's, computed on daily OHLC)
- **Fees:** Alpaca structure via `shared/fees.py` — SEC fee + FINRA TAF + 2bp slippage

### Per-Ticker Grid Search
Since all baskets failed at the basket level in v2, per-ticker optimization is applied to every basket. Best params are selected by maximizing **net Sharpe** (after fees) across the grid:

| Parameter | Values |
|---|---|
| `window_size` | 5, 10, 15 minutes |
| `atr_percent` | 2%, 5%, 10% |
| `threshold` | 0.00%, 0.01%, 0.02% |

27 combinations per ticker.

### Significance Test — Bonferroni-Corrected 3-Gate
All 3 gates must pass simultaneously at the Bonferroni-corrected α = 0.05/N:

| Gate | Test | Criterion |
|---|---|---|
| 1 | One-sided t-test on monthly returns | p < α |
| 2 | Bootstrap 5th-percentile Sharpe (2000 samples) | > 0 |
| 3 | Sign-randomization permutation p (2000 trials) | p < α |

Gate 3 uses sign randomization (permute returns × random ±1 signs), matching the v2 methodology. This tests whether the positive mean is attributable to directional signal vs. random luck.

### Bonferroni Thresholds

| Basket | N | α = 0.05/N |
|---|---|---|
| us_equity_broad | 7 | 0.00714 |
| us_factor | 8 | 0.00625 |
| us_sectors | 11 | 0.00455 |
| bonds_us | 5 | 0.01000 |
| commodities | 4 | 0.01250 |
| em_regional | 4 | 0.01250 |
| intl_liquid | 5 | 0.01000 |

---

## Results by Basket

### us_equity_broad (α = 0.00714)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| SPY | 5 | 10 | 0.02 | +0.07 | 0.41473 | −2.09 | 0.407 | ✗ |
| **QQQ** | **5** | **5** | **0.02** | **+0.83** | **0.00356** | **+1.70** | **0.004** | **✓** |
| IWM | 10 | 10 | 0.02 | +0.16 | 0.30675 | −1.59 | 0.297 | ✗ |
| DIA | 10 | 10 | 0.02 | −0.05 | 1.00000 | −2.70 | 0.542 | ✗ |
| **MDY** | **10** | **2** | **0.02** | **+0.85** | **0.00383** | **+1.72** | **0.005** | **✓** |
| IVV | 5 | 10 | 0.01 | +0.23 | 0.22034 | −1.32 | 0.206 | ✗ |
| VOO | 5 | 5 | 0.01 | +0.24 | 0.20662 | −1.17 | 0.189 | ✗ |

**Passing: QQQ, MDY**

### us_factor (α = 0.00625)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| IWF | 5 | 10 | 0.02 | −0.08 | 1.00000 | −3.10 | 0.603 | ✗ |
| IWD | 5 | 10 | 0.02 | −0.53 | 1.00000 | −5.06 | 0.954 | ✗ |
| **MTUM** | **5** | **2** | **0.00** | **+1.23** | **0.00014** | **+3.23** | **0.001** | **✓** |
| USMV | 5 | 10 | 0.02 | −0.58 | 1.00000 | −5.99 | 0.988 | ✗ |
| VTV | 5 | 10 | 0.00 | −0.22 | 1.00000 | −3.84 | 0.749 | ✗ |
| VUG | 5 | 10 | 0.02 | −0.43 | 1.00000 | −5.05 | 0.906 | ✗ |
| DVY | 10 | 2 | 0.00 | +0.14 | 0.32701 | −1.90 | 0.341 | ✗ |
| QUAL | 15 | 10 | 0.01 | +0.56 | 0.03078 | +0.41 | 0.032 | ✗ |

**Passing: MTUM**

Note: QUAL has Sharpe +0.56 with positive boot5 but fails gates 1 and 3 at Bonferroni threshold (raw p ≈ 0.031, α = 0.00625).

### us_sectors (α = 0.00455)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| XLK | 5 | 10 | 0.02 | −0.16 | 1.00000 | −3.51 | 0.734 | ✗ |
| XLC | 10 | 5 | 0.02 | −0.84 | 1.00000 | −6.99 | 0.993 | ✗ |
| XLI | 15 | 5 | 0.02 | −0.57 | 1.00000 | −5.85 | 0.973 | ✗ |
| XLV | 5 | 10 | 0.01 | +0.11 | 0.36664 | −1.90 | 0.360 | ✗ |
| XLY | 5 | 10 | 0.02 | −0.25 | 1.00000 | −4.19 | 0.796 | ✗ |
| XLF | 5 | 10 | 0.00 | −2.26 | 1.00000 | −14.83 | 1.000 | ✗ |
| XLE | 5 | 10 | 0.02 | −1.23 | 1.00000 | −9.29 | 1.000 | ✗ |
| XLU | 5 | 10 | 0.00 | −1.96 | 1.00000 | −12.21 | 1.000 | ✗ |
| XLB | 15 | 10 | 0.02 | −2.26 | 1.00000 | −12.98 | 1.000 | ✗ |
| XLP | 5 | 10 | 0.00 | −0.85 | 1.00000 | −6.89 | 0.996 | ✗ |
| XLRE | 10 | 10 | 0.00 | −1.80 | 1.00000 | −12.13 | 1.000 | ✗ |

**Passing: none**

### bonds_us (α = 0.01000)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| TLT | 15 | 5 | 0.02 | −0.55 | 1.00000 | −5.61 | 0.987 | ✗ |
| IEF | 15 | 10 | 0.02 | −1.55 | 1.00000 | −10.05 | 1.000 | ✗ |
| SHY | 5 | 10 | 0.02 | −4.04 | 1.00000 | −16.27 | 1.000 | ✗ |
| HYG | 15 | 10 | 0.01 | −2.32 | 1.00000 | −14.69 | 1.000 | ✗ |
| LQD | 10 | 10 | 0.02 | −0.83 | 1.00000 | −7.15 | 0.993 | ✗ |

**Passing: none**

### commodities (α = 0.01250)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| GLD | 5 | 10 | 0.00 | +0.07 | 0.41478 | −2.18 | 0.431 | ✗ |
| SLV | 15 | 10 | 0.01 | −2.38 | 1.00000 | −14.81 | 1.000 | ✗ |
| USO | 10 | 5 | 0.01 | −0.49 | 1.00000 | −4.69 | 0.951 | ✗ |
| GDX | 15 | 10 | 0.02 | −0.53 | 1.00000 | −6.49 | 0.984 | ✗ |

**Passing: none**

### em_regional (α = 0.01250)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| EEM | 5 | 10 | 0.00 | −1.60 | 1.00000 | −11.68 | 1.000 | ✗ |
| EWZ | 15 | 10 | 0.02 | −1.56 | 1.00000 | −8.72 | 1.000 | ✗ |
| INDA | 5 | 10 | 0.02 | −2.23 | 1.00000 | −13.68 | 1.000 | ✗ |
| EWW | 5 | 5 | 0.00 | −0.72 | 1.00000 | −6.03 | 0.979 | ✗ |

**Passing: none**

### intl_liquid (α = 0.01000)

| Ticker | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p | Pass |
|---|---|---|---|---|---|---|---|---|
| EFA | 5 | 10 | 0.02 | −0.66 | 1.00000 | −5.79 | 0.958 | ✗ |
| EZU | 5 | 10 | 0.02 | −1.33 | 1.00000 | −9.99 | 1.000 | ✗ |
| EWJ | 15 | 10 | 0.02 | −1.31 | 1.00000 | −9.01 | 1.000 | ✗ |
| EWG | 10 | 10 | 0.00 | −1.79 | 1.00000 | −12.63 | 1.000 | ✗ |
| EWU | 5 | 10 | 0.00 | −2.70 | 1.00000 | −18.51 | 1.000 | ✗ |

**Passing: none**

---

## Summary — Passing Tickers

| Ticker | Basket | Window | ATR% | Th% | Net Sharpe | t-p | Boot5 | Perm-p |
|---|---|---|---|---|---|---|---|---|
| **QQQ** | us_equity_broad | 5 min | 5% | 0.02% | **+0.83** | 0.00356 | +1.70 | 0.004 |
| **MDY** | us_equity_broad | 10 min | 2% | 0.02% | **+0.85** | 0.00383 | +1.72 | 0.005 |
| **MTUM** | us_factor | 5 min | 2% | 0.00% | **+1.23** | 0.00014 | +3.23 | 0.001 |

All three pass all 3 gates at their respective Bonferroni-corrected thresholds. Equity curves saved to `short_term/orb/results/orb_per_ticker_equity/`.

---

## Interpretation & Recommendation

### Notable findings

**QQQ** — Already validated in v1 (net Sharpe 0.89, atr=5). Per-ticker optimization with atr=5%, window=5min, threshold=0.02% yields Sharpe 0.83 here on the full sample. The slight difference from v1 is expected (different date ranges / minor parameter differences). Confirmed signal.

**MTUM** — Strongest result: Sharpe +1.23, t-p=0.00014 (well inside Bonferroni α=0.00625), bootstrap 5th-pct Sharpe +3.23 (strongly positive), perm-p=0.001. Optimal params: 5-min OR, 2% ATR stop, no threshold filter. Very tight ATR stop (2%) suggests the strategy captures short directional moves with quick risk control. This was hinted in v2 (Sharpe 1.02 at basket params); per-ticker optimization confirms and strengthens it.

**MDY** — Mid-cap blend ETF (S&P 400). Sharpe +0.85 with 10-min OR window and 2% ATR stop. Both t-p (0.0038) and perm-p (0.005) comfortably inside Bonferroni α=0.00714. Novel discovery — not seen in v1.

### Pattern

All 3 passing tickers share: small/tight ATR stop (2–5%), short OR window (5–10 min), small threshold (0.02% or none). The signal appears to extract value from early-session momentum in liquid US equity ETFs — specifically momentum/growth-oriented products (QQQ = large-cap tech-heavy, MTUM = momentum factor, MDY = mid-cap growth-heavy index).

Bonds, international, EM, commodities, and defensive US sectors show no ORB edge even at per-ticker optimal params. This is consistent with ORB being fundamentally an equity momentum phenomenon driven by overnight information and opening gap dynamics.

### Recommendation

**Include in Portfolio A v2 (conditional):**
- **QQQ** — confirmed across v1 and per-ticker v2. Use params: window=5min, atr=5%, threshold=0.02%.
- **MTUM** — strong new signal. Use params: window=5min, atr=2%, threshold=0.00%. Note the very tight stop; monitor for regime sensitivity.
- **MDY** — new discovery with good significance. Use params: window=10min, atr=2%, threshold=0.02%.

**Do not include:** all remaining 41 tickers. Their best per-ticker Sharpe values are negative or do not survive the Bonferroni 3-gate test.

**Risk note:** All 3 passing tickers are US equity ETFs from the same basket (us_equity_broad + us_factor). They will be correlated — especially during gap-up/gap-down days. Portfolio weighting should account for this correlation.

---

*Full results: `short_term/orb/results/orb_per_ticker_bonferroni_results.json`*  
*Equity curves: `short_term/orb/results/orb_per_ticker_equity/{QQQ,MDY,MTUM}.csv`*
