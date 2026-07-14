# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
generate_overnight_v1window_equity_v3.py
=========================================
Generates per-ticker daily equity curves for the overnight v1 window strategy.

V1 Window timing:
  - Entry  : close of after_market session (~19:55)
  - Exit   : open  of pre_market session (~04:00) next trading day
  - Signal : enter long only when prior intraday_ret < filter_threshold
             intraday_ret = (market_close_1555 - market_open_0930) / market_open_0930

Optimal thresholds (from overnight_v1window_all_baskets.json):
  SPY:  -0.005, QQQ: -0.001, IWM: -0.003, MDY: -0.005
  EEM:  -0.005, EWZ: -0.003, INDA:-0.005, EWW: -0.005

Output: per-ticker equity CSV in
  short_term/overnight/results/overnight_v1window_per_ticker_equity/{TICKER}.csv

Each CSV has columns: date, equity (starting at 100_000)
"""

import sys, os
import numpy as np
import pandas as pd
from datetime import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

DATA_DIR    = os.path.join(ROOT, 'short_term', 'data', 'intraday_5min')
RESULTS_DIR = os.path.join(ROOT, 'short_term', 'overnight', 'results',
                           'overnight_v1window_per_ticker_equity')
os.makedirs(RESULTS_DIR, exist_ok=True)

try:
    from _shared.fees import calculate_fees_pct as _fee_fn
    def fee_for_trade(entry, exit_):
        return _fee_fn(entry, exit_, 'long')
    FEE_MODE = 'shared/fees.py'
except Exception as e:
    print(f"WARNING: could not import shared.fees ({e}), using 1 bps fallback")
    def fee_for_trade(entry, exit_):
        return 0.0001
    FEE_MODE = 'fixed 1 bps fallback'

OPTIMAL_THRESHOLDS = {
    'SPY':  -0.005,
    'QQQ':  -0.001,
    'IWM':  -0.003,
    'MDY':  -0.005,
    'EEM':  -0.005,
    'EWZ':  -0.003,
    'INDA': -0.005,
    'EWW':  -0.005,
}

START_DATE = '2016-01-01'
END_DATE   = '2026-06-01'
START_NAV  = 100_000.0


def assign_session(t):
    if time(4, 0) <= t <= time(9, 25):
        return 'pre_market'
    elif time(9, 30) <= t <= time(15, 55):
        return 'market'
    elif time(16, 0) <= t <= time(19, 55):
        return 'after_market'
    return None


def load_and_build(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('US/Eastern')
    df = df.sort_values('timestamp').reset_index(drop=True)
    df = df[(df['timestamp'] >= pd.Timestamp(START_DATE, tz='US/Eastern')) &
            (df['timestamp'] <  pd.Timestamp(END_DATE,   tz='US/Eastern'))]

    df['session'] = df['timestamp'].apply(lambda ts: assign_session(ts.time()))
    df['session_date'] = df['timestamp'].dt.date
    df = df.dropna(subset=['session']).copy()

    session_ohlc = df.groupby(['session_date', 'session']).agg(
        session_open=('open', 'first'),
        session_close=('close', 'last'),
    ).reset_index()

    session_order = ['pre_market', 'market', 'after_market']
    session_ohlc['session'] = pd.Categorical(
        session_ohlc['session'], categories=session_order, ordered=True)
    session_ohlc = session_ohlc.sort_values(['session_date', 'session']).reset_index(drop=True)

    # Only keep days that have all 3 sessions
    counts = session_ohlc.groupby('session_date')['session'].count()
    valid_dates = counts[counts == 3].index
    session_ohlc = session_ohlc[session_ohlc['session_date'].isin(valid_dates)].reset_index(drop=True)

    pivot = session_ohlc.pivot(index='session_date', columns='session',
                               values=['session_open', 'session_close'])
    pivot.columns = ['_'.join(col) for col in pivot.columns.values]
    pivot = pivot.reset_index()

    # v1 window: entry = after_market close, exit = next day pre_market open
    pivot['entry_price'] = pivot['session_close_after_market']
    pivot['exit_price']  = pivot['session_open_pre_market'].shift(-1)
    pivot['market_close_signal'] = pivot['session_close_market']
    pivot['market_open_signal']  = pivot['session_open_market']

    # signal date is the day we hold overnight (exit is next day)
    pivot['date'] = pd.to_datetime(pivot['session_date'])
    pivot = pivot.dropna(subset=['entry_price', 'exit_price']).copy()

    pivot['intraday_ret'] = ((pivot['market_close_signal'] - pivot['market_open_signal'])
                             / pivot['market_open_signal'])

    return pivot[['date', 'entry_price', 'exit_price', 'intraday_ret']].set_index('date')


def compute_equity(daily, threshold):
    """Return daily equity series starting at START_NAV."""
    mask   = daily['intraday_ret'] < threshold
    gross  = daily['exit_price'] / daily['entry_price'] - 1
    fees   = daily.apply(lambda r: fee_for_trade(r['entry_price'], r['exit_price']), axis=1)
    net    = np.where(mask, gross - fees, 0.0)
    rets   = pd.Series(net, index=daily.index, name='ret')
    equity = (1 + rets).cumprod() * START_NAV
    return equity


def sharpe(rets):
    r = rets[rets != 0].dropna()
    if len(r) < 30 or r.std() == 0:
        return float('nan')
    return float(r.mean() / r.std() * np.sqrt(252))


print(f"Fee mode: {FEE_MODE}")
print(f"Period: {START_DATE} to {END_DATE}")
print()

results_summary = {}

for tk, thr in OPTIMAL_THRESHOLDS.items():
    print(f"Processing {tk} (threshold={thr})...")
    daily  = load_and_build(tk)
    equity = compute_equity(daily, thr)

    # Net returns for stats
    mask  = daily['intraday_ret'] < thr
    gross = daily['exit_price'] / daily['entry_price'] - 1
    fees  = daily.apply(lambda r: fee_for_trade(r['entry_price'], r['exit_price']), axis=1)
    net   = pd.Series(np.where(mask, gross - fees, 0.0), index=daily.index)

    sh   = sharpe(net)
    n_tr = int((net != 0).sum())
    yrs  = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float(equity.iloc[-1] / START_NAV) ** (1 / max(yrs, 0.5)) - 1
    peak = equity.expanding().max()
    mdd  = float(((equity - peak) / peak).min())

    print(f"  Sharpe={sh:.4f}, CAGR={cagr*100:.2f}%, MaxDD={mdd*100:.2f}%, n_trades={n_tr}")

    # Save equity CSV
    out = equity.reset_index()
    out.columns = ['date', 'equity']
    out['date'] = out['date'].dt.strftime('%Y-%m-%d')
    out_path = os.path.join(RESULTS_DIR, f'{tk}.csv')
    out.to_csv(out_path, index=False)
    print(f"  Saved -> {out_path}")

    results_summary[tk] = {'sharpe': sh, 'cagr': cagr, 'max_dd': mdd, 'n_trades': n_tr}

print("\nDone. Summary:")
for tk, s in results_summary.items():
    print(f"  {tk:5s}: Sharpe={s['sharpe']:.4f}  CAGR={s['cagr']*100:.2f}%  MaxDD={s['max_dd']*100:.2f}%")
