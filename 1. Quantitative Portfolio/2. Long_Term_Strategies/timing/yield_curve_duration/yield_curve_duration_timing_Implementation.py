# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Yield Curve Duration — Implementation (single-instrument stub)

NOTE: This strategy is a single-instrument timing / factor-return strategy.
Basket weighting variants (equal_weight, inverse_vol_weight, signal_strength_weight)
do not apply because there is no cross-sectional instrument selection.
See todo/refactor_discussion_points.md §2.1.

Signal: regime switch: long/mid/short duration based on T10Y2Y spread
Instrument: bond_regime

What this file CAN do:
- Test EXPOSURE LEVEL variants (conservative / baseline / aggressive)
  by loading results/yield_curve_duration_trades.csv and calling shared.implementations.
- For parameter sweeps (e.g. different VIX thresholds, holding periods),
  modify yield_curve_duration_Backtest.py and re-run.

To run full sizing comparison, see:
    shared.implementations.simple_bet / vol_targeting / risk_based
    (already applied in yield_curve_duration_Backtest.py results)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import json

SAVE_NAME        = "yield_curve_duration"
STRATEGY_NAME    = "Yield Curve Duration"
STARTING_CAPITAL = 100_000
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

# ── Load signal (for reference) ──
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
if os.path.exists(signal_path):
    sig = pd.read_csv(signal_path, parse_dates=["date"])
    print(f"Signal loaded: {len(sig)} rows, instrument={sig['instrument'].iloc[0] if len(sig) else 'N/A'}")
    print(f"Score stats: mean={sig['score'].mean():.3f}, min={sig['score'].min():.3f}, max={sig['score'].max():.3f}")
else:
    print(f"WARNING: {signal_path} not found. Run {SAVE_NAME}_Backtest.py first.")

# ── Load trades for sizing variants ──
from _shared.implementations import simple_bet, vol_targeting, risk_based, compare_implementations

trades_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_trades.csv")
if not os.path.exists(trades_path):
    print(f"ERROR: {trades_path} not found. Run {SAVE_NAME}_Backtest.py first.")
    sys.exit(1)

trades = pd.read_csv(trades_path, parse_dates=["entry_time", "exit_time"])
print(f"\nLoaded {len(trades)} trades")
print(f"Period: {trades['entry_time'].iloc[0].date()} → {trades['exit_time'].iloc[-1].date()}")

# ── Sizing variants (Type 1 style — the applicable Implementation for this strategy) ──
print("\nRunning sizing variants...")
r_simple_85  = simple_bet(trades, bet_size=0.85)
r_simple_100 = simple_bet(trades, bet_size=1.00)
r_vol_10     = vol_targeting(trades, target_vol=0.10, lookback=60)
r_vol_15     = vol_targeting(trades, target_vol=0.15, lookback=60)
r_risk_1pct  = risk_based(trades, risk_pct=0.01, leverage=1)
r_risk_2pct  = risk_based(trades, risk_pct=0.02, leverage=1)

all_results = [r_simple_85, r_simple_100, r_vol_10, r_vol_15, r_risk_1pct, r_risk_2pct]

print("\nSIZING IMPLEMENTATIONS:")
compare_implementations(all_results)

# ── Save implementations.json ──
def _key(label):
    return (label.lower()
            .replace(" ", "_").replace("(", "").replace(")", "")
            .replace("%", "pct").replace("=", "").replace(",", "")
            .replace("x", "x").replace(".", "p"))

impl_summary = {}
for r in all_results:
    k = _key(r["label"])
    impl_summary[k] = dict(r["stats"])
    impl_summary[k]["label"] = r["label"]

viable = [r for r in all_results if r["stats"]["max_dd"] > -50]
if viable:
    best = max(viable, key=lambda r: r["stats"]["sharpe"])
    impl_summary["_recommended"] = best["label"]
    print(f"\nRecommended: {best['label']}")

impl_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_implementations.json")
with open(impl_path, "w") as f:
    json.dump(impl_summary, f, indent=2)
print(f"Saved → {impl_path}")

# Save per-variant equity curves
equity_dir = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(equity_dir, exist_ok=True)
for r in all_results:
    k = _key(r["label"])
    dates_full = [trades["entry_time"].iloc[0]] + trades["exit_time"].tolist()
    eq = r["equity_curve"]
    eq_df = pd.DataFrame({"date": dates_full[:len(eq)], "equity": eq})
    eq_df.to_csv(os.path.join(equity_dir, f"{k}.csv"), index=False)

print(f"Per-variant equity CSVs → {equity_dir}/")
print("Done.")
