"""
ibs_mean_reversion_Backtest_multiasset_v2.py
============================================
Multi-asset v2 backtest for IBS Mean Reversion (Daily portfolio).

Canonical two-phase framework (mirrors ema_crossover, adapted to daily bars):
  Phase 1 - per-basket grid search over (ibs_buy, ibs_sell, stop_loss);
            canonical params = max median Sharpe across basket instruments;
            binomial instrument-count test + 3-gate significance on the
            basket composite monthly returns. Passing baskets emit
            trade-level CSVs for every instrument.
  Phase 2 - Bonferroni rescue: for failed baskets, each ticker is
            individually grid-searched and 3-gate tested at alpha = 0.05/N.
            Rescued tickers emit trade CSVs too.

Outputs (canonical layout):
  results/trades/ibs_mean_reversion_v2_trades_{basket}_{ticker}.csv
  results/trades/ibs_mean_reversion_v2_trades_bonferroni_{basket}_{ticker}.csv
  results/ibs_mean_reversion_v2_canonical_params.json   (with _run_info key)
  results/ibs_mean_reversion_v2_bonferroni_results.json
  results/ibs_mean_reversion_v2_backtest_results.csv

Resumable: baskets already present in the canonical params JSON are skipped,
so the script can be re-run until it prints ALL BASKETS DONE.

v2.1 changelog (fable standardization run, 2026-07-02):
  - FIXED ROOT path bug (plan section 0 class 1): old ROOT used two '..' from
    short_term/Daily/<strategy>/ which resolved to short_term/ and made
    DATA_DIR point at a nonexistent short_term/long_term/... path. Paths now
    come from shared.paths (marker-file root discovery + data manifest).
  - Integrated Phase 2 Bonferroni rescue into the main script (previously a
    one-off side file, results/ibs_v2_bonferroni_rescue_bonds_us.json).
  - Emits per-instrument trade CSVs (previously none existed).
  - Canonical params JSON now carries a _run_info string; all readers must
    isinstance-guard (plan section 0 class 3).
"""
import os, sys, json
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp, binom
from itertools import product

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root marker not found'
    _d = _p
sys.path.insert(0, _d)

from _shared.paths import data_dir

DATA_DIR    = data_dir('daily_tickers')
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, 'results')
TRADES_DIR  = os.path.join(RESULTS_DIR, 'trades')
os.makedirs(TRADES_DIR, exist_ok=True)

CANON_PATH = os.path.join(RESULTS_DIR, 'ibs_mean_reversion_v2_canonical_params.json')
BONF_PATH  = os.path.join(RESULTS_DIR, 'ibs_mean_reversion_v2_bonferroni_results.json')
CSV_PATH   = os.path.join(RESULTS_DIR, 'ibs_mean_reversion_v2_backtest_results.csv')

TC       = 0.0005
MIN_DAYS = 252

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "DIA", "MDY", "IVV", "VOO"],
    "us_factor":       ["IWF", "IWD", "MTUM", "USMV", "VTV", "VUG", "DVY", "QUAL"],
    "us_sectors":      ["XLK", "XLC", "XLI", "XLV", "XLY", "XLF", "XLE", "XLU", "XLB", "XLP", "XLRE"],
    "bonds_us":        ["TLT", "IEF", "SHY", "HYG", "LQD"],
    "commodities":     ["GLD", "SLV", "USO", "GDX"],
    "em_regional":     ["EEM", "EWZ", "INDA", "EWW"],
    "intl_liquid":     ["EFA", "EZU", "EWJ", "EWG", "EWU"],
}

PARAM_GRID = {
    'ibs_buy':   [0.1, 0.15, 0.2, 0.25],
    'ibs_sell':  [0.7, 0.75, 0.8, 0.85],
    'stop_loss': [-0.02, -0.03, -0.05, None],
}
param_keys   = list(PARAM_GRID.keys())
param_combos = list(product(*PARAM_GRID.values()))

_cache = {}
def load_ticker(ticker):
    if ticker in _cache:
        return _cache[ticker]
    path = os.path.join(DATA_DIR, f'{ticker}.csv')
    df = None
    if os.path.exists(path):
        d = pd.read_csv(path, parse_dates=['date'], index_col='date').sort_index()
        if all(c in d.columns for c in ['open', 'high', 'low', 'close']):
            d = d[['open', 'high', 'low', 'close']].dropna()
            if len(d) >= MIN_DAYS:
                df = d
    _cache[ticker] = df
    return df

def run_ibs(df, ibs_buy, ibs_sell, stop_loss, collect_trades=False):
    """Return logic identical to the original v2 script (verified by
    reproduction test); optionally also emits discrete trades."""
    op = df['open'].values.astype(float)
    hi = df['high'].values.astype(float)
    lo = df['low'].values.astype(float)
    cl = df['close'].values.astype(float)
    idx = df.index
    n = len(cl)
    rng_ = hi - lo
    ibs = np.where(rng_ > 0, (cl - lo) / rng_, 0.5)
    ibs = np.clip(ibs, 0, 1)
    rets = np.zeros(n, dtype=float)
    trades = []
    in_pos = False
    entry = 0.0
    entry_i = -1
    for i in range(1, n):
        if not in_pos:
            if ibs[i-1] < ibs_buy:
                entry = op[i]; entry_i = i; in_pos = True
                pnl = (cl[i] - entry) / entry
                if stop_loss is not None and pnl <= stop_loss:
                    rets[i] = stop_loss - 2*TC; in_pos = False
                    if collect_trades:
                        trades.append((idx[entry_i], idx[i], entry, entry*(1+stop_loss), entry*(1+stop_loss), 'stop'))
                elif ibs[i] > ibs_sell:
                    rets[i] = pnl - 2*TC; in_pos = False
                    if collect_trades:
                        trades.append((idx[entry_i], idx[i], entry, cl[i], None, 'signal'))
                else:
                    rets[i] = pnl - TC
        else:
            day_ret    = cl[i]/cl[i-1] - 1
            from_entry = (cl[i] - entry)/entry
            if stop_loss is not None and from_entry <= stop_loss:
                stop_px = entry*(1+stop_loss)
                rets[i] = (stop_px/cl[i-1] - 1) - TC; in_pos = False
                if collect_trades:
                    trades.append((idx[entry_i], idx[i], entry, stop_px, stop_px, 'stop'))
            elif ibs[i] > ibs_sell:
                rets[i] = day_ret - TC; in_pos = False
                if collect_trades:
                    trades.append((idx[entry_i], idx[i], entry, cl[i], None, 'signal'))
            else:
                rets[i] = day_ret
    r = pd.Series(rets, index=idx, name='ret')
    if collect_trades:
        tdf = pd.DataFrame(trades, columns=['entry_time','exit_time','entry_price','exit_price','stop_price','exit_reason'])
        return r, tdf
    return r

def sharpe_daily(rets):
    r = rets.dropna()
    if len(r) < 50 or r.std() == 0: return np.nan
    return float(r.mean()/r.std()*np.sqrt(252))

def ttest_p(rets):
    r = rets.dropna()
    if len(r) < 10: return 1.0
    t, p2 = ttest_1samp(r, 0)
    return float(p2/2 if t > 0 else 1.0)

def to_monthly(equity):
    eq = equity.copy()
    if not isinstance(eq.index, pd.DatetimeIndex):
        eq.index = pd.to_datetime(eq.index)
    return eq.resample('ME').last().pct_change().dropna()

def gate2_boot5(mrets, n_boot=3000, seed=42):
    r = mrets.dropna().values
    if len(r) < 6: return -np.inf
    rng = np.random.RandomState(seed)
    sims = []
    for _ in range(n_boot):
        s = rng.choice(r, size=len(r), replace=True)
        sims.append(s.mean()/s.std()*np.sqrt(12) if s.std() > 0 else 0)
    return float(np.percentile(sims, 5))

def gate3_perm(mrets, n_perm=3000, seed=42):
    r = mrets.dropna().values
    if len(r) < 6: return 1.0
    rng = np.random.RandomState(seed)
    obs = r.mean()/r.std()*np.sqrt(12) if r.std() > 0 else 0
    cnt = 0
    for _ in range(n_perm):
        s = r * rng.choice([-1, 1], len(r))
        sh = s.mean()/s.std()*np.sqrt(12) if s.std() > 0 else 0
        if sh >= obs: cnt += 1
    return float(cnt/n_perm)

def three_gates(mrets, alpha=0.05):
    g1, g2, g3 = ttest_p(mrets), gate2_boot5(mrets), gate3_perm(mrets)
    return g1, g2, g3, (g1 < alpha) and (g2 > 0) and (g3 < alpha)

def perf(equity):
    eq = equity.dropna()
    r  = eq.pct_change().dropna()
    sh = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else 0
    years = (eq.index[-1]-eq.index[0]).days/365.25
    c  = float(eq.iloc[-1]/eq.iloc[0])**(1/max(years, 0.5)) - 1
    rm = eq.expanding().max()
    dd = float(((eq-rm)/rm).min())
    return sh, c, dd

def _load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def _save_json(path, obj):
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2)

def emit_trades(tk, basket, params, prefix):
    _, tdf = run_ibs(load_ticker(tk), collect_trades=True, **params)
    tdf['direction']  = 'long'
    tdf['instrument'] = tk
    tdf['basket']     = basket
    cols = ['entry_time','exit_time','entry_price','exit_price','stop_price','direction','instrument','basket','exit_reason']
    out = os.path.join(TRADES_DIR, f'ibs_mean_reversion_v2_trades_{prefix}{basket}_{tk}.csv')
    tdf[cols].to_csv(out, index=False)
    return len(tdf)

def main():
    canonical = _load_json(CANON_PATH)
    bonf      = _load_json(BONF_PATH)
    if '_run_info' not in canonical:
        canonical['_run_info'] = 'fable standardization run 2026-07-02; readers must isinstance-guard non-dict keys'

    done = [b for b in BASKETS if isinstance(canonical.get(b), dict)]
    todo = [b for b in BASKETS if b not in done]
    print(f"Baskets done: {done} | todo: {todo}")

    for basket_name in todo:
        basket_tickers = BASKETS[basket_name]
        print(f"\n[{basket_name}]")
        avail = [tk for tk in basket_tickers if load_ticker(tk) is not None]
        print(f"  Available {len(avail)}/{len(basket_tickers)}: {avail}")
        if len(avail) < 2:
            print("  Too few - skip")
            canonical[basket_name] = {'params': None, 'instruments': avail, 'passes': False, 'note': 'too few instruments'}
            _save_json(CANON_PATH, canonical)
            continue

        best_params, best_med = None, -np.inf
        for combo in param_combos:
            p   = dict(zip(param_keys, combo))
            shs = [sharpe_daily(run_ibs(load_ticker(tk), **p)) for tk in avail]
            shs = [s for s in shs if not np.isnan(s)]
            if not shs: continue
            med = float(np.median(shs))
            if med > best_med: best_med, best_params = med, p
        print(f"  Canonical: {best_params}  (median Sharpe={best_med:.3f})")

        inst_rets = {tk: run_ibs(load_ticker(tk), **best_params) for tk in avail}
        rets_df   = pd.DataFrame(inst_rets).dropna()
        basket_rets = rets_df.mean(axis=1)
        basket_eq   = (1 + basket_rets).cumprod() * 100_000
        mrets       = to_monthly(basket_eq)

        k       = sum(1 for tk in avail if ttest_p(inst_rets[tk]) < 0.05)
        N       = len(avail)
        p_binom = float(1 - binom.cdf(k-1, N, 0.05))
        g1, g2, g3, pass_3g = three_gates(mrets)
        pass_b  = p_binom < 0.05
        passes  = pass_b and pass_3g
        sh, c, mdd = perf(basket_eq)
        print(f"  Sharpe={sh:.3f} CAGR={c*100:.1f}% MaxDD={mdd*100:.1f}% | binom k={k}/{N} p={p_binom:.4f} | gates t={g1:.4f} boot5={g2:.3f} perm={g3:.4f} -> {'PASS' if passes else 'FAIL'}")

        canonical[basket_name] = {
            'params': best_params, 'instruments': avail, 'passes': bool(passes),
            'median_sharpe_grid': round(best_med, 4),
            'stats': {'basket_sharpe': round(sh,4), 'cagr_pct': round(c*100,2), 'maxdd_pct': round(mdd*100,2),
                      'binom_k': k, 'binom_p': round(p_binom,4),
                      'gate1_p': round(g1,4), 'gate2_boot5': round(g2,4), 'gate3_p': round(g3,4)},
        }

        if passes:
            for tk in avail:
                n_tr = emit_trades(tk, basket_name, best_params, '')
                print(f"    trades {tk}: {n_tr}")
        else:
            alpha = 0.05 / N
            print(f"  Phase 2 Bonferroni rescue at alpha={alpha:.5f}")
            bonf.setdefault(basket_name, {})
            for tk in avail:
                bp, bm = None, -np.inf
                for combo in param_combos:
                    p = dict(zip(param_keys, combo))
                    s = sharpe_daily(run_ibs(load_ticker(tk), **p))
                    if not np.isnan(s) and s > bm: bm, bp = s, p
                r  = run_ibs(load_ticker(tk), **bp)
                eq = (1 + r).cumprod() * 100_000
                mr = to_monthly(eq)
                g1t, g2t, g3t, ok = three_gates(mr, alpha)
                bonf[basket_name][tk] = {
                    'params': bp, 'sharpe': round(bm, 4), 'rescued': bool(ok),
                    'gate1_p': round(g1t,4), 'gate2_boot5': round(g2t,4), 'gate3_p': round(g3t,4), 'alpha': alpha,
                }
                print(f"    {tk}: Sharpe={bm:.2f} t={g1t:.4f} boot5={g2t:.3f} perm={g3t:.4f} -> {'RESCUED' if ok else 'no'}")
                if ok:
                    emit_trades(tk, basket_name, bp, 'bonferroni_')
            _save_json(BONF_PATH, bonf)

        _save_json(CANON_PATH, canonical)

    rows = []
    for b, meta in canonical.items():
        if not isinstance(meta, dict) or meta.get('params') is None: continue
        rows.append({'basket': b, **meta['params'], 'passes': meta['passes'],
                     'median_sharpe_grid': meta.get('median_sharpe_grid'), **meta.get('stats', {})})
    pd.DataFrame(rows).to_csv(CSV_PATH, index=False)
    if not todo:
        print("\nALL BASKETS DONE")
    print(f"Saved -> {RESULTS_DIR}")

if __name__ == '__main__':
    main()
