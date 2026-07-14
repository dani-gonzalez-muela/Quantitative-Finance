"""
build_portfolio_a_v3.py
Builds Portfolio A v3. Overnight equity CSVs have gaps on days without
a complete 3-session bar (e.g. EWW misses ~1160 trading days).
Fix: load equity, ffill to full trading calendar, then compute returns.
"""
import sys, os, json
import numpy as np
import pandas as pd

ROOT     = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
ST       = os.path.join(ROOT, 'short_term')
LT       = os.path.join(ROOT, 'long_term')
PORT_DIR = os.path.join(ROOT, 'portfolio_creation', 'PORTFOLIO_A_V3')
os.makedirs(PORT_DIR, exist_ok=True)


def load_raw_equity(path):
    """Load equity CSV; return equity Series indexed by date (no return computation yet)."""
    df = pd.read_csv(path)
    date_candidates = [c for c in df.columns if 'date' in c.lower() or c == '' or c.startswith('Unnamed')]
    date_col = date_candidates[0] if date_candidates else df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    df.index.name = 'date'
    eq_col = df.select_dtypes(include=[np.number]).columns[0]
    return df[eq_col].dropna()


def equity_to_returns(eq, ref_calendar=None):
    """Convert equity series to returns; if ref_calendar given, ffill equity first."""
    if ref_calendar is not None:
        # Restrict to dates that overlap
        start = max(eq.index[0], ref_calendar[0])
        end   = min(eq.index[-1], ref_calendar[-1])
        cal   = ref_calendar[(ref_calendar >= start) & (ref_calendar <= end)]
        eq    = eq.reindex(eq.index.union(cal)).sort_index().ffill()
        eq    = eq.reindex(cal)
    return eq.pct_change().fillna(0)


def calc_stats(rets, label=''):
    r = rets.dropna()
    active = r[r != 0]
    if len(active) < 30 or active.std() == 0:
        sharpe = float('nan')
    else:
        sharpe = float(r.mean() / active.std() * np.sqrt(252))
    eq   = (1 + r).cumprod()
    yrs  = (r.index[-1] - r.index[0]).days / 365.25
    cagr = float(eq.iloc[-1]) ** (1 / max(yrs, 0.5)) - 1
    peak = eq.expanding().max()
    mdd  = float(((eq - peak) / peak).min())
    calmar = cagr / abs(mdd) if mdd != 0 else float('nan')
    return {'label': label, 'sharpe': round(sharpe, 4), 'cagr': round(cagr, 4),
            'max_dd': round(mdd, 4), 'calmar': round(calmar, 4),
            'n_days': len(r), 'start': str(r.index[0].date()), 'end': str(r.index[-1].date())}


# ── Load raw equities ─────────────────────────────────────────────────────
print("Loading raw equities...")
raw = {}
raw['EMA']       = load_raw_equity(os.path.join(ST,'ema_crossover','results','ema_crossover_daily_equity','intraday_asset_vol_2pct_14d_1x_max.csv'))
raw['IMOM']      = load_raw_equity(os.path.join(ST,'intraday_momentum','results','intraday_momentum_daily_equity','intraday_asset_vol_2pct_14d_1x_max.csv'))
raw['ORB_QQQ']   = load_raw_equity(os.path.join(ST,'orb','results','orb_per_ticker_equity','QQQ.csv'))
raw['ORB_MDY']   = load_raw_equity(os.path.join(ST,'orb','results','orb_per_ticker_equity','MDY.csv'))
raw['ORB_MTUM']  = load_raw_equity(os.path.join(ST,'orb','results','orb_per_ticker_equity','MTUM.csv'))
raw['VWAP_MTUM'] = load_raw_equity(os.path.join(ST,'vwap_trend','results','vwap_trend_v2_per_ticker_equity','MTUM.csv'))
raw['VWAP_EWW']  = load_raw_equity(os.path.join(ST,'vwap_trend','results','vwap_trend_v2_per_ticker_equity','EWW.csv'))
on_tickers = ['SPY','QQQ','IWM','MDY','EEM','EWZ','INDA','EWW']
ON_DIR = os.path.join(ST,'overnight','results','overnight_v1window_per_ticker_equity')
for tk in on_tickers:
    raw[f'ON_{tk}'] = load_raw_equity(os.path.join(ON_DIR, f'{tk}.csv'))
raw['IBS_v2']  = load_raw_equity(os.path.join(ST,'ibs_mean_reversion','results','ibs_mean_reversion_v2_multiasset_daily_equity','combined_equity.csv'))
raw['IBS_v1']  = load_raw_equity(os.path.join(ST,'ibs_mean_reversion','results','ibs_mean_reversion_daily_equity','asset_vol_10pct_1x.csv'))
raw['TFT']     = load_raw_equity(os.path.join(LT,'timing','congress_trade_for_trade','results','congress_trade_for_trade_daily_equity','total_nav_3pct_d180_min30d_1x.csv'))
raw['Quiver']  = load_raw_equity(os.path.join(ST,'congress_momentum','results','congress_momentum_quiver_open_daily_equity','quiver_open_10pct_1x.csv'))

# Build reference trading calendar from EMA (most complete)
ref_cal = raw['EMA'].index

print("\nRaw series date ranges:")
for name, s in raw.items():
    print(f"  {name:12s}: {s.index[0].date()} to {s.index[-1].date()}  ({len(s)} rows)")

# ── Convert to returns using ref_calendar for overnight (fills gaps) ──────
rets = {}
on_keys = {f'ON_{tk}' for tk in on_tickers}
for name, eq in raw.items():
    if name in on_keys:
        # overnight: ffill to full calendar to handle sparse session dates
        rets[name] = equity_to_returns(eq, ref_calendar=ref_cal)
    else:
        rets[name] = equity_to_returns(eq)

# ── Find common date range (intersection) ────────────────────────────────
common_idx = None
for s in rets.values():
    common_idx = s.index if common_idx is None else common_idx.intersection(s.index)
common_idx = common_idx.sort_values()
print(f"\nCommon date range: {common_idx[0].date()} to {common_idx[-1].date()} ({len(common_idx)} trading days)")

aligned = {name: s.reindex(common_idx).fillna(0) for name, s in rets.items()}
df = pd.DataFrame(aligned)

# ── Build composites ──────────────────────────────────────────────────────
df['ORB_composite']       = df[['ORB_QQQ','ORB_MDY','ORB_MTUM']].mean(axis=1)
df['VWAP_composite']      = df[['VWAP_MTUM','VWAP_EWW']].mean(axis=1)
df['intraday_composite']  = df[['EMA','IMOM','ORB_composite','VWAP_composite']].mean(axis=1)
on_cols = [f'ON_{tk}' for tk in on_tickers]
df['overnight_composite'] = df[on_cols].mean(axis=1)
df['Bucket_A']            = df['intraday_composite'] + df['overnight_composite']
df['Bucket_B']            = df[['IBS_v2','IBS_v1','TFT','Quiver']].mean(axis=1)
df['Portfolio']           = 0.5 * df['Bucket_A'] + 0.5 * df['Bucket_B']

# ── Stats ─────────────────────────────────────────────────────────────────
stat_cols = [
    ('Portfolio',          'Portfolio A v3'),
    ('Bucket_A',           'Bucket A'),
    ('intraday_composite', 'Intraday Composite'),
    ('overnight_composite','Overnight Composite'),
    ('Bucket_B',           'Bucket B'),
    ('EMA',                'EMA Crossover'),
    ('IMOM',               'Intraday Momentum'),
    ('ORB_composite',      'ORB Composite'),
    ('VWAP_composite',     'VWAP Composite'),
    ('ORB_QQQ',            'ORB QQQ'),
    ('ORB_MDY',            'ORB MDY'),
    ('ORB_MTUM',           'ORB MTUM'),
    ('VWAP_MTUM',          'VWAP MTUM'),
    ('VWAP_EWW',           'VWAP EWW'),
    ('ON_SPY',             'Overnight SPY'),
    ('ON_QQQ',             'Overnight QQQ'),
    ('ON_IWM',             'Overnight IWM'),
    ('ON_MDY',             'Overnight MDY'),
    ('ON_EEM',             'Overnight EEM'),
    ('ON_EWZ',             'Overnight EWZ'),
    ('ON_INDA',            'Overnight INDA'),
    ('ON_EWW',             'Overnight EWW'),
    ('IBS_v2',             'IBS v2'),
    ('IBS_v1',             'IBS v1'),
    ('TFT',                'TFT Congress'),
    ('Quiver',             'Quiver Congress'),
]
all_stats = {col: calc_stats(df[col], label) for col, label in stat_cols}

bucket_a_cols = ['EMA','IMOM','ORB_composite','VWAP_composite','overnight_composite']
corr_matrix = df[bucket_a_cols].corr().round(3)

# ── Save outputs ──────────────────────────────────────────────────────────
def save_equity(rets, filename, start_nav=100_000.0):
    eq = (1 + rets).cumprod() * start_nav
    out = eq.reset_index()
    out.columns = ['date', 'equity']
    out['date'] = out['date'].dt.strftime('%Y-%m-%d')
    path = os.path.join(PORT_DIR, filename)
    out.to_csv(path, index=False)
    print(f"Saved: {path}")

save_equity(df['Portfolio'],           'portfolio_a_v3_combined_equity.csv')
save_equity(df['Bucket_A'],            'portfolio_a_v3_bucket_a_equity.csv')
save_equity(df['intraday_composite'],  'portfolio_a_v3_bucket_a_intraday_equity.csv')
save_equity(df['overnight_composite'], 'portfolio_a_v3_bucket_a_overnight_equity.csv')
save_equity(df['Bucket_B'],            'portfolio_a_v3_bucket_b_equity.csv')

strat_ret_cols = ['EMA','IMOM','ORB_composite','VWAP_composite','intraday_composite',
                  'overnight_composite','Bucket_A','Bucket_B','Portfolio',
                  'IBS_v2','IBS_v1','TFT','Quiver'] + on_cols
strat_df = df[strat_ret_cols].copy()
strat_df.index.name = 'date'
strat_df.index = strat_df.index.strftime('%Y-%m-%d')
strat_df.to_csv(os.path.join(PORT_DIR, 'portfolio_a_v3_strategy_returns.csv'))
print(f"Saved: {os.path.join(PORT_DIR, 'portfolio_a_v3_strategy_returns.csv')}")

json_out = {
    'portfolio': 'Portfolio A v3',
    'date_range': {'start': str(common_idx[0].date()), 'end': str(common_idx[-1].date())},
    'n_common_days': len(common_idx),
    'stats': all_stats,
    'bucket_a_correlations': corr_matrix.to_dict(),
    'issues': [
        'ON_EWW sparse: 1455/2615 session-complete days; gaps filled with 0-return via ffill.',
        'ON_MDY sparse: 1786/2615 session-complete days; same fix applied.',
        'Common end truncated to 2025-06-26 by Quiver (ends 2025-08-13) and TFT (ends 2025-07-02).',
    ]
}
json_path = os.path.join(PORT_DIR, 'portfolio_a_v3_stats.json')
with open(json_path, 'w') as f:
    json.dump(json_out, f, indent=2)
print(f"Saved: {json_path}")

# ── Print report ──────────────────────────────────────────────────────────
print("\n" + "="*75)
print("PORTFOLIO A V3 — STATS")
print("="*75)
print(f"Common date range: {common_idx[0].date()} to {common_idx[-1].date()} ({len(common_idx)} trading days)\n")
print(f"{'Strategy':<25} {'Sharpe':>7} {'CAGR':>8} {'MaxDD':>8} {'Calmar':>8}")
print("-"*60)
for col, label in stat_cols:
    s = all_stats[col]
    sh = f"{s['sharpe']:.4f}" if not (s['sharpe'] != s['sharpe']) else "  nan"
    cal = f"{s['calmar']:.4f}" if not (s['calmar'] != s['calmar']) else "  nan"
    print(f"{label:<25} {sh:>7} {s['cagr']*100:>7.2f}% {s['max_dd']*100:>7.2f}% {cal:>8}")

print("\n" + "="*75)
print("BUCKET A CORRELATIONS (EMA, IMOM, ORB, VWAP, Overnight)")
print("="*75)
print(corr_matrix.to_string())
print("\nData issues:")
for issue in json_out['issues']:
    print(f"  - {issue}")
print("\nDone.")
