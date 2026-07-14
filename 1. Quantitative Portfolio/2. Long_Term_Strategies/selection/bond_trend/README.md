# Bond Trend

**Portfolio:** LongTerm | **Status:** ⚠️ Active but weak | **Canonical:** `bond_trend_*_multiasset` outputs

## 1. Strategy

Time-series momentum on bond ETFs: v2 canonical = top 25% by 3m momentum, rebalanced every 2 months, across bonds_us (7 tickers) + bonds_intl (EMB, BNDX). v1 proxy version: 12m momentum long/flat.

## 2. Validation

v2 combined Sharpe ≈ 0.62 (simple_85, two sleeves); v1 proxy era NOT significant (0/3 — proxy data). Flagged by the 2026-07-02 family Bonferroni layer as a **weak member carried by the selection basket** (monthly Sharpe 0.19, perm-p 0.18); also on the todo IEF re-benchmark list.

## 3. Portfolio role

**Selected in the 2026-07-02 LongTerm portfolio** (step 4) on diversification value; its inclusion is the portfolio's most fragile leg — re-assess after the quarterly/IEF re-benchmark.

## 4. Files

| File | Description |
|---|---|
| `results/bond_trend_v2_multiasset_daily_equity/combined_equity.csv` | Canonical equity |
| `results/bond_trend_{multiasset_,}summary.json` | Stats |
| `bond_trend_selection_backtest.py` | v1 (proxy era; paths + NameError fixed, now emits signal.csv) |
