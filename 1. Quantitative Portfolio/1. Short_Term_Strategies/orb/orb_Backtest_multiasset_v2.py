"""
ORB (Opening Range Breakout) — Multi-Asset Backtest v2
Phase 1: Basket-level canonical param search + 3-gate significance test
Phase 2: Per-ticker Bonferroni rescue on failed baskets

Signal: matches v1 exactly — OR close vs OR open direction; entry at next bar open
Threshold: abs(OR_close - OR_open) > (threshold/100) * OR_open  [threshold in % units, e.g. 0.02 = 0.02%]
Grid: window_size [5,10,15] min, atr_percent [2,5,10], threshold [0.0, 0.01, 0.02]

Outputs:
  results/orb_v2_backtest_results.csv
  results/orb_v2_canonical_params.json
  results/orb_per_ticker_bonferroni_results.json
  results/trades/orb_v2_trades_{basket}_{ticker}.csv             (passing baskets only)
  results/trades/orb_v2_trades_bonferroni_{basket}_{ticker}.csv  (Bonferroni-rescued tickers)
"""
import os, sys, json, warnings, itertools
import numpy as np
import pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")

ROOT    = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
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
BONFERRONI_ALPHA = {}  # filled after BASKETS defined

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "DIA", "MDY", "IVV", "VOO"],
    "us_factor":       ["IWF", "IWD", "MTUM", "USMV", "VTV", "VUG", "DVY", "QUAL"],
    "us_sectors":      ["XLK", "XLC", "XLI", "XLV", "XLY", "XLF", "XLE", "XLU", "XLB", "XLP", "XLRE"],
    "bonds_us":        ["TLT", "IEF", "SHY", "HYG", "LQD"],
    "commodities":     ["GLD", "SLV", "USO", "GDX"],
    "em_regional":     ["EEM", "EWZ", "INDA", "EWW"],
    "intl_liquid":     ["EFA", "EZU", "EWJ", "EWG", "EWU"],
}

BONFERRONI_ALPHA = {b: 0.05 / len(t) for b, t in BASKETS.items()}

# Grid matches v1's tested space; threshold is in % units (0.02 = 0.02% of open)
PARAM_GRID = list(itertools.product(
    [5, 10, 15],          # window_size (minutes)
    [2, 5, 10],           # atr_percent
    [0.0, 0.01, 0.02],    # threshold (% of open price, same units as v1)
))

# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------

def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    return df[['open', 'high', 'low', 'close', 'volume']].sort_index()

# ------------------------------------------------------------------
# ATR — matches v1 compute_atr_df exactly (Wilder's, current day included, no shift)
# ------------------------------------------------------------------

def compute_atr_wilder(df5):
    """
    Compute daily ATR-14 using Wilder's smoothing, matching v1 exactly.
    ATR for date D uses that day's TR (no lag/shift).
    Returns dict: {pd.Timestamp(date) -> atr_value}
    """
    df = df5.between_time('09:30', '15:55').copy()
    df['date'] = pd.to_datetime(df.index.date)
    grouped = df.groupby('date')

    period = 14
    prev_close = None
    records = []  # (date, tr)

    for date, group in grouped:
        high_d  = group['high'].max()
        low_d   = group['low'].min()
        close_d = group['close'].iloc[-1]
        if prev_close is None:
            prev_close = close_d
            records.append((date, np.nan))
            continue
        tr = max(abs(high_d - low_d), abs(high_d - prev_close), abs(low_d - prev_close))
        records.append((date, tr))
        prev_close = close_d

    atr_map = {}
    tr_vals = [(d, tr) for d, tr in records if not np.isnan(tr)]
    if len(tr_vals) < period:
        return atr_map

    # First ATR = SMA of first 14 TRs
    first_atr = np.mean([t for _, t in tr_vals[:period]])
    atr_map[pd.Timestamp(tr_vals[period - 1][0])] = first_atr

    prev_atr = first_atr
    for i in range(period, len(tr_vals)):
        date_i, tr_i = tr_vals[i]
        new_atr = (prev_atr * (period - 1) + tr_i) / period
        atr_map[pd.Timestamp(date_i)] = new_atr
        prev_atr = new_atr

    return atr_map

# ------------------------------------------------------------------
# Core ORB logic — v1-faithful
# ------------------------------------------------------------------

def run_orb(df5, window_size, atr_percent, threshold, atr_map=None, return_trades=False):
    """
    Vectorized v1-faithful ORB. entry_mode=basic, stop_loss=atr.
    threshold in % units (e.g. 0.02 = 0.02% of open).
    Returns pd.Series of daily net returns, or (daily_rets, trades_df) if return_trades=True.
    trades_df columns match ema_crossover: entry_time, exit_time, entry_price, exit_price,
    stop_price, direction.
    """
    df = df5.between_time('09:30', '15:55').copy()
    if atr_map is None:
        atr_map = compute_atr_wilder(df5)

    n_bars = max(1, window_size // 5)
    df['_date'] = df.index.date

    # Build per-day index bounds once
    dates_list, starts, ends = [], [], []
    grp_idxs = df.groupby('_date').indices
    for d in sorted(grp_idxs.keys()):
        idx = grp_idxs[d]
        if len(idx) < n_bars + 1:
            continue
        dates_list.append(d)
        starts.append(idx[0])
        ends.append(idx[-1])

    if not dates_list:
        if return_trades:
            return pd.Series(dtype=float), pd.DataFrame(
                columns=['entry_time', 'exit_time', 'entry_price', 'exit_price', 'stop_price', 'direction'])
        return pd.Series(dtype=float)

    open_arr   = df['open'].values
    high_arr   = df['high'].values
    low_arr    = df['low'].values
    close_arr  = df['close'].values
    timestamps = df.index

    th_frac = threshold / 100.0
    ap_frac = atr_percent / 100.0
    daily_rets = {}
    trades_list = [] if return_trades else None

    for i, day in enumerate(dates_list):
        s, e = starts[i], ends[i]
        or_open  = open_arr[s]
        or_close = close_arr[s + n_bars - 1]

        if abs(or_close - or_open) <= th_frac * or_open:
            daily_rets[day] = 0.0; continue
        signal = 1 if or_close > or_open else (-1 if or_close < or_open else 0)
        if signal == 0:
            daily_rets[day] = 0.0; continue

        entry_idx   = s + n_bars
        entry_price = open_arr[entry_idx]
        atr_val     = atr_map.get(pd.Timestamp(day), np.nan)
        if np.isnan(atr_val) or atr_val <= 0:
            daily_rets[day] = 0.0; continue

        stop_price = entry_price - signal * ap_frac * atr_val
        rem_high   = high_arr[entry_idx:e+1]
        rem_low    = low_arr[entry_idx:e+1]
        rem_close  = close_arr[entry_idx:e+1]

        if signal == 1:
            hits = np.where(rem_low <= stop_price)[0]
        else:
            hits = np.where(rem_high >= stop_price)[0]
        if len(hits) > 0:
            exit_price = stop_price
            exit_idx = entry_idx + hits[0]
        else:
            exit_price = rem_close[-1]
            exit_idx = e

        if signal == 1:
            gross = (exit_price - entry_price) / entry_price
        else:
            gross = (entry_price - exit_price) / entry_price

        direction = 'long' if signal == 1 else 'short'
        fee = calculate_fees_pct(entry_price, exit_price, direction)
        daily_rets[day] = gross - fee

        if return_trades:
            trades_list.append({
                'entry_time':  timestamps[entry_idx],
                'exit_time':   timestamps[exit_idx],
                'entry_price': entry_price,
                'exit_price':  exit_price,
                'stop_price':  stop_price,
                'direction':   direction,
            })

    rets_series = pd.Series(daily_rets)
    if return_trades:
        trades_df = pd.DataFrame(trades_list) if trades_list else pd.DataFrame(
            columns=['entry_time', 'exit_time', 'entry_price', 'exit_price', 'stop_price', 'direction'])
        return rets_series, trades_df
    return rets_series

# ------------------------------------------------------------------
# Statistics helpers
# ------------------------------------------------------------------

def sharpe(rets):
    if len(rets) < 30:
        return np.nan
    m, s = rets.mean(), rets.std()
    return m / s * np.sqrt(252) if s > 0 else np.nan

def ttest_p(rets):
    if len(rets) < 10:
        return 1.0
    t, p = stats.ttest_1samp(rets.dropna(), 0)
    return p / 2 if t > 0 else 1.0

def binomial_test(k, n, p0=0.05):
    return 1 - stats.binom.cdf(k - 1, n, p0)

def bootstrap_sharpe_5th(rets, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    r   = rets.values
    return np.percentile(
        [sharpe(pd.Series(rng.choice(r, len(r), replace=True))) for _ in range(n_boot)], 5)

def permutation_p(rets, n_perm=1000, seed=42):
    rng  = np.random.default_rng(seed)
    obs  = sharpe(rets)
    r    = rets.values
    return sum(
        sharpe(pd.Series(rng.permutation(r) * np.sign(rng.uniform(-1, 1, len(r))))) >= obs
        for _ in range(n_perm)
    ) / n_perm

def three_gate(monthly, alpha=0.05):
    """3-gate test. Use alpha=0.05 for basket-level; Bonferroni-corrected alpha for per-ticker rescue."""
    if len(monthly) < 12:
        return False, {}
    p_t    = ttest_p(monthly)
    boot5  = bootstrap_sharpe_5th(monthly)
    perm_p = permutation_p(monthly)
    passed = (p_t < alpha) and (boot5 > 0) and (perm_p < alpha)
    return passed, {'t_p': p_t, 'boot5': boot5, 'perm_p': perm_p}

# ------------------------------------------------------------------
# Phase 2: Bonferroni rescue
# ------------------------------------------------------------------

def run_bonferroni_rescue(basket_name, ticker_data, atr_maps, trades_dir):
    """Per-ticker grid search + Bonferroni-corrected 3-gate for a failed basket."""
    alpha = BONFERRONI_ALPHA[basket_name]
    print(f"\n  [Bonferroni] {basket_name}  alpha={alpha:.5f}")
    results = []
    for ticker, df5 in ticker_data.items():
        atr = atr_maps[ticker]
        best_sh, best_pms, best_rets = float('-inf'), None, None
        for ws, ap, th in PARAM_GRID:
            try:
                rets = run_orb(df5, ws, ap, th, atr)
                sh   = sharpe(rets)
                if not np.isnan(sh) and sh > best_sh:
                    best_sh, best_pms, best_rets = sh, (ws, ap, th), rets
            except Exception:
                continue
        if best_pms is None:
            results.append({'ticker': ticker, 'pass': False, 'reason': 'no_valid_params'})
            continue
        ws, ap, th = best_pms
        best_rets.index = pd.to_datetime(best_rets.index)
        try:
            monthly = best_rets.resample('ME').apply(lambda r: (1 + r).prod() - 1).dropna()
        except ValueError:
            monthly = best_rets.resample('M').apply(lambda r: (1 + r).prod() - 1).dropna()
        passed, gs = three_gate(monthly, alpha=alpha)
        rec = {
            'ticker':          ticker,
            'basket':          basket_name,
            'window_size':     int(ws),
            'atr_percent':     float(ap),
            'threshold':       float(th),
            'net_sharpe':      round(float(best_sh), 4),
            'gate_t_p':        gs.get('t_p'),
            'gate_boot5':      gs.get('boot5'),
            'gate_perm_p':     gs.get('perm_p'),
            'bonferroni_alpha': round(alpha, 6),
            'pass':            bool(passed),
        }
        results.append(rec)
        print(f"    {ticker}: Sh={best_sh:.4f} -> {'PASS' if passed else 'fail'}")
        if passed:
            try:
                _, trades_df = run_orb(df5, ws, ap, th, atr, return_trades=True)
                if not trades_df.empty:
                    trades_df['instrument'] = ticker
                    trades_df['basket'] = basket_name
                    out_path = os.path.join(trades_dir, f'orb_v2_trades_bonferroni_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    rec['trades_file'] = os.path.basename(out_path)
                    print(f"      {ticker}: RESCUED | {len(trades_df)} trades saved")
            except Exception as e:
                print(f"    {ticker}: trade save error — {e}")
    return results


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    all_results = []
    canonical   = {}
    ticker_data_cache = {}  # saved for Phase 2
    atr_maps_cache    = {}
    TRADES_DIR = os.path.join(OUT_DIR, 'trades')
    os.makedirs(TRADES_DIR, exist_ok=True)

    for basket_name, tickers in BASKETS.items():
        print(f"\n{'='*60}\nBasket: {basket_name}")
        ticker_data = {}
        for ticker in tickers:
            df5 = load_5min(ticker)
            if df5 is None or df5.index.normalize().nunique() < MIN_DAYS:
                print(f"  {ticker}: skip")
                continue
            ticker_data[ticker] = df5
        if not ticker_data:
            continue

        # Pre-compute ATR maps once per ticker (reused across grid and Phase 2)
        atr_maps = {t: compute_atr_wilder(df5) for t, df5 in ticker_data.items()}
        ticker_data_cache[basket_name] = ticker_data
        atr_maps_cache[basket_name]    = atr_maps

        # Grid search: canonical = max median Sharpe across basket
        param_sharpes = {}
        for ws, ap, th in PARAM_GRID:
            shs = []
            for ticker, df5 in ticker_data.items():
                try:
                    shs.append(sharpe(run_orb(df5, ws, ap, th, atr_maps[ticker])))
                except Exception:
                    continue
            if shs:
                param_sharpes[(ws, ap, th)] = np.median(shs)
        if not param_sharpes:
            continue

        canon = max(param_sharpes, key=param_sharpes.get)
        ws, ap, th = canon
        print(f"  Canonical: window={ws}min  atr={ap}%  threshold={th}%  "
              f"(median Sharpe={param_sharpes[canon]:.4f})")

        # Evaluate each ticker at canonical params
        ticker_rets = {}
        t_pvals     = []
        for ticker, df5 in ticker_data.items():
            try:
                rets = run_orb(df5, ws, ap, th, atr_maps[ticker])
                ticker_rets[ticker] = rets
                t_pvals.append(ttest_p(rets))
                all_results.append({
                    'basket':      basket_name,
                    'ticker':      ticker,
                    'window_size': ws,
                    'atr_percent': ap,
                    'threshold':   th,
                    'sharpe':      sharpe(rets),
                })
            except Exception:
                continue

        N       = len(ticker_rets)
        k       = sum(p < 0.05 for p in t_pvals)
        binom_p = binomial_test(k, N) if k > 0 else 1.0
        print(f"  Binomial: k={k}/{N}  p={binom_p:.4f}  {'PASS' if binom_p < 0.05 else 'fail'}")

        aligned     = pd.DataFrame(ticker_rets).fillna(0)
        basket_rets = aligned.mean(axis=1)
        basket_rets.index = pd.to_datetime(basket_rets.index)
        try:
            monthly = basket_rets.resample('ME').apply(lambda r: (1 + r).prod() - 1)
        except ValueError:
            monthly = basket_rets.resample('M').apply(lambda r: (1 + r).prod() - 1)
        gate_pass, gate_stats = three_gate(monthly)
        print(f"  3-gate: {'PASS' if gate_pass else 'fail'}  |  {gate_stats}")

        canonical[basket_name] = {
            'window_size':    int(ws),
            'atr_percent':    float(ap),
            'threshold':      float(th),
            'binom_p':        float(binom_p),
            'binom_pass':     bool(binom_p < 0.05),
            'gate_pass':      bool(gate_pass),
            'gate_stats':     gate_stats,
            'n_tickers':      N,
            'k_significant':  int(k),
        }

        # Emit trade CSVs for passing baskets (at basket canonical params)
        if gate_pass:
            print(f"  Saving basket trades for {basket_name}...")
            for ticker, df5 in ticker_data.items():
                try:
                    _, trades_df = run_orb(df5, ws, ap, th, atr_maps[ticker], return_trades=True)
                    if trades_df.empty:
                        continue
                    trades_df['instrument'] = ticker
                    trades_df['basket'] = basket_name
                    out_path = os.path.join(TRADES_DIR, f'orb_v2_trades_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    print(f"    {ticker}: {len(trades_df)} trades saved")
                except Exception as e:
                    print(f"    {ticker}: trade save error — {e}")

    pd.DataFrame(all_results).to_csv(
        os.path.join(OUT_DIR, 'orb_v2_backtest_results.csv'), index=False)
    with open(os.path.join(OUT_DIR, 'orb_v2_canonical_params.json'), 'w') as f:
        json.dump(canonical, f, indent=2)

    print("\n-- Basket Summary --")
    for b, c in canonical.items():
        print(f"  {b}: binom_p={c['binom_p']:.4f}  gate={'PASS' if c['gate_pass'] else 'fail'}"
              f"  k={c['k_significant']}/{c['n_tickers']}")

    # ----------------------------------------------------------------
    # Phase 2: Bonferroni rescue on failed baskets
    # ----------------------------------------------------------------
    failed = [b for b, c in canonical.items() if not c['gate_pass']]
    print(f"\n{'='*60}\nPhase 2: Bonferroni Rescue  ({len(failed)} failed baskets)\n{'='*60}")

    bonferroni_results = {
        'methodology': {
            'signal':       'ORB: entry at bar after OR window, exit EOD or ATR stop',
            'grid':         'window_size=[5,10,15], atr_percent=[2,5,10], threshold=[0.0,0.01,0.02]',
            'selection':    'best params = max net Sharpe per ticker',
            'significance': '3-gate at Bonferroni-corrected alpha per basket',
            'bonferroni_alphas': {b: round(BONFERRONI_ALPHA[b], 6) for b in BASKETS},
        },
        'baskets': {},
    }
    all_rescued = []
    for basket_name in failed:
        if basket_name not in ticker_data_cache:
            bonferroni_results['baskets'][basket_name] = []
            continue
        results = run_bonferroni_rescue(
            basket_name, ticker_data_cache[basket_name], atr_maps_cache[basket_name], TRADES_DIR)
        bonferroni_results['baskets'][basket_name] = results
        all_rescued.extend(r['ticker'] for r in results if r.get('pass'))

    bonferroni_results['rescued_tickers'] = all_rescued

    bonf_path = os.path.join(OUT_DIR, 'orb_per_ticker_bonferroni_results.json')
    with open(bonf_path, 'w') as f:
        json.dump(bonferroni_results, f, indent=2)

    print(f"\nRescued tickers: {all_rescued}")
    print(f"Bonferroni results -> {bonf_path}")
    print(f"Trade CSVs        -> {TRADES_DIR}")

if __name__ == '__main__':
    main()
