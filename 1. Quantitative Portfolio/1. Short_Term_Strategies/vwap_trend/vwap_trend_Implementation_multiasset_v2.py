"""
VWAP Trend -- Multi-Asset Implementation v2
============================================
Reads canonical params + per-ticker trade CSVs produced by the Backtest
(Phase 1 basket-passing + Phase 2 Bonferroni rescue). Runs multiple sizing
variants using shared.implementations, prints comparison, and saves
combined equity curves per variant plus the best-by-Sharpe final curve.

Mirrors ema_crossover_Implementation_multiasset_v2.py's pattern exactly.

Sizing variants compared:
  1. simple_bet         -- fixed 85% of equity per trade
  2. intraday_asset_vol  -- underlying asset vol targeting (paper's method, 2% daily, 4x max)
  3. vol_targeting      -- strategy return vol targeting (10% ann, 2x max)

After computing all three, the variant with the highest portfolio Sharpe is
selected as the final combined equity for the strategy.

Outputs:
  results/equity/combined_equity_simple.csv
  results/equity/combined_equity_asset_vol.csv
  results/equity/combined_equity_vol_target.csv
  results/equity/combined_equity_final.csv        (selected variant, best Sharpe)
  results/vwap_trend_v2_implementations.json      (comparison summary + selected_variant)
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
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
DATA_DIR    = data_dir('intraday_5min')
RESULTS_DIR = os.path.join(HERE, 'results')
TRADES_DIR  = os.path.join(RESULTS_DIR, 'trades')
EQUITY_DIR  = os.path.join(RESULTS_DIR, 'equity')
CANON_PATH  = os.path.join(RESULTS_DIR, 'vwap_trend_v2_canonical_params.json')
BONF_PATH   = os.path.join(RESULTS_DIR, 'vwap_trend_v2_bonferroni_results.json')
os.makedirs(EQUITY_DIR, exist_ok=True)

from _shared.implementations import (
    simple_bet, intraday_asset_vol, vol_targeting,
    build_daily_equity, compare_implementations,
)

STARTING_CAPITAL = 100_000
SLIPPAGE = float(os.environ.get('SLIPPAGE', '0.0'))  # $/share per side; canonical default set 2026-07-10

# __CKPT__ per-ticker checkpoint cache (2026-07-10): lets long runs resume; keyed by slippage
import pickle as _pkl, tempfile as _tmpf
_CKPT_DIR = _os_ckpt = None
def _ckpt(key, fn):
    global _CKPT_DIR
    if _CKPT_DIR is None:
        _CKPT_DIR = os.path.join(_tmpf.gettempdir(), 'impl_ckpt', os.path.basename(HERE) + '_' + str(SLIPPAGE))
        os.makedirs(_CKPT_DIR, exist_ok=True)
    p = os.path.join(_CKPT_DIR, key + '.pkl')
    if os.path.exists(p):
        with open(p, 'rb') as f: return _pkl.load(f)
    v = fn()
    with open(p, 'wb') as f: _pkl.dump(v, f)
    return v
MIN_DAYS         = 252

# Must match vwap_trend_Backtest_multiasset_v2.py's BASKETS exactly (this was
# previously scrambled: missing VOO, missing em_regional, EEM/EWZ misfiled
# into intl_liquid instead of em_regional).
BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "DIA", "MDY", "IVV", "VOO"],
    "us_factor":       ["IWF", "IWD", "MTUM", "USMV", "VTV", "VUG", "DVY", "QUAL"],
    "us_sectors":      ["XLK", "XLC", "XLI", "XLV", "XLY", "XLF", "XLE", "XLU", "XLB", "XLP", "XLRE"],
    "bonds_us":        ["TLT", "IEF", "SHY", "HYG", "LQD"],
    "commodities":     ["GLD", "SLV", "USO", "GDX"],
    "em_regional":     ["EEM", "EWZ", "INDA", "EWW"],
    "intl_liquid":     ["EFA", "EZU", "EWJ", "EWG", "EWU"],
}

SIZING_VARIANTS = ['simple', 'asset_vol', 'vol_target']


# -- Data loaders -----------------------------------------------------------

def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path): return None
    # __CACHE5MIN__ perf cache (2026-07-10): parse once, reuse as parquet in temp dir
    import tempfile
    _c = os.path.join(tempfile.gettempdir(), '5min_cache', f'{ticker}.pkl')
    if os.path.exists(_c):
        return pd.read_pickle(_c)
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    df = df[['open', 'high', 'low', 'close', 'volume']].sort_index()
    try:
        os.makedirs(os.path.dirname(_c), exist_ok=True); df.to_pickle(_c)
    except Exception:
        pass
    return df

def get_daily_closes(ticker, df5=None):
    """Extract daily close prices from 5-min data (used by intraday_asset_vol)."""
    if df5 is None:
        df5 = load_5min(ticker)
    if df5 is None: return None
    daily = df5.groupby(df5.index.date)['close'].last()
    daily.index = pd.to_datetime(daily.index)
    return daily

def load_trades(basket_name, ticker, bonferroni=False):
    if bonferroni:
        path = os.path.join(TRADES_DIR, f'vwap_trend_v2_trades_bonferroni_{basket_name}_{ticker}.csv')
    else:
        path = os.path.join(TRADES_DIR, f'vwap_trend_v2_trades_{basket_name}_{ticker}.csv')
    if not os.path.exists(path): return None
    trades = pd.read_csv(path, parse_dates=['entry_time', 'exit_time'])
    if trades.empty: return None
    # entry_time/exit_time cross DST transitions (mixed -04:00/-05:00 offsets), which
    # pandas' CSV parser leaves as an object column of mixed-offset datetime.datetime.
    # Force to a proper tz-aware UTC datetime64 dtype so downstream pd.to_datetime()
    # calls (including shared.implementations.build_daily_equity) don't choke on it.
    # (Same fix as ema_crossover_Implementation_multiasset_v2.py.)
    trades['entry_time'] = pd.to_datetime(trades['entry_time'], utc=True)
    trades['exit_time']  = pd.to_datetime(trades['exit_time'], utc=True)
    return trades


# -- Stats helpers ------------------------------------------------------------

def sharpe(rets):
    m, s = rets.mean(), rets.std()
    return m / s * np.sqrt(252) if s > 0 else np.nan

def max_dd(eq):
    return ((eq - eq.cummax()) / eq.cummax()).min()

def cagr(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1


# -- Build per-ticker daily equity for each sizing variant --------------------

def build_ticker_equities_bonferroni(basket_name, ticker, sleeve_cap):
    """Same as build_ticker_equities but loads the Bonferroni trade CSV."""
    df5 = load_5min(ticker)
    if df5 is None or df5.index.normalize().nunique() < MIN_DAYS:
        return {}
    trades = load_trades(basket_name, ticker, bonferroni=True)
    if trades is None or len(trades) < 10:
        return {}
    daily_prices = get_daily_closes(ticker, df5)
    results = {}
    try:
        r = simple_bet(trades, bet_size=0.85, starting_capital=sleeve_cap, slippage=SLIPPAGE)
        results['simple'] = build_daily_equity(trades, r['equity_curve'], sleeve_cap)
    except Exception as e:
        print(f"    {ticker} simple_bet error: {e}")
    try:
        r = intraday_asset_vol(trades, daily_prices, target_vol=0.02, lookback=14,
                               max_leverage=4.0, starting_capital=sleeve_cap, cost_per_share=SLIPPAGE)
        results['asset_vol'] = build_daily_equity(trades, r['equity_curve'], sleeve_cap)
    except Exception as e:
        print(f"    {ticker} intraday_asset_vol error: {e}")
    try:
        r = vol_targeting(trades, target_vol=0.10, lookback=60, max_leverage=2.0,
                          starting_capital=sleeve_cap, slippage=SLIPPAGE)
        results['vol_target'] = build_daily_equity(trades, r['equity_curve'], sleeve_cap)
    except Exception as e:
        print(f"    {ticker} vol_targeting error: {e}")
    return results


def build_ticker_equities(basket_name, ticker, sleeve_cap):
    """
    Returns dict {variant_name: daily_equity_Series} for one ticker.
    sleeve_cap = STARTING_CAPITAL / N_total_instruments
    """
    df5 = load_5min(ticker)
    if df5 is None or df5.index.normalize().nunique() < MIN_DAYS:
        return {}

    trades = load_trades(basket_name, ticker)
    if trades is None or len(trades) < 10:
        return {}

    daily_prices = get_daily_closes(ticker, df5)

    results = {}

    try:
        r = simple_bet(trades, bet_size=0.85, starting_capital=sleeve_cap, slippage=SLIPPAGE)
        eq = build_daily_equity(trades, r['equity_curve'], sleeve_cap)
        results['simple'] = eq
    except Exception as e:
        print(f"    {ticker} simple_bet error: {e}")

    try:
        r = intraday_asset_vol(trades, daily_prices, target_vol=0.02, lookback=14,
                               max_leverage=4.0, starting_capital=sleeve_cap, cost_per_share=SLIPPAGE)
        eq = build_daily_equity(trades, r['equity_curve'], sleeve_cap)
        results['asset_vol'] = eq
    except Exception as e:
        print(f"    {ticker} intraday_asset_vol error: {e}")

    try:
        r = vol_targeting(trades, target_vol=0.10, lookback=60, max_leverage=2.0,
                          starting_capital=sleeve_cap, slippage=SLIPPAGE)
        eq = build_daily_equity(trades, r['equity_curve'], sleeve_cap)
        results['vol_target'] = eq
    except Exception as e:
        print(f"    {ticker} vol_targeting error: {e}")

    return results


# -- Main -----------------------------------------------------------------------

def main():
    if not os.path.exists(CANON_PATH):
        print(f"ERROR: {CANON_PATH} not found. Run backtest first."); sys.exit(1)
    with open(CANON_PATH) as f:
        canonical = json.load(f)

    # Load Bonferroni rescued tickers {ticker -> {basket, vwap_threshold, exit_time}}
    rescued = {}
    if os.path.exists(BONF_PATH):
        with open(BONF_PATH) as f:
            bonf = json.load(f)
        for basket_name, results in bonf.get('baskets', {}).items():
            for r in results:
                if r.get('pass'):
                    rescued[r['ticker']] = {
                        'basket': basket_name,
                        'vwap_threshold': r['vwap_threshold'], 'exit_time': r['exit_time'],
                    }
    else:
        print("WARNING: bonferroni results not found -- only basket-passing tickers included.")

    # Guard against non-dict values in canonical.items() (matches ema_crossover's fix)
    passing = {b: p for b, p in canonical.items() if isinstance(p, dict) and p.get('gate_pass', False)}
    print(f"\nPassing baskets:       {len(passing)}/{len(canonical)}")
    print(f"Bonferroni rescued:    {list(rescued.keys()) if rescued else 'none'}")

    # Total validated instruments: all tickers in passing baskets + rescued tickers
    basket_tickers = {t for b in passing for t in BASKETS[b]}
    rescued_only = {t: v for t, v in rescued.items() if t not in basket_tickers}
    N_total = len(basket_tickers) + len(rescued_only)
    print(f"Total instruments:     {N_total} ({len(basket_tickers)} basket + {len(rescued_only)} rescued-only)")

    if N_total == 0:
        print("No validated instruments -- nothing to size."); sys.exit(0)

    sleeve_per_instrument = STARTING_CAPITAL / N_total

    all_equities = {v: {} for v in SIZING_VARIANTS}
    impl_summary = {'baskets': {}, 'rescued': {}}

    # -- Basket-passing tickers (at basket canonical params) ---------------------
    N_baskets = len(passing)
    for basket_name, params in passing.items():
        tickers = BASKETS[basket_name]
        vt = params['vwap_threshold']; et = params['exit_time']
        print(f"\n{'='*60}")
        print(f"Basket: {basket_name} | threshold={vt} exit={et}")

        basket_impl = {}
        for ticker in tickers:
            print(f"  {ticker}:")
            per_ticker = _ckpt('b_'+basket_name+'_'+ticker, lambda: build_ticker_equities(basket_name, ticker, sleeve_per_instrument))
            for variant, eq in per_ticker.items():
                all_equities[variant][ticker] = eq
                ret = eq.pct_change().dropna()
                sh = sharpe(ret); dd = max_dd(eq); ca = cagr(eq)
                print(f"    [{variant}] Sharpe={sh:.3f}  MaxDD={dd:.2%}  CAGR={ca:.2%}")
            if per_ticker:
                basket_impl[ticker] = {v: round(sharpe(per_ticker[v].pct_change().dropna()), 4)
                                       for v in per_ticker}
        impl_summary['baskets'][basket_name] = basket_impl

    # -- Bonferroni rescued tickers (at per-ticker optimal params) --------------
    if rescued_only:
        print(f"\n{'='*60}")
        print(f"Bonferroni rescued tickers ({len(rescued_only)}):")
        for ticker, params in rescued_only.items():
            basket_name = params['basket']
            print(f"  {ticker} (from {basket_name}):")
            per_ticker = _ckpt('r_'+basket_name+'_'+ticker, lambda: build_ticker_equities_bonferroni(basket_name, ticker, sleeve_per_instrument))
            for variant, eq in per_ticker.items():
                all_equities[variant][ticker] = eq
                ret = eq.pct_change().dropna()
                sh = sharpe(ret); dd = max_dd(eq); ca = cagr(eq)
                print(f"    [{variant}] Sharpe={sh:.3f}  MaxDD={dd:.2%}  CAGR={ca:.2%}")
            if per_ticker:
                impl_summary['rescued'][ticker] = {v: round(sharpe(per_ticker[v].pct_change().dropna()), 4)
                                                   for v in per_ticker}

    # -- Combine all instruments into portfolio equity for each variant ---------
    print(f"\n{'='*60}")
    print(f"PORTFOLIO COMBINED (1/N equal-weight, N={N_total} instruments)")
    print(f"{'='*60}")

    portfolio_summary = {}
    combined_by_variant = {}
    for variant in SIZING_VARIANTS:
        curves = all_equities[variant]
        if not curves:
            print(f"  [{variant}] No instruments -- skipped"); continue

        all_dates = sorted(set().union(*[c.index for c in curves.values()]))
        aligned = {t: c.reindex(pd.to_datetime(all_dates)).ffill().bfill()
                   for t, c in curves.items()}
        n = len(aligned)
        combined = sum(c / c.iloc[0] * (STARTING_CAPITAL / n) for c in aligned.values())
        combined.index.name = 'date'
        combined.name = 'equity'

        ret = combined.pct_change().dropna()
        sh  = sharpe(ret)
        dd  = max_dd(combined)
        ca  = cagr(combined)
        print(f"  [{variant}] Sharpe={sh:.4f}  CAGR={ca:.2%}  MaxDD={dd:.2%}  N={n}")

        out_path = os.path.join(EQUITY_DIR, f'combined_equity_{variant}.csv')
        combined.reset_index().to_csv(out_path, index=False)
        print(f"    Saved: {out_path}")

        portfolio_summary[variant] = {
            'sharpe': round(sh, 4), 'cagr': round(ca, 4),
            'max_dd': round(dd, 4), 'n_instruments': n,
        }
        combined_by_variant[variant] = combined

    # -- Select winning variant (highest portfolio Sharpe) and save as final ----
    selected_variant = None
    if portfolio_summary:
        selected_variant = max(portfolio_summary, key=lambda v: portfolio_summary[v]['sharpe'])
        final_path = os.path.join(EQUITY_DIR, 'combined_equity_final.csv')
        combined_by_variant[selected_variant].reset_index().to_csv(final_path, index=False)
        print(f"\n{'='*60}")
        print(f"SELECTED VARIANT: {selected_variant}  "
              f"(Sharpe={portfolio_summary[selected_variant]['sharpe']:.4f})")
        print(f"Saved final: {final_path}")
        print(f"{'='*60}")
    else:
        print("\nWARNING: no variant produced a portfolio equity curve -- nothing selected.")

    # Save implementation summary
    summary = {
        'starting_capital': STARTING_CAPITAL,
        'n_passing_baskets': N_baskets,
        'n_rescued_tickers': len(rescued_only),
        'n_total_instruments': N_total,
        'portfolio': portfolio_summary,
        'selected_variant': selected_variant,
        'selection_criterion': 'highest portfolio Sharpe',
        'instruments': impl_summary,
    }
    json_path = os.path.join(RESULTS_DIR, 'vwap_trend_v2_implementations.json')
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved: {json_path}")

    print("\n-- Sizing Comparison --------------------------------------")
    print(f"{'Variant':<18} {'Sharpe':>8} {'CAGR':>8} {'MaxDD':>8}")
    print("-" * 46)
    for v, s in portfolio_summary.items():
        print(f"  {v:<16} {s['sharpe']:>8.4f} {s['cagr']:>7.2%} {s['max_dd']:>7.2%}")
    print("\nReview the table above.")


if __name__ == '__main__':
    main()
