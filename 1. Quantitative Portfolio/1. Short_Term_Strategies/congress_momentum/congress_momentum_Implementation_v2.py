"""
congress_momentum_Implementation_v2.py
======================================
Sizing layer for Congress Momentum (fable run 2026-07-02).

Loads the canonical trades CSV from the Backtest and compares three
bet-fraction variants (the sensible sizing axis for a same-day event
strategy where per-share vol targeting doesn't apply):
  conservative  5% of capital per trade
  base         10% (the notebook's confirmed setting)
  aggressive   20%
Best-by-Sharpe is auto-selected -> results/equity/combined_equity_final.csv.

Note: trades are sequential same-day events sized as a fraction of running
capital; concurrent-overlap effects are ignored (matches the notebook sim).
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

SAVE_NAME        = 'congress_momentum_quiver_open'
INITIAL_CAPITAL  = 100_000
VARIANTS = {'conservative_5pct': 0.05, 'base_10pct': 0.10, 'aggressive_20pct': 0.20}

trades = pd.read_csv(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_trades.csv'))
trades['entry_time'] = pd.to_datetime(trades['entry_time'], utc=True).dt.tz_convert(None)
trades = trades.sort_values('entry_time').reset_index(drop=True)
print(f"Loaded {len(trades):,} trades")

def simulate(frac):
    capital = INITIAL_CAPITAL
    ts = []
    for _, row in trades.iterrows():
        capital += capital * frac * row['pct_return_gross']
        ts.append((row['entry_time'], capital))
    eq = pd.Series(dict(ts)).sort_index()
    # Business-day grid: sqrt(252) annualization needs ~252 obs/yr; the notebook's
    # calendar-D padding (weekend zero rows) deflated Sharpe ~15%. Fixed 2026-07-02.
    daily = eq.resample('B').last().ffill()
    dr = daily.pct_change().dropna()
    sharpe = dr.mean()/dr.std()*np.sqrt(252) if dr.std() > 0 else 0
    years = (eq.index[-1]-eq.index[0]).days/365.25
    cagr = (eq.iloc[-1]/INITIAL_CAPITAL)**(1/years) - 1
    mdd = ((eq - eq.cummax())/eq.cummax()).min()
    return daily, round(float(sharpe),3), round(float(cagr)*100,2), round(float(mdd)*100,2)

summary = {}
best_v, best_sh = None, -np.inf
for name, frac in VARIANTS.items():
    daily, sh, cagr, mdd = simulate(frac)
    daily.rename('equity').to_csv(os.path.join(EQUITY_DIR, f'combined_equity_{name}.csv'), index_label='date')
    summary[name] = {'fraction': frac, 'sharpe': sh, 'cagr_pct': cagr, 'maxdd_pct': mdd}
    print(f"[{name:18s}] Sharpe={sh:.3f}  CAGR={cagr:.1f}%  MaxDD={mdd:.1f}%")
    if sh > best_sh:
        best_sh, best_v = sh, name
        daily.rename('equity').to_csv(os.path.join(EQUITY_DIR, 'combined_equity_final.csv'), index_label='date')

summary['selected_variant'] = best_v
with open(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_implementations.json'), 'w') as f:
    json.dump(summary, f, indent=2)
print(f"\nSelected: {best_v} (Sharpe {best_sh:.3f})")
