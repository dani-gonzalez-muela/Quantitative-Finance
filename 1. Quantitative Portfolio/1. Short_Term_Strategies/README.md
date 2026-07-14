# 1. Short_Term_Strategies — the 9-strategy short-term universe

One flat folder per strategy (the old Intraday/Daily split is retired; since
2026-07-10 all 9 feed ONE merged candidate pool for the SHORT-TERM portfolio,
built in `3. Portfolio_construction`). The former `vol_overlay/` was extracted
to a self-contained regime-classification project (2026-07-10).

## Strategies

| Folder | Type | In ST portfolio? | Canonical |
|---|---|---|---|
| `ema_crossover/` | intraday session (5-min) | ✅ selected | `*_Implementation_multiasset_v2.py` |
| `overnight/` | overnight carry | ✅ selected (normal pool member) | `*_v2.py` |
| `ibs_mean_reversion/` | daily mean reversion | ✅ selected | `*_v2.py` |
| `orb/` | intraday session | ✅ selected | `*_v2.py` |
| `congress_momentum/` | daily (Quiver congress) | ✅ selected (5th, diversifier) | `*_v2.py` |
| `intraday_momentum/` | intraday session | evaluated, not selected | `*_v2.py` |
| `vwap_trend/` | intraday session | evaluated, not selected (cost-fragile ⚠) | `*_v2.py` |
| `vix_mean_reversion/` | daily (SVXY) | evaluated, not selected | notebooks (v2 curve standardized to `results/equity/combined_equity_final.csv`) |
| `vix_etn_dual/` | daily (VIX ETNs) | evaluated, not selected | `*_v2.py` |

## Conventions

- Each folder: `README.md` (rules, procedure, results), `*_Backtest_*_v2.py` ->
  trade CSVs + canonical params + 3-gate significance; `*_Implementation_*_v2.py` ->
  sizing variants -> `results/equity/combined_equity_final.csv` (the portfolio-facing curve).
- Historical/monolith notebooks live in each strategy's `v1/`.
- **Fees (2026-07-10 rerun):** intraday session strategies at **$0.005/share per side**
  (`SLIPPAGE` env-overridable); vwap_trend canonically slippage-0 (limit-order rationale)
  and collapses at $0.005 — see `_fee_sensitivity.md`. Old curves preserved per strategy in
  `results/_slip0/` (frictionless) and `results/_slip0p01_backup/` (pre-rerun).

Run order per strategy: Backtest -> Implementation. Portfolio: see `3. Portfolio_construction/README.md`.
