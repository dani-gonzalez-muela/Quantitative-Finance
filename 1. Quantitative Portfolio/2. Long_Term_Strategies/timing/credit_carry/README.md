# Credit Carry

**Portfolio:** LongTerm | **Status:** ✅ Active (v2) | **Canonical:** `credit_carry_v2` outputs

## 1. Strategy

Bond-ETF carry/momentum switch: hold credit ETF when its momentum (v2: 3m window) beats the IEF benchmark; else IEF. Monthly.

## 2. Validation

v2 multiasset (bonds_us, 6 instruments): basket passes — combined Sharpe 0.56, CAGR 1.5%, MaxDD −6.4%. v1 proxy-data version was NOT significant (0/3) — superseded by v2 with real ETF data. Older per-instrument variant rescued only BIL (Sharpe 4.7 on ~cash returns — an artifact of near-zero vol, treat with suspicion).

## 3. Portfolio role

**Selected in the 2026-07-02 LongTerm portfolio** (step 5) — low-vol bond sleeve that trims portfolio drawdown. Also flagged as one of the weaker family members in absolute Sharpe; candidate for the IEF re-benchmark pass alongside the other bond strategies.

## 4. Files

| File | Description |
|---|---|
| `results/credit_carry_v2_multiasset_daily_equity/combined_equity.csv` | Canonical equity |
| `results/credit_carry_{v2_,}implementations_multiasset.json` | Stats |
| `credit_carry_timing_backtest.py` | v1 (proxy era; paths fixed 2026-07-02) |
