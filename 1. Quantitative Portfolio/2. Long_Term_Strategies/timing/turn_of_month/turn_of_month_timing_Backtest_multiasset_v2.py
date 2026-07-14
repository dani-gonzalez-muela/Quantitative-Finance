# -*- coding: utf-8 -*-
"""
Turn of Month — Multi-Asset Timing Backtest v2
(optimized: vectorized TOM mask + equity builder, no Python day loop)
Grid: 5x5 = 25 combos
"""

import sys, os
import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d)
    assert _p != _d, ".project_root marker not found - place it at the algo_trading root"
    _d = _p
_ROOT = _d
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json, warnings, itertools
import numpy as np
import pandas as pd
from scipy.stats import binom
from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test
warnings.filterwarnings("ignore")

STRATEGY_NAME = "Turn of Month v2 (Multi-Asset)"
START_DATE    = "2016-01-01"
END_DATE      = "2026-04-01"
TC_BPS_OW     = 5
TC_RT         = 2 * TC_BPS_OW / 10_000

N_BEFORE_LIST = [1, 2, 3, 4, 5]
N_AFTER_LIST  = [1, 2, 3, 4, 5]

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
}

DATA_DIR    = data_dir("daily_tickers")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
UNIV_DIR    = os.path.join(RESULTS_DIR, "turn_of_month_v2_universality")
ALL_COMBOS  = list(itertools.product(N_BEFORE_LIST, N_AFTER_LIST))


def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        return df if len(df) >= 252 and "close" in df.columns else None
    except: return None


def build_tom_masks(dates):
    """Pre-compute TOM mask for ALL (n_before, n_after) combos at once."""
    months = dates.to_period("M")
    unique_months = months.unique()
    # For each month, store indices of last N days and first N days
    # We want the max possible (5+5=10 per month), then select subsets
    last_indices = {}  # m -> sorted list of day-of-month indices (0-based in month)
    first_indices = {}
    
    masks = {}  # (nb, na) -> bool array
    
    # Build per-month position lists
    month_day_positions = []  # list of (month_period, array_of_positions)
    for m in unique_months:
        m_pos = np.where(months == m)[0]
        month_day_positions.append((m, m_pos))
    
    for nb, na in ALL_COMBOS:
        mask = np.zeros(len(dates), dtype=bool)
        for m, m_pos in month_day_positions:
            if len(m_pos) == 0: continue
            # last nb days: m_pos[-nb:]
            for p in m_pos[-nb:]: mask[p] = True
            # first na days: m_pos[:na]
            for p in m_pos[:na]:  mask[p] = True
        masks[(nb, na)] = mask
    return masks


def compute_tom_monthly_returns(close_arr, dates, mask):
    """
    Vectorized TOM equity: hold during mask==True, flat otherwise.
    TC applied at each round-trip transition.
    Returns monthly return series.
    """
    n = len(close_arr)
    daily_ret = np.empty(n); daily_ret[0] = 0.0
    daily_ret[1:] = close_arr[1:] / close_arr[:-1] - 1

    # Count round trips for TC
    transitions = np.diff(mask.astype(int))
    n_entries = int((transitions == 1).sum())
    n_exits   = int((transitions == -1).sum())
    n_rt      = min(n_entries, n_exits)
    total_tc  = TC_RT * n_rt

    # Distribute TC as a per-trading-day drag during holding
    n_hold_days = int(mask.sum())
    tc_per_hold_day = total_tc / max(n_hold_days, 1)

    # Equity factor per day: holding days earn daily_ret - tc_drag, flat days = 0
    adj_ret = daily_ret * mask - tc_per_hold_day * mask
    equity  = np.cumprod(1 + adj_ret)
    
    eq_series = pd.Series(equity, index=dates)
    return eq_series.resample("ME").last().dropna().pct_change().dropna()


def annualized_sharpe(mret):
    r = pd.Series(mret).dropna()
    if len(r) < 6 or r.std() == 0: return 0.0
    return float(r.mean() / r.std() * np.sqrt(12))


def check_3gates(mret, n_boot=500):
    r = pd.Series(mret).dropna()
    if len(r) < 6: return 0
    t  = ttest_returns(r)
    bs = bootstrap_sharpe(r, n=n_boot)
    pm = permutation_test(r, n=n_boot)
    return int(t["significant"]) + int(bs["significant"]) + int(pm["significant"])


print("=" * 75)
print("TURN OF MONTH TIMING -- Multi-Asset Backtest v2 (vectorized)")
print("=" * 75)
print(f"Grid: {len(N_BEFORE_LIST)} n_before x {len(N_AFTER_LIST)} n_after = {len(ALL_COMBOS)} combos")

all_tickers = list(dict.fromkeys(t for ts in BASKETS.values() for t in ts))
print("Loading price data...")
ticker_data = {}
for t in all_tickers:
    df = load_ohlc(t); ticker_data[t] = df
    print(f"  {t:<8} {'OK' if df is not None else 'NO DATA'}")

os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(UNIV_DIR, exist_ok=True)
all_combo_rows = {}; summary_per_basket = {}

for basket_name, basket_tickers in BASKETS.items():
    print(f"\n{'='*75}\nBASKET: {basket_name}\n{'='*75}")
    available = [(t, ticker_data[t]) for t in basket_tickers if ticker_data.get(t) is not None]
    if not available: continue
    N = len(available); tickers_avail = [t for t, _ in available]
    instr_combo_sharpes = {t: {} for t in tickers_avail}
    combo_rows = []

    # Pre-compute all TOM masks per instrument (dates vary slightly between tickers)
    # Use the first ticker's dates as reference, then per-ticker
    print(f"  Pre-computing TOM masks for {N} instruments...")
    tom_masks = {}  # ticker -> {(nb,na): mask_arr}
    for ticker, df in available:
        tom_masks[ticker] = build_tom_masks(df.index)

    print(f"  Running {len(ALL_COMBOS)} combos x {N} instruments...")
    print(f"  {'#':>3}  {'nb':>4}  {'na':>4}  {'med_sh':>7}  {'pass':>5}  {'p':>8}  sig")

    for cidx, (nb, na) in enumerate(ALL_COMBOS):
        sharpes = []; pass_count = 0
        for ticker, df in available:
            mask  = tom_masks[ticker][(nb, na)]
            close = df["close"].values
            mret  = compute_tom_monthly_returns(close, df.index, mask)
            if len(mret) < 6:
                instr_combo_sharpes[ticker][(nb, na)] = np.nan; continue
            sh = annualized_sharpe(mret)
            instr_combo_sharpes[ticker][(nb, na)] = sh; sharpes.append(sh)
            if check_3gates(mret) >= 2: pass_count += 1
        if not sharpes: continue
        n_v = len(sharpes); med_sh = float(np.median(sharpes))
        bp = float(binom.sf(pass_count - 1, n_v, 0.05)); bs_ = bp < 0.05
        row = {"basket": basket_name, "n_before": nb, "n_after": na,
               "n_instruments": n_v, "median_sharpe": round(med_sh, 4),
               "mean_sharpe": round(float(np.mean(sharpes)), 4), "pass_count": pass_count,
               "binomial_pvalue": round(bp, 6), "binomial_significant": bs_}
        combo_rows.append(row); all_combo_rows.setdefault(basket_name, []).append(row)
        print(f"  {cidx+1:>3}  {nb:>4}  {na:>4}  {med_sh:>7.3f}  "
              f"{pass_count:>2}/{n_v}  {bp:>8.4f}  {'SIG' if bs_ else ''}")

    if not combo_rows: continue
    instrument_best = {}
    for ticker in tickers_avail:
        cs = {c: sh for c, sh in instr_combo_sharpes[ticker].items() if not np.isnan(sh)}
        if cs: instrument_best[ticker] = max(cs, key=cs.get)
    pd.DataFrame([{"ticker": t, "n_before": b[0], "n_after": b[1],
                   "best_sharpe": round(instr_combo_sharpes[t][b], 4)}
                  for t, b in instrument_best.items()]).to_csv(
        os.path.join(UNIV_DIR, f"{basket_name}_best_combos.csv"), index=False)

    ranked = pd.DataFrame(combo_rows).sort_values(by=["binomial_significant","median_sharpe"],
                                                   ascending=[False,False]).reset_index(drop=True)
    cr = ranked.iloc[0]
    canon = {"n_before": int(cr["n_before"]), "n_after": int(cr["n_after"])}
    binom_p = float(cr["binomial_pvalue"]); verdict = "STRATEGY EXISTS" if binom_p < 0.05 else "NO EVIDENCE"
    print(f"\n  {verdict}: p={binom_p:.6f}, canon=nb={canon['n_before']},na={canon['n_after']}, "
          f"medSh={cr['median_sharpe']:.3f}")
    summary_per_basket[basket_name] = {
        "instruments": tickers_avail, "n_instruments": int(cr["n_instruments"]),
        "pass_count_at_canon": int(cr["pass_count"]), "binomial_pvalue": round(binom_p, 6),
        "binomial_significant": bool(binom_p < 0.05), "verdict": verdict,
        "canonical_params": canon, "canonical_median_sharpe": float(cr["median_sharpe"]),
    }

grid_rows = [r for rows in all_combo_rows.values() for r in rows]
pd.DataFrame(grid_rows).to_csv(os.path.join(RESULTS_DIR, "turn_of_month_v2_multiasset_grid.csv"), index=False)
with open(os.path.join(RESULTS_DIR, "turn_of_month_v2_multiasset_summary.json"), "w") as f:
    json.dump({"strategy": STRATEGY_NAME, "period": f"{START_DATE}->{END_DATE}",
               "grid": {"n_before": N_BEFORE_LIST, "n_after": N_AFTER_LIST, "n_combos": len(ALL_COMBOS)},
               "baskets": summary_per_basket}, f, indent=2, default=str)

print(f"\n{'='*75}\nFINAL RESULTS")
for bn, bd in summary_per_basket.items():
    cp = bd["canonical_params"]
    print(f"  {bn}: {bd['verdict']} | n_before={cp['n_before']}, n_after={cp['n_after']} | "
          f"medSh={bd['canonical_median_sharpe']:.3f} | p={bd['binomial_pvalue']:.4f}")
print(f"\n{'='*75}\nDone.\n{'='*75}")


# ── Tier 2: INTEGRATED Bonferroni rescue (fable refactor 2026-07-02) ─────────
# Runs after Tier 1 on the NEXT execution of this script; on-disk results
# remain canonical until then. Engine: shared/basket_significance.py.
# Requires: summary_per_basket dict + per-instrument best combos + a
# (ticker, combo) -> monthly returns callable. Wire the lambda below to this
# script's own signal/equity functions if the auto-detected name is wrong.
try:
    from _shared.basket_significance import bonferroni_rescue
    if "summary_per_basket" in dir() and "instrument_best" in dir():
        bonferroni_rescue(
            summary_per_basket=summary_per_basket,
            instrument_best=instrument_best,
            monthly_returns_fn=lambda _t, _c: compute_monthly_returns(
                build_daily_equity_from_trades(
                    ticker_data[_t]["close"], generate_tom_trades_v2(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "turn_of_month_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
