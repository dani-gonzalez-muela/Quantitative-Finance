# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
shared/daily_impl_utils.py
==========================
Helpers shared by Daily-portfolio Implementation scripts (fable run 2026-07-02).

daily_equity_from : mark-to-market daily equity for one instrument sleeve from
                    trade-level results (multi-day holds supported).
eq_stats          : (sharpe, cagr_pct, maxdd_pct) from a daily equity Series.
run_three_variants: canonical daily-bar sizing trio (simple 85% bet,
                    asset-vol 1%d/14d/2x, vol-target 10%ann/60d/2x).
"""
import numpy as np
import pandas as pd
from _shared.implementations import simple_bet, asset_vol_targeting, vol_targeting

DAILY_VARIANTS = ['simple', 'asset_vol', 'vol_target']

def daily_equity_from(trades, equity_curve, shares, closes):
    """Daily MTM equity for one instrument sleeve.
    trades: DataFrame with entry_time/exit_time (tz-naive Timestamps) and entry_price.
    equity_curve: list from a shared.implementations sizing fn (len = ntrades+1).
    shares: shares per trade (same length as trades).
    closes: daily close Series for the instrument."""
    tr = trades.copy()
    tr['shares'] = list(shares)
    tr['entry_date'] = pd.to_datetime(tr['entry_time']).dt.normalize()
    tr['exit_date']  = pd.to_datetime(tr['exit_time']).dt.normalize()
    all_days = pd.bdate_range(tr['entry_date'].iloc[0], tr['exit_date'].iloc[-1])
    px = closes.copy()
    px.index = pd.to_datetime(px.index).normalize()
    px = px.reindex(all_days).ffill()
    eq_after = np.array(equity_curve[1:])
    exits = dict(pd.Series(eq_after, index=tr['exit_date'].values).groupby(level=0).last())
    out = {}
    cash = equity_curve[0]
    open_pos = []
    ti = 0
    tr_sorted = tr.sort_values('entry_date').reset_index(drop=True)
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

def eq_stats(eq):
    r = eq.pct_change().dropna()
    sh = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else 0
    years = (eq.index[-1]-eq.index[0]).days/365.25
    cagr = (eq.iloc[-1]/eq.iloc[0])**(1/max(years, 0.5)) - 1
    dd = ((eq - eq.cummax())/eq.cummax()).min()
    return round(float(sh), 4), round(float(cagr)*100, 2), round(float(dd)*100, 2)

def run_three_variants(trades, closes, sleeve_cap):
    """Returns {variant: (daily_equity, sharpe)} for the canonical trio."""
    runs = {
        'simple':     simple_bet(trades, bet_size=0.85, starting_capital=sleeve_cap),
        'asset_vol':  asset_vol_targeting(trades, closes, target_vol=0.01, lookback=14,
                                          max_leverage=2.0, starting_capital=sleeve_cap),
        'vol_target': vol_targeting(trades, target_vol=0.10, lookback=60,
                                    max_leverage=2.0, starting_capital=sleeve_cap),
    }
    out = {}
    for v, res in runs.items():
        shares = res.get('shares_per_trade', [0]*len(trades))
        deq = daily_equity_from(trades, res['equity_curve'], shares, closes)
        out[v] = deq
    return out
