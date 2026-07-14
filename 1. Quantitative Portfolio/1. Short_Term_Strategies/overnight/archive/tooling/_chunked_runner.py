"""
Chunked driver for overnight_Backtest_multiasset_v2.py -- runs one basket's
Phase 1 or Phase 2 per invocation and persists incrementally to the same
output files main() would produce, so the end result is byte-for-byte
equivalent to a monolithic run. This exists purely because the execution
sandbox kills background processes between tool calls, so a single ~60-90s
run has to be split into <45s chunks. Not part of the shipped pipeline --
delete after the run completes (main() remains the source of truth for any
future re-run).
"""
import sys, os, json
sys.path.insert(0, '.')
import overnight_Backtest_multiasset_v2 as m
import numpy as np
import pandas as pd

TRADES_DIR = os.path.join(m.OUT_DIR, 'trades')
os.makedirs(TRADES_DIR, exist_ok=True)
CANON_PATH = os.path.join(m.OUT_DIR, 'overnight_v2_canonical_params.json')
RESULTS_CSV_PATH = os.path.join(m.OUT_DIR, 'overnight_v2_backtest_results.csv')
BONF_PATH = os.path.join(m.OUT_DIR, 'overnight_v2_bonferroni_results.json')


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def get_ticker_pivots(basket_name):
    tickers = m.BASKETS[basket_name]
    ticker_pivots = {}
    for ticker in tickers:
        df5 = m.load_5min(ticker)
        if df5 is None:
            print(f"  {ticker}: no data"); continue
        n_days = df5.index.normalize().nunique()
        if n_days < m.MIN_DAYS:
            print(f"  {ticker}: only {n_days} days, skip"); continue
        piv = m.build_overnight_pivot(df5)
        if piv.empty or len(piv) < m.MIN_DAYS:
            print(f"  {ticker}: insufficient overnight sessions, skip"); continue
        ticker_pivots[ticker] = piv
    return ticker_pivots


def run_phase1_basket(basket_name):
    print(f"Basket: {basket_name} ({len(m.BASKETS[basket_name])} tickers)")
    ticker_pivots = get_ticker_pivots(basket_name)
    if not ticker_pivots:
        print("  no usable data for basket"); return

    param_sharpes = {}
    for thr in m.PARAM_GRID:
        shs = []
        for ticker, piv in ticker_pivots.items():
            try: shs.append(m.sharpe(m.run_overnight(piv, thr)))
            except Exception: continue
        shs = [s for s in shs if not np.isnan(s)]
        if shs: param_sharpes[thr] = np.median(shs)
    if not param_sharpes:
        print("  no valid params"); return
    canon_thr = max(param_sharpes, key=param_sharpes.get)
    print(f"  Canonical threshold={canon_thr} (median Sharpe={param_sharpes[canon_thr]:.4f})")

    ticker_rets = {}; t_pvals = []
    rows = pd.read_csv(RESULTS_CSV_PATH).to_dict('records') if os.path.exists(RESULTS_CSV_PATH) else []
    rows = [r for r in rows if r.get('basket') != basket_name]  # idempotent: drop stale rows for this basket (smoke-test reruns)
    for ticker, piv in ticker_pivots.items():
        rets = m.run_overnight(piv, canon_thr)
        ticker_rets[ticker] = rets; t_pvals.append(m.ttest_p(rets))
        rows.append({'basket': basket_name, 'ticker': ticker, 'threshold': canon_thr, 'sharpe': m.sharpe(rets)})
    pd.DataFrame(rows).to_csv(RESULTS_CSV_PATH, index=False)

    N = len(ticker_rets); k = sum(p < 0.05 for p in t_pvals)
    binom_p = m.binomial_test(k, N) if k > 0 else 1.0
    print(f"  Binomial: k={k}/{N} p={binom_p:.4f}", "PASS" if binom_p < 0.05 else "fail")

    aligned = pd.DataFrame(ticker_rets).fillna(0)
    basket_rets = aligned.mean(axis=1)
    basket_rets.index = pd.to_datetime(basket_rets.index)
    try:
        monthly = basket_rets.resample('ME').apply(lambda r: (1 + r).prod() - 1)
    except (ValueError, TypeError):
        monthly = basket_rets.resample('M').apply(lambda r: (1 + r).prod() - 1)
    gate_pass, gate_stats = m.three_gate(monthly)
    print(f"  3-gate: {gate_pass} | {gate_stats}")

    canonical = load_json(CANON_PATH, {})
    canonical[basket_name] = {
        'threshold': float(canon_thr),
        'binom_p': float(binom_p), 'binom_pass': bool(binom_p < 0.05),
        'gate_pass': bool(gate_pass), 'gate_stats': gate_stats,
        'n_tickers': N, 'k_significant': int(k),
    }
    with open(CANON_PATH, 'w') as f:
        json.dump(canonical, f, indent=2)

    if gate_pass:
        print(f"  Saving basket trades for {basket_name}...")
        for ticker, piv in ticker_pivots.items():
            _, trades_df = m.run_overnight(piv, canon_thr, return_trades=True)
            if trades_df.empty: continue
            trades_df['instrument'] = ticker; trades_df['basket'] = basket_name
            out_path = os.path.join(TRADES_DIR, f'overnight_v2_trades_{basket_name}_{ticker}.csv')
            trades_df.to_csv(out_path, index=False)
            print(f"    {ticker}: {len(trades_df)} trades saved")
    print(f"DONE Phase1 {basket_name}")


def run_phase2_basket(basket_name):
    print(f"Phase 2 rescue: {basket_name} (alpha={m.BONFERRONI_ALPHA[basket_name]:.4f})")
    ticker_pivots = get_ticker_pivots(basket_name)
    if not ticker_pivots:
        print("  no usable data"); return
    results = m.run_bonferroni_rescue(basket_name, ticker_pivots, TRADES_DIR)

    bonferroni_results = load_json(BONF_PATH, {
        'methodology': 'per-ticker 3-gate at alpha=0.05/N per basket',
        'baskets': {}, 'rescued_tickers': [],
    })
    bonferroni_results['baskets'][basket_name] = results
    rescued = [r['ticker'] for r in results if r.get('pass')]
    all_rescued = sorted(set(bonferroni_results.get('rescued_tickers', [])) | set(rescued))
    bonferroni_results['rescued_tickers'] = all_rescued
    with open(BONF_PATH, 'w') as f:
        json.dump(bonferroni_results, f, indent=2)
    print(f"DONE Phase2 {basket_name}: rescued={rescued}")


def finalize():
    canonical = load_json(CANON_PATH, {})
    canonical['_run_info'] = ("v2 multiasset backtest (5-min session-based overnight window, "
                               "ported from OG_Research + archived v1window prototype) -- "
                               "3-gate significance (t-test + bootstrap + sign-permutation), "
                               "Bonferroni rescue for failed baskets, trade CSVs emitted for sizing")
    with open(CANON_PATH, 'w') as f:
        json.dump(canonical, f, indent=2)

    print("\n-- Summary --")
    for b, c in canonical.items():
        if not isinstance(c, dict): continue
        print(f"  {b}: gate={'PASS' if c['gate_pass'] else 'fail'}  k={c['k_significant']}/{c['n_tickers']}")
    bonf = load_json(BONF_PATH, {'rescued_tickers': []})
    print(f"Bonferroni rescued: {bonf.get('rescued_tickers') or 'none'}")
    print("FINALIZED")


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'phase1':
        run_phase1_basket(sys.argv[2])
    elif mode == 'phase2':
        run_phase2_basket(sys.argv[2])
    elif mode == 'finalize':
        finalize()
    else:
        raise ValueError(mode)
