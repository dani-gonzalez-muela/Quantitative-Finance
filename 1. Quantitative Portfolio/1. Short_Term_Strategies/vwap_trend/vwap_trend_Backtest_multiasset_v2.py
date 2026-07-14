"""
VWAP Trend — Multi-Asset Backtest v2 (canonical)

Signal: at 09:30, enter long if close > VWAP*(1+threshold), short if close < VWAP*(1-threshold).
Flip when price crosses VWAP, but suppress flips until min_hold_min minutes have elapsed
since the last flip (debounces whipsaws). Exit at 15:55.

Methodology locked in per family standardization decision (2026-07-01):
  - 5-minute bars (short_term/data/intraday_5min), matching the rest of the family.
  - min_hold_min = 10 (from the minhold rescue: suppresses VWAP-cross whipsaws).
  - slippage = 0.0 — VWAP-cross entries/exits are modeled as limit orders that fill
    exactly at VWAP/close; only SEC fee + FINRA TAF apply (calculate_fees_pct).
    This is the "proper fees" / optimistic-fill assumption, chosen as canonical
    over the 0.5% flat-slippage alternative.
  - exit_time fixed at 15:55 (grid search is over vwap_threshold only).
  - Grid: vwap_threshold in [0.0, 0.001, 0.002].

This supersedes vwap_trend_Backtest_multiasset_v2_minhold.py and
vwap_trend_v2_proper_fees_expansion.py, which are folded into this single
two-phase script (matching the ema_crossover_Backtest_multiasset_v2.py pattern).
Those two files, STATUS.md, and the pre-multiasset single-ticker QQQ artifacts
are superseded historical references only — see README.md.

Phase 1: Per-basket grid search over vwap_threshold. Canonical params = max
         median Sharpe across instruments in basket. 3-gate significance test
         (t-test, bootstrap Sharpe, sign-randomization permutation) on the
         equal-weight basket composite.
Phase 2: For baskets that fail Phase 1, per-ticker Bonferroni-corrected rescue
         (alpha = 0.05/N tickers in basket).
Trade-level CSVs are emitted for basket-passing tickers (Phase 1) and rescued
tickers (Phase 2), for Implementation to load directly (no signal recompute).

Outputs:
  results/vwap_trend_v2_backtest_results.csv
  results/vwap_trend_v2_canonical_params.json
  results/vwap_trend_v2_bonferroni_results.json
  results/trades/vwap_trend_v2_trades_{basket}_{ticker}.csv              (basket-passing)
  results/trades/vwap_trend_v2_trades_bonferroni_{basket}_{ticker}.csv   (Bonferroni rescued)
"""
import os, sys, json, warnings, itertools
import numpy as np
import pandas as pd
from datetime import time as dt_time
from scipy import stats
warnings.filterwarnings("ignore")

# -- fable path bootstrap (Phase C fix: replaces dead session-specific paths) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
_sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file

ROOT = _bd
DATA_DIR = data_dir('intraday_5min')
OUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
os.makedirs(OUT_DIR, exist_ok=True)

from _shared.fees import calculate_fees_pct

MIN_DAYS     = 252
MIN_HOLD_MIN = 10       # suppress VWAP-cross flips for 10 min after last flip
SLIP         = 0.0      # VWAP limit orders fill exactly at VWAP; only reg. fees apply
EXIT_TIME    = dt_time(15, 55)
ENTRY_TIME   = dt_time(9, 30)
THRESHOLDS   = [0.0, 0.001, 0.002]
N_PERM       = 1000
N_BOOT       = 1000
BONF_ALPHA   = 0.05

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "DIA", "MDY", "IVV", "VOO"],
    "us_factor":       ["IWF", "IWD", "MTUM", "USMV", "VTV", "VUG", "DVY", "QUAL"],
    "us_sectors":      ["XLK", "XLC", "XLI", "XLV", "XLY", "XLF", "XLE", "XLU", "XLB", "XLP", "XLRE"],
    "bonds_us":        ["TLT", "IEF", "SHY", "HYG", "LQD"],
    "commodities":     ["GLD", "SLV", "USO", "GDX"],
    "em_regional":     ["EEM", "EWZ", "INDA", "EWW"],
    "intl_liquid":     ["EFA", "EZU", "EWJ", "EWG", "EWU"],
}

BONFERRONI_ALPHA = {b: BONF_ALPHA / len(t) for b, t in BASKETS.items()}


def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    if not os.path.exists(path): return None
    df = pd.read_csv(path, index_col='timestamp')
    df.index = pd.to_datetime(df.index, utc=True).tz_convert('US/Eastern')
    return df[['open', 'high', 'low', 'close', 'volume']].sort_index()


def add_vwap(df5):
    df = df5.copy()
    df['date'] = df.index.normalize()
    df['hlc3'] = (df['high'] + df['low'] + df['close']) / 3
    df['hlc3_vol'] = df['hlc3'] * df['volume']
    df['cum_vol'] = df.groupby('date')['volume'].cumsum()
    df['cum_hlc3_vol'] = df.groupby('date')['hlc3_vol'].cumsum()
    df['vwap'] = df['cum_hlc3_vol'] / df['cum_vol'].replace(0, np.nan)
    return df


def run_vwap(df5, vwap_threshold, exit_time=EXIT_TIME, min_hold_min=MIN_HOLD_MIN,
             slip=SLIP, return_trades=False):
    df = add_vwap(df5).between_time('09:30', '16:00').copy()
    df['date'] = df.index.date
    df['time'] = df.index.time
    min_hold_td = pd.Timedelta(minutes=min_hold_min)
    daily_rets = {}
    trades_list = [] if return_trades else None

    for day, day_df in df.groupby('date'):
        day_df = day_df.sort_index()
        entry_bar = day_df[day_df['time'] >= ENTRY_TIME]
        if entry_bar.empty: continue
        first_bar = entry_bar.iloc[0]
        vwap_val = first_bar['vwap']
        if pd.isna(vwap_val) or vwap_val == 0: continue

        if first_bar['close'] > vwap_val * (1 + vwap_threshold):
            position = 1
        elif first_bar['close'] < vwap_val * (1 - vwap_threshold):
            position = -1
        else:
            daily_rets[day] = 0.0
            continue

        entry_price  = first_bar['close']
        entry_time   = first_bar.name
        last_flip_ts = first_bar.name
        day_pnl      = 0.0
        timestamps   = day_df.index
        day_arr      = day_df[['time', 'close', 'vwap']].to_numpy()

        for i in range(len(day_arr)):
            bar_time  = day_arr[i, 0]
            bar_close = float(day_arr[i, 1])
            bar_vwap  = float(day_arr[i, 2])
            bar_ts    = timestamps[i]
            if bar_time <= ENTRY_TIME: continue
            is_exit = bar_time >= exit_time
            if pd.isna(bar_vwap) or bar_vwap == 0: continue

            should_flip = (position == 1  and bar_close < bar_vwap) or \
                          (position == -1 and bar_close > bar_vwap)
            if should_flip:
                elapsed = bar_ts - last_flip_ts
                if elapsed < min_hold_td:
                    should_flip = False

            if should_flip or is_exit:
                exit_price = bar_close
                gross      = position * (exit_price - entry_price) / entry_price
                d          = 'long' if position == 1 else 'short'
                day_pnl   += gross - calculate_fees_pct(entry_price, exit_price, d, slippage=slip)
                if return_trades:
                    trades_list.append({
                        'entry_time': entry_time, 'exit_time': bar_ts,
                        'entry_price': entry_price, 'exit_price': exit_price,
                        'stop_price': np.nan, 'direction': d,
                    })
                position = 0
                if should_flip and not is_exit:
                    position      = -1 if (bar_close < bar_vwap) else 1
                    entry_price   = bar_close
                    entry_time    = bar_ts
                    last_flip_ts  = bar_ts
                else:
                    break

        daily_rets[day] = day_pnl

    rets_series = pd.Series(daily_rets)
    if return_trades:
        trades_df = pd.DataFrame(trades_list) if trades_list else pd.DataFrame(
            columns=['entry_time', 'exit_time', 'entry_price', 'exit_price', 'stop_price', 'direction'])
        return rets_series, trades_df
    return rets_series


def sharpe(rets):
    if len(rets) < 30: return np.nan
    m, s = rets.mean(), rets.std()
    return m / s * np.sqrt(252) if s > 0 else np.nan

def to_monthly(daily):
    s = daily.copy()
    s.index = pd.to_datetime(s.index)
    try:
        return s.resample('ME').apply(lambda r: (1 + r).prod() - 1)
    except ValueError:
        return s.resample('M').apply(lambda r: (1 + r).prod() - 1)

def ttest_p(monthly):
    if len(monthly) < 10: return 1.0
    t, p = stats.ttest_1samp(monthly.dropna(), 0)
    return (p / 2) if t > 0 else 1.0

def binomial_test(k, n, p0=0.05):
    if k == 0: return 1.0
    return 1 - stats.binom.cdf(k - 1, n, p0)

def bootstrap_sharpe_5th(daily, n_boot=N_BOOT, seed=42):
    rng = np.random.default_rng(seed)
    r = daily.values
    boot = [sharpe(pd.Series(rng.choice(r, len(r), replace=True))) for _ in range(n_boot)]
    return np.percentile(boot, 5)

def sign_perm_p(daily, n_perm=N_PERM, seed=42):
    rng = np.random.default_rng(seed)
    obs = sharpe(daily)
    r = daily.values
    count = 0
    for _ in range(n_perm):
        signs = rng.choice([-1, 1], size=len(r))
        if sharpe(pd.Series(r * signs)) >= obs:
            count += 1
    return count / n_perm

def three_gate(daily, alpha=0.05):
    monthly = to_monthly(daily)
    if len(monthly) < 12:
        return False, {'t_p': np.nan, 'boot5': np.nan, 'perm_p': np.nan}
    p_t    = ttest_p(monthly)
    boot5  = bootstrap_sharpe_5th(daily)
    perm_p = sign_perm_p(daily)
    passed = (p_t < alpha) and (boot5 > 0) and (perm_p < alpha)
    return passed, {'t_p': p_t, 'boot5': boot5, 'perm_p': perm_p}


def run_bonferroni_rescue(basket_name, ticker_data, trades_dir):
    alpha = BONFERRONI_ALPHA[basket_name]
    results = []

    for ticker, df5 in ticker_data.items():
        best_vt, best_sh, best_rets = None, -np.inf, None
        for vt in THRESHOLDS:
            try:
                rets = run_vwap(df5, vt)
                sh = sharpe(rets)
                if not np.isnan(sh) and sh > best_sh:
                    best_vt, best_sh, best_rets = vt, sh, rets
            except Exception:
                continue

        if best_rets is None:
            results.append({'ticker': ticker, 'pass': False, 'reason': 'no valid params'})
            continue

        gate_pass, gate_stats = three_gate(best_rets, alpha=alpha)
        result = {
            'ticker': ticker, 'pass': bool(gate_pass),
            'vwap_threshold': float(best_vt), 'exit_time': str(EXIT_TIME),
            'sharpe': round(float(best_sh), 4),
            'bonferroni_alpha': round(alpha, 6),
            'gate_stats': {k: (float(v) if v is not None and not pd.isna(v) else None)
                           for k, v in gate_stats.items()},
        }

        if gate_pass:
            try:
                _, trades_df = run_vwap(df5, best_vt, return_trades=True)
                if not trades_df.empty:
                    trades_df['instrument'] = ticker
                    trades_df['basket'] = basket_name
                    out_path = os.path.join(trades_dir,
                        f'vwap_trend_v2_trades_bonferroni_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    result['trades_file'] = os.path.basename(out_path)
                    print(f"    {ticker}: RESCUED Sharpe={best_sh:.4f} (alpha={alpha:.6f}) | {len(trades_df)} trades")
            except Exception as e:
                print(f"    {ticker}: trade save error - {e}")
        else:
            print(f"    {ticker}: fail (best Sharpe={best_sh:.4f}, alpha={alpha:.6f})")

        results.append(result)

    return results


def main():
    all_results = []; canonical = {}; ticker_data_cache = {}
    TRADES_DIR = os.path.join(OUT_DIR, 'trades')
    os.makedirs(TRADES_DIR, exist_ok=True)

    for basket_name, tickers in BASKETS.items():
        print(f"\n{'='*60}\nBasket: {basket_name}  ({len(tickers)} tickers)")

        ticker_data = {}
        for ticker in tickers:
            df5 = load_5min(ticker)
            if df5 is None:
                print(f"  {ticker}: no data"); continue
            n_days = df5.index.normalize().nunique()
            if n_days < MIN_DAYS:
                print(f"  {ticker}: only {n_days} days, skip"); continue
            ticker_data[ticker] = df5
        if not ticker_data: continue
        ticker_data_cache[basket_name] = ticker_data

        param_sharpes = {}
        for vt in THRESHOLDS:
            shs = []
            for ticker, df5 in ticker_data.items():
                try: shs.append(sharpe(run_vwap(df5, vt)))
                except Exception: continue
            if shs: param_sharpes[vt] = np.median(shs)
        if not param_sharpes: continue

        canon_vt = max(param_sharpes, key=param_sharpes.get)
        print(f"  Canonical: threshold={canon_vt} exit={EXIT_TIME} (median Sharpe={param_sharpes[canon_vt]:.4f})")

        ticker_rets = {}; t_pvals = []
        for ticker, df5 in ticker_data.items():
            try:
                rets = run_vwap(df5, canon_vt)
                ticker_rets[ticker] = rets
                monthly = to_monthly(rets)
                t_pvals.append(ttest_p(monthly) if len(monthly) >= 10 else 1.0)
                all_results.append({'basket': basket_name, 'ticker': ticker,
                                     'vwap_threshold': canon_vt, 'exit_time': str(EXIT_TIME),
                                     'sharpe': sharpe(rets)})
            except Exception: continue

        N = len(ticker_rets); k = sum(p < 0.05 for p in t_pvals)
        binom_p = binomial_test(k, N)
        print(f"  Binomial test: k={k}/{N} -> p={binom_p:.4f}", "PASS" if binom_p < 0.05 else "fail")

        aligned = pd.DataFrame(ticker_rets).fillna(0)
        basket_rets = aligned.mean(axis=1)
        basket_rets.index = pd.to_datetime(basket_rets.index)
        gate_pass, gate_stats = three_gate(basket_rets)
        print(f"  3-gate: {gate_pass} | {gate_stats}")

        canonical[basket_name] = {
            'vwap_threshold': float(canon_vt), 'exit_time': str(EXIT_TIME),
            'median_sharpe': float(param_sharpes[canon_vt]),
            'binom_p': float(binom_p), 'binom_pass': bool(binom_p < 0.05),
            'gate_pass': bool(gate_pass),
            'gate_stats': {k2: (float(v) if v is not None and not pd.isna(v) else None)
                           for k2, v in gate_stats.items()},
            'n_tickers': N, 'k_significant': int(k),
        }

        if gate_pass:
            print(f"  Saving basket trades for {basket_name}...")
            for ticker, df5 in ticker_data.items():
                try:
                    _, trades_df = run_vwap(df5, canon_vt, return_trades=True)
                    if trades_df.empty: continue
                    trades_df['instrument'] = ticker; trades_df['basket'] = basket_name
                    out_path = os.path.join(TRADES_DIR, f'vwap_trend_v2_trades_{basket_name}_{ticker}.csv')
                    trades_df.to_csv(out_path, index=False)
                    print(f"    {ticker}: {len(trades_df)} trades saved")
                except Exception as e:
                    print(f"    {ticker}: trade save error - {e}")

    pd.DataFrame(all_results).to_csv(os.path.join(OUT_DIR, 'vwap_trend_v2_backtest_results.csv'), index=False)
    with open(os.path.join(OUT_DIR, 'vwap_trend_v2_canonical_params.json'), 'w') as f:
        json.dump(canonical, f, indent=2)

    print(f"\n{'='*60}\nPhase 2 - Bonferroni Rescue")
    failed = [b for b, c in canonical.items() if not c['gate_pass']]
    bonferroni_results = {
        'methodology': 'per-ticker 3-gate at alpha=0.05/N per basket; '
                        f'min_hold={MIN_HOLD_MIN}min, slippage={SLIP}, exit_time={EXIT_TIME}',
        'baskets': {}, 'rescued_tickers': [],
    }
    all_rescued = []
    for basket_name in failed:
        if basket_name not in ticker_data_cache: continue
        print(f"\n  {basket_name} (alpha={BONFERRONI_ALPHA[basket_name]:.6f}):")
        results = run_bonferroni_rescue(basket_name, ticker_data_cache[basket_name], TRADES_DIR)
        bonferroni_results['baskets'][basket_name] = results
        rescued = [r['ticker'] for r in results if r.get('pass')]
        all_rescued.extend(rescued)
    bonferroni_results['rescued_tickers'] = all_rescued

    bonf_path = os.path.join(OUT_DIR, 'vwap_trend_v2_bonferroni_results.json')
    with open(bonf_path, 'w') as f:
        json.dump(bonferroni_results, f, indent=2)

    print(f"\n-- Summary --")
    for b, c in canonical.items():
        print(f"  {b}: gate={'PASS' if c['gate_pass'] else 'fail'}  k={c['k_significant']}/{c['n_tickers']}")
    print(f"Bonferroni rescued: {all_rescued if all_rescued else 'none'}")
    print(f"Outputs: {OUT_DIR}")

if __name__ == '__main__':
    main()
