# Commodity Trend

**Portfolio:** LongTerm | **Status:** ✅ Validated (thin universe) | **Canonical:** `commodity_trend_selection_Backtest_multiasset_v2.py`

## 1. Strategy

12-month time-series momentum on commodities: long when 12m return > 0, else flat. Equal weight. v1 universe was only gold+oil (proxy data); v2 multiasset extends to the ETF universe incl. a real-assets sleeve (REITs+MLPs).

## 2. Validation & Results

2001–2025: net Sharpe 0.36, **2/3 gates, SIGNIFICANT (moderate)**. CAGR 5.6%, MaxDD −67.1% (2-asset v1 concentration; v2 sleeves are tamer). Its **real_assets sleeve (Sharpe ~1.1)** is the strongest piece — which is what `commodity_combined.py` exploits.

## 3. Portfolio role

Not selected standalone (commodity_carry won the slot). Value lives in the real-assets sleeve and the 50/50 combined blend — consider promoting `commodity_combined` to a named greedy candidate (open judgment call).

## 4. Files

`results/commodity_trend_summary.json` + `_multiasset_` + `_v2_multiasset_summary.json` · older generations → `v1/`.
