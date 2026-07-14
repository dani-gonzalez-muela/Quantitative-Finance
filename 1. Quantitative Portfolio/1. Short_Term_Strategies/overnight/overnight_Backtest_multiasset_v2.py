"""
overnight_Backtest_multiasset_v2.py
====================================
Multi-Asset Backtest v2 -- Overnight Premium (5-min, session-based)

Phase 1: Per-basket grid search over `threshold` (filter on same-day market-
session return). Canonical params = max median Sharpe across instruments in
basket. 3-gate significance test (t-test, bootstrap Sharpe, permutation) on
the equal-weight basket composite.
Phase 2: For baskets that fail Phase 1, per-ticker Bonferroni-corrected
rescue (alpha = 0.05 / N tickers in basket).

Signal (long-only), ported from OG_Research/Overnight.ipynb's session
decomposition + the exploratory overnight_v1window_all_baskets.json run
(now archived under archive/pre_5min_port_2026-07-01/), generalized from a
fixed threshold=0 to a swept grid:
  - Session decomposition of 5-min bars: pre-market (04:00-09:25),
    market (09:30-15:55), after-market (16:00-19:55).
  - market_return = same-day (market_close - market_open) / market_open.
  - Enter long overnight if market_return < threshold, at that day's
    after-market-session close price; exit at the *next* day's pre-market-
    session open price. Entry/exit use the actual last/first bar timestamp
    of each session (robust to holidays/half-days), not a fixed clock time.
  - Long-only by design: OG_Research explicitly tested long+short and found
    long-only superior (shorts added cost, not edge) -- see
    OG_Research/Overnight.ipynb, section 9 ("Why Long-Only?").
  - Replaces the prior daily-OHLCV close->next-open approximation (archived
    scripts/overnight_Backtest_multiasset_v2_dailyOHLCV.py), which the
    codebase's own earlier notes flagged as understating signal quality
    because daily "open" bakes in pre-market moves.

Outputs:
  results/overnight_v2_backtest_results.csv
  results/overnight_v2_canonical_params.json
  results/overnight_v2_bonferroni_results.json
  results/trades/overnight_v2_trades_{basket}_{ticker}.csv              (passing baskets)
  results/trades/overnight_v2_trades_bonferroni_{basket}_{ticker}.csv   (Bonferroni rescues)
"""
import os, sys, json, warnings
from datetime import time
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
    "em_regional":     ["EEM", "EWZ", "INDA", "EWW"],
    "intl_liquid":     ["EFA", "EZU", "EWJ", "EWG", "EWU"],
}
# Note: overnight does not define bonds_us / commodities baskets -- that
# scope was never part of this strategy (matches the pre-existing
# daily-OHLCV BASKETS dict and the archived v1window_all_baskets.json run).

# Threshold grid -- ported verbatim from the archived
# overnight_v1window_all_baskets.json's param_grid.
PARAM_GRID = [0.0, -0.001, -0.002, -0.003, -0.005]


def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path): return None
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    return df[['open', 'high', 'low', 'close', 'volume']].sort_index()


def assign_session(t):
    """t is a datetime.time. Regular RTH (09:30-15:55) is 'market' -- used
    only to compute market_return, not as a tradeable session itself."""
    if time(4, 0) <= t <= time(9, 25):
        return 'pre_market'
    elif time(9, 30) <= t <= time(15, 55):
        return 'market'
    elif time(16, 0) <= t <= time(19, 55):
        return 'after_market'
    return None


def build_overnight_pivot(df5):
    """
    Session-decompose 5-min bars into a per-day table:
      market_return          -- (market close - market open) / market open, same day
      overnight_entry_time   -- actual timestamp of that day's after-market session's last bar
      overnight_entry_price  -- close of that bar
      overnight_exit_time    -- actual timestamp of the *next* day's pre-market session's first bar
      overnight_exit_price   -- open of that bar
    Only session_dates with all 3 sessions present (and a following day with
    a pre-market session) are kept -- matches OG_Research's "complete days"
    filter. Uses actual bar timestamps (not fixed clock times) so holidays /
    early closes / late opens resolve correctly.
    """
    df = df5.copy()
    df['session'] = [assign_session(t) for t in df.index.time]
    df['session_date'] = df.index.normalize()
    df['ts'] = df.index
    df = df.dropna(subset=['session'])
    if df.empty:
        return pd.DataFrame()

    agg = df.groupby(['session_date', 'session']).agg(
        s_open=('open', 'first'), s_close=('close', 'last'),
        first_ts=('ts', 'first'), last_ts=('ts', 'last'),
    ).reset_index()

    counts = agg.groupby('session_date')['session'].count()
    valid_dates = counts[counts == 3].index
    agg = agg[agg['session_date'].isin(valid_dates)]
    if agg.empty:
        return pd.DataFrame()

    piv = agg.pivot(index='session_date', columns='session',
                     values=['s_open', 's_close', 'first_ts', 'last_ts'])
    piv.columns = ['_'.join(c) for c in piv.columns.values]
    piv = piv.reset_index().sort_values('session_date').reset_index(drop=True)

    piv['market_return'] = (piv['s_close_market'] - piv['s_open_market']) / piv['s_open_market']
    piv['overnight_entry_time']  = piv['last_ts_after_market']
    piv['overnight_entry_price'] = piv['s_close_after_market']
    piv['overnight_exit_time']   = piv['first_ts_pre_market'].shift(-1)
    piv['overnight_exit_price']  = piv['s_open_pre_market'].shift(-1)

    piv = piv.dropna(subset=['overnight_exit_time', 'overnight_exit_price']).reset_index(drop=True)
    return piv[['session_date', 'market_return',
                'overnight_entry_time', 'overnight_entry_price',
                'overnight_exit_time', 'overnight_exit_price']]


def run_overnight(pivot, threshold, return_trades=False):
    """
    Long-only overnight signal: enter if same-day market_return < threshold.
    Vectorized. Returns a daily-return Series indexed by session_date (0.0
    on no-signal days), and optionally a trades_df (entry_time, exit_time,
    entry_price, exit_price, stop_price, direction) for signal days only.
    """
    if pivot.empty:
        empty = pd.Series(dtype=float)
        if return_trades:
            return empty, pd.DataFrame(columns=['entry_time', 'exit_time', 'entry_price',
                                                  'exit_price', 'stop_price', 'direction'])
        return empty

    enter = (pivot['market_return'] < threshold).values
    entry_px = pivot['overnight_entry_price'].values.astype(float)
    exit_px  = pivot['overnight_exit_price'].values.astype(float)
    gross = (exit_px - entry_px) / entry_px
    fees  = calculate_fees_pct(entry_px, exit_px, 'long')
    net   = np.where(enter, gross - fees, 0.0)

    daily_rets = pd.Series(net, index=pd.to_datetime(pivot['session_date'].values))

    if return_trades:
        # NOTE: do NOT use .values on the tz-aware entry/exit time columns --
        # Series.values on a tz-aware datetime64 column silently converts to
        # naive UTC numpy datetime64, which corrupts the local clock time
        # (e.g. 19:55 ET becomes displayed as the UTC hour with no offset).
        # Keeping them as Series preserves the US/Eastern tz-aware dtype.
        sub = pivot.loc[enter].reset_index(drop=True)
        trades_df = pd.DataFrame({
            'entry_time':  sub['overnight_entry_time'],
            'exit_time':   sub['overnight_exit_time'],
            'entry_price': sub['overnight_entry_price'].astype(float).values,
            'exit_price':  sub['overnight_exit_price'].astype(float).values,
            'stop_price':  np.nan,   # session-based signal has no intrabar stop
            'direction':   'long',
        })
        return daily_rets, trades_df
    return daily_rets


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

def bootstrap_sharpe_5th(rets, n_boot=2000, seed=42):
    rng = np.random.default_rng(seed); r = rets.values
    return np.percentile([sharpe(pd.Series(rng.choice(r, size=len(r), replace=True))) for _ in range(n_boot)], 5)

def permutation_p(rets, n_perm=2000, seed=42):
    rng = np.random.default_rng(seed); obs = sharpe(rets); r = rets.values
    return sum(sharpe(pd.Series(rng.permutation(r) * np.sign(rng.uniform(-1, 1, len(r))))) >= obs for _ in range(n_perm)) / n_perm

def three_gate(monthly_rets, alpha=0.05):
    # n_boot/n_perm=2000 (not ema_crossover's default 1000) -- matches the
    # methodology recorded in the archived overnight_v1window_all_baskets.json.
    if len(monthly_rets) < 12: return False, {}
    p_t = ttest_p(monthly_rets); boot5 = bootstrap_sharpe_5th(monthly_rets); perm_p = permutation_p(monthly_rets)
    return (p_t < alpha) and (boot5 > 0) and (perm_p < alpha), {'t_p': p_t, 'boot5_sharpe': boot5, 'perm_p': perm_p}


BONFERRONI_ALPHA = {b: 0.05 / len(t) for b, t in BASKETS.items()}


def run_bonferroni_rescue(basket_name, ticker_pivots, trades_dir):
    """
    Per-ticker rescue for a failed basket.
    For each ticker: find best threshold (max Sharpe), apply 3-gate at
    Bonferroni alpha. Saves trade CSV for rescued tickers.
    """
    alpha = BONFERRONI_ALPHA[basket_name]
    results = []

    for ticker, piv in ticker_pivots.items():
        best_sh, best_thr, best_rets = -np.inf, None, None
        for thr in PARAM_GRID:
            try:
                rets = run_overnight(piv, thr)
                sh = sharpe(rets)
                if sh > best_sh:
                    best_sh = sh; best_thr = thr; best_rets = rets
            except Exception:
                continue

        if best_thr is None or best_rets is None:
            results.append({'ticker': ticker, 'pass': False, 'reason': 'no valid params'})
            continue

        try:
            monthly = best_rets.resample('ME').apply(lambda r: (1 + r).prod() - 1)
        except (ValueError, TypeError):
            monthly = best_rets.resample('M').apply(lambda r: (1 + r).prod() - 1)

        gate_pass, gate_stats = three_gate(monthly, alpha=alpha)
        result = {
            'ticker': ticker, 'pass': bool(gate_pass),
            'threshold': float(best_thr),
            'sharpe': round(float(best_sh), 4),
            'bonferroni_alpha': round(alpha, 6),
            'gate_stats': gate_stats,
        }

        if gate_pass:
            try:
                _, trades_df = run_overnight(piv, best_thr, return_trades=True)
                if not trades_df.empty:
                    trades_df['instrument'] = ticker
                    trades_df['basket'] = basket_name
                    out_path = os.path.join(trades_dir,
                        f'overnight_v2_trades_bonferroni_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    result['trades_file'] = os.path.basename(out_path)
                    print(f"    {ticker}: RESCUED Sharpe={best_sh:.4f} (alpha={alpha:.4f}) | {len(trades_df)} trades")
            except Exception as e:
                print(f"    {ticker}: trade save error -- {e}")
        else:
            print(f"    {ticker}: fail (best Sharpe={best_sh:.4f}, alpha={alpha:.4f})")

        results.append(result)

    return results


def main():
    all_results = []; canonical = {}; pivot_cache = {}
    TRADES_DIR = os.path.join(OUT_DIR, 'trades')
    os.makedirs(TRADES_DIR, exist_ok=True)

    print(f"\n{'='*70}\nOVERNIGHT PREMIUM -- Multi-Asset Backtest v2 (5-min session-based)\n{'='*70}")

    # -- Phase 1: basket-level grid search + 3-gate ----------------------------
    for basket_name, tickers in BASKETS.items():
        print(f"\n{'='*60}\nBasket: {basket_name}  ({len(tickers)} tickers)")

        ticker_pivots = {}
        for ticker in tickers:
            df5 = load_5min(ticker)
            if df5 is None: print(f"  {ticker}: no data"); continue
            n_days = df5.index.normalize().nunique()
            if n_days < MIN_DAYS: print(f"  {ticker}: only {n_days} days, skip"); continue
            piv = build_overnight_pivot(df5)
            if piv.empty or len(piv) < MIN_DAYS: print(f"  {ticker}: insufficient overnight sessions, skip"); continue
            ticker_pivots[ticker] = piv
        if not ticker_pivots: continue
        pivot_cache[basket_name] = ticker_pivots

        param_sharpes = {}
        for thr in PARAM_GRID:
            shs = []
            for ticker, piv in ticker_pivots.items():
                try: shs.append(sharpe(run_overnight(piv, thr)))
                except Exception: continue
            shs = [s for s in shs if not np.isnan(s)]
            if shs: param_sharpes[thr] = np.median(shs)
        if not param_sharpes: continue

        canon_thr = max(param_sharpes, key=param_sharpes.get)
        print(f"  Canonical: threshold={canon_thr} (median Sharpe={param_sharpes[canon_thr]:.4f})")

        ticker_rets = {}; t_pvals = []
        for ticker, piv in ticker_pivots.items():
            try:
                rets = run_overnight(piv, canon_thr)
                ticker_rets[ticker] = rets; t_pvals.append(ttest_p(rets))
                all_results.append({'basket': basket_name, 'ticker': ticker,
                                     'threshold': canon_thr, 'sharpe': sharpe(rets)})
            except Exception:
                continue

        N = len(ticker_rets); k = sum(p < 0.05 for p in t_pvals)
        binom_p = binomial_test(k, N) if k > 0 else 1.0
        print(f"  Binomial test: k={k}/{N} -> p={binom_p:.4f}", "PASS" if binom_p < 0.05 else "fail")

        aligned = pd.DataFrame(ticker_rets).fillna(0)
        basket_rets = aligned.mean(axis=1)
        basket_rets.index = pd.to_datetime(basket_rets.index)
        try:
            monthly = basket_rets.resample('ME').apply(lambda r: (1 + r).prod() - 1)
        except (ValueError, TypeError):
            monthly = basket_rets.resample('M').apply(lambda r: (1 + r).prod() - 1)
        gate_pass, gate_stats = three_gate(monthly)
        print(f"  3-gate: {gate_pass} | {gate_stats}")

        canonical[basket_name] = {
            'threshold': float(canon_thr),
            'binom_p': float(binom_p), 'binom_pass': bool(binom_p < 0.05),
            'gate_pass': bool(gate_pass), 'gate_stats': gate_stats,
            'n_tickers': N, 'k_significant': int(k),
        }

        if gate_pass:
            print(f"  Saving basket trades for {basket_name}...")
            for ticker, piv in ticker_pivots.items():
                try:
                    _, trades_df = run_overnight(piv, canon_thr, return_trades=True)
                    if trades_df.empty: continue
                    trades_df['instrument'] = ticker; trades_df['basket'] = basket_name
                    out_path = os.path.join(TRADES_DIR, f'overnight_v2_trades_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    print(f"    {ticker}: {len(trades_df)} trades saved")
                except Exception as e:
                    print(f"    {ticker}: trade save error -- {e}")

    # Deliberately mirrors ema_crossover's real canonical_params.json shape: a
    # plain-string metadata key sitting alongside the per-basket dicts. Every
    # comprehension below (and in the Implementation script) must guard with
    # isinstance(v, dict) because of this.
    canonical['_run_info'] = ("v2 multiasset backtest (5-min session-based overnight window, "
                               "ported from OG_Research + archived v1window prototype) -- "
                               "3-gate significance (t-test + bootstrap + sign-permutation), "
                               "Bonferroni rescue for failed baskets, trade CSVs emitted for sizing")

    pd.DataFrame(all_results).to_csv(os.path.join(OUT_DIR, 'overnight_v2_backtest_results.csv'), index=False)
    with open(os.path.join(OUT_DIR, 'overnight_v2_canonical_params.json'), 'w') as f:
        json.dump(canonical, f, indent=2)

    # -- Phase 2: Bonferroni rescue on failed baskets --------------------------
    print(f"\n{'='*60}\nPhase 2 -- Bonferroni Rescue")
    failed = [b for b, c in canonical.items() if isinstance(c, dict) and not c['gate_pass']]
    bonferroni_results = {
        'methodology': 'per-ticker 3-gate at alpha=0.05/N per basket',
        'baskets': {}, 'rescued_tickers': [],
    }
    all_rescued = []
    for basket_name in failed:
        if basket_name not in pivot_cache: continue
        print(f"\n  {basket_name} (alpha={BONFERRONI_ALPHA[basket_name]:.4f}):")
        results = run_bonferroni_rescue(basket_name, pivot_cache[basket_name], TRADES_DIR)
        bonferroni_results['baskets'][basket_name] = results
        rescued = [r['ticker'] for r in results if r.get('pass')]
        all_rescued.extend(rescued)
    bonferroni_results['rescued_tickers'] = all_rescued

    bonf_path = os.path.join(OUT_DIR, 'overnight_v2_bonferroni_results.json')
    with open(bonf_path, 'w') as f:
        json.dump(bonferroni_results, f, indent=2)

    print(f"\n-- Summary --")
    for b, c in canonical.items():
        if not isinstance(c, dict): continue
        print(f"  {b}: gate={'PASS' if c['gate_pass'] else 'fail'}  k={c['k_significant']}/{c['n_tickers']}")
    print(f"Bonferroni rescued: {all_rescued if all_rescued else 'none'}")
    print(f"Outputs: {OUT_DIR}")

if __name__ == '__main__':
    main()
