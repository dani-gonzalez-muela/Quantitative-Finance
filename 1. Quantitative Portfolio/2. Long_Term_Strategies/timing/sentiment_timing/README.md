# Sentiment Timing (VIX)

**Portfolio:** LongTerm | **Status:** ⚠️ Validated v1, but v2 equity construction is BUGGED — excluded until fixed | **Canonical:** `sentiment_timing_timing_Backtest_multiasset_v2.py` (after fix)

## 1. Strategy

Contrarian sentiment exposure: month-end VIX>25 → 150% SPY, VIX<15 → 50%, else 100%. Monthly, 5bps/side. (Baker-Wurgler sentiment index blocked; VIX per Da et al. 2015.)

## 2. Validation & Results (v1, 1990–2026)

Net Sharpe 0.60, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 10.9%, MaxDD −61.1% (buying more when VIX>25 concentrates drawdowns — the price of contrarianism).

## 3. ⚠️ Known bug (from methodology v4 §5 — the reason it's benched)

The v2 multiasset Implementation linearly interpolates monthly returns to daily (`np.linspace`), compressing daily vol ~10× and inflating daily Sharpe to a spurious 2.60 (true monthly ≈ 0.67). Its canonical params (vix_low=12, vix_high=32) also leave it invested 99.2% of the time — signal nearly inactive. **Fix both before portfolio re-admission** (unified TODO item 2).

## 4. Files

`results/sentiment_timing_summary.json` (v1, trustworthy) · `results/sentiment_timing_v2_multiasset_summary.json` (bugged — do not consume) · older scripts → `v1/`.
