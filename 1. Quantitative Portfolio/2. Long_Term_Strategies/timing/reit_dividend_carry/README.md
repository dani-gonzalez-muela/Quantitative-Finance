# REIT Dividend Carry

**Portfolio:** LongTerm | **Status:** ✅ Validated (proxy data) | **Canonical:** `reit_dividend_carry_timing_Backtest_multiasset.py`

## 1. Strategy

REIT exposure timed by dividend-yield carry: annualized CRSP income return vs its 24m average — yield>avg → 100%, yield<0.7×avg → 50%, else 75%. REIT return proxy = FF Mkt+0.5×HML. Monthly, 5bps/side. **Proxies:** VNQ/XLRE downloads were blocked; both the yield source and the REIT leg are proxies (todo log).

## 2. Validation & Results

2005-12→2025-02: net Sharpe 0.48, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 5.4%, MaxDD −33.1%. Regime counts show the signal spent 96% of months underweight — effectively a defensive de-risking rule over this rates cycle.

## 3. Portfolio role

Candidate, not selected. Re-test with real VNQ/XLRE data once downloads are possible; the proxy pair (S&P yield → HML-tilted return) is the weakest link in the chain.

## 4. Files

`results/reit_dividend_carry_summary.json` · `results/reit_dividend_carry_daily_equity/` · v1 → `v1/`.
