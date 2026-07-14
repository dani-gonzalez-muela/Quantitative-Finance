"""
EMA Crossover — Multi-Asset Backtest v2
Phase 1: Per-basket grid search over (fast_ema, slow_ema, stop_val)
Canonical params = max median Sharpe across instruments in basket.
3-gate significance test (t-test, bootstrap Sharpe, permutation).
Phase 2: For passing baskets, emit trade-level CSVs for Implementation sizing.

Outputs:
  results/ema_crossover_v2_backtest_results.csv
  results/ema_crossover_v2_canonical_params.json
  results/trades/ema_crossover_v2_trades_{basket}_{ticker}.csv  (passing baskets only)
"""
import os, sys, json, warnings, itertools
import numpy as np
import pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, ROOT)
# -- fable data-manifest bootstrap (Phase E consolidation) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
if _bd not in _sys.path:
    _sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
DATA_DIR = data_dir('intraday_5min')
OUT_DIR  = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(OUT_DIR, exist_ok=True)

from _shared.fees import calculate_fees_pct

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

PARAM_GRID = list(itertools.product(
    [8, 13, 21],
    [34, 48, 55],
    [0.03, 0.05, 0.07],
))
PARAM_GRID = [(f, s, v) for f, s, v in PARAM_GRID if f < s]


def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path): return None
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    return df[['open','high','low','close','volume']].sort_index()


def run_ema_fast(df5, fast_ema, slow_ema, stop_val, return_trades=False):
    """
    Vectorized EMA crossover.
    If return_trades=True, returns (daily_rets, trades_df) where trades_df has columns:
      entry_time, exit_time, entry_price, exit_price, stop_price, direction
    Otherwise returns daily_rets Series only.
    """
    # Compute EMAs on ALL bars before RTH filter (no lookahead)
    df_all = df5.copy()
    df_all['ema_fast']  = df_all['close'].ewm(span=fast_ema, adjust=False).mean()
    df_all['ema_slow']  = df_all['close'].ewm(span=slow_ema, adjust=False).mean()
    df_all['ema_trend'] = df_all['close'].ewm(span=200,      adjust=False).mean()

    df = df_all.between_time('09:30','15:55').copy()
    long_sig  = (df['ema_fast'] > df['ema_slow']) & (df['ema_slow'] > df['ema_trend'])
    short_sig = (df['ema_fast'] < df['ema_slow']) & (df['ema_slow'] < df['ema_trend'])
    # Shift signal by 1 bar — no lookahead
    sig_raw = np.where(long_sig, 1, np.where(short_sig, -1, 0))
    sig = np.empty_like(sig_raw); sig[0] = 0; sig[1:] = sig_raw[:-1]

    df['date'] = df.index.normalize()
    # Proper True Range ATR
    daily = df.groupby('date').agg(high=('high','max'), low=('low','min'), close=('close','last'))
    tr = pd.DataFrame({
        'hl': daily['high'] - daily['low'],
        'hc': (daily['high'] - daily['close'].shift(1)).abs(),
        'lc': (daily['low']  - daily['close'].shift(1)).abs(),
    }).max(axis=1)
    atr14 = tr.ewm(span=14, adjust=False).mean().shift(1)
    df['atr14'] = df['date'].map(atr14.to_dict())
    df.dropna(subset=['atr14','ema_fast','ema_slow','ema_trend'], inplace=True)

    daily_rets = {}
    trades_list = [] if return_trades else None
    position  = 0
    entry_px  = 0.0
    stop_px   = 0.0
    direction = ''
    entry_time = None
    cur_date  = None
    day_pnl   = 0.0

    timestamps = df.index
    opens  = df['open'].values
    highs  = df['high'].values
    lows   = df['low'].values
    closes = df['close'].values
    atrs   = df['atr14'].values
    dates  = df.index.date
    sigs   = sig[-len(df):]
    n = len(df)

    for i in range(n):
        d = dates[i]
        if cur_date is None: cur_date = d

        # EOD force-close at day boundary
        if d != cur_date:
            if position != 0:
                close_p = closes[i-1]
                gross = position * (close_p - entry_px) / entry_px
                day_pnl += gross - calculate_fees_pct(entry_px, close_p, direction)
                if return_trades:
                    trades_list.append({'entry_time': entry_time, 'exit_time': timestamps[i-1],
                                        'entry_price': entry_px, 'exit_price': close_p,
                                        'stop_price': stop_px, 'direction': direction})
                position = 0
            daily_rets[cur_date] = day_pnl
            day_pnl = 0.0; cur_date = d

        atr_val = atrs[i]; s = sigs[i]

        if position == 0:
            if s == 1:
                position = 1; direction = 'long'
                entry_px = opens[i]; stop_px = entry_px - stop_val * atr_val
                if return_trades: entry_time = timestamps[i]
            elif s == -1:
                position = -1; direction = 'short'
                entry_px = opens[i]; stop_px = entry_px + stop_val * atr_val
                if return_trades: entry_time = timestamps[i]
        elif position == 1:
            if lows[i] <= stop_px:
                gross = (stop_px - entry_px) / entry_px
                day_pnl += gross - calculate_fees_pct(entry_px, stop_px, 'long')
                if return_trades:
                    trades_list.append({'entry_time': entry_time, 'exit_time': timestamps[i],
                                        'entry_price': entry_px, 'exit_price': stop_px,
                                        'stop_price': stop_px, 'direction': 'long'})
                position = 0
        elif position == -1:
            if highs[i] >= stop_px:
                gross = (entry_px - stop_px) / entry_px
                day_pnl += gross - calculate_fees_pct(entry_px, stop_px, 'short')
                if return_trades:
                    trades_list.append({'entry_time': entry_time, 'exit_time': timestamps[i],
                                        'entry_price': entry_px, 'exit_price': stop_px,
                                        'stop_price': stop_px, 'direction': 'short'})
                position = 0

    # final close last day
    if cur_date is not None:
        if position != 0:
            gross = position * (closes[-1] - entry_px) / entry_px
            day_pnl += gross - calculate_fees_pct(entry_px, closes[-1], direction)
            if return_trades:
                trades_list.append({'entry_time': entry_time, 'exit_time': timestamps[-1],
                                    'entry_price': entry_px, 'exit_price': closes[-1],
                                    'stop_price': stop_px, 'direction': direction})
        daily_rets[cur_date] = day_pnl

    rets_series = pd.Series(daily_rets)
    if return_trades:
        trades_df = pd.DataFrame(trades_list) if trades_list else pd.DataFrame(
            columns=['entry_time','exit_time','entry_price','exit_price','stop_price','direction'])
        return rets_series, trades_df
    return rets_series


def sharpe(rets):
    if len(rets) < 30: return np.nan
    m, s = rets.mean(), rets.std()
    return m / s * np.sqrt(252) if s > 0 else np.nan

def ttest_p(rets):
    if len(rets) < 10: return 1.0
    t, p = stats.ttest_1samp(rets.dropna(), 0)
    return p / 2 if t > 0 else 1.0

def binomial_test(k, n, p0=0.05):
    return 1 - stats.binom.cdf(k - 1, n, p0)

def bootstrap_sharpe_5th(rets, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed); r = rets.values
    return np.percentile([sharpe(pd.Series(rng.choice(r, size=len(r), replace=True))) for _ in range(n_boot)], 5)

def permutation_p(rets, n_perm=1000, seed=42):
    rng = np.random.default_rng(seed); obs = sharpe(rets); r = rets.values
    return sum(sharpe(pd.Series(rng.permutation(r)*np.sign(rng.uniform(-1,1,len(r))))) >= obs for _ in range(n_perm)) / n_perm

def three_gate(monthly_rets, alpha=0.05):
    if len(monthly_rets) < 12: return False, {}
    p_t = ttest_p(monthly_rets); boot5 = bootstrap_sharpe_5th(monthly_rets); perm_p = permutation_p(monthly_rets)
    return (p_t < alpha) and (boot5 > 0) and (perm_p < alpha), {'t_p': p_t, 'boot5_sharpe': boot5, 'perm_p': perm_p}


BONFERRONI_ALPHA = {b: 0.05 / len(t) for b, t in BASKETS.items()}


def run_bonferroni_rescue(basket_name, ticker_data, trades_dir):
    """
    Per-ticker rescue for a failed basket.
    For each ticker: find best params (max Sharpe), apply 3-gate at Bonferroni alpha.
    Saves trade CSV for rescued tickers. Returns list of result dicts.
    """
    alpha = BONFERRONI_ALPHA[basket_name]
    results = []

    for ticker, df5 in ticker_data.items():
        # Find best params for this ticker
        best_sh, best_params, best_rets = -np.inf, None, None
        for fast, slow, sv in PARAM_GRID:
            try:
                rets = run_ema_fast(df5, fast, slow, sv)
                sh = sharpe(rets)
                if sh > best_sh:
                    best_sh = sh; best_params = (fast, slow, sv); best_rets = rets
            except: continue

        if best_params is None or best_rets is None:
            results.append({'ticker': ticker, 'pass': False, 'reason': 'no valid params'})
            continue

        fast, slow, sv = best_params
        try:
            monthly = best_rets.resample('ME').apply(lambda r: (1+r).prod()-1)
        except (ValueError, TypeError):
            monthly = best_rets.resample('M').apply(lambda r: (1+r).prod()-1)

        gate_pass, gate_stats = three_gate(monthly, alpha=alpha)
        result = {
            'ticker': ticker, 'pass': bool(gate_pass),
            'fast_ema': int(fast), 'slow_ema': int(slow), 'stop_val': float(sv),
            'sharpe': round(float(best_sh), 4),
            'bonferroni_alpha': round(alpha, 6),
            'gate_stats': gate_stats,
        }

        if gate_pass:
            try:
                _, trades_df = run_ema_fast(df5, fast, slow, sv, return_trades=True)
                if not trades_df.empty:
                    trades_df['instrument'] = ticker
                    trades_df['basket'] = basket_name
                    out_path = os.path.join(trades_dir,
                        f'ema_crossover_v2_trades_bonferroni_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    result['trades_file'] = os.path.basename(out_path)
                    print(f"    {ticker}: RESCUED Sharpe={best_sh:.4f} (alpha={alpha:.4f}) | {len(trades_df)} trades")
            except Exception as e:
                print(f"    {ticker}: trade save error — {e}")
        else:
            print(f"    {ticker}: fail (best Sharpe={best_sh:.4f}, alpha={alpha:.4f})")

        results.append(result)

    return results


def main():
    all_results = []; canonical = {}; ticker_data_cache = {}
    TRADES_DIR = os.path.join(OUT_DIR, 'trades')
    os.makedirs(TRADES_DIR, exist_ok=True)

    # ── Phase 1: basket-level grid search + 3-gate ────────────────────────────
    for basket_name, tickers in BASKETS.items():
        print(f"\n{'='*60}\nBasket: {basket_name}  ({len(tickers)} tickers)")

        ticker_data = {}
        for ticker in tickers:
            df5 = load_5min(ticker)
            if df5 is None: print(f"  {ticker}: no data"); continue
            n_days = df5.index.normalize().nunique()
            if n_days < MIN_DAYS: print(f"  {ticker}: only {n_days} days, skip"); continue
            ticker_data[ticker] = df5
        if not ticker_data: continue
        ticker_data_cache[basket_name] = ticker_data

        param_sharpes = {}
        for fast, slow, sv in PARAM_GRID:
            shs = []
            for ticker, df5 in ticker_data.items():
                try: shs.append(sharpe(run_ema_fast(df5, fast, slow, sv)))
                except: continue
            if shs: param_sharpes[(fast, slow, sv)] = np.median(shs)
        if not param_sharpes: continue

        canon = max(param_sharpes, key=param_sharpes.get)
        canon_fast, canon_slow, canon_sv = canon
        print(f"  Canonical: fast={canon_fast} slow={canon_slow} sv={canon_sv} (median Sharpe={param_sharpes[canon]:.4f})")

        ticker_rets = {}; t_pvals = []
        for ticker, df5 in ticker_data.items():
            try:
                rets = run_ema_fast(df5, canon_fast, canon_slow, canon_sv)
                ticker_rets[ticker] = rets; t_pvals.append(ttest_p(rets))
                all_results.append({'basket': basket_name, 'ticker': ticker,
                                     'fast_ema': canon_fast, 'slow_ema': canon_slow, 'stop_val': canon_sv,
                                     'sharpe': sharpe(rets)})
            except: continue

        N = len(ticker_rets); k = sum(p < 0.05 for p in t_pvals)
        binom_p = binomial_test(k, N) if k > 0 else 1.0
        print(f"  Binomial test: k={k}/{N} -> p={binom_p:.4f}", "PASS" if binom_p < 0.05 else "fail")

        aligned = pd.DataFrame(ticker_rets).fillna(0)
        basket_rets = aligned.mean(axis=1)
        basket_rets.index = pd.to_datetime(basket_rets.index)
        try:
            monthly = basket_rets.resample('ME').apply(lambda r: (1+r).prod()-1)
        except (ValueError, TypeError):
            monthly = basket_rets.resample('M').apply(lambda r: (1+r).prod()-1)
        gate_pass, gate_stats = three_gate(monthly)
        print(f"  3-gate: {gate_pass} | {gate_stats}")

        canonical[basket_name] = {
            'fast_ema': int(canon_fast), 'slow_ema': int(canon_slow), 'stop_val': float(canon_sv),
            'binom_p': float(binom_p), 'binom_pass': bool(binom_p < 0.05),
            'gate_pass': bool(gate_pass), 'gate_stats': gate_stats,
            'n_tickers': N, 'k_significant': int(k),
        }

        # Emit trade CSVs for passing baskets (at basket canonical params)
        if gate_pass:
            print(f"  Saving basket trades for {basket_name}...")
            for ticker, df5 in ticker_data.items():
                try:
                    _, trades_df = run_ema_fast(df5, canon_fast, canon_slow, canon_sv, return_trades=True)
                    if trades_df.empty: continue
                    trades_df['instrument'] = ticker; trades_df['basket'] = basket_name
                    out_path = os.path.join(TRADES_DIR, f'ema_crossover_v2_trades_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    print(f"    {ticker}: {len(trades_df)} trades saved")
                except Exception as e:
                    print(f"    {ticker}: trade save error — {e}")

    pd.DataFrame(all_results).to_csv(os.path.join(OUT_DIR, 'ema_crossover_v2_backtest_results.csv'), index=False)
    with open(os.path.join(OUT_DIR, 'ema_crossover_v2_canonical_params.json'), 'w') as f:
        json.dump(canonical, f, indent=2)

    # ── Phase 2: Bonferroni rescue on failed baskets ──────────────────────────
    print(f"\n{'='*60}\nPhase 2 — Bonferroni Rescue")
    failed = [b for b, c in canonical.items() if not c['gate_pass']]
    bonferroni_results = {
        'methodology': 'per-ticker 3-gate at alpha=0.05/N per basket',
        'baskets': {}, 'rescued_tickers': [],
    }
    all_rescued = []
    for basket_name in failed:
        if basket_name not in ticker_data_cache: continue
        print(f"\n  {basket_name} (alpha={BONFERRONI_ALPHA[basket_name]:.4f}):")
        results = run_bonferroni_rescue(basket_name, ticker_data_cache[basket_name], TRADES_DIR)
        bonferroni_results['baskets'][basket_name] = results
        rescued = [r['ticker'] for r in results if r.get('pass')]
        all_rescued.extend(rescued)
    bonferroni_results['rescued_tickers'] = all_rescued

    bonf_path = os.path.join(OUT_DIR, 'ema_crossover_v2_bonferroni_results.json')
    with open(bonf_path, 'w') as f:
        json.dump(bonferroni_results, f, indent=2)

    print(f"\n-- Summary --")
    for b, c in canonical.items():
        print(f"  {b}: gate={'PASS' if c['gate_pass'] else 'fail'}  k={c['k_significant']}/{c['n_tickers']}")
    print(f"Bonferroni rescued: {all_rescued if all_rescued else 'none'}")
    print(f"Outputs: {OUT_DIR}")

if __name__ == '__main__':
    main()
