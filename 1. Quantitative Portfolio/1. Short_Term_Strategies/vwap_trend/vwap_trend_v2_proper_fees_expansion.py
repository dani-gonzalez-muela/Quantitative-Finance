"""
VWAP Trend v2 — Multi-Asset Expansion (Proper Fees + MinHold=10min)

Changes vs vwap_trend_Backtest_multiasset_v2_minhold.py:
  - slippage=0 (VWAP limit orders — only SEC + FINRA TAF apply)
  - exit_time fixed to 15:55 (match v1 canonical)
  - Grid: vwap_threshold [0.0, 0.001, 0.002] x exit_time [15:55] only
  - Saves to _proper_fees suffix files (does NOT overwrite existing)

Three-tier framework:
  Step 1: Basket-level 3-gate binomial test
  Step 2: Per-ticker Bonferroni for failed baskets (sign-randomization perm test)
  Step 3: Save results to CSV + JSON

QQQ is already Tier 1 (validated in v1, Sharpe=0.55) — noted but not re-tested.
"""
import os, sys, json, warnings
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

MIN_DAYS     = 252
MIN_HOLD_MIN = 10      # suppress VWAP-cross flips for 10 min after last flip
SLIP         = 0.0     # slippage=0: VWAP limit orders hit at VWAP price exactly
EXIT_TIME    = dt_time(15, 55)
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


def run_vwap(df5, vwap_threshold, exit_time=EXIT_TIME, min_hold_min=MIN_HOLD_MIN, slip=SLIP):
    """
    VWAP trend backtest with minhold and proper fee model.
    slippage=0 because limit orders execute at VWAP; only SEC + FINRA TAF charged.
    """
    df = add_vwap(df5).between_time('09:30', '16:00').copy()
    df['date'] = df.index.date
    df['time'] = df.index.time
    ENTRY_TIME = dt_time(9, 30)
    min_hold_td = pd.Timedelta(minutes=min_hold_min)
    daily_rets = {}

    for day, day_df in df.groupby('date'):
        day_df = day_df.sort_index()
        entry_bar = day_df[day_df['time'] >= ENTRY_TIME]
        if entry_bar.empty: continue
        first_bar = entry_bar.iloc[0]
        vwap_val  = first_bar['vwap']
        if pd.isna(vwap_val) or vwap_val == 0: continue

        if first_bar['close'] > vwap_val * (1 + vwap_threshold):
            position = 1
        elif first_bar['close'] < vwap_val * (1 - vwap_threshold):
            position = -1
        else:
            daily_rets[day] = 0.0
            continue

        entry_price  = first_bar['close']
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
                position   = 0
                if should_flip and not is_exit:
                    position      = -1 if (bar_close < bar_vwap) else 1
                    entry_price   = bar_close
                    last_flip_ts  = bar_ts
                else:
                    break

        daily_rets[day] = day_pnl

    return pd.Series(daily_rets)


# ── Statistical helpers ───────────────────────────────────────────────────────

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
    t, _ = stats.ttest_1samp(monthly.dropna(), 0)
    return (_ / 2) if t > 0 else 1.0  # one-sided

def bootstrap_sharpe_5th(daily, n_boot=N_BOOT, seed=42):
    rng = np.random.default_rng(seed)
    r = daily.values
    boot = [sharpe(pd.Series(rng.choice(r, len(r), replace=True))) for _ in range(n_boot)]
    return np.percentile(boot, 5)

def sign_perm_p(daily, n_perm=N_PERM, seed=42):
    """Sign-randomization permutation test: multiply daily returns by random ±1."""
    rng = np.random.default_rng(seed)
    obs = sharpe(daily)
    r = daily.values
    count = 0
    for _ in range(n_perm):
        signs = rng.choice([-1, 1], size=len(r))
        perm_sh = sharpe(pd.Series(r * signs))
        if perm_sh >= obs:
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

def binomial_test(k, n, p0=0.05):
    if k == 0: return 1.0
    return 1 - stats.binom.cdf(k - 1, n, p0)


# ── Step 1: Basket-level test ─────────────────────────────────────────────────

def run_basket(basket_name, tickers, ticker_data):
    """
    Grid search over thresholds, select best median Sharpe,
    run 3-gate binomial basket test.
    """
    # Grid search
    param_sharpes = {}
    for vt in THRESHOLDS:
        shs = []
        for ticker, df5 in ticker_data.items():
            try:
                shs.append(sharpe(run_vwap(df5, vt)))
            except Exception:
                continue
        if shs:
            param_sharpes[vt] = np.median(shs)

    if not param_sharpes:
        return None, {}, {}

    best_vt = max(param_sharpes, key=param_sharpes.get)
    print(f"  Canonical threshold={best_vt}  median Sharpe={param_sharpes[best_vt]:.4f}")

    # Run each ticker at best params
    ticker_rets = {}
    row_records = []
    t_pvals = []

    for ticker, df5 in ticker_data.items():
        try:
            rets = run_vwap(df5, best_vt)
            ticker_rets[ticker] = rets
            t_monthly = to_monthly(rets)
            p = ttest_p(t_monthly) if len(t_monthly) >= 10 else 1.0
            t_pvals.append(p)
            row_records.append({
                'basket':         basket_name,
                'ticker':         ticker,
                'vwap_threshold': best_vt,
                'exit_time':      str(EXIT_TIME),
                'sharpe':         sharpe(rets),
                'n_days':         len(rets),
            })
        except Exception as e:
            print(f"    ERROR {ticker}: {e}")
            continue

    N = len(ticker_rets)
    k = sum(p < 0.05 for p in t_pvals)
    binom_p = binomial_test(k, N)
    print(f"  Binomial k={k}/{N}  p={binom_p:.4f}  {'✓' if binom_p < 0.05 else '✗'}")

    # Basket-level Sharpe (equal-weight)
    aligned      = pd.DataFrame(ticker_rets).fillna(0)
    basket_daily = aligned.mean(axis=1)
    basket_daily.index = pd.to_datetime(basket_daily.index)
    gate_pass, gate_stats = three_gate(basket_daily)
    print(f"  3-gate: {gate_pass} | t_p={gate_stats['t_p']:.4f}  boot5={gate_stats['boot5']:.4f}  perm_p={gate_stats['perm_p']:.4f}")

    basket_summary = {
        'vwap_threshold':  float(best_vt),
        'exit_time':       str(EXIT_TIME),
        'n_tickers':       N,
        'k_significant':   int(k),
        'binom_p':         float(binom_p),
        'binom_pass':      bool(binom_p < 0.05),
        'basket_sharpe':   float(sharpe(basket_daily)),
        'gate_pass':       bool(gate_pass),
        'gate_stats':      {k: float(v) for k, v in gate_stats.items()},
        'median_sharpe':   float(param_sharpes[best_vt]),
        'param_sharpes':   {str(vt): float(sh) for vt, sh in param_sharpes.items()},
    }

    return basket_summary, ticker_rets, row_records


# ── Step 2: Per-ticker Bonferroni ─────────────────────────────────────────────

def run_per_ticker_bonferroni(basket_name, ticker_data):
    """
    For each ticker: find best threshold, run 3-gate at Bonferroni alpha.
    sign-randomization permutation test (NOT shuffling).
    """
    N = len(ticker_data)
    bonf_alpha = BONF_ALPHA / N
    print(f"  Per-ticker Bonferroni: N={N}  alpha={bonf_alpha:.6f}")

    results = []
    for ticker, df5 in ticker_data.items():
        best_vt = None
        best_sh = -np.inf
        best_rets = None

        for vt in THRESHOLDS:
            try:
                rets = run_vwap(df5, vt)
                sh   = sharpe(rets)
                if not np.isnan(sh) and sh > best_sh:
                    best_sh   = sh
                    best_vt   = vt
                    best_rets = rets
            except Exception:
                continue

        if best_rets is None:
            results.append({'ticker': ticker, 'basket': basket_name,
                            'status': 'no_data', 'pass': False})
            continue

        monthly = to_monthly(best_rets)
        if len(monthly) < 12:
            results.append({'ticker': ticker, 'basket': basket_name,
                            'status': 'insufficient_data', 'pass': False})
            continue

        p_t    = ttest_p(monthly)
        boot5  = bootstrap_sharpe_5th(best_rets)
        perm_p = sign_perm_p(best_rets)

        g1 = p_t    < bonf_alpha
        g2 = boot5  > 0
        g3 = perm_p < bonf_alpha
        passed = g1 and g2 and g3

        sym = '✓' if passed else '✗'
        print(f"    {ticker:6s} thr={best_vt} Sharpe={best_sh:.3f} "
              f"t_p={p_t:.4f} boot5={boot5:.3f} perm_p={perm_p:.4f} {sym}")

        results.append({
            'ticker':          ticker,
            'basket':          basket_name,
            'status':          'analyzed',
            'vwap_threshold':  float(best_vt),
            'net_sharpe':      float(best_sh),
            'n_days':          int(len(best_rets)),
            'bonferroni_alpha': float(bonf_alpha),
            'gate_t_p':        float(p_t),
            'gate_boot5':      float(boot5),
            'gate_perm_p':     float(perm_p),
            'gate1_pass':      bool(g1),
            'gate2_pass':      bool(g2),
            'gate3_pass':      bool(g3),
            'pass':            bool(passed),
        })

    return results, bonf_alpha


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("VWAP Trend v2 — Proper Fees (slippage=0) + MinHold=10min")
    print(f"Grid: threshold={THRESHOLDS}, exit_time={EXIT_TIME}")
    print("=" * 70)

    # Pre-load all ticker data
    print("\nLoading data...")
    all_ticker_data = {}
    for basket_name, tickers in BASKETS.items():
        for ticker in tickers:
            if ticker in all_ticker_data: continue
            df5 = load_5min(ticker)
            if df5 is None:
                print(f"  SKIP {ticker}: no data file")
                continue
            n_days = df5.index.normalize().nunique()
            if n_days < MIN_DAYS:
                print(f"  SKIP {ticker}: only {n_days} days")
                continue
            all_ticker_data[ticker] = df5
    print(f"Loaded {len(all_ticker_data)} tickers with ≥{MIN_DAYS} days")

    # Step 1: Basket-level
    basket_results = {}
    all_row_records = []
    failed_baskets  = {}   # baskets that fail basket-level gate
    passed_baskets  = {}

    for basket_name, tickers in BASKETS.items():
        print(f"\n{'─'*60}")
        print(f"Basket: {basket_name}")
        ticker_data = {t: all_ticker_data[t] for t in tickers if t in all_ticker_data}
        if not ticker_data:
            print("  No data — skip")
            continue

        bsummary, ticker_rets, row_records = run_basket(basket_name, tickers, ticker_data)
        if bsummary is None: continue

        all_row_records.extend(row_records)
        basket_results[basket_name] = bsummary

        if bsummary['gate_pass'] and bsummary['binom_pass']:
            passed_baskets[basket_name] = (ticker_data, bsummary)
        else:
            failed_baskets[basket_name] = ticker_data

    # Save Step 1 CSV
    out_csv = os.path.join(OUT_DIR, 'vwap_trend_v2_minhold_proper_fees_results.csv')
    pd.DataFrame(all_row_records).to_csv(out_csv, index=False)
    print(f"\nStep 1 CSV saved: {out_csv}")

    # Print basket summary
    print("\n── Basket Summary (Step 1) ──")
    for b, c in basket_results.items():
        g = '✓' if (c['gate_pass'] and c['binom_pass']) else '✗'
        print(f"  {b:20s}: Sharpe={c['median_sharpe']:+.3f}  "
              f"binom_p={c['binom_p']:.4f}  gate={'✓' if c['gate_pass'] else '✗'}  "
              f"k={c['k_significant']}/{c['n_tickers']}  PASS={g}")

    # Step 2: Per-ticker Bonferroni for failed baskets
    print("\n" + "=" * 70)
    print("Step 2: Per-Ticker Bonferroni (failed baskets)")
    print("=" * 70)

    bonf_results = {}
    for basket_name, ticker_data in failed_baskets.items():
        print(f"\nBasket: {basket_name}")
        results, bonf_alpha = run_per_ticker_bonferroni(basket_name, ticker_data)
        bonf_results[basket_name] = {
            'bonferroni_alpha': float(bonf_alpha),
            'n_tickers':        len(ticker_data),
            'tickers':          results,
        }

    # Also note passed baskets in bonf_results structure
    for basket_name in passed_baskets:
        bonf_results[basket_name] = {
            'note': 'basket-level test PASSED — per-ticker Bonferroni not needed',
            'basket_pass': True,
        }

    # Save Step 2 JSON
    out_json = os.path.join(OUT_DIR, 'vwap_trend_v2_per_ticker_bonferroni_results.json')

    methodology = {
        "signal": "VWAP Trend: enter at 09:30 if close crosses VWAP*(1±threshold); flip on VWAP cross (min hold 10min); exit at 15:55",
        "grid": "vwap_threshold=[0.0, 0.001, 0.002], exit_time=[15:55]",
        "fee_model": "slippage=0 (VWAP limit orders); SEC fee + FINRA TAF only",
        "min_hold_min": 10,
        "selection": "best params = max net Sharpe per ticker across grid",
        "significance": "3-gate at Bonferroni alpha: one-sided t-test + bootstrap 5th-pct Sharpe>0 + sign-randomization perm-p",
        "perm_test": "sign-randomization: multiply each daily return by random ±1, 1000 iterations",
        "n_perm": N_PERM,
        "n_boot": N_BOOT,
        "bonferroni": {b: round(BONF_ALPHA / len(BASKETS[b]), 6) for b in BASKETS},
    }

    full_json = {
        "methodology":    methodology,
        "basket_results": basket_results,
        "per_ticker":     bonf_results,
    }

    with open(out_json, 'w') as f:
        json.dump(full_json, f, indent=2)
    print(f"\nStep 2 JSON saved: {out_json}")

    # Final summary
    print("\n── Per-Ticker Bonferroni Summary ──")
    all_passing = []
    for basket_name, bdata in bonf_results.items():
        if 'tickers' not in bdata: continue
        passing = [t['ticker'] for t in bdata['tickers'] if t.get('pass', False)]
        if passing:
            print(f"  {basket_name}: {passing}")
            all_passing.extend([(t, basket_name) for t in passing])
        else:
            print(f"  {basket_name}: none")

    print(f"\nAll passing tickers (Bonferroni): {[t for t,b in all_passing]}")
    print("\nNote: QQQ already Tier 1 (v1 validated, Sharpe=0.55)")

    return full_json


if __name__ == '__main__':
    main()
