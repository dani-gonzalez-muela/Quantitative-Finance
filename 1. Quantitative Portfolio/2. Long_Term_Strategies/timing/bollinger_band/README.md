# Bollinger Band

**Portfolio:** Daily (sub-monthly holds) | **Status:** ✅ Active | **Canonical file:** `bollinger_band_Backtest_multiasset_v2.py` era outputs (`*_v2_multiasset_daily_equity/`)

## 1. Strategy

Mean-reversion band timing on daily bars: long when price crosses below the lower Bollinger Band (30d, 2.0σ), minimum 30-day hold. Long only, 5bps/side.

## 2. Validation

Multi-asset framework across us_equity_broad / us_sectors / us_factor (21 instruments): **19/21 instruments pass** the 3-gate test at canonical params (bb_period=30, bb_std=2.0, min_hold=30). SPY per-instrument Sharpe 2.36 (t-p 0.0001). v1 single-instrument version (SPY/QQQ/IWM): 3/3 gates, Sharpe 0.73.

## 3. Results

v2 multiasset combined equity (2016→2026-04): monthly Sharpe ≈ 1.08 (Daily-portfolio measurement). v1 sizing variants: simple 85% Sharpe 0.73/CAGR 9.1%; asset-vol 10% Sharpe 0.73/CAGR 10.7%.

## 4. Portfolio role

Daily-portfolio candidate (frequency-based classification). Selected in the 2026-06-28 Daily portfolio (step 3, took Sharpe 1.96→2.15); not selected in the 2026-07-02 rebuild (improved ibs base). ρ≈0.69 with Donchian — the two rarely coexist in a portfolio.

## 5. Files

| File | Description |
|---|---|
| `results/bollinger_band_v2_multiasset_daily_equity/combined_equity.csv` | Canonical equity (portfolio input) |
| `results/bollinger_band_multiasset_summary.json` | Per-instrument gates |
| `results/bollinger_band_implementations*.json` | Sizing variants |
