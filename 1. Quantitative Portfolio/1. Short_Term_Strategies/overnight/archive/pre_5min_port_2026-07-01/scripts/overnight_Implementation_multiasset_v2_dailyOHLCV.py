"""
overnight_Implementation_multiasset_v2.py
==========================================
Multi-asset v2 implementation for Overnight Premium.
1/N across instruments within basket, 1/N across passing baskets.
"""
import os, sys, json
import numpy as np
import pandas as pd

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR    = os.path.join(ROOT, 'long_term', 'multi_asset_expansion', 'data', 'tickers')
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
OUT_DIR     = os.path.join(RESULTS_DIR, 'overnight_v2_multiasset_daily_equity')
os.makedirs(OUT_DIR, exist_ok=True)
TC = 0.0001

PARAMS_PATH = os.path.join(RESULTS_DIR, 'overnight_v2_canonical_params.json')
if not os.path.exists(PARAMS_PATH):
    raise FileNotFoundError(f"Run backtest first: {PARAMS_PATH}")
with open(PARAMS_PATH) as f:
    canonical_meta = json.load(f)

passing_baskets = {k: v for k, v in canonical_meta.items() if v['passes']}
print(f"\nPassing baskets: {list(passing_baskets.keys())}")
if not passing_baskets:
    print("No baskets passed — exiting"); raise SystemExit(0)

def load_ticker(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}.csv')
    if not os.path.exists(path): return None
    df = pd.read_csv(path, parse_dates=['date'], index_col='date')
    df.index = pd.to_datetime(df.index)
    return df[['open','close']].dropna().sort_index()

def run_overnight(df, filter_threshold):
    op = df['open'].values.astype(float); cl = df['close'].values.astype(float)
    n  = len(cl); rets = np.zeros(n, dtype=float)
    for i in range(1, n):
        intraday = (cl[i-1] - op[i-1]) / op[i-1]
        if filter_threshold is None or intraday < filter_threshold:
            rets[i] = (op[i]/cl[i-1]-1) - 2*TC
    return pd.Series(rets, index=df.index, name='ret')

def perf(equity):
    eq = equity.dropna(); r = eq.pct_change().dropna()
    sh = r.mean()/r.std()*np.sqrt(252) if r.std()>0 else 0
    years = (eq.index[-1]-eq.index[0]).days/365.25
    c  = float(eq.iloc[-1]/eq.iloc[0])**(1/max(years,0.5))-1
    rm = eq.expanding().max(); dd = float(((eq-rm)/rm).min())
    return sh, c, dd

basket_equities = {}
for basket_name, meta in passing_baskets.items():
    p = meta['params']; threshold = p.get('filter_threshold')
    instruments = meta['instruments']
    print(f"\n[{basket_name}] threshold={threshold}, instruments={instruments}")

    inst_rets = {}
    for tk in instruments:
        df = load_ticker(tk)
        if df is None: print(f"  WARNING: {tk} not found"); continue
        inst_rets[tk] = run_overnight(df, filter_threshold=threshold)

    if not inst_rets: continue
    rets_df = pd.DataFrame(inst_rets).fillna(0)
    basket_ret = rets_df.mean(axis=1)
    basket_eq  = (1 + basket_ret).cumprod() * 100_000
    basket_equities[basket_name] = basket_eq
    sh, c, mdd = perf(basket_eq)
    print(f"  Sharpe={sh:.3f}  CAGR={c*100:.1f}%  MaxDD={mdd*100:.1f}%")
    if sh < 0: print(f"  WARNING: negative Sharpe")
    if mdd < -0.50: print(f"  WARNING: MaxDD > -50%")

if not basket_equities:
    print("No valid baskets"); raise SystemExit(1)

basket_rets_df = pd.DataFrame({k: eq.pct_change() for k, eq in basket_equities.items()}).fillna(0)
combined_ret   = basket_rets_df.mean(axis=1)
combined_eq    = (1 + combined_ret).cumprod() * 100_000
combined_eq.name = 'equity'

sh, c, mdd = perf(combined_eq)
print(f"\nCombined: Sharpe={sh:.4f}  CAGR={c*100:.2f}%  MaxDD={mdd*100:.2f}%")
print(f"Period: {combined_eq.index[0].date()} → {combined_eq.index[-1].date()}")

assert sh > 0, f"Sharpe negative: {sh}"
assert mdd > -0.50, f"MaxDD > -50%: {mdd*100:.1f}%"
assert combined_eq.min() > 0, "Equity went negative"
print("✓ All validation checks passed")

out_path = os.path.join(OUT_DIR, 'combined_equity.csv')
combined_eq.to_csv(out_path, index_label='date')
print(f"Saved → {out_path}")
