# -*- coding: utf-8 -*-
"""
Bond Trend — Multi-Asset Selection Backtest
============================================
Adapts bond_trend_selection_backtest.py to ETF universes.
Original signal: 12m return > 0 → long; else flat (binary trend-follow).
Multiasset adaptation: cross-sectional momentum on bond ETFs — rank by
N-month return, hold top_pct fraction (generalises the binary rule).

Universes
---------
  bonds_us    — TLT, IEF, SHY, TIP, BIL, LQD, HYG
  bonds_intl  — EMB, BNDX  (thin — 2 tickers; note in results)

Grid
----
  TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
  REBAL_FREQS = ['ME', '2ME', 'QE', '6ME', '12ME']
  MOM_WINDOWS = [3, 6, 9, 12]   (months)
  = 120 combos × 2 universes = 240 total runs

Outputs
-------
  results/bond_trend_multiasset_grid.csv
  results/bond_trend_multiasset_summary.json
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

import json, warnings
import numpy as np
import pandas as pd
from itertools import product

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "Bond Trend (Multi-Asset)"
SAVE_NAME        = "bond_trend_multiasset"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

UNIVERSE_SPECS = {
    "bonds_us":   ["TLT","IEF","SHY","TIP","BIL","LQD","HYG"],
    "bonds_intl": ["EMB","BNDX"],
}
MIN_TICKERS = 2

TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
MOM_WINDOWS = [3, 6, 9, 12]
_FREQ_MONTHS = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

print("=" * 75)
print("BOND TREND — Multi-Asset Backtest")
print("=" * 75)
print(f"Period   : {START_DATE} → {END_DATE}\n")

# ── Data loading ──────────────────────────────────────────────────────────────

def load_universe_prices(tickers):
    frames = {}
    for ticker in tickers:
        path = os.path.join(DATA_DIR, f"{ticker}.csv")
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
            df.index = pd.to_datetime(df.index)
            if "close" not in df.columns:
                continue
            s = df["close"].dropna()
            s = s[(s.index >= START_DATE) & (s.index <= END_DATE)]
            if len(s) >= 252:
                frames[ticker] = s
        except Exception:
            pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()

UNIVERSES = {}
print("Loading universes:")
for uni_name, tickers in UNIVERSE_SPECS.items():
    wide = load_universe_prices(tickers)
    available = list(wide.columns)
    print(f"  {uni_name:<15}: {len(available):>2}/{len(tickers)} tickers  [{', '.join(available)}]")
    if len(available) >= MIN_TICKERS:
        UNIVERSES[uni_name] = wide
    else:
        print(f"  *** {uni_name} excluded — only {len(available)} tickers ***")

print(f"\nActive universes ({len(UNIVERSES)}): {list(UNIVERSES.keys())}")

# ── Signal + portfolio helpers ────────────────────────────────────────────────

def compute_momentum(prices_wide, mom_window_months, rebalance_freq):
    monthly = prices_wide.resample(rebalance_freq).last()
    months_per_period = _FREQ_MONTHS.get(rebalance_freq, 1)
    window_periods = max(1, int(round(mom_window_months / months_per_period)))
    signal_df = pd.DataFrame(index=monthly.index, columns=monthly.columns, dtype=float)
    for i in range(len(monthly)):
        past_idx = i - window_periods - 1   # skip-1-period
        if past_idx < 0 or i - 1 < 0:
            continue
        signal_df.iloc[i] = monthly.iloc[i-1] / monthly.iloc[past_idx] - 1
    return signal_df


def generate_trades(prices_wide, signal_df, top_n, rebalance_freq):
    rebal_dates = signal_df.dropna(how="all").index.tolist()
    trades = []
    for i, rd in enumerate(rebal_dates):
        scores = signal_df.loc[rd].dropna()
        top_t  = scores.nlargest(top_n).index.tolist() if top_n < len(scores) else scores.index.tolist()
        if not top_t:
            continue
        entry_cands = prices_wide.index[prices_wide.index >= rd]
        if len(entry_cands) == 0:
            continue
        entry_date = entry_cands[0]
        if i + 1 < len(rebal_dates):
            exit_cands = prices_wide.index[prices_wide.index >= rebal_dates[i+1]]
            if len(exit_cands) == 0:
                continue
            exit_date = exit_cands[0]; exit_reason = "rebalance"
        else:
            exit_date = prices_wide.index[-1]; exit_reason = "end_of_data"
        for sym in top_t:
            if sym not in prices_wide.columns:
                continue
            ep = prices_wide.loc[entry_date, sym]; xp = prices_wide.loc[exit_date, sym]
            if pd.isna(ep) or pd.isna(xp):
                continue
            trades.append({"entry_time": entry_date, "exit_time": exit_date, "direction": "long",
                           "instrument": sym, "entry_price": round(float(ep), 4),
                           "exit_price": round(float(xp), 4),
                           "pct_return_gross": round(float((xp-ep)/ep), 6),
                           "exit_reason": exit_reason, "stop_price": np.nan})
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time","instrument"]).reset_index(drop=True)


def basket_metrics(trades):
    if trades.empty:
        return {"sharpe": 0.0}
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
    cohort.columns = ["entry_time","gross"]
    cohort["net"] = cohort["gross"] - tc_rt
    r = cohort["net"]
    gaps = cohort["entry_time"].diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    sh   = r.mean() / r.std() * np.sqrt(ppy) if r.std() > 0 else 0.0
    return {"sharpe": round(float(sh), 4)}


def run_single(prices, top_pct, freq, mom_win):
    n = len(prices.columns)
    top_n = max(1, round(n * top_pct))
    try:
        sig    = compute_momentum(prices, mom_win, freq)
        trades = generate_trades(prices, sig, top_n, freq)
        if trades.empty or len(trades) < max(top_n, 2):
            return None
        return basket_metrics(trades)["sharpe"]
    except Exception:
        return None

# ── Grid search ───────────────────────────────────────────────────────────────

all_combos = list(product(TOP_PCTS, REBAL_FREQS, MOM_WINDOWS))
uni_names  = list(UNIVERSES.keys())

print(f"\n{'='*75}")
print(f"GRID SEARCH — {len(all_combos)} combos × {len(UNIVERSES)} universes = "
      f"{len(all_combos)*len(UNIVERSES)} runs")
print(f"{'='*75}\n")

results_raw = []
for idx, (top_pct, freq, mom_win) in enumerate(all_combos, 1):
    row = {"top_pct": top_pct, "freq": freq, "mom_window": mom_win}
    sharpes = []
    for uni_name, prices in UNIVERSES.items():
        s = run_single(prices, top_pct, freq, mom_win)
        row[uni_name] = s
        if s is not None:
            sharpes.append(s)
    row["median_sharpe"] = round(float(np.median(sharpes)), 4) if sharpes else None
    row["min_sharpe"]    = round(float(np.min(sharpes)), 4) if sharpes else None
    row["n_positive"]    = int(sum(s > 0 for s in sharpes))
    results_raw.append(row)
    if idx % 30 == 0:
        print(f"  {idx}/{len(all_combos)} done...")

print(f"  {len(all_combos)}/{len(all_combos)} done.\n")

grid_df = pd.DataFrame(results_raw)
n_prim  = len(UNIVERSES[uni_names[0]].columns)
grid_df["top_n"] = grid_df["top_pct"].apply(lambda p: max(1, round(n_prim * p)))

lookup = {(r["top_pct"], r["freq"], r["mom_window"]): r["median_sharpe"]
          for _, r in grid_df.iterrows()}
stab_scores = []
for _, row in grid_df.iterrows():
    nbrs = []
    for di in [-1,1]:
        ni = TOP_PCTS.index(row["top_pct"]) + di
        if 0<=ni<len(TOP_PCTS): nbrs.append((TOP_PCTS[ni], row["freq"], row["mom_window"]))
    for dj in [-1,1]:
        nj = REBAL_FREQS.index(row["freq"]) + dj
        if 0<=nj<len(REBAL_FREQS): nbrs.append((row["top_pct"], REBAL_FREQS[nj], row["mom_window"]))
    for dk in [-1,1]:
        nk = MOM_WINDOWS.index(row["mom_window"]) + dk
        if 0<=nk<len(MOM_WINDOWS): nbrs.append((row["top_pct"], row["freq"], MOM_WINDOWS[nk]))
    nbr_s = [lookup.get(k) for k in nbrs if lookup.get(k) is not None]
    if nbr_s and row["median_sharpe"] and row["median_sharpe"] != 0:
        stab_scores.append(round(float(np.mean(nbr_s)) / row["median_sharpe"], 4))
    else:
        stab_scores.append(None)
grid_df["stability"] = stab_scores
grid_df_sorted = grid_df.sort_values("median_sharpe", ascending=False).reset_index(drop=True)
grid_df_sorted.index += 1

print(f"{'='*75}\nTOP-20 PARAMETER COMBINATIONS\n{'='*75}")
for rank, row in grid_df_sorted.head(20).iterrows():
    uni_vals = "  ".join(f"{row[u]:>8.3f}" if row[u] is not None else f"{'n/a':>8}" for u in uni_names)
    stab_str = f"{row['stability']:>7.3f}" if row['stability'] is not None else "    n/a"
    print(f"{rank:>4}  top_pct={row['top_pct']:.2f}  mom={int(row['mom_window']):>2}  "
          f"{row['freq']:>5}  med={row['median_sharpe']:>6.3f}  stab={stab_str}  [{uni_vals}]")

# ── Save outputs ──────────────────────────────────────────────────────────────

os.makedirs(RESULTS_DIR, exist_ok=True)
best = grid_df_sorted.iloc[0]
col_order = ["top_pct","top_n","freq","mom_window","median_sharpe","min_sharpe","n_positive","stability"] + uni_names
grid_df[[c for c in col_order if c in grid_df.columns]].sort_values(
    "median_sharpe", ascending=False).to_csv(os.path.join(RESULTS_DIR, "bond_trend_multiasset_grid.csv"), index=False)

per_universe = {u: {"n_tickers": len(UNIVERSES[u].columns), "tickers": list(UNIVERSES[u].columns),
                     "best_sharpe": round(float(best[u]), 4) if best[u] is not None else None}
                for u in uni_names}

summary = {
    "strategy": STRATEGY_NAME, "period": f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW, "universes": per_universe,
    "grid_search": {"top_pcts": TOP_PCTS, "rebal_freqs": REBAL_FREQS, "mom_windows": MOM_WINDOWS,
                    "combos_per_universe": len(all_combos), "total_runs": len(all_combos)*len(UNIVERSES)},
    "best_params": {
        "top_pct": float(best["top_pct"]), "top_n_primary": int(best["top_n"]),
        "mom_window": int(best["mom_window"]), "freq": best["freq"],
        "median_sharpe": float(best["median_sharpe"]) if best["median_sharpe"] is not None else None,
        "min_sharpe": float(best["min_sharpe"]) if best["min_sharpe"] is not None else None,
        "n_positive": int(best["n_positive"]),
        "stability": float(best["stability"]) if best["stability"] is not None else None,
        "per_universe_sharpe": {u: (round(float(best[u]), 4) if best[u] is not None else None) for u in uni_names},
    },
}
with open(os.path.join(RESULTS_DIR, "bond_trend_multiasset_summary.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"\n  grid CSV + summary JSON → {RESULTS_DIR}")

# ── Significance tests ────────────────────────────────────────────────────────

from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns

def get_period_returns(prices, top_pct, freq, mom_win):
    n = len(prices.columns); top_n = max(1, round(n*top_pct))
    try:
        sig    = compute_momentum(prices, mom_win, freq)
        trades = generate_trades(prices, sig, top_n, freq)
        if trades.empty or len(trades) < max(top_n, 2):
            return None, None
        cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
        cohort["net"] = cohort["pct_return_gross"] - 2*TC_BPS_OW/10_000
        r = cohort.set_index("entry_time")["net"]
        gaps = cohort["entry_time"].diff().dropna().dt.days
        ppy  = 365/gaps.median() if len(gaps)>0 else 12
        return r, ppy
    except Exception:
        return None, None

_top3 = grid_df_sorted.head(3)
print("\n" + "="*75 + "\nSIGNIFICANCE TESTS\n" + "="*75)

_pret_cache = {}
for _, _r in _top3.iterrows():
    _tp = float(_r["top_pct"]); _freq = _r["freq"]; _mw = int(_r["mom_window"])
    print(f"\n  -- top_pct={_tp:.2f}  mom={_mw}  {_freq} --")
    print("  {:<15}  {:>7}  {:>7}  {:>7}  {:>8}  {:>7}  Score".format("Universe","Sharpe","t-stat","t-p","boot5%","perm-p"))
    print("  "+"-"*71)
    for _uni, _prices in UNIVERSES.items():
        _ck = (_tp, _freq, _mw, _uni)
        if _ck not in _pret_cache:
            _pret_cache[_ck] = get_period_returns(_prices, _tp, _freq, _mw)
        _r_s, _ppy = _pret_cache[_ck]
        if _r_s is None or len(_r_s) < 5:
            print(f"  {_uni:<15}  INSUFFICIENT DATA"); continue
        _ann = np.sqrt(_ppy); _ra = np.array(_r_s)
        _sh  = _ra.mean()/_ra.std()*_ann if _ra.std()>0 else 0.0
        _tt  = ttest_returns(_r_s)
        _rng = np.random.RandomState(42)
        _bs  = [_rng.choice(_ra, size=len(_ra), replace=True) for _ in range(1000)]
        _bp5 = float(np.percentile([b.mean()/b.std()*_ann if b.std()>0 else 0.0 for b in _bs], 5))
        _abs = np.abs(_ra); _rng2 = np.random.RandomState(42); _cnt = 0
        for _ in range(1000):
            _sh2 = _abs*_rng2.choice([-1,1],size=len(_abs))
            if (_sh2.mean()/_sh2.std()*_ann if _sh2.std()>0 else 0.0) >= _sh: _cnt+=1
        _pp  = _cnt/1000
        _np_ = int(_tt["significant"]) + int(_bp5>0) + int(_pp<0.05)
        print("  {:<15}  {:>7.3f}  {:>7.3f}  {:>7.4f}  {:>+8.3f}  {:>7.4f}  [{}/3]{}".format(
              _uni, _sh, _tt["t_stat"], _tt["p_value"], _bp5, _pp, _np_,
              "  ***" if _np_==3 else ("  **" if _np_==2 else "")))

print("\n"+"="*75+"\nSignificance tests complete.\n"+"="*75)
