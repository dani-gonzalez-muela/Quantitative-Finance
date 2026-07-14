"""
ibs_mean_reversion_Implementation_multiasset_v2.py
==================================================
Reads canonical params + per-ticker trade CSVs produced by the Backtest.
Runs three sizing variants via shared.implementations and auto-selects the
best-by-Sharpe variant (canonical ema_crossover pattern, adapted to daily bars).

Sizing variants (daily-bar adaptation, see README):
  1. simple      - simple_bet: fixed 85% of sleeve equity per trade
  2. asset_vol   - asset_vol_targeting: underlying-asset daily vol targeting
                   (1% daily target, 14d lookback, 2x max leverage - the
                   daily-bar analog of the intraday paper method; intraday's
                   2%/4x is too aggressive for multi-day holds)
  3. vol_target  - vol_targeting: 10% annualized strategy-vol target, 2x max

Outputs:
  results/equity/combined_equity_simple.csv
  results/equity/combined_equity_asset_vol.csv
  results/equity/combined_equity_vol_target.csv
  results/equity/combined_equity_final.csv     (selected, best Sharpe)
  results/ibs_mean_reversion_v2_implementations.json

v2.1 changelog (fable run 2026-07-02):
  - New file behavior: previously the Implementation only built one 1/N
    equal-weight combined curve into a custom-named folder
    (ibs_mean_reversion_v2_multiasset_daily_equity/). Now: 3 sizing variants,
    best-by-Sharpe auto-selection, canonical results/equity/ layout.
  - Paths via shared.paths (ROOT bug class fixed).
  - Trade timestamps parsed with utc=True then tz-dropped (DST bug class;
    daily bars are date-only but the guard costs nothing).
  - Canonical params JSON readers isinstance-guard the _run_info key.
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root marker not found'
    _d = _p
sys.path.insert(0, _d)

from _shared.paths import data_dir
from _shared.implementations import simple_bet, asset_vol_targeting, vol_targeting

DATA_DIR    = data_dir('daily_tickers')
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, 'results')
TRADES_DIR  = os.path.join(RESULTS_DIR, 'trades')
EQUITY_DIR  = os.path.join(RESULTS_DIR, 'equity')
CANON_PATH  = os.path.join(RESULTS_DIR, 'ibs_mean_reversion_v2_canonical_params.json')
BONF_PATH   = os.path.join(RESULTS_DIR, 'ibs_mean_reversion_v2_bonferroni_results.json')
os.makedirs(EQUITY_DIR, exist_ok=True)

STARTING_CAPITAL = 100_000
SAVE = 'ibs_mean_reversion_v2'

# ── Collect validated instruments (basket passes + Bonferroni rescues) ──────
with open(CANON_PATH) as f:
    canonical = json.load(f)
bonf = {}
if os.path.exists(BONF_PATH):
    with open(BONF_PATH) as f:
        bonf = json.load(f)

validated = []   # (basket, ticker, prefix)
for b, meta in canonical.items():
    if not isinstance(meta, dict):        # _run_info guard (bug class 3)
        continue
    if meta.get('passes'):
        for tk in meta['instruments']:
            validated.append((b, tk, ''))
for b, tks in bonf.items():
    if not isinstance(tks, dict):
        continue
    for tk, r in tks.items():
        if isinstance(r, dict) and r.get('rescued'):
            validated.append((b, tk, 'bonferroni_'))

print(f"Validated instruments: {len(validated)}")
if not validated:
    raise SystemExit('No validated instruments - run Backtest first')

sleeve_cap = STARTING_CAPITAL / len(validated)

def load_daily_close(tk):
    df = pd.read_csv(os.path.join(DATA_DIR, f'{tk}.csv'), parse_dates=['date'], index_col='date').sort_index()
    return df['close']

def load_trades(basket, tk, prefix):
    path = os.path.join(TRADES_DIR, f'{SAVE}_trades_{prefix}{basket}_{tk}.csv')
    t = pd.read_csv(path)
    # DST-safe parse (bug class 2): parse as UTC then drop tz
    for c in ('entry_time', 'exit_time'):
        t[c] = pd.to_datetime(t[c], utc=True).dt.tz_convert(None)
    return t

def daily_equity_from(trades, equity_curve, shares, closes):
    """Daily mark-to-market equity for one instrument sleeve."""
    tr = trades.copy()
    tr['shares'] = shares
    tr['entry_date'] = tr['entry_time'].dt.normalize()
    tr['exit_date']  = tr['exit_time'].dt.normalize()
    all_days = pd.bdate_range(tr['entry_date'].iloc[0], tr['exit_date'].iloc[-1])
    px = closes.copy()
    px.index = pd.to_datetime(px.index).normalize()
    px = px.reindex(all_days).ffill()
    eq_after = np.array(equity_curve[1:])
    cash_after_exit = pd.Series(eq_after, index=tr['exit_date'].values).groupby(level=0).last()
    out = {}
    cash = equity_curve[0]
    open_pos = []
    ti = 0
    tr_sorted = tr.sort_values('entry_date').reset_index(drop=True)
    exits = dict(cash_after_exit)
    for day in all_days:
        while ti < len(tr_sorted) and tr_sorted.loc[ti, 'entry_date'] <= day:
            row = tr_sorted.loc[ti]
            if row['exit_date'] > day:
                open_pos.append(row)
            ti += 1
        open_pos = [p for p in open_pos if p['exit_date'] > day]
        if day in exits:
            cash = exits[day]
        mtm = cash
        for p in open_pos:
            pxd = px.loc[day]
            if not np.isnan(pxd) and p['entry_price'] > 0:
                mtm += p['shares'] * (pxd - p['entry_price'])
        out[day] = mtm
    return pd.Series(out).sort_index()

def stats(eq):
    r = eq.pct_change().dropna()
    sh = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else 0
    years = (eq.index[-1]-eq.index[0]).days/365.25
    cagr = (eq.iloc[-1]/eq.iloc[0])**(1/max(years, 0.5)) - 1
    dd = ((eq - eq.cummax())/eq.cummax()).min()
    return round(float(sh), 4), round(float(cagr)*100, 2), round(float(dd)*100, 2)

VARIANTS = ['simple', 'asset_vol', 'vol_target']
per_variant_daily = {v: [] for v in VARIANTS}
per_inst_sharpe = {v: {} for v in VARIANTS}

for basket, tk, prefix in validated:
    trades = load_trades(basket, tk, prefix)
    if len(trades) < 10:
        continue
    closes = load_daily_close(tk)
    runs = {
        'simple':     simple_bet(trades, bet_size=0.85, starting_capital=sleeve_cap),
        'asset_vol':  asset_vol_targeting(trades, closes, target_vol=0.01, lookback=14,
                                          max_leverage=2.0, starting_capital=sleeve_cap),
        'vol_target': vol_targeting(trades, target_vol=0.10, lookback=60,
                                    max_leverage=2.0, starting_capital=sleeve_cap),
    }
    for v, res in runs.items():
        shares = res.get('shares_per_trade', [0]*len(trades))
        deq = daily_equity_from(trades, res['equity_curve'], shares, closes)
        per_variant_daily[v].append(deq)
        s, c, d = stats(deq)
        per_inst_sharpe[v][f'{tk}{"(B)" if prefix else ""}'] = s
    print(f"  {tk:6s} ({basket}{' bonf' if prefix else ''})  " +
          "  ".join(f"{v}:{per_inst_sharpe[v][f'{tk}{chr(40)}B{chr(41)}' if prefix else tk]:+.2f}" for v in VARIANTS))

summary = {}
best_v, best_sh = None, -np.inf
for v in VARIANTS:
    curves = per_variant_daily[v]
    all_days = pd.bdate_range(min(c.index[0] for c in curves), max(c.index[-1] for c in curves))
    total = sum(c.reindex(all_days).ffill().fillna(c.iloc[0] if len(c) else sleeve_cap) for c in curves)
    total.name = 'equity'
    out = os.path.join(EQUITY_DIR, f'combined_equity_{v}.csv')
    total.to_csv(out, index_label='date')
    sh, cagr, dd = stats(total)
    summary[v] = {'sharpe': sh, 'cagr_pct': cagr, 'maxdd_pct': dd,
                  'per_instrument_sharpe': per_inst_sharpe[v]}
    print(f"[{v:10s}] Sharpe={sh:.3f}  CAGR={cagr:.1f}%  MaxDD={dd:.1f}%  -> {out}")
    if sh > best_sh:
        best_sh, best_v = sh, v
        total.to_csv(os.path.join(EQUITY_DIR, 'combined_equity_final.csv'), index_label='date')

summary['selected_variant'] = best_v
summary['n_instruments'] = len(validated)
summary['sleeve_capital'] = sleeve_cap
summary['starting_capital'] = STARTING_CAPITAL
with open(os.path.join(RESULTS_DIR, f'{SAVE}_implementations.json'), 'w') as f:
    json.dump(summary, f, indent=2)
print(f"\nSelected: {best_v} (Sharpe {best_sh:.3f}) -> results/equity/combined_equity_final.csv")
