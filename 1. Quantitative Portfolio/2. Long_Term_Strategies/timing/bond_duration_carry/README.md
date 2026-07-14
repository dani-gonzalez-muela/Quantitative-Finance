# Bond Duration Carry

**Portfolio:** LongTerm | **Status:** ❌ NOT significant (0/3) — on the IEF re-benchmark list | **Canonical:** `bond_duration_carry_timing_Backtest_multiasset_v2.py`

## 1. Strategy

Duration selection on real-yield carry: DFII10 (synthetic) + slope — real yield >1% & steep → 20yr, >0 → 10yr, <−0.5% → 2yr. Duration-model returns, monthly, 5bps/side.

## 2. Validation & Results

2016-02→2025-07: net Sharpe **−0.04, 0/3 gates**. CAGR 0.7%, MaxDD −21.8%. Spent 85/114 months in the middle bucket — the signal barely differentiates on this sample.

## 3. Portfolio role

**Excluded.** Same disposition path as yield_curve_duration: quarterly IEF re-benchmark (unified TODO item 1) decides retire-vs-retune. The two strategies share data, sample and failure mode — evaluate them together.

## 4. Files

`results/bond_duration_carry_summary.json` + `_v2_multiasset_summary.json` · older scripts → `v1/`.
