# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Donchian Channel — Multi-Asset Timing Backtest v2
OPTIMIZATION: single pass per (ticker, channel_period) handles all (mh, sl) combos at once.
Grid: 4 ch x 4 mh x 3 sl = 48 combos
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings, itertools
import numpy as np
import pandas as pd
from scipy.stats import binom
from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test
warnings.filterwarnings("ignore")

STRATEGY_NAME   = "Donchian Channel v2 (Multi-Asset)"
START_DATE      = "2016-01-01"
END_DATE        = "2026-04-01"
TC_BPS_OW       = 5
TC_RT           = 2 * TC_BPS_OW / 10_000

CHANNEL_PERIODS = [10, 20, 30, 50]
MIN_HOLD_DAYS   = [15, 30, 45, 60]
STOP_LOSSES     = [-0.05, -0.08, -0.12]

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
    "us_factor":       ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"],
}
DATA_DIR    = data_dir("daily_tickers")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
UNIV_DIR    = os.path.join(RESULTS_DIR, "donchian_channel_v2_universality")
ALL_COMBOS  = list(itertools.product(CHANNEL_PERIODS, MIN_HOLD_DAYS, STOP_LOSSES))
MH_SL_COMBOS = list(itertools.product(MIN_HOLD_DAYS, STOP_LOSSES))  # 12 combos

def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        return df if len(df) >= 252 and "close" in df.columns else None
    except: return None


def generate_all_trades_for_ch(close_vals, rh_arr, rl_arr, ch):
    """
    ONE pass over close_vals: generates trades for ALL (mh, sl) combos simultaneously.
    Returns: dict {(mh, sl): [(entry_idx, exit_idx, entry_price, exit_price), ...]}
    """
    n = len(close_vals)
    active = {k: None for k in MH_SL_COMBOS}      # k -> (ei, ep) or None
    trades = {k: []   for k in MH_SL_COMBOS}

    for i in range(ch + 1, n):
        cp = close_vals[i]
        rl = rl_arr[i]; rh = rh_arr[i]
        rh_ok = not np.isnan(rh); rl_ok = not np.isnan(rl)

        for (mh, sl), state in active.items():
            if state is None:
                if rh_ok and cp > rh:
                    active[(mh, sl)] = (i, cp)
            else:
                ei, ep = state
                dh = i - ei; pr = (cp - ep) / ep
                if (pr <= sl) or (rl_ok and cp < rl and dh >= mh) or (dh >= mh * 3):
                    trades[(mh, sl)].append((ei, i, ep, cp))
                    active[(mh, sl)] = None

    # Close open trades at end of data
    for k, state in active.items():
        if state:
            ei, ep = state
            trades[k].append((ei, n - 1, ep, close_vals[-1]))
    return trades


def monthly_equity_from_trade_list(close_vals, dates, trade_list):
    """Fast monthly equity from trade tuples (ei, xi, ep, xp)."""
    n = len(close_vals)
    arr = np.empty(n); arr[:] = np.nan
    cap = 1.0; prev = -1
    for (ei, xi, ep, xp) in sorted(trade_list):
        if prev + 1 < ei: arr[prev + 1: ei] = cap
        if xi > ei: arr[ei: xi] = cap * (close_vals[ei: xi] / ep)
        net_ret = (xp - ep) / ep - TC_RT
        arr[xi] = cap * (1 + net_ret); cap *= (1 + net_ret); prev = xi
    if prev + 1 < n: arr[prev + 1:] = cap
    eq = pd.Series(arr, index=dates)
    return eq.resample("ME").last().dropna().pct_change().dropna()


def annualized_sharpe(mret):
    r = pd.Series(mret).dropna()
    if len(r) < 6 or r.std() == 0: return 0.0
    return float(r.mean() / r.std() * np.sqrt(12))


def check_3gates(mret, n_boot=500):
    r = pd.Series(mret).dropna()
    if len(r) < 6: return 0
    return (int(ttest_returns(r)["significant"]) +
            int(bootstrap_sharpe(r, n=n_boot)["significant"]) +
            int(permutation_test(r, n=n_boot)["significant"]))


print("=" * 75)
print("DONCHIAN CHANNEL -- Multi-Asset Backtest v2 (single-pass per ch)")
print("=" * 75)
print(f"Grid: {len(CHANNEL_PERIODS)}ch x {len(MIN_HOLD_DAYS)}mh x {len(STOP_LOSSES)}sl = {len(ALL_COMBOS)} combos")

all_tickers = list(dict.fromkeys(t for ts in BASKETS.values() for t in ts))
print("Loading data + pre-computing rolling arrays...")
ticker_data = {}; roll_cache = {}
for t in all_tickers:
    df = load_ohlc(t)
    if df is not None:
        ticker_data[t] = df
        close = df["close"]
        roll_cache[t] = {ch: (close.shift(1).rolling(ch).max().values,
                               close.shift(1).rolling(ch).min().values)
                         for ch in CHANNEL_PERIODS}
    print(f"  {t:<8} {'OK' if df is not None else 'NO DATA'}")

os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(UNIV_DIR, exist_ok=True)
all_combo_rows = {}; summary_per_basket = {}

for basket_name, basket_tickers in BASKETS.items():
    print(f"\n{'='*70}\nBASKET: {basket_name}\n{'='*70}")
    available = [(t, ticker_data[t]) for t in basket_tickers if t in ticker_data]
    if not available: continue
    N = len(available); tickers_avail = [t for t, _ in available]

    # Pre-compute all trades for all (ticker, ch) pairs with one pass each
    # Result: all_trades_cache[ticker][ch][(mh,sl)] = trade_list
    print(f"  Pre-computing signals (1 pass per ticker×ch = {N*len(CHANNEL_PERIODS)} passes)...")
    all_trades_cache = {}
    for ticker, df in available:
        all_trades_cache[ticker] = {}
        cv = df["close"].values; dates = df.index
        for ch in CHANNEL_PERIODS:
            rh, rl = roll_cache[ticker][ch]
            all_trades_cache[ticker][ch] = generate_all_trades_for_ch(cv, rh, rl, ch)

    # Now grid search: just compute equity curves and sharpes (no signal recomputation)
    combo_rows = []
    instr_combo_sharpes = {t: {} for t in tickers_avail}
    print(f"  Computing {len(ALL_COMBOS)} combos x {N} instruments (equity + sharpe only)...")
    print(f"  {'#':>3}  {'ch':>4}  {'mh':>4}  {'sl':>6}  {'med_sh':>7}  {'pass':>5}  {'p':>8}  sig")

    for cidx, (ch, mh, sl) in enumerate(ALL_COMBOS):
        sharpes = []; pass_count = 0
        for ticker, df in available:
            trade_list = all_trades_cache[ticker][ch][(mh, sl)]
            mret = monthly_equity_from_trade_list(df["close"].values, df.index, trade_list)
            if len(mret) < 6:
                instr_combo_sharpes[ticker][(ch, mh, sl)] = np.nan; continue
            sh = annualized_sharpe(mret)
            instr_combo_sharpes[ticker][(ch, mh, sl)] = sh; sharpes.append(sh)
            if check_3gates(mret) >= 2: pass_count += 1
        if not sharpes: continue
        n_v = len(sharpes); med_sh = float(np.median(sharpes))
        bp = float(binom.sf(pass_count - 1, n_v, 0.05)); bs_ = bp < 0.05
        row = {"basket": basket_name, "ch": ch, "mh": mh, "sl": sl,
               "n_instruments": n_v, "median_sharpe": round(med_sh, 4),
               "mean_sharpe": round(float(np.mean(sharpes)), 4), "pass_count": pass_count,
               "binomial_pvalue": round(bp, 6), "binomial_significant": bs_}
        combo_rows.append(row); all_combo_rows.setdefault(basket_name, []).append(row)
        if cidx % 8 == 0 or bs_:
            print(f"  {cidx+1:>3}  {ch:>4}  {mh:>4}  {sl:>6.2f}  {med_sh:>7.3f}  "
                  f"{pass_count:>2}/{n_v}  {bp:>8.4f}  {'YES' if bs_ else ''}")

    if not combo_rows: continue
    instrument_best = {}
    for t in tickers_avail:
        cs = {c: s for c, s in instr_combo_sharpes[t].items() if not np.isnan(s)}
        if cs: instrument_best[t] = max(cs, key=cs.get)
    pd.DataFrame([{"ticker": t, "ch": b[0], "mh": b[1], "sl": b[2],
                   "best_sharpe": round(instr_combo_sharpes[t][b], 4)}
                  for t, b in instrument_best.items()]).to_csv(
        os.path.join(UNIV_DIR, f"{basket_name}_best_combos.csv"), index=False)

    ranked = pd.DataFrame(combo_rows).sort_values(by=["binomial_significant","median_sharpe"],
                                                   ascending=[False,False]).reset_index(drop=True)
    print(f"\n  TOP 5:")
    for _, row in ranked.head(5).iterrows():
        print(f"    ch={int(row['ch'])} mh={int(row['mh'])} sl={row['sl']:.2f}  "
              f"medSh={row['median_sharpe']:.3f}  {int(row['pass_count'])}/{int(row['n_instruments'])}  "
              f"p={row['binomial_pvalue']:.4f}  {'*' if row['binomial_significant'] else ''}")
    cr = ranked.iloc[0]
    canon = {"ch": int(cr["ch"]), "mh": int(cr["mh"]), "sl": float(cr["sl"])}
    binom_p = float(cr["binomial_pvalue"]); verdict = "STRATEGY EXISTS" if binom_p < 0.05 else "NO EVIDENCE"
    print(f"\n  {verdict}: p={binom_p:.4f} | ch={canon['ch']},mh={canon['mh']},sl={canon['sl']} | medSh={cr['median_sharpe']:.3f}")
    summary_per_basket[basket_name] = {
        "instruments": tickers_avail, "n_instruments": int(cr["n_instruments"]),
        "pass_count_at_canon": int(cr["pass_count"]), "binomial_pvalue": round(binom_p, 6),
        "binomial_significant": bool(binom_p < 0.05), "verdict": verdict,
        "canonical_params": canon, "canonical_median_sharpe": float(cr["median_sharpe"]),
    }

grid_rows = [r for rows in all_combo_rows.values() for r in rows]
pd.DataFrame(grid_rows).to_csv(os.path.join(RESULTS_DIR, "donchian_channel_v2_multiasset_grid.csv"), index=False)
with open(os.path.join(RESULTS_DIR, "donchian_channel_v2_multiasset_summary.json"), "w") as f:
    json.dump({"strategy": STRATEGY_NAME, "period": f"{START_DATE}->{END_DATE}",
               "grid": {"channel_periods": CHANNEL_PERIODS, "min_hold_days": MIN_HOLD_DAYS,
                        "stop_losses": STOP_LOSSES, "n_combos": len(ALL_COMBOS)},
               "baskets": summary_per_basket}, f, indent=2, default=str)

print(f"\n{'='*70}\nFINAL RESULTS")
for bn, bd in summary_per_basket.items():
    cp = bd["canonical_params"]; print(f"  {bn}: {bd['verdict']} | ch={cp['ch']},mh={cp['mh']},sl={cp['sl']} | medSh={bd['canonical_median_sharpe']:.3f} | p={bd['binomial_pvalue']:.4f}")
print(f"\n{'='*70}\nDone.\n{'='*70}")


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
                    ticker_data[_t]["close"], generate_donchian_trades_v2(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "donchian_channel_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
