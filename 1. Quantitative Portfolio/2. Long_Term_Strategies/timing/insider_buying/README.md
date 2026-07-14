# Insider Buying (VIX-Spike Proxy)

**Portfolio:** LongTerm | **Status:** ✅ Validated (proxy data) | **Canonical:** `insider_buying_timing_Backtest_multiasset.py`

## 1. Strategy

Exposure timing on an insider-buying proxy: insiders buy after dislocations, so VIX>1.3×3m-avg → 130% SPY, VIX<0.8×12m-avg → 80%, else 100%. Monthly, 5bps/side. **Proxy note:** true EDGAR Form-4/OpenInsider feed was network-blocked; VIX spike is the documented stand-in (see todo proxy log).

## 2. Validation & Results

1990–2026: net Sharpe 0.63, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 10.2%, MaxDD −54.6% (mostly market beta — the tilt is ±30%). Regimes: 13 overweight / 64 underweight / 357 neutral months.

## 3. Portfolio role

Candidate, not selected (greedy). Mostly-beta profile limits diversification value; revisit when real insider data replaces the proxy.

## 4. Files

`results/insider_buying_summary.json` · `results/insider_buying_daily_equity/` · v1 in `v1/` after refactor.
