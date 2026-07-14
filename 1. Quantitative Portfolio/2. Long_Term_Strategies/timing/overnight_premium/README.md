# Overnight Premium (long-term family)

**Portfolio:** LongTerm | **Status:** ❌ REJECTED — no evidence of effect | **Canonical:** `overnight_premium_timing_Backtest_multiasset_v2.py`

## 1. Strategy

Hold close→open every night on daily-bar ETFs (no hyperparameters). Tests the "overnight premium" anomaly at DAILY data granularity with 5bps/side.

## 2. Validation & Results (v2 multiasset, 2016→2026-04)

**Every instrument fails, both baskets fail**: us_equity_broad median Sharpe −1.18 (0/4 pass), us_sectors −1.26 (0/11 pass), binomial p=1.0. At ~2,400 trades/instrument, 10bps round-trip per night annihilates the ~−4 to −9bps/night net means.

## 3. Important distinction

This is NOT the Intraday family's `overnight` strategy — that one works on 5-min session data with a down-day entry filter and passes validation. This daily-bar unconditional version is the null result that motivated the filtered intraday redesign. **Keep as documented negative result** (prevents re-testing the same dead end).

## 4. Files

`results/overnight_premium_v2_multiasset_summary.json` (the full per-instrument FAIL table) · older generations → `v1/` after refactor.
