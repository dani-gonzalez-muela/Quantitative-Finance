# Quality / Profitability

**Portfolio:** LongTerm — **SELECTED (seed of the greedy, Sharpe 1.118)** | **Status:** ✅ Validated | **Canonical:** `quality_profitability_selection_Backtest_multiasset_v2.py`

## 1. Strategy

Novy-Marx profitability tilt: long `Mkt + ½RMW` when the 12m cumulative RMW signal is positive, else market only. FF5 RMW (Compustat GP construction was OOM; `quality_v2` variant rebuilt it from the Compustat zip via DuckDB — see below). Monthly, 5bps/side.

## 2. Validation & Results

1963–2026 (62 years!): net Sharpe 0.88, **3/3 gates, SIGNIFICANT (strong)**. CAGR 9.2%, MaxDD −43.5%. The longest validated sample in the family.

## 3. Portfolio role

**Seed of the LongTerm portfolio** — highest standalone monthly Sharpe on the common window (1.118, matching the retired Portfolio-B-v2 seed value exactly). Watch item: ρ=0.87 with us_earnings_momentum (shared factor DNA) — arguably one factor bet counted twice; a demotion decision between the two is an open judgment call.

## 4. Housekeeping

`quality_v2_selection_backtest.py` + `quality_profitability_v2_selection_Implementation.py` (the DuckDB/Compustat intermediate, §3.3 flag) → `v1/` after the refactor; its `quality_v2_summary.json` + equity stay in results (that curve fed the old Portfolio B).

## 5. Files

`results/quality_profitability_summary.json` (+ `_multiasset_`, `_v2_multiasset_`, `quality_v2_` variants) · drafts → `v1/`.
