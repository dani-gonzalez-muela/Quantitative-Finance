"""
congress_momentum_Backtest_v2.py
================================
Script conversion of congress_momentum_Backtest.ipynb (fable run 2026-07-02).

Winner strategy from V2_02_basic_strategies.ipynb section 7-8:
  Universe: US Congressional Purchase disclosures (QuiverQuant)
  Filter:   Annualized_Traded_To_File > 1.5 (stock already moving pre-publication)
            and Quiver upload within 3 days of SEC filing
  Entry:    buy at OPEN on Quiver upload day; Exit: sell at CLOSE same day

SCOPE NOTE: single-signal event strategy on a cross-section of stocks - the
basket+Bonferroni framework does not apply (refactor_discussion_points 2.1);
validation = shared.significance 3-gate on per-trade returns.

DATA: final_data_MEGA.pkl via the shared manifest store 'congress_quiver'
(kept private/outside the price stores - distinct source & licensing, per
plan Phase B item 4). If /tmp/final_data_MEGA.pkl exists it is used instead
(fast local staging).

v2 changelog:
  - Notebook->script conversion; removed the hardcoded absolute Windows path
    (ROOT-bug class) in favor of shared.paths.
  - get_open_to_close vectorized (pre-normalized, searchsorted) - the
    notebook version re-sorted every ticker frame per trade.
  - Saves canonical 9-col trades to results/, daily equity, and summary JSON
    with 3-gate significance.
"""
import os, sys, json, pickle
import numpy as np
import pandas as pd

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root marker not found'
    _d = _p
sys.path.insert(0, _d)

from _shared.paths import data_file
from _shared.significance import full_significance_report, print_significance_report

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)

MOMENTUM_THRESHOLD = 1.5
MAX_QUIVER_DELAY   = 3
INITIAL_CAPITAL    = 100_000
MAX_PCT_PER_TRADE  = 0.10
SAVE_NAME          = "congress_momentum_quiver_open"

_local = '/tmp/final_data_MEGA.pkl'
DATA_PKL = _local if os.path.exists(_local) else data_file('congress_quiver', 'final_data_MEGA.pkl')

print(f"Loading {DATA_PKL} ...")
with open(DATA_PKL, 'rb') as f:
    data = pickle.load(f)
final_df   = data['congresist_df_dict']
stock_dict = data['stock_dict']
print(f"Trades: {len(final_df):,} | Tickers: {len(stock_dict):,} | Politicians: {final_df['Name'].nunique()}")

df = final_df.copy()
df['Filed']              = pd.to_datetime(df['Filed'])
df['Quiver_Upload_Time'] = pd.to_datetime(df['Quiver_Upload_Time'])
df['Quiver_Upload_Date'] = df['Quiver_Upload_Time'].dt.normalize()

quiver_gap = (df['Quiver_Upload_Date'] - df['Filed']).dt.days.abs()
df = df[quiver_gap <= MAX_QUIVER_DELAY].copy()

df['days_to_file_nz'] = df['days_to_file'].replace(0, np.nan)
df['Annualized_Traded_To_File'] = (1 + df['Return_Traded_To_File']) ** (365 / df['days_to_file_nz']) - 1
df_filtered = df[(df['Transaction'] == 'Purchase') &
                 (df['Annualized_Traded_To_File'] > MOMENTUM_THRESHOLD)].copy()
print(f"After delay filter: {len(df):,} | after momentum filter: {len(df_filtered):,}")

# ── Vectorized open->close return on/after upload date ───────────────────────
print("Preprocessing price frames...")
prepped = {}
for tk, s in stock_dict.items():
    s = s[['timestamp', 'open', 'close']].copy()
    ts = pd.to_datetime(s['timestamp'])
    if getattr(ts.dt, 'tz', None) is not None:
        ts = ts.dt.tz_localize(None)
    s['d'] = ts.dt.normalize()
    s = s.sort_values('d')
    prepped[tk] = (s['d'].values, s['open'].values, s['close'].values)

def get_open_to_close(ticker, date):
    if ticker not in prepped:
        return np.nan, np.nan, np.nan
    d, op, cl = prepped[ticker]
    i = np.searchsorted(d, np.datetime64(date))
    if i >= len(d) or op[i] == 0:
        return np.nan, np.nan, np.nan
    return cl[i]/op[i] - 1, op[i], cl[i]

print("Computing QUIVER_OPEN returns...")
res = df_filtered.apply(lambda r: get_open_to_close(r['Ticker'], r['Quiver_Upload_Date']), axis=1)
df_filtered[['return_1d_QUIVER_OPEN', 'px_open', 'px_close']] = pd.DataFrame(res.tolist(), index=df_filtered.index)
df_filtered = df_filtered.dropna(subset=['return_1d_QUIVER_OPEN'])
print(f"Trades with valid returns: {len(df_filtered):,} | mean {df_filtered['return_1d_QUIVER_OPEN'].mean()*100:+.3f}%")

# ── Significance (3-gate on per-trade returns) ──────────────────────────────
trades_sig = pd.DataFrame({'net_pnl': df_filtered['return_1d_QUIVER_OPEN'].values,
                           'equity_before': 1.0, 'position': 'long', 'direction': 'long'})
report = full_significance_report(trades_sig, strategy_name='Congress Momentum QUIVER_OPEN')
print_significance_report(report)

# ── Capital simulation (fixed fraction per trade, sequential by Filed) ──────
df_sim = df_filtered.sort_values('Filed').reset_index(drop=True)
capital = INITIAL_CAPITAL
equity_ts = []
for _, row in df_sim.iterrows():
    capital += capital * MAX_PCT_PER_TRADE * row['return_1d_QUIVER_OPEN']
    equity_ts.append((row['Filed'], capital))
equity = pd.Series(dict(equity_ts)).sort_index()
equity.index = pd.to_datetime(equity.index)

total_days = (equity.index[-1] - equity.index[0]).days
ann_return = (capital / INITIAL_CAPITAL) ** (365 / total_days) - 1
# Business-day grid: sqrt(252) annualization needs ~252 obs/yr; the notebook's
# calendar-D padding (weekend zero rows) deflated Sharpe ~15%. Fixed 2026-07-02.
daily = equity.resample('B').last().ffill()
dr = daily.pct_change().dropna()
sharpe = dr.mean()/dr.std()*np.sqrt(252) if dr.std() > 0 else 0
max_dd = ((equity - equity.cummax())/equity.cummax()).min()
eq_year = equity.resample('YE').last()
per_year = (eq_year.values / eq_year.shift(1).fillna(INITIAL_CAPITAL).values - 1)
print(f"\nFinal ${capital:,.0f} | ann {ann_return:.2%} | Sharpe {sharpe:.2f} | MaxDD {max_dd:.2%} | trades {len(df_sim):,}")
print(f"Positive years: {(per_year > 0).sum()}/{len(per_year)}")

# ── Save ─────────────────────────────────────────────────────────────────────
trades_out = df_filtered.rename(columns={'Quiver_Upload_Date': 'entry_time', 'Ticker': 'instrument',
                                         'return_1d_QUIVER_OPEN': 'pct_return_gross'}).copy()
trades_out['exit_time']   = trades_out['entry_time']
trades_out['direction']   = 'long'
trades_out['entry_price'] = trades_out['px_open']
trades_out['exit_price']  = trades_out['px_close']
trades_out['exit_reason'] = 'eod_close'
trades_out['stop_price']  = np.nan
std_cols = ['entry_time','exit_time','direction','instrument','entry_price','exit_price',
            'pct_return_gross','exit_reason','stop_price']
trades_out[std_cols].to_csv(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_trades.csv'), index=False)

daily.rename('equity').to_csv(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_daily_equity.csv'), index_label='date')

summary = {
    'strategy': 'Congress Momentum + QUIVER_OPEN', 'portfolio': 'Daily',
    'period': f"{equity.index[0].date()} -> {equity.index[-1].date()}",
    'params': {'momentum_threshold': MOMENTUM_THRESHOLD, 'max_quiver_delay': MAX_QUIVER_DELAY,
               'max_pct_per_trade': MAX_PCT_PER_TRADE},
    'n_trades': int(len(df_sim)),
    'stats': {'ann_return_pct': round(ann_return*100, 2), 'sharpe': round(float(sharpe), 3),
              'maxdd_pct': round(float(max_dd)*100, 2),
              'positive_years': f"{int((per_year > 0).sum())}/{len(per_year)}"},
    'significance': {'verdict': report['verdict'], 'tests_passed': report['tests_passed']},
    'note': 'Live execution requires intraday Quiver API polling; trades uploaded after close not executable same-day.',
}
with open(os.path.join(RESULTS_DIR, f'{SAVE_NAME}_summary.json'), 'w') as f:
    json.dump(summary, f, indent=2, default=str)
print(f"Saved -> {RESULTS_DIR}")
