"""
vix_etn_dual_Implementation_multiasset_v2.py
============================================
Script conversion of vix_etn_dual_Implementation.ipynb (fable run 2026-07-02).

Loads the canonical strategy (eVRP+BoC+Sizing) trades + daily equity produced
by the Backtest, runs a leverage sweep (1.0x/1.5x/2.0x - the strategy's sizing
variants; per-trade share sizing doesn't apply to a weight-driven ETN
rotation), compares to SPY at matched leverage and matched drawdown, and
auto-selects the best-by-Sharpe leverage as the final equity curve.

Outputs:
  results/equity/combined_equity_{1p0x,1p5x,2p0x}.csv
  results/equity/combined_equity_final.csv      (selected leverage)
  results/vix_etn_dual_implementations.json     (incl. _recommended,
                                                 _matched_dd_edges)
Runnable OFFLINE from existing results/ artifacts (no price fetch needed).
"""
import os, sys, json
import numpy as np
import pandas as pd

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root marker not found'
    _d = _p
sys.path.insert(0, _d)

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, 'results')
EQUITY_DIR  = os.path.join(RESULTS_DIR, 'equity')
os.makedirs(EQUITY_DIR, exist_ok=True)

SAVE_NAME        = 'vix_etn_dual'
STARTING_CAPITAL = 100_000
LEVERAGES        = [1.0, 1.5, 2.0]

trades = pd.read_csv(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_trades.csv'))
for c in ('entry_time', 'exit_time'):
    trades[c] = pd.to_datetime(trades[c], utc=True).dt.tz_convert(None)   # DST-safe
print(f"Loaded {len(trades):,} trades | period {trades['entry_time'].min().date()} -> {trades['exit_time'].max().date()}")
print(f"By instrument: {dict(trades['instrument'].value_counts())}")
print(f"Win rate (gross): {(trades['pct_return_gross'] > 0).mean()*100:.1f}%")

with open(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_summary.json')) as f:
    summary = json.load(f)
canonical = summary['canonical_strategy']
safe = canonical.replace('+', '_').replace(' ', '_').lower()
eq_canon = pd.read_csv(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_daily_equity_{safe}.csv'),
                       parse_dates=[0], index_col=0).iloc[:, 0]
ret_canon = eq_canon.pct_change().fillna(0)
eq_spy = pd.read_csv(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_daily_equity_spybench.csv'),
                     parse_dates=[0], index_col=0).iloc[:, 0]
ret_spy = eq_spy.pct_change().fillna(0)
print(f"Canonical: {canonical} ({len(eq_canon):,} daily points)")

def stats_from_eq(eq, ret):
    r = ret.dropna()
    sharpe = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else 0
    peak = eq.expanding().max()
    max_dd = ((eq - peak)/peak).min() * 100
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = ((eq.iloc[-1]/STARTING_CAPITAL)**(1/years) - 1) * 100 if years > 0 else 0
    tot = (eq.iloc[-1]/STARTING_CAPITAL - 1) * 100
    return {"total_return": round(tot, 1), "cagr": round(cagr, 2),
            "sharpe": round(sharpe, 2), "max_dd": round(max_dd, 1)}

def run_lev(ret_series, leverage, label):
    r = ret_series * leverage
    eq = STARTING_CAPITAL * (1 + r).cumprod()
    return {"label": label, "daily_equity": eq, "daily_returns": r, "stats": stats_from_eq(eq, r)}

vix_results = [run_lev(ret_canon, lev, f"{canonical} {lev}x") for lev in LEVERAGES]
spy_results = [run_lev(ret_spy,  lev, f"SPY {lev}x")          for lev in LEVERAGES]

print(f"\n{'Label':<32} {'TotRet%':>10} {'CAGR%':>8} {'Sharpe':>8} {'MaxDD%':>8}")
for r in vix_results + spy_results:
    s = r["stats"]
    print(f"{r['label']:<32} {s['total_return']:>10,.1f} {s['cagr']:>8.2f} {s['sharpe']:>8.2f} {s['max_dd']:>8.1f}")

# Matched-drawdown comparison: for each VIX leverage, find the SPY leverage
# with the closest MaxDD and report the CAGR edge.
matched_dd_edges = {}
for v in vix_results:
    closest = min(spy_results, key=lambda s: abs(s["stats"]["max_dd"] - v["stats"]["max_dd"]))
    matched_dd_edges[v["label"]] = {
        "matched_to": closest["label"], "vix_dd": v["stats"]["max_dd"],
        "spy_dd": closest["stats"]["max_dd"], "vix_cagr": v["stats"]["cagr"],
        "spy_cagr": closest["stats"]["cagr"],
        "cagr_edge": round(v["stats"]["cagr"] - closest["stats"]["cagr"], 2)}

def _key(label):
    return (label.lower().replace(" ", "_").replace(".", "p")
            .replace("+", "_").replace("&", "and").replace("/", "_"))

impl_summary = {}
for r in vix_results + spy_results:
    k = _key(r["label"])
    impl_summary[k] = dict(r["stats"]); impl_summary[k]["label"] = r["label"]
impl_summary["_matched_dd_edges"] = matched_dd_edges

best = max(vix_results, key=lambda r: r["stats"]["sharpe"])
impl_summary["_recommended"] = best["label"]
print(f"\nBest by Sharpe: {best['label']} - Sh {best['stats']['sharpe']}, DD {best['stats']['max_dd']}%, CAGR {best['stats']['cagr']}%")

with open(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_implementations.json'), 'w') as f:
    json.dump(impl_summary, f, indent=2)

for r, lev in zip(vix_results, LEVERAGES):
    r["daily_equity"].rename('equity').to_csv(
        os.path.join(EQUITY_DIR, f"combined_equity_{str(lev).replace('.','p')}x.csv"), index_label='date')
best["daily_equity"].rename('equity').to_csv(
    os.path.join(EQUITY_DIR, 'combined_equity_final.csv'), index_label='date')
print(f"Saved -> {EQUITY_DIR}")
