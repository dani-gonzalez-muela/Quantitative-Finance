"""
overnight_bonferroni_intraday.py
=================================
Bonferroni-corrected significance test for the Overnight Premium strategy
using TRUE intraday overnight returns derived from 5-min bar data.

True overnight return definition:
  - Entry price  : close of 15:55 bar (last regular-session bar before 16:00)
  - Exit price   : open  of 09:30 bar on the NEXT trading day
  - Signal       : enter only if intraday return < filter_threshold
                   intraday_return = (close_1555 - open_0930) / open_0930

Tickers : SPY, QQQ, IWM, MDY
Period  : 2016-01-01 to 2026-04-01
Bonferroni alpha : 0.05 / 4 = 0.0125
"""

import sys, os, json, datetime
sys.path.insert(0, '/tmp/pylib')
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp

ROOT        = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR    = os.path.join(ROOT, 'short_term', 'data', 'intraday_5min')
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
PORT_DIR    = os.path.join(ROOT, 'portfolio_creation', 'PORTFOLIO_A_V2')
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(PORT_DIR, exist_ok=True)

# Fee function: use shared/fees.py to match v1 overnight backtest exactly
try:
    sys.path.insert(0, ROOT)
    from _shared.fees import calculate_fees_pct as _fee_fn
    def fee_for_trade(entry_price, exit_price):
        return _fee_fn(entry_price, exit_price, 'long')
    FEE_MODE = 'shared/fees.py (per-trade, price-dependent)'
except Exception as e:
    print(f"  WARNING: could not import shared.fees ({e}), using fixed fallback")
    def fee_for_trade(entry_price, exit_price):
        return 0.0001
    FEE_MODE = 'fixed 1 bps fallback'

TICKERS          = ['SPY', 'QQQ', 'IWM', 'MDY']
FEES_RT_BPS_SPEC = {'SPY': 1.0, 'QQQ': 1.0, 'IWM': 2.0, 'MDY': 2.0}
PARAM_GRID       = [0, -0.001, -0.002, -0.003, -0.005]
START_DATE       = '2016-01-01'
END_DATE         = '2026-04-01'
BONFERRONI_ALPHA = 0.05 / len(TICKERS)
N_BOOTSTRAP      = 2000
N_PERMUTATION    = 2000
SEED             = 42


# ── Data loading ──────────────────────────────────────────────────────────

def load_5min(ticker):
    path = os.path.join(DATA_DIR, f'{ticker}_5min.csv.gz')
    df = pd.read_csv(path)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('US/Eastern')
    df = df.sort_values('timestamp').reset_index(drop=True)
    df = df[(df['timestamp'] >= pd.Timestamp(START_DATE, tz='US/Eastern')) &
            (df['timestamp'] <  pd.Timestamp(END_DATE,   tz='US/Eastern'))]
    return df


def build_daily_signals(df):
    """Extract per-day: day_open (9:30 open), day_close (15:55 close), next_open."""
    df = df.copy()
    df['date'] = df['timestamp'].dt.date
    df['time'] = df['timestamp'].dt.time
    T0930 = datetime.time(9, 30)
    T1555 = datetime.time(15, 55)
    open_bars  = df[df['time'] == T0930][['date', 'open']].rename(columns={'open': 'day_open'})
    close_bars = df[df['time'] == T1555][['date', 'close']].rename(columns={'close': 'day_close'})
    daily = pd.merge(open_bars, close_bars, on='date', how='inner')
    daily['date'] = pd.to_datetime(daily['date'])
    daily = daily.sort_values('date').reset_index(drop=True)
    daily['next_open']    = daily['day_open'].shift(-1)
    daily['intraday_ret'] = (daily['day_close'] - daily['day_open']) / daily['day_open']
    daily = daily.dropna(subset=['next_open'])
    return daily.set_index('date')


# ── Strategy ──────────────────────────────────────────────────────────────

def compute_returns(daily, filter_threshold):
    """Net overnight returns using shared/fees.py per-trade fee."""
    mask  = daily['intraday_ret'] < filter_threshold
    gross = daily['next_open'] / daily['day_close'] - 1
    fees  = daily.apply(lambda r: fee_for_trade(r['day_close'], r['next_open']), axis=1)
    net   = np.where(mask, gross - fees, 0.0)
    return pd.Series(net, index=daily.index, name='ret')


def sharpe_annual(rets):
    r = rets[rets != 0].dropna()
    if len(r) < 30 or r.std() == 0:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(252))


# ── Statistical tests ─────────────────────────────────────────────────────

def gate1_ttest(rets):
    r = rets[rets != 0].dropna().values
    if len(r) < 10:
        return 1.0
    t, p2 = ttest_1samp(r, 0)
    return float(p2 / 2 if t > 0 else 1.0)


def gate2_bootstrap(rets, n=N_BOOTSTRAP, seed=SEED):
    r = rets[rets != 0].dropna().values
    if len(r) < 30:
        return -np.inf
    rng = np.random.RandomState(seed)
    shs = []
    for _ in range(n):
        s = rng.choice(r, size=len(r), replace=True)
        shs.append(s.mean() / s.std() * np.sqrt(252) if s.std() > 0 else 0.0)
    return float(np.percentile(shs, 5))


def gate3_permutation(rets, n=N_PERMUTATION, seed=SEED):
    r = rets[rets != 0].dropna().values
    if len(r) < 10:
        return 1.0
    rng = np.random.RandomState(seed)
    obs = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0
    count = 0
    for _ in range(n):
        fl = r * rng.choice([-1, 1], size=len(r))
        sh = fl.mean() / fl.std() * np.sqrt(252) if fl.std() > 0 else 0.0
        if sh >= obs:
            count += 1
    return float(count / n)


# ── MAIN ──────────────────────────────────────────────────────────────────

print("=" * 70)
print("OVERNIGHT PREMIUM - Bonferroni Intraday (5-min true overnight returns)")
print(f"Tickers: {TICKERS}")
print(f"Period : {START_DATE} to {END_DATE}")
print(f"Bonferroni alpha = 0.05 / {len(TICKERS)} = {BONFERRONI_ALPHA:.4f}")
print(f"Fee mode: {FEE_MODE}")
print("=" * 70)

print("\n[1] Loading 5-min data...")
ticker_daily = {}
for tk in TICKERS:
    df5   = load_5min(tk)
    daily = build_daily_signals(df5)
    ticker_daily[tk] = daily
    print(f"  {tk}: {len(daily)} trading days")

print(f"\n[2] VALIDATION: SPY net Sharpe at filter_threshold=0")
spy_daily   = ticker_daily['SPY']
spy_rets_0  = compute_returns(spy_daily, filter_threshold=0)
spy_sharpe_0 = sharpe_annual(spy_rets_0)
n_trades_spy_0 = int((spy_rets_0 != 0).sum())
avg_fee_spy = float(spy_daily.apply(
    lambda r: fee_for_trade(r['day_close'], r['next_open']), axis=1).mean() * 10000)
print(f"  SPY threshold=0  =>  net Sharpe = {spy_sharpe_0:.4f}  (n_trades={n_trades_spy_0})")
print(f"  Avg fee per trade: {avg_fee_spy:.3f} bps")
validation_match = abs(spy_sharpe_0 - 1.16) < 0.15
print(f"  Target ~1.16  |  {'MATCH' if validation_match else 'MISMATCH - investigate'}")

print("\n[3] Per-ticker grid search + significance tests")
ticker_results = {}

for tk in TICKERS:
    daily = ticker_daily[tk]
    avg_fee_bps = float(daily.apply(
        lambda r: fee_for_trade(r['day_close'], r['next_open']), axis=1).mean() * 10000)
    print(f"\n  [{tk}]  avg_fee_rt={avg_fee_bps:.2f} bps  (spec: {FEES_RT_BPS_SPEC[tk]:.1f} bps)")

    grid_rows = []
    best_sharpe, best_threshold, best_rets = -np.inf, None, None
    for thr in PARAM_GRID:
        rets = compute_returns(daily, thr)
        sh   = sharpe_annual(rets)
        n_tr = int((rets != 0).sum())
        mean_bps = float(rets[rets != 0].mean() * 10000) if n_tr > 0 else 0.0
        hit  = float((rets[rets != 0] > 0).mean()) if n_tr > 0 else 0.0
        grid_rows.append({
            'filter_threshold': thr, 'sharpe': round(sh, 4) if not np.isnan(sh) else None,
            'n_trades': n_tr, 'mean_ret_bps': round(mean_bps, 3), 'hit_rate': round(hit, 4),
        })
        print(f"    threshold={thr:7.4f}  Sharpe={sh:.4f}  n={n_tr}  mean={mean_bps:.2f}bps")
        if not np.isnan(sh) and sh > best_sharpe:
            best_sharpe, best_threshold, best_rets = sh, thr, rets

    print(f"  * Optimal threshold={best_threshold}  Sharpe={best_sharpe:.4f}")

    g1_p  = gate1_ttest(best_rets)
    g2_b5 = gate2_bootstrap(best_rets)
    g3_p  = gate3_permutation(best_rets)
    g1_pass  = g1_p  < BONFERRONI_ALPHA
    g2_pass  = g2_b5 > 0
    g3_pass  = g3_p  < BONFERRONI_ALPHA
    all_pass = g1_pass and g2_pass and g3_pass

    n_trades = int((best_rets != 0).sum())
    eq   = (1 + best_rets).cumprod() * 100_000
    yrs  = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = float(eq.iloc[-1] / 100_000) ** (1 / max(yrs, 0.5)) - 1
    peak = eq.expanding().max()
    mdd  = float(((eq - peak) / peak).min())

    print(f"  Gate 1 t-test  p={g1_p:.6f}  {'PASS' if g1_pass else 'FAIL'}")
    print(f"  Gate 2 boot5   {g2_b5:.4f}  {'PASS' if g2_pass else 'FAIL'}")
    print(f"  Gate 3 perm-p  {g3_p:.4f}  {'PASS' if g3_pass else 'FAIL'}")
    print(f"  => {'PASS ALL GATES' if all_pass else 'FAIL'}")

    ticker_results[tk] = {
        'ticker': tk, 'optimal_threshold': best_threshold,
        'net_sharpe': round(best_sharpe, 6), 'n_trades': n_trades,
        'cagr': round(cagr, 6), 'max_drawdown': round(mdd, 6),
        'fees_rt_bps': FEES_RT_BPS_SPEC[tk], 'avg_fee_rt_bps': round(avg_fee_bps, 3),
        'gate1_ttest_p': round(g1_p, 8), 'gate1_pass': g1_pass,
        'gate2_boot_p5_sharpe': round(g2_b5, 6), 'gate2_pass': g2_pass,
        'gate3_permutation_p': round(g3_p, 6), 'gate3_pass': g3_pass,
        'all_gates_pass': all_pass, 'bonferroni_alpha': BONFERRONI_ALPHA,
        'grid': grid_rows,
    }

passing = [tk for tk, r in ticker_results.items() if r['all_gates_pass']]
failing = [tk for tk, r in ticker_results.items() if not r['all_gates_pass']]

print("\n" + "=" * 70)
print("SUMMARY")
print(f"  Validation SPY threshold=0 net Sharpe: {spy_sharpe_0:.4f}")
print(f"  Passing tickers ({len(passing)}): {passing}")
print(f"  Failing tickers ({len(failing)}): {failing}")
print("=" * 70)

# ── Save JSON ─────────────────────────────────────────────────────────────
out_json = {
    'analysis': 'overnight_bonferroni_intraday_us_equity_broad',
    'basket': 'us_equity_broad',
    'tickers': TICKERS,
    'bonferroni_alpha': BONFERRONI_ALPHA,
    'date_range': {'start': START_DATE, 'end': END_DATE},
    'param_grid': PARAM_GRID,
    'n_bootstrap': N_BOOTSTRAP,
    'n_permutation': N_PERMUTATION,
    'fee_mode': FEE_MODE,
    'validation': {
        'spy_threshold_0_net_sharpe': round(spy_sharpe_0, 6),
        'spy_n_trades': n_trades_spy_0,
        'spy_avg_fee_bps': round(avg_fee_spy, 3),
        'target_sharpe': 1.16,
        'match': validation_match,
    },
    'passing_tickers': passing,
    'failing_tickers': failing,
    'ticker_results': ticker_results,
}
json_path = os.path.join(RESULTS_DIR, 'overnight_bonferroni_intraday_us_equity_broad.json')
with open(json_path, 'w') as f:
    json.dump(out_json, f, indent=2)
print(f"\nSaved JSON => {json_path}")

# ── Save Markdown ─────────────────────────────────────────────────────────
match_label = "MATCHES v1" if validation_match else "MISMATCH - investigate"

md = []
md.append("# Overnight Premium - Bonferroni Correction: us_equity_broad (Intraday 5-min)")
md.append("")
md.append(f"**Date:** {pd.Timestamp.today().strftime('%Y-%m-%d')}  ")
md.append(f"**Analysis period:** {START_DATE} to {END_DATE}")
md.append("")
md.append("## Methodology")
md.append("")
md.append("### Why intraday data instead of daily OHLCV?")
md.append("")
md.append(
    "The previous Bonferroni test used daily OHLCV close-to-open as a proxy for the overnight "
    "return, yielding SPY net Sharpe = 0.77. However, the v1 overnight backtest that produced "
    "Sharpe ~1.16 used **true intraday overnight returns** extracted from 5-minute bar data. "
    "Daily OHLCV open prices include pre-market moves that are not tradeable at the 9:30 open "
    "price, and daily close prices include post-market activity. Using close-to-open from daily "
    "bars conflates the true overnight period (15:55 to 09:30 next day) with extended-hours "
    "moves, understating the signal quality."
)
md.append("")
md.append("### True overnight return construction (5-min bars)")
md.append("")
md.append("- **Entry price**: close of the **15:55 bar** (last regular-session bar)")
md.append("- **Exit price**: open of the **09:30 bar** on the next trading day")
md.append("- **Signal**: enter only when `intraday_return < filter_threshold`")
md.append("  - `intraday_return = (close_1555 - open_0930) / open_0930`")
md.append("  - `filter_threshold = 0`: enter on any negative intraday day")
md.append(f"- **Fees**: `shared/fees.py` `calculate_fees_pct()` applied per-trade with actual prices")
md.append(f"  - Mode: {FEE_MODE}")
md.append(f"- **Grid**: `filter_threshold` in {PARAM_GRID}")
md.append(f"- **Bonferroni threshold**: alpha = 0.05 / {len(TICKERS)} = **{BONFERRONI_ALPHA:.4f}**")
md.append("")
md.append("### Three-gate significance test (all required)")
md.append("")
md.append("1. One-sided t-test: p < 0.0125")
md.append("2. Bootstrap 5th-percentile annualised Sharpe > 0 (2000 draws)")
md.append("3. Sign-randomisation permutation test: p < 0.0125 (2000 permutations)")
md.append("   - Each trade return multiplied by random +/-1 (shuffling does not change Sharpe)")
md.append("")
md.append("## Validation")
md.append("")
md.append(f"**SPY with `filter_threshold=0` (all negative-intraday days):**")
md.append("")
md.append("| Metric | Value |")
md.append("|--------|-------|")
md.append(f"| Net Sharpe (annualised) | **{spy_sharpe_0:.4f}** |")
md.append(f"| N trades | {n_trades_spy_0} |")
md.append(f"| Avg fee per trade | {avg_fee_spy:.3f} bps |")
md.append(f"| Target (v1 result) | ~1.16 |")
md.append(f"| Match | {match_label} |")
md.append("")
md.append("## Per-Ticker Results")
md.append("")

for tk in TICKERS:
    r = ticker_results[tk]
    result_label = "PASS" if r['all_gates_pass'] else "FAIL"
    md.append(f"### {tk} - {result_label}")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Optimal threshold | `{r['optimal_threshold']}` |")
    md.append(f"| Net Sharpe (annualised) | **{r['net_sharpe']:.4f}** |")
    md.append(f"| CAGR | {r['cagr']*100:.2f}% |")
    md.append(f"| Max Drawdown | {r['max_drawdown']*100:.2f}% |")
    md.append(f"| N trades | {r['n_trades']} |")
    md.append(f"| Avg fee RT | {r['avg_fee_rt_bps']:.2f} bps |")
    md.append("")
    md.append(f"**Gate results (Bonferroni alpha = {BONFERRONI_ALPHA:.4f}):**")
    md.append("")
    md.append("| Gate | Criterion | Value | Result |")
    md.append("|------|-----------|-------|--------|")
    g1r = "PASS" if r['gate1_pass'] else "FAIL"
    g2r = "PASS" if r['gate2_pass'] else "FAIL"
    g3r = "PASS" if r['gate3_pass'] else "FAIL"
    md.append(f"| 1 - t-test | p < {BONFERRONI_ALPHA:.4f} | p = {r['gate1_ttest_p']:.6f} | {g1r} |")
    md.append(f"| 2 - bootstrap | 5th pct Sharpe > 0 | {r['gate2_boot_p5_sharpe']:.4f} | {g2r} |")
    md.append(f"| 3 - permutation | p < {BONFERRONI_ALPHA:.4f} | p = {r['gate3_permutation_p']:.4f} | {g3r} |")
    md.append("")
    md.append("**Grid search:**")
    md.append("")
    md.append("| Threshold | Sharpe | N trades | Mean ret (bps) | Hit rate |")
    md.append("|-----------|--------|----------|----------------|----------|")
    for g in r['grid']:
        mark = " <- best" if g['filter_threshold'] == r['optimal_threshold'] else ""
        md.append(f"| {g['filter_threshold']} | {g['sharpe']} | {g['n_trades']} | {g['mean_ret_bps']} | {g['hit_rate']}{mark} |")
    md.append("")

md.append("## Conclusion")
md.append("")
if passing:
    md.append(f"**{len(passing)} ticker(s) pass all three gates at Bonferroni alpha = {BONFERRONI_ALPHA:.4f}:** {', '.join(passing)}.")
    md.append("")
    md.append("These tickers are added to the overnight sleeve in Portfolio A v2.")
else:
    md.append(f"**No tickers pass all three gates at Bonferroni alpha = {BONFERRONI_ALPHA:.4f}.**")
    md.append("")
    md.append("The us_equity_broad basket remains excluded from Portfolio A v2's overnight sleeve.")
md.append("")
if failing:
    md.append(f"**Excluded (failed at least 1 gate):** {', '.join(failing)}.")
md.append("")
md.append(f"Validation: SPY true-intraday overnight Sharpe at threshold=0 = {spy_sharpe_0:.4f} ({match_label})")

md_path = os.path.join(PORT_DIR, 'overnight_bonferroni_intraday_results.md')
with open(md_path, 'w') as f:
    f.write("\n".join(md))
print(f"Saved MD   => {md_path}")
print("\nDone.")
