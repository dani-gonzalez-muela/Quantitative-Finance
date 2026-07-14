"""
Intraday Momentum — Multi-Asset Backtest v2
Signal: checkpoint breaks (every 30-min from 10:00 to 15:30) vs rolling noise bands
Grid: lookback [8,10,14,21], vol_multiplier [0.5, 1.0, 1.5, 2.0]
V2 fully rewrites run_intraday_momentum to match v1 generate_signals (fast_alpha=True):
  - Price-based boundaries: upper = ref_upper*(1+vol_mult*sigma)
  - Trailing stop at each checkpoint
  - Fast alpha entry/exit
  - Reversal logic
  - Fees via shared/fees.py

Phase 1: Per-basket grid search, 3-gate significance test on passing baskets,
trade-level CSVs emitted for passing-basket tickers (canonical params).
Phase 2: Bonferroni rescue on failed baskets (per-ticker grid search at
alpha=0.05/N), rescued tickers' trades also written to results/trades/.

Resumable: precompute_imom results are disk-cached per ticker (the expensive
step), and canonical_params.json / bonferroni_results.json are checkpointed
after each basket, with trade-CSV existence re-checked per ticker on resume.
A killed/timed-out run can simply be re-invoked to continue.

Outputs:
  results/intraday_momentum_v2_backtest_results.csv
  results/intraday_momentum_v2_canonical_params.json
  results/intraday_momentum_v2_bonferroni_results.json
  results/trades/intraday_momentum_v2_trades_{basket}_{ticker}.csv (passing baskets)
  results/trades/intraday_momentum_v2_trades_bonferroni_{basket}_{ticker}.csv (rescued)
"""
import os, sys, json, warnings, itertools, pickle
import numpy as np
import pandas as pd
from datetime import time as dt_time
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

CHECKPOINTS = [dt_time(10,0), dt_time(10,30), dt_time(11,0), dt_time(11,30),
               dt_time(12,0), dt_time(12,30), dt_time(13,0), dt_time(13,30),
               dt_time(14,0), dt_time(14,30), dt_time(15,0), dt_time(15,30)]

PARAM_GRID = list(itertools.product([8,10,14,21], [0.5,1.0,1.5,2.0]))

CANON_PATH = os.path.join(OUT_DIR, 'intraday_momentum_v2_canonical_params.json')
BONF_PATH  = os.path.join(OUT_DIR, 'intraday_momentum_v2_bonferroni_results.json')
CACHE_DIR  = os.path.join(OUT_DIR, '.precompute_cache')


def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path): return None
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    return df[['open','high','low','close','volume']].sort_index()


def precompute_imom(df5):
    """Pre-compute checkpoint data once per ticker (reused across all grid params).
    Optimized: searchsorted for checkpoint lookup (3x faster than boolean filtering).

    Carries the actual tz-aware bar timestamp ('ts') alongside each checkpoint/
    pullback row so trade-level entry_time/exit_time are real timestamps (with
    correct DST offsets) rather than reconstructed from date + time-of-day.
    """
    df = df5.between_time('09:30', '16:00').copy()
    df['date'] = pd.to_datetime(df.index.date)
    df['time'] = df.index.time
    df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
    df['hlc3_vol'] = df['hlc3'] * df['volume']
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_hlc3_vol'] = df.groupby('date')['hlc3_vol'].cumsum()
    df['vwap'] = df['cum_hlc3_vol'] / df['cum_vol'].replace(0, np.nan)
    daily_close = df.groupby('date')['close'].last()
    prev_close_map = daily_close.shift(1)
    df['ret'] = df.groupby('date')['close'].pct_change()
    rows = []
    fm_dict = {}
    for date, day_df in df.groupby('date'):
        day_df = day_df.sort_values('time')
        if len(day_df) < 6:
            continue
        d_open = day_df['open'].iloc[0]
        d_prev = prev_close_map.get(date, np.nan)
        bars = day_df[['time','close','ret']].dropna(subset=['ret']).copy()
        bars['ts'] = bars.index
        bars = bars.reset_index(drop=True)
        fm_dict[pd.Timestamp(date)] = bars
        times   = day_df['time'].values
        closes  = day_df['close'].values
        vwaps   = day_df['vwap'].values
        idx_arr = day_df.index
        for cp in CHECKPOINTS:
            idx = np.searchsorted(times, cp, side='right') - 1
            if idx < 0:
                continue
            cp_close = closes[idx]
            cp_vwap  = vwaps[idx]
            cp_ts    = idx_arr[idx]
            move = abs(cp_close / d_open - 1) if d_open != 0 else np.nan
            rows.append({'date': pd.Timestamp(date), 'checkpoint': cp,
                         'open': d_open, 'close': cp_close,
                         'move_from_open': move, 'vwap': cp_vwap,
                         'prev_close': d_prev, 'ts': cp_ts})
    return pd.DataFrame(rows), fm_dict


def get_precomputed(ticker):
    """precompute_imom result, disk-cached per ticker (expensive ~O(days) step;
    caching lets repeated script invocations skip re-computing it). Returns
    None if the ticker has no data or too little history."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f'{ticker}.pkl')
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            pass
    df5 = load_5min(ticker)
    if df5 is None or df5.index.normalize().nunique() < MIN_DAYS:
        with open(cache_path, 'wb') as f:
            pickle.dump(None, f)
        return None
    precomp = precompute_imom(df5)
    with open(cache_path, 'wb') as f:
        pickle.dump(precomp, f)
    return precomp


def _find_pullback(day_bars, after_time, direction, max_wait=6):
    future = day_bars[day_bars['time'] > after_time]
    for _, bar in future.head(max_wait).iterrows():
        if direction == 'long'  and bar['ret'] < 0: return bar['close'], bar['ts']
        if direction == 'short' and bar['ret'] > 0: return bar['close'], bar['ts']
    return None, None


def _find_exit_pullback(day_bars, after_time, position, max_wait=6):
    future = day_bars[day_bars['time'] > after_time]
    for _, bar in future.head(max_wait).iterrows():
        if position == 'long'  and bar['ret'] > 0: return bar['close'], bar['ts']
        if position == 'short' and bar['ret'] < 0: return bar['close'], bar['ts']
    return None, None


def run_intraday_momentum(df5, lookback, vol_mult, precomputed=None, return_trades=False):
    """
    V1-faithful IMOM. Matches v1 generate_signals with fast_alpha=True exactly:
    price-based boundaries, trailing stops, fast alpha entry/exit, reversal, EOD close.

    If return_trades=True, returns (daily_rets, trades_df) where trades_df has
    columns: entry_time, exit_time, entry_price, exit_price, direction (tz-aware
    timestamps). Otherwise returns daily_rets Series only.
    """
    if precomputed is None:
        cp_df, fm_dict = precompute_imom(df5)
    else:
        cp_df, fm_dict = precomputed

    empty_trades = pd.DataFrame(columns=['entry_time','exit_time','entry_price','exit_price','direction'])
    if cp_df.empty:
        return (pd.Series(dtype=float), empty_trades) if return_trades else pd.Series(dtype=float)

    pivot_piv = cp_df.pivot_table(
        index='date', columns='checkpoint', values='move_from_open', aggfunc='first')
    sigma_piv = pivot_piv.shift(1).rolling(lookback, min_periods=lookback).mean()
    sigma_long = sigma_piv.reset_index().melt(
        id_vars='date', var_name='checkpoint', value_name='sigma')
    cp_full = cp_df.merge(sigma_long, on=['date','checkpoint'], how='left')
    valid = cp_full.dropna(subset=['sigma']).copy()

    if valid.empty:
        return (pd.Series(dtype=float), empty_trades) if return_trades else pd.Series(dtype=float)

    daily_rets = {}
    trades_list = [] if return_trades else None
    for day in sorted(valid['date'].unique()):
        day_data = valid[valid['date'] == day].sort_values('checkpoint')
        if len(day_data) < 3:
            continue

        day_bars = fm_dict.get(pd.Timestamp(day), None)
        d_open = day_data['open'].iloc[0]
        d_prev = day_data['prev_close'].iloc[0]

        if not np.isnan(d_prev):
            ref_upper = max(d_open, d_prev)
            ref_lower = min(d_open, d_prev)
        else:
            ref_upper = ref_lower = d_open

        position = None
        entry_price = None
        entry_time = None
        last_stop = None
        day_pnl = 0.0

        for _, cp in day_data.iterrows():
            cp_price = cp['close']
            cp_time  = cp['checkpoint']
            cp_ts    = cp['ts']
            sigma    = cp['sigma']
            vwap     = cp['vwap']
            upper = ref_upper * (1 + vol_mult * sigma)
            lower = ref_lower * (1 - vol_mult * sigma)

            if position is None:
                signal = None
                if cp_price > upper:   signal = 'long'
                elif cp_price < lower: signal = 'short'
                if signal is not None:
                    act_entry = cp_price
                    act_time  = cp_ts
                    if day_bars is not None:
                        pb_p, pb_t = _find_pullback(day_bars, cp_time, signal)
                        if pb_p is not None:
                            act_entry = pb_p
                            act_time  = pb_t
                    position = signal
                    entry_price = act_entry
                    entry_time  = act_time
                    last_stop = max(upper, vwap) if signal == 'long' else min(lower, vwap)
            else:
                if position == 'long':
                    trail_stop = max(upper, vwap)
                    last_stop  = trail_stop
                    should_close = (cp_price < trail_stop)
                else:
                    trail_stop = min(lower, vwap)
                    last_stop  = trail_stop
                    should_close = (cp_price > trail_stop)

                if should_close:
                    act_exit = cp_price
                    act_time = cp_ts
                    if day_bars is not None:
                        ex_p, ex_t = _find_exit_pullback(day_bars, cp_time, position)
                        if ex_p is not None:
                            act_exit = ex_p
                            act_time = ex_t
                    if position == 'long':
                        gross = (act_exit - entry_price) / entry_price
                    else:
                        gross = (entry_price - act_exit) / entry_price
                    day_pnl += gross - calculate_fees_pct(entry_price, act_exit, position)
                    if return_trades:
                        trades_list.append({'entry_time': entry_time, 'exit_time': act_time,
                                            'entry_price': entry_price, 'exit_price': act_exit,
                                            'direction': position})

                    if position == 'long' and cp_price < lower:
                        rev_entry = cp_price
                        rev_time = cp_ts
                        if day_bars is not None:
                            pb_p, pb_t = _find_pullback(day_bars, cp_time, 'short')
                            if pb_p is not None: rev_entry = pb_p; rev_time = pb_t
                        position = 'short'
                        entry_price = rev_entry
                        entry_time  = rev_time
                        last_stop   = min(lower, vwap)
                    elif position == 'short' and cp_price > upper:
                        rev_entry = cp_price
                        rev_time = cp_ts
                        if day_bars is not None:
                            pb_p, pb_t = _find_pullback(day_bars, cp_time, 'long')
                            if pb_p is not None: rev_entry = pb_p; rev_time = pb_t
                        position = 'long'
                        entry_price = rev_entry
                        entry_time  = rev_time
                        last_stop   = max(upper, vwap)
                    else:
                        position = None

        if position is not None:
            eod_price = day_data['close'].iloc[-1]
            eod_time  = day_data['ts'].iloc[-1]
            if position == 'long':
                gross = (eod_price - entry_price) / entry_price
            else:
                gross = (entry_price - eod_price) / entry_price
            day_pnl += gross - calculate_fees_pct(entry_price, eod_price, position)
            if return_trades:
                trades_list.append({'entry_time': entry_time, 'exit_time': eod_time,
                                    'entry_price': entry_price, 'exit_price': eod_price,
                                    'direction': position})

        daily_rets[day] = day_pnl

    rets_series = pd.Series(daily_rets)
    if return_trades:
        trades_df = pd.DataFrame(trades_list) if trades_list else empty_trades
        return rets_series, trades_df
    return rets_series


def sharpe(rets):
    if len(rets) < 30: return np.nan
    m, s = rets.mean(), rets.std()
    return m/s*np.sqrt(252) if s > 0 else np.nan

def ttest_p(rets):
    if len(rets) < 10: return 1.0
    t, p = stats.ttest_1samp(rets.dropna(), 0)
    return p/2 if t > 0 else 1.0

def binomial_test(k, n, p0=0.05):
    return 1 - stats.binom.cdf(k-1, n, p0)

def bootstrap_sharpe_5th(rets, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed); r = rets.values
    return np.percentile([sharpe(pd.Series(rng.choice(r,len(r),replace=True))) for _ in range(n_boot)], 5)

def permutation_p(rets, n_perm=1000, seed=42):
    rng = np.random.default_rng(seed); obs = sharpe(rets); r = rets.values
    return sum(sharpe(pd.Series(rng.permutation(r)*np.sign(rng.uniform(-1,1,len(r))))) >= obs for _ in range(n_perm)) / n_perm

def three_gate(monthly, alpha=0.05):
    if len(monthly) < 12: return False, {}
    p_t = ttest_p(monthly); boot5 = bootstrap_sharpe_5th(monthly); perm_p = permutation_p(monthly)
    return (p_t < alpha) and (boot5 > 0) and (perm_p < alpha), {'t_p': p_t, 'boot5': boot5, 'perm_p': perm_p}


def _monthly(rets):
    rets = rets.copy()
    rets.index = pd.to_datetime(rets.index)
    try:
        return rets.resample('ME').apply(lambda r: (1+r).prod()-1)
    except (ValueError, TypeError):
        return rets.resample('M').apply(lambda r: (1+r).prod()-1)


BONFERRONI_ALPHA = {b: 0.05 / len(t) for b, t in BASKETS.items()}


def run_imom_fast(precomputed, lookback, vol_mult):
    """
    Fast IMOM for basket grid search — no fast_alpha pullback. Same core signal
    logic as run_intraday_momentum, much faster; used only for the PARAM_GRID
    search to find canonical (lookback, vol_mult). Final canonical-param and
    Bonferroni-rescue runs use the full accurate run_intraday_momentum (with
    return_trades=True) for reported results and trade CSVs.
    """
    cp_df, _ = precomputed
    if cp_df.empty: return pd.Series(dtype=float)
    pivot_piv = cp_df.pivot_table(index='date', columns='checkpoint', values='move_from_open', aggfunc='first')
    sigma_piv = pivot_piv.shift(1).rolling(lookback, min_periods=lookback).mean()
    sigma_long = sigma_piv.reset_index().melt(id_vars='date', var_name='checkpoint', value_name='sigma')
    cp_full = cp_df.merge(sigma_long, on=['date','checkpoint'], how='left')
    valid = cp_full.dropna(subset=['sigma']).sort_values(['date','checkpoint']).copy()
    if valid.empty: return pd.Series(dtype=float)
    dates_arr  = valid['date'].values
    cp_close   = valid['close'].values
    sigma_arr  = valid['sigma'].values
    vwap_arr   = valid['vwap'].values
    opens_arr  = valid['open'].values
    prev_c_arr = valid['prev_close'].values
    unique_dates, day_start_idx = np.unique(dates_arr, return_index=True)
    day_end_idx = np.append(day_start_idx[1:], len(dates_arr))
    daily_rets = {}
    for i in range(len(unique_dates)):
        day = unique_dates[i]; s, e = day_start_idx[i], day_end_idx[i]
        if (e-s) < 3: continue
        d_open = opens_arr[s]; d_prev = prev_c_arr[s]
        ref_upper = max(d_open, d_prev) if not np.isnan(d_prev) else d_open
        ref_lower = min(d_open, d_prev) if not np.isnan(d_prev) else d_open
        position = 0; entry_price = 0.0; day_pnl = 0.0
        for j in range(s, e):
            sig = sigma_arr[j]; cp_p = cp_close[j]; vwap = vwap_arr[j]
            upper = ref_upper * (1 + vol_mult * sig)
            lower = ref_lower * (1 - vol_mult * sig)
            if position == 0:
                if cp_p > upper: position = 1; entry_price = cp_p
                elif cp_p < lower: position = -1; entry_price = cp_p
            elif position == 1:
                trail = max(upper, vwap)
                if cp_p < trail:
                    day_pnl += (cp_p-entry_price)/entry_price - calculate_fees_pct(entry_price, cp_p, 'long')
                    if cp_p < lower: position = -1; entry_price = cp_p
                    else: position = 0
            else:
                trail = min(lower, vwap)
                if cp_p > trail:
                    day_pnl += (entry_price-cp_p)/entry_price - calculate_fees_pct(entry_price, cp_p, 'short')
                    if cp_p > upper: position = 1; entry_price = cp_p
                    else: position = 0
        if position != 0:
            lp = cp_close[e-1]; d = 'long' if position==1 else 'short'
            day_pnl += position*(lp-entry_price)/entry_price - calculate_fees_pct(entry_price, lp, d)
        daily_rets[day] = day_pnl
    return pd.Series(daily_rets)


def rescue_one_ticker(basket_name, ticker, precomp, trades_dir):
    """Rescue attempt for a single ticker (used so Phase 2 can checkpoint
    after every ticker, not just after a whole basket)."""
    alpha = BONFERRONI_ALPHA[basket_name]
    best_sh, best_params = -np.inf, None
    for lb, vm in PARAM_GRID:
        try:
            rets = run_imom_fast(precomp, lb, vm)
            sh = sharpe(rets)
            if sh is not None and not np.isnan(sh) and sh > best_sh:
                best_sh = sh; best_params = (lb, vm)
        except Exception:
            continue

    if best_params is None:
        return {'ticker': ticker, 'pass': False, 'reason': 'no valid params'}

    lb, vm = best_params
    best_rets = run_intraday_momentum(None, lb, vm, precomputed=precomp)
    gate_pass, gate_stats = three_gate(_monthly(best_rets), alpha=alpha)
    result = {
        'ticker': ticker, 'pass': bool(gate_pass),
        'lookback': int(lb), 'vol_mult': float(vm),
        'sharpe': round(float(sharpe(best_rets)), 4),
        'bonferroni_alpha': round(alpha, 6),
        'gate_stats': gate_stats,
    }

    if gate_pass:
        try:
            _, trades_df = run_intraday_momentum(None, lb, vm, precomputed=precomp, return_trades=True)
            if not trades_df.empty:
                trades_df['instrument'] = ticker
                trades_df['basket'] = basket_name
                out_path = os.path.join(trades_dir,
                    f'intraday_momentum_v2_trades_bonferroni_{basket_name}_{ticker}.csv')
                trades_df.to_csv(out_path, index=False)
                result['trades_file'] = os.path.basename(out_path)
                print(f"    {ticker}: RESCUED Sharpe={result['sharpe']:.4f} (alpha={alpha:.4f}) | {len(trades_df)} trades", flush=True)
        except Exception as e:
            print(f"    {ticker}: trade save error — {e}", flush=True)
    else:
        print(f"    {ticker}: fail (best Sharpe={result['sharpe']:.4f}, alpha={alpha:.4f})", flush=True)

    return result


def run_bonferroni_rescue(basket_name, ticker_precomp, trades_dir, already_done_tickers=None, on_ticker_done=None):
    """
    Per-ticker rescue for a failed basket.
    For each ticker: find best (lookback, vol_mult) by max Sharpe (fast grid
    search), apply 3-gate at Bonferroni-corrected alpha using the accurate
    function. Saves trade CSV for rescued tickers. Skips tickers already in
    already_done_tickers (resume support) and calls on_ticker_done(result)
    after each ticker so the caller can checkpoint incrementally.
    """
    already_done_tickers = already_done_tickers or {}
    results = list(already_done_tickers.values())

    for ticker, precomp in ticker_precomp.items():
        if ticker in already_done_tickers:
            continue
        result = rescue_one_ticker(basket_name, ticker, precomp, trades_dir)
        results.append(result)
        if on_ticker_done:
            on_ticker_done(result)

    return results


def _load_json(path):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def main():
    TRADES_DIR = os.path.join(OUT_DIR, 'trades')
    os.makedirs(TRADES_DIR, exist_ok=True)

    canonical = _load_json(CANON_PATH)
    canonical = {b: c for b, c in canonical.items()
                 if isinstance(c, dict) and 'ticker_sharpes' in c and 'gate_pass' in c}

    bonf_existing = _load_json(BONF_PATH)
    # A basket only counts as "done" once EVERY ticker in it has a result --
    # checkpointing writes the basket key after the FIRST ticker, so checking
    # key-presence alone would wrongly skip a partially-rescued basket.
    bonf_done_baskets = set()
    if 'baskets' in bonf_existing:
        for b, results in bonf_existing['baskets'].items():
            done_tickers = {r.get('ticker') for r in results if isinstance(r, dict)}
            if b in BASKETS and done_tickers >= set(BASKETS[b]):
                bonf_done_baskets.add(b)

    all_results = []
    ticker_precomp_cache = {}

    # ── Phase 1: basket-level grid search + 3-gate ────────────────────────────
    for basket_name, tickers in BASKETS.items():
        already_done = basket_name in canonical
        trades_needed = False
        if already_done and canonical[basket_name]['gate_pass']:
            trades_needed = not all(
                os.path.exists(os.path.join(TRADES_DIR, f'intraday_momentum_v2_trades_{basket_name}_{t}.csv'))
                for t in tickers)
        need_precomp_for_phase2 = (already_done and not canonical[basket_name]['gate_pass']
                                    and basket_name not in bonf_done_baskets)

        if already_done and not need_precomp_for_phase2 and not trades_needed:
            print(f"\n{'='*60}\nBasket: {basket_name} — already done, skipping", flush=True)
            continue

        print(f"\n{'='*60}\nBasket: {basket_name}", flush=True)

        ticker_precomp = {}
        for ticker in tickers:
            try:
                precomp = get_precomputed(ticker)
                if precomp is None:
                    print(f"  {ticker}: skip"); continue
                ticker_precomp[ticker] = precomp
            except Exception as e:
                print(f"  {ticker}: precompute failed ({e})"); continue

        if not ticker_precomp: continue
        ticker_precomp_cache[basket_name] = ticker_precomp

        if already_done:
            if trades_needed:
                lb = canonical[basket_name]['lookback']; vm = canonical[basket_name]['vol_mult']
                print(f"  Saving basket trades for {basket_name} (resumed)...", flush=True)
                for ticker, precomp in ticker_precomp.items():
                    out_path = os.path.join(TRADES_DIR, f'intraday_momentum_v2_trades_{basket_name}_{ticker}.csv')
                    if os.path.exists(out_path):
                        continue
                    try:
                        _, trades_df = run_intraday_momentum(None, lb, vm, precomputed=precomp, return_trades=True)
                        if trades_df.empty: continue
                        trades_df['instrument'] = ticker; trades_df['basket'] = basket_name
                        trades_df.to_csv(out_path, index=False)
                        print(f"    {ticker}: {len(trades_df)} trades saved")
                    except Exception as e:
                        print(f"    {ticker}: trade save error — {e}")
            continue

        # Grid search uses the fast (non-pullback) approximation for speed;
        # canonical param + final trade emission uses the accurate function.
        param_sharpes = {}
        for lb, vm in PARAM_GRID:
            shs = []
            for ticker, precomp in ticker_precomp.items():
                try:
                    rets = run_imom_fast(precomp, lb, vm)
                    shs.append(sharpe(rets))
                except: continue
            if shs: param_sharpes[(lb, vm)] = np.median(shs)

        if not param_sharpes: continue
        canon = max(param_sharpes, key=param_sharpes.get)
        lb, vm = canon
        print(f"  Canonical: lookback={lb} vol_mult={vm} (median Sharpe={param_sharpes[canon]:.4f})", flush=True)

        ticker_rets = {}; t_pvals = []
        for ticker, precomp in ticker_precomp.items():
            try:
                rets = run_intraday_momentum(None, lb, vm, precomputed=precomp)
                ticker_rets[ticker] = rets; t_pvals.append(ttest_p(rets))
            except: continue

        N = len(ticker_rets); k = sum(p < 0.05 for p in t_pvals)
        binom_p = binomial_test(k, N) if k > 0 else 1.0
        print(f"  Binomial: k={k}/{N} p={binom_p:.4f}", "PASS" if binom_p < 0.05 else "fail", flush=True)

        for ticker, rets in ticker_rets.items():
            all_results.append({'basket': basket_name, 'ticker': ticker,
                                 'lookback': lb, 'vol_mult': vm, 'sharpe': sharpe(rets)})

        aligned = pd.DataFrame(ticker_rets).fillna(0)
        basket_rets = aligned.mean(axis=1)
        monthly = _monthly(basket_rets)
        gate_pass, gate_stats = three_gate(monthly)
        print(f"  3-gate: {'PASS' if gate_pass else 'fail'}  |  {gate_stats}", flush=True)

        canonical[basket_name] = {'lookback': int(lb), 'vol_mult': float(vm),
                                   'median_sharpe': float(param_sharpes[canon]),
                                   'binom_p': float(binom_p), 'binom_pass': bool(binom_p < 0.05),
                                   'gate_pass': bool(gate_pass), 'gate_stats': gate_stats,
                                   'n_tickers': N, 'k_significant': int(k),
                                   'ticker_sharpes': {t: float(sharpe(r)) for t, r in ticker_rets.items()}}

        if gate_pass:
            print(f"  Saving basket trades for {basket_name}...", flush=True)
            for ticker, precomp in ticker_precomp.items():
                out_path = os.path.join(TRADES_DIR, f'intraday_momentum_v2_trades_{basket_name}_{ticker}.csv')
                if os.path.exists(out_path):
                    continue
                try:
                    _, trades_df = run_intraday_momentum(None, lb, vm, precomputed=precomp, return_trades=True)
                    if trades_df.empty: continue
                    trades_df['instrument'] = ticker; trades_df['basket'] = basket_name
                    trades_df.to_csv(out_path, index=False)
                    print(f"    {ticker}: {len(trades_df)} trades saved")
                except Exception as e:
                    print(f"    {ticker}: trade save error — {e}")

        # Checkpoint after every basket so partial progress survives a timeout/restart.
        existing_results_csv = os.path.join(OUT_DIR,'intraday_momentum_v2_backtest_results.csv')
        if all_results:
            new_df = pd.DataFrame(all_results)
            if os.path.exists(existing_results_csv):
                try:
                    old_df = pd.read_csv(existing_results_csv)
                    new_df = pd.concat([old_df[~old_df['basket'].isin(new_df['basket'].unique())], new_df], ignore_index=True)
                except Exception:
                    pass
            new_df.to_csv(existing_results_csv, index=False)
            all_results = []
        with open(CANON_PATH,'w') as f:
            json.dump(canonical, f, indent=2)

    print("\n── Basket Summary ──")
    for b, c in canonical.items():
        print(f"  {b}: binom_p={c['binom_p']:.4f} gate={'PASS' if c['gate_pass'] else 'fail'}"
              f"  k={c['k_significant']}/{c['n_tickers']}")

    # ── Phase 2: Bonferroni rescue on failed baskets ──────────────────────────
    print(f"\n{'='*60}\nPhase 2 — Bonferroni Rescue", flush=True)
    failed = [b for b, c in canonical.items() if not c['gate_pass']]
    bonferroni_results = bonf_existing if bonf_existing else {
        'methodology': 'per-ticker 3-gate at alpha=0.05/N per basket',
        'baskets': {}, 'rescued_tickers': [],
    }
    bonferroni_results.setdefault('baskets', {})
    all_rescued = list(bonferroni_results.get('rescued_tickers', []))

    for basket_name in failed:
        if basket_name in bonf_done_baskets:
            print(f"\n  {basket_name} — already rescued, skipping", flush=True)
            continue
        if basket_name not in ticker_precomp_cache:
            print(f"\n  {basket_name} — no cached precompute, skipping this run (will retry next invocation)", flush=True)
            continue
        print(f"\n  {basket_name} (alpha={BONFERRONI_ALPHA[basket_name]:.4f}):", flush=True)

        # Resume support: reload any per-ticker results already saved for this
        # basket in a prior (possibly killed) invocation.
        partial = bonferroni_results['baskets'].get(basket_name, [])
        already_done_tickers = {r['ticker']: r for r in partial if isinstance(r, dict) and 'ticker' in r}

        def _checkpoint(result, basket_name=basket_name, already_done_tickers=already_done_tickers):
            already_done_tickers[result['ticker']] = result
            bonferroni_results['baskets'][basket_name] = list(already_done_tickers.values())
            with open(BONF_PATH, 'w') as f:
                json.dump(bonferroni_results, f, indent=2)

        results = run_bonferroni_rescue(basket_name, ticker_precomp_cache[basket_name], TRADES_DIR,
                                         already_done_tickers=already_done_tickers, on_ticker_done=_checkpoint)
        bonferroni_results['baskets'][basket_name] = results
        rescued = [r['ticker'] for r in results if r.get('pass')]
        all_rescued.extend(rescued)
        bonferroni_results['rescued_tickers'] = all_rescued
        with open(BONF_PATH, 'w') as f:
            json.dump(bonferroni_results, f, indent=2)

    print(f"Bonferroni rescued: {all_rescued if all_rescued else 'none'}")
    print(f"Outputs: {OUT_DIR}")

    done_phase1 = all(b in canonical for b in BASKETS)
    done_phase2 = all((b in bonferroni_results['baskets']) or canonical.get(b, {}).get('gate_pass')
                       for b in BASKETS if b in canonical)
    if done_phase1 and done_phase2:
        print("\nALL BASKETS COMPLETE (Phase 1 + Phase 2).")
    else:
        print("\nNOT YET COMPLETE -- re-run this script to continue (resumable).")

if __name__ == '__main__':
    main()
