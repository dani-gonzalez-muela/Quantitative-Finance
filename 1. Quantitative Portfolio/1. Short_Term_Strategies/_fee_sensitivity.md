# Intraday Fee Sensitivity — 2026-07-10 rerun

Slippage rerun of the 5 intraday session strategies. All numbers are the **selected
sizing variant (asset_vol)** portfolio stats from `*_v2_implementations.json`.
Fees = SEC + FINRA TAF + slippage per side (asset_vol variant: flat cost/share).

**Canonical from 2026-07-10:** ema / orb / intraday_momentum / overnight at
**$0.005/share per side**; vwap_trend stays **slippage-0** (limit-orders-at-VWAP
rationale) with the $0.005 run recorded as sensitivity.

## Important correction to the plan's premise

The pre-rerun canonical curves were **not** slippage-0. The selected `asset_vol`
variant used the paper's flat `cost_per_share=$0.0045`, while the unselected
simple/vol_target variants used the `_shared/fees.py` default `$0.01`. That's why
"old" numbers sit close to the new $0.005 ones. The rerun unifies all variants on
one configurable slippage (`SLIPPAGE` env var, default 0.005).

## Results (selected variant = asset_vol)

| Strategy | Trades/day | Sharpe @ slip 0 | Sharpe @ $0.005 | Sharpe old ($0.0045 flat) | CAGR @ 0 | CAGR @ $0.005 | MaxDD @ $0.005 |
|---|---|---|---|---|---|---|---|
| ema_crossover | ~5 | 7.77 | **5.68** | 5.84 | 188.6% | 129.0% | −4.7% |
| orb | ~1 | 2.61 | **2.20** | 2.24 | 20.1% | 16.3% | −4.7% |
| intraday_momentum | ~1 | 1.69 | **1.46** | 1.48 | 16.3% | 13.7% | −11.5% |
| overnight | ~0.5 | 1.88 | **1.66** | 1.68 | 13.8% | 12.1% | −13.9% |
| vwap_trend | ~16 | **1.58** (canonical) | 0.28 ⚠ | 0.34 | 33.7% | 3.1% | −46.7% |

## Reading

- **orb / intraday_momentum / overnight barely move** (−0.2 Sharpe from frictionless) — low turnover, robust to costs.
- **ema_crossover loses a large chunk** (7.77 → 5.68) but remains very strong; ~5 trades/day makes it fee-sensitive in absolute terms.
- **vwap_trend is cost-fragile as flagged**: 1.58 slippage-0 → 0.28 at $0.005 (simple/vol_target variants go **negative**). Its edge (sub-bp) does not survive half-spread costs at ~16 trades/day. Significance check on the $0.005 curve: **0/3 gates** (t=0.80) — it only passes frictionless, exactly as the plan warned. Canonical stays slippage-0 only under the strict limit-order-at-VWAP execution assumption — do not trade it with marketable orders.

## File locations (per strategy `results/`)

- `equity/` + `*_v2_implementations.json` — canonical ($0.005; vwap: $0)
- `_slip0/` — frictionless run
- `_slip0p01_backup/` — pre-2026-07-10 canonical (mixed 0.0045/0.01 fee bases)
- `vwap_trend/results/_slip0p005/` — vwap $0.005 sensitivity
