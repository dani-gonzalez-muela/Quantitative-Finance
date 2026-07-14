"""
VWAP Trend — Multi-Asset Backtest v2 + MinHold=10min
Signal: at 9:31, enter long if close > VWAP*(1+threshold), short if close < VWAP*(1-threshold).
Flip when price crosses VWAP, BUT suppress flips until at least 10 minutes have elapsed
since the last flip (min_hold_min=10). Exit at exit_time.
Grid: vwap_threshold [0.0, 0.001, 0.002], exit_time ['15:30', '15:45', '15:55']

Changes vs v2:
  - min_hold_min=10: VWAP-cross flips suppressed within 10 min of last flip
  - slippage=0.005 (0.5%) consistent with the minhold rebuild analysis
  - Output files have _minhold suffix; original v2 results are NOT overwritten
"""
import os, sys, json, warnings, itertools
import numpy as np
import pandas as pd
from datetime import time as dt_time
from scipy import stats
warnings.filterwarnings("ignore")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
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
from _shared.fees import calculate_fees_pct
OUT_DIR  = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(OUT_DIR, exist_ok=True)

MIN_DAYS    = 252
MIN_HOLD_MIN = 10   # suppress VWAP-cross flips for 10 minutes after last flip
SLIP        = 0.005  # 0.5% slippage per side, consistent with minhold rebuild analysis

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
    [0.0, 0.001, 0.002],
    [dt_time(15,30), dt_time(15,45), dt_time(15,55)],
))


def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path): return None
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    return df[['open','high','low','close','volume']].sort_index()


def add_vwap(df5):
    df = df5.copy()
    df['date'] = df.index.normalize()
    df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
    df['hlc3_vol'] = df['hlc3'] * df['volume']
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_hlc3_vol'] = df.groupby('date')['hlc3_vol'].cumsum()
    df['vwap'] = df['cum_hlc3_vol'] / df['cum_vol'].replace(0, np.nan)
    return df


def _fee(entry_price, exit_price, direction):
    """Round-trip fee with 0.5% slippage (consistent with minhold rebuild analysis)."""
    return calculate_fees_pct(entry_price, exit_price, direction, slippage=SLIP)


def run_vwap_minhold(df5, vwap_threshold, exit_time, min_hold_min=MIN_HOLD_MIN):
    """
    Identical to v2 run_vwap but with two changes:
      1. Suppress VWAP-cross flips until min_hold_min minutes have elapsed since
         the last flip (entry counts as t=0 for the first hold window).
      2. slippage=0.005 (0.5%) instead of 0.
    """
    df = add_vwap(df5).between_time('09:30','16:00').copy()
    df['date'] = df.index.date
    df['time']  = df.index.time
    ENTRY_TIME = dt_time(9, 30)
    min_hold_td = pd.Timedelta(minutes=min_hold_min)
    daily_rets = {}

    for day, day_df in df.groupby('date'):
        day_df = day_df.sort_index()
        entry_bar = day_df[day_df['time'] >= ENTRY_TIME]
        if entry_bar.empty: continue
        first_bar  = entry_bar.iloc[0]
        vwap_val   = first_bar['vwap']
        if pd.isna(vwap_val) or vwap_val == 0: continue

        # Entry signal
        if first_bar['close'] > vwap_val * (1 + vwap_threshold):
            position = 1
        elif first_bar['close'] < vwap_val * (1 - vwap_threshold):
            position = -1
        else:
            daily_rets[day] = 0.0
            continue

        entry_price   = first_bar['close']
        last_flip_ts  = first_bar.name   # entry bar timestamp = t=0 for hold window
        day_pnl       = 0.0

        # Precompute arrays for speed
        timestamps = day_df.index
        day_arr    = day_df[['time', 'close', 'vwap']].to_numpy()

        for i in range(len(day_arr)):
            bar_time  = day_arr[i, 0]
            bar_close = float(day_arr[i, 1])
            bar_vwap  = float(day_arr[i, 2])
            bar_ts    = timestamps[i]

            if bar_time <= ENTRY_TIME: continue
            is_exit = bar_time >= exit_time
            if pd.isna(bar_vwap) or bar_vwap == 0: continue

            # Raw flip signal
            should_flip = (position == 1  and bar_close < bar_vwap) or \
                          (position == -1 and bar_close > bar_vwap)

            # Min-hold suppression: ignore flip if < 10 min since last flip
            if should_flip:
                elapsed = bar_ts - last_flip_ts
                if elapsed < min_hold_td:
                    should_flip = False

            if should_flip or is_exit:
                exit_price = bar_close
                gross      = position * (exit_price - entry_price) / entry_price
                d          = 'long' if position == 1 else 'short'
                day_pnl   += gross - _fee(entry_price, exit_price, d)
                position   = 0
                if should_flip and not is_exit:
                    position      = -1 if (bar_close < bar_vwap) else 1
                    entry_price   = bar_close
                    last_flip_ts  = bar_ts   # reset hold window on each actual flip
                else:
                    break

        daily_rets[day] = day_pnl

    return pd.Series(daily_rets)


# ── Statistical tests (identical to v2) ─────────────────────────────────────

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
    return np.percentile([sharpe(pd.Series(rng.choice(r, len(r), replace=True))) for _ in range(n_boot)], 5)

def permutation_p(rets, n_perm=1000, seed=42):
    rng = np.random.default_rng(seed); obs = sharpe(rets); r = rets.values
    return sum(sharpe(pd.Series(rng.permutation(r) * np.sign(rng.uniform(-1,1,len(r))))) >= obs
               for _ in range(n_perm)) / n_perm

def three_gate(monthly):
    if len(monthly) < 12: return False, {}
    p_t   = ttest_p(monthly)
    boot5 = bootstrap_sharpe_5th(monthly)
    perm_p = permutation_p(monthly)
    passed = (p_t < 0.05) and (boot5 > 0) and (perm_p < 0.05)
    return passed, {'t_p': p_t, 'boot5': boot5, 'perm_p': perm_p}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    all_results = []; canonical = {}

    for basket_name, tickers in BASKETS.items():
        print(f"\n{'='*60}\nBasket: {basket_name}")
        ticker_data = {}
        for ticker in tickers:
            df5 = load_5min(ticker)
            if df5 is None or df5.index.normalize().nunique() < MIN_DAYS: continue
            ticker_data[ticker] = df5
        if not ticker_data: continue

        # Grid search over canonical params
        param_sharpes = {}
        for vt, et in PARAM_GRID:
            shs = []
            for ticker, df5 in ticker_data.items():
                try:
                    shs.append(sharpe(run_vwap_minhold(df5, vt, et)))
                except:
                    continue
            if shs:
                param_sharpes[(vt, et)] = np.median(shs)
        if not param_sharpes: continue

        canon = max(param_sharpes, key=param_sharpes.get)
        vt, et = canon
        print(f"  Canonical: threshold={vt} exit={et} (median Sharpe={param_sharpes[canon]:.4f})")

        ticker_rets = {}; t_pvals = []
        for ticker, df5 in ticker_data.items():
            try:
                rets = run_vwap_minhold(df5, vt, et)
                ticker_rets[ticker] = rets
                t_pvals.append(ttest_p(rets))
                all_results.append({
                    'basket':          basket_name,
                    'ticker':          ticker,
                    'vwap_threshold':  vt,
                    'exit_time':       str(et),
                    'sharpe':          sharpe(rets),
                })
            except:
                continue

        N = len(ticker_rets)
        k = sum(p < 0.05 for p in t_pvals)
        binom_p = binomial_test(k, N) if k > 0 else 1.0
        print(f"  Binomial: k={k}/{N} p={binom_p:.4f}", "✓" if binom_p < 0.05 else "✗")

        aligned     = pd.DataFrame(ticker_rets).fillna(0)
        basket_rets = aligned.mean(axis=1)
        basket_rets.index = pd.to_datetime(basket_rets.index)
        try:
            monthly = basket_rets.resample('ME').apply(lambda r: (1+r).prod()-1)
        except ValueError:
            monthly = basket_rets.resample('M').apply(lambda r: (1+r).prod()-1)

        gate_pass, gate_stats = three_gate(monthly)
        print(f"  3-gate: {gate_pass} | {gate_stats}")

        canonical[basket_name] = {
            'vwap_threshold':  float(vt),
            'exit_time':       str(et),
            'binom_p':         float(binom_p),
            'binom_pass':      bool(binom_p < 0.05),
            'gate_pass':       bool(gate_pass),
            'gate_stats':      gate_stats,
            'n_tickers':       N,
            'k_significant':   int(k),
            'median_sharpe':   float(param_sharpes[canon]),
        }

    # Save results — _minhold suffix, originals untouched
    out_csv  = os.path.join(OUT_DIR, 'vwap_trend_v2_minhold_backtest_results.csv')
    out_json = os.path.join(OUT_DIR, 'vwap_trend_v2_minhold_canonical_params.json')
    pd.DataFrame(all_results).to_csv(out_csv, index=False)
    with open(out_json, 'w') as f:
        json.dump(canonical, f, indent=2)

    print("\n── Basket Summary ──")
    for b, c in canonical.items():
        sym = '✓' if c['gate_pass'] else '✗'
        print(f"  {b}: median_sharpe={c['median_sharpe']:.4f}  "
              f"binom_p={c['binom_p']:.4f}  gate={sym}  "
              f"k={c['k_significant']}/{c['n_tickers']}")

    print(f"\nResults saved to:\n  {out_csv}\n  {out_json}")
    return canonical


if __name__ == '__main__':
    main()
