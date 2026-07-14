# -*- coding: utf-8 -*-
"""
Sector Momentum — Multi-Asset Selection Backtest
=================================================
Cross-sectional price momentum applied to sector and factor ETF universes.
Adapted from Sector_Momentum.ipynb (FORMATION=126 ~6m, TOP_N=5 on us_sectors).

Universes
---------
  us_sectors  — 11 SPDR sector ETFs
  us_factor   — 7 factor ETFs

Grid
----
  TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
  REBAL_FREQS = ['ME', '2ME', 'QE', '6ME', '12ME']
  MOM_WINDOWS = [3, 6, 9, 12]   (months)
  = 120 combos × 2 universes = 240 runs total

Significance: 3-gate only (t-test vs zero, bootstrap Sharpe, permutation).

Outputs
-------
  results/sector_momentum_multiasset_grid.csv
  results/sector_momentum_multiasset_summary.json
"""

import sys
import os

import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d)
    assert _p != _d, ".project_root marker not found - place it at the algo_trading root"
    _d = _p
_ROOT = _d
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import warnings
import numpy as np
import pandas as pd
from itertools import product

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGY_NAME    = "Sector Momentum (Multi-Asset)"
SAVE_NAME        = "sector_momentum_multiasset"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

UNIVERSE_SPECS = {
    "us_sectors": ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
    "us_factor":  ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"],
}
MIN_TICKERS_PER_UNIVERSE = 5

TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
MOM_WINDOWS = [3, 6, 9, 12]

_FREQ_MONTHS = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

# v1 canonical reference (from notebook: TOP_N=5, FORMATION=126d≈6m, monthly)
V1_CANONICAL = {"top_pct": round(5/11, 2), "mom_window": 6, "freq": "ME"}

print("=" * 75)
print("SECTOR MOMENTUM — Multi-Asset Backtest")
print("=" * 75)
print(f"\nData dir : {DATA_DIR}")
print(f"Period   : {START_DATE} → {END_DATE}")
print()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_universe_prices(tickers):
    frames = {}
    for ticker in tickers:
        path = os.path.join(DATA_DIR, f"{ticker}.csv")
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, parse_dates=["date"], index_col="date")
            df = df.sort_index()
            df.index = pd.to_datetime(df.index)
            if "close" not in df.columns:
                continue
            s = df["close"].dropna()
            s = s[(s.index >= START_DATE) & (s.index <= END_DATE)]
            if len(s) >= 252:
                frames[ticker] = s
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).sort_index()

UNIVERSES = {}
print("Loading universes:")
for uni_name, tickers in UNIVERSE_SPECS.items():
    wide = load_universe_prices(tickers)
    available = list(wide.columns)
    print(f"  {uni_name:<15}: {len(available):>2}/{len(tickers)} tickers  [{', '.join(available)}]")
    if len(available) >= MIN_TICKERS_PER_UNIVERSE:
        UNIVERSES[uni_name] = wide
    else:
        print(f"  *** {uni_name} excluded — fewer than {MIN_TICKERS_PER_UNIVERSE} tickers ***")

print(f"\nActive universes ({len(UNIVERSES)}): {list(UNIVERSES.keys())}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SIGNAL ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def compute_momentum(prices_wide, mom_window_months, rebalance_freq):
    monthly = prices_wide.resample(rebalance_freq).last()
    months_per_period = _FREQ_MONTHS.get(rebalance_freq, 1)
    periods_per_month = 1.0 / months_per_period
    skip_periods      = 1
    window_periods    = max(1, int(round(mom_window_months * periods_per_month)))

    signal_df = pd.DataFrame(index=monthly.index, columns=monthly.columns, dtype=float)
    for i in range(len(monthly)):
        past_idx   = i - window_periods - skip_periods
        recent_idx = i - skip_periods
        if past_idx < 0 or recent_idx < 0:
            continue
        signal_df.iloc[i] = monthly.iloc[recent_idx] / monthly.iloc[past_idx] - 1
    return signal_df


def basket_portfolio_metrics(trades):
    if trades.empty:
        return {"sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0, "n_trades": 0}
    tc_rt = 2 * TC_BPS_OW / 10_000
    cohort = (trades.groupby("entry_time")["pct_return_gross"]
              .mean().reset_index()
              .rename(columns={"pct_return_gross": "period_return_gross"}))
    cohort["period_return_net"] = cohort["period_return_gross"] - tc_rt
    r = cohort["period_return_net"]
    gaps = cohort["entry_time"].diff().dropna().dt.days
    median_gap = gaps.median() if len(gaps) > 0 else 30
    periods_per_year = 365 / median_gap if median_gap > 0 else 12
    sharpe = r.mean() / r.std() * np.sqrt(periods_per_year) if r.std() > 0 else 0.0
    eq   = STARTING_CAPITAL * (1 + r).cumprod()
    yrs  = (cohort["entry_time"].iloc[-1] - cohort["entry_time"].iloc[0]).days / 365.25
    cagr = (eq.iloc[-1] / STARTING_CAPITAL) ** (1 / yrs) - 1 if yrs > 0 else 0.0
    peak = eq.expanding().max()
    max_dd = ((eq - peak) / peak).min()
    return {"sharpe": round(float(sharpe), 4), "cagr": round(float(cagr * 100), 2),
            "max_dd": round(float(max_dd * 100), 2), "n_trades": len(trades)}


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
            exit_cands = prices_wide.index[prices_wide.index >= rebal_dates[i + 1]]
            if len(exit_cands) == 0:
                continue
            exit_date = exit_cands[0]; exit_reason = "rebalance"
        else:
            exit_date = prices_wide.index[-1]; exit_reason = "end_of_data"
        for sym in top_t:
            if sym not in prices_wide.columns:
                continue
            ep = prices_wide.loc[entry_date, sym]
            xp = prices_wide.loc[exit_date,  sym]
            if pd.isna(ep) or pd.isna(xp):
                continue
            trades.append({"entry_time": entry_date, "exit_time": exit_date,
                           "direction": "long", "instrument": sym,
                           "entry_price": round(float(ep), 4), "exit_price": round(float(xp), 4),
                           "pct_return_gross": round(float((xp - ep) / ep), 6),
                           "exit_reason": exit_reason, "stop_price": np.nan})
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time", "instrument"]).reset_index(drop=True)


def run_single_universe(prices_wide, top_pct, freq, mom_win):
    n = len(prices_wide.columns)
    top_n = max(1, round(n * top_pct))
    try:
        sig    = compute_momentum(prices_wide, mom_win, freq)
        trades = generate_trades(prices_wide, sig, top_n, freq)
        if trades.empty or len(trades) < top_n * 2:
            return None
        return basket_portfolio_metrics(trades)["sharpe"]
    except Exception:
        return None

# ═══════════════════════════════════════════════════════════════════════════════
# 3. GRID SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

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
        s = run_single_universe(prices, top_pct, freq, mom_win)
        row[uni_name] = s
        if s is not None:
            sharpes.append(s)
    row["median_sharpe"] = round(float(np.median(sharpes)), 4) if sharpes else None
    row["min_sharpe"]    = round(float(np.min(sharpes)), 4) if sharpes else None
    row["n_positive"]    = int(sum(s > 0 for s in sharpes))
    results_raw.append(row)
    if idx % 30 == 0:
        print(f"  {idx}/{len(all_combos)} combos done...")

print(f"  {len(all_combos)}/{len(all_combos)} combos done.\n")

grid_df = pd.DataFrame(results_raw)
primary_uni = uni_names[0]
n_primary   = len(UNIVERSES[primary_uni].columns)
grid_df["top_n"] = grid_df["top_pct"].apply(lambda p: max(1, round(n_primary * p)))

# Stability metric
lookup = {(r["top_pct"], r["freq"], r["mom_window"]): r["median_sharpe"]
          for _, r in grid_df.iterrows()}

def get_neighbors(top_pct, freq, mom_win):
    nbrs = []
    for di in [-1, 1]:
        ni = TOP_PCTS.index(top_pct) + di
        if 0 <= ni < len(TOP_PCTS): nbrs.append((TOP_PCTS[ni], freq, mom_win))
    for dj in [-1, 1]:
        nj = REBAL_FREQS.index(freq) + dj
        if 0 <= nj < len(REBAL_FREQS): nbrs.append((top_pct, REBAL_FREQS[nj], mom_win))
    for dk in [-1, 1]:
        nk = MOM_WINDOWS.index(mom_win) + dk
        if 0 <= nk < len(MOM_WINDOWS): nbrs.append((top_pct, freq, MOM_WINDOWS[nk]))
    return nbrs

stab_scores = []
for _, row in grid_df.iterrows():
    nbrs = get_neighbors(row["top_pct"], row["freq"], row["mom_window"])
    nbr_sharpes = [lookup.get(k) for k in nbrs if lookup.get(k) is not None]
    if nbr_sharpes and row["median_sharpe"] and row["median_sharpe"] != 0:
        stab_scores.append(round(float(np.mean(nbr_sharpes)) / row["median_sharpe"], 4))
    else:
        stab_scores.append(None)
grid_df["stability"] = stab_scores

grid_df_sorted = grid_df.sort_values("median_sharpe", ascending=False).reset_index(drop=True)
grid_df_sorted.index = grid_df_sorted.index + 1

print(f"\n{'='*75}")
print("TOP-20 PARAMETER COMBINATIONS")
print(f"{'='*75}")
uni_hdr = "  ".join(f"{u[:12]:>12}" for u in uni_names)
hdr = (f"{'rank':>4}  {'top_pct':>7}  {'top_n':>5}  {'mom':>3}  {'freq':>5}  "
       f"{'med_sharpe':>10}  {'min_sharpe':>10}  {'n_pos':>5}  {'stability':>9}  " + uni_hdr)
print(hdr)
print("-" * len(hdr))
for rank, row in grid_df_sorted.head(20).iterrows():
    uni_vals = "  ".join(f"{row[u]:>12.3f}" if row[u] is not None else f"{'n/a':>12}" for u in uni_names)
    stab_str = f"{row['stability']:>9.3f}" if row['stability'] is not None else f"{'n/a':>9}"
    print(f"{rank:>4}  {row['top_pct']:>7.2f}  {int(row['top_n']):>5}  "
          f"{int(row['mom_window']):>3}  {row['freq']:>5}  "
          f"{row['median_sharpe']:>10.3f}  {row['min_sharpe']:>10.3f}  "
          f"{int(row['n_positive']):>5}  {stab_str}  " + uni_vals)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

os.makedirs(RESULTS_DIR, exist_ok=True)

col_order = (["top_pct", "top_n", "freq", "mom_window", "median_sharpe", "min_sharpe",
               "n_positive", "stability"] + uni_names)
col_order = [c for c in col_order if c in grid_df.columns]
csv_path  = os.path.join(RESULTS_DIR, "sector_momentum_multiasset_grid.csv")
grid_df[col_order].sort_values("median_sharpe", ascending=False).to_csv(csv_path, index=False)
print(f"\n  grid CSV  → {csv_path}")

best = grid_df_sorted.iloc[0]
per_universe = {}
for u in uni_names:
    per_universe[u] = {"n_tickers": len(UNIVERSES[u].columns),
                       "tickers":   list(UNIVERSES[u].columns),
                       "best_sharpe": round(float(best[u]), 4) if best[u] is not None else None}

summary = {
    "strategy":      STRATEGY_NAME,
    "period":        f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "universes":     per_universe,
    "grid_search":   {"top_pcts": TOP_PCTS, "rebal_freqs": REBAL_FREQS,
                      "mom_windows": MOM_WINDOWS,
                      "combos_per_universe": len(all_combos),
                      "total_runs": len(all_combos) * len(UNIVERSES)},
    "best_params": {
        "top_pct":       float(best["top_pct"]),
        "top_n_primary": int(best["top_n"]),
        "mom_window":    int(best["mom_window"]),
        "freq":          best["freq"],
        "median_sharpe": float(best["median_sharpe"]) if best["median_sharpe"] is not None else None,
        "min_sharpe":    float(best["min_sharpe"])    if best["min_sharpe"] is not None else None,
        "n_positive":    int(best["n_positive"]),
        "stability":     float(best["stability"])     if best["stability"] is not None else None,
        "per_universe_sharpe": {u: (round(float(best[u]), 4) if best[u] is not None else None)
                                 for u in uni_names},
    },
}

json_path = os.path.join(RESULTS_DIR, "sector_momentum_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"  summary JSON → {json_path}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SIGNIFICANCE TESTS  (3-gate: t-test vs 0, bootstrap Sharpe, permutation)
# ═══════════════════════════════════════════════════════════════════════════════

from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns

def get_period_returns(prices_wide, top_pct, freq, mom_win):
    n = len(prices_wide.columns)
    top_n = max(1, round(n * top_pct))
    try:
        sig    = compute_momentum(prices_wide, mom_win, freq)
        trades = generate_trades(prices_wide, sig, top_n, freq)
        if trades.empty or len(trades) < top_n * 2:
            return None, None
        tc_rt  = 2 * TC_BPS_OW / 10_000
        cohort = (trades.groupby("entry_time")["pct_return_gross"]
                  .mean().reset_index()
                  .rename(columns={"pct_return_gross": "period_return_gross"}))
        cohort["period_return_net"] = cohort["period_return_gross"] - tc_rt
        r    = cohort.set_index("entry_time")["period_return_net"]
        gaps = cohort["entry_time"].diff().dropna().dt.days
        ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
        return r, ppy
    except Exception:
        return None, None

_top3  = grid_df_sorted.head(3)
_combos = [{"label": "top_pct={:.2f}  mom={}  {}".format(r["top_pct"], int(r["mom_window"]), r["freq"]),
             "top_pct": float(r["top_pct"]), "freq": r["freq"], "mom_window": int(r["mom_window"])}
            for _, r in _top3.iterrows()]

print("\n" + "=" * 75)
print("SIGNIFICANCE TESTS")
print("=" * 75)
print("  (1) t-test: mean period return > 0  [p < 0.05 = pass]")
print("  (2) Bootstrap Sharpe 1000 resamples, 5th pct > 0")
print("  (3) Permutation test 1000 shuffles  [p < 0.05 = pass]")
print()

_pret_cache = {}
for _combo in _combos:
    _tp = _combo["top_pct"]; _freq = _combo["freq"]; _mw = _combo["mom_window"]
    print(f"\n  -- {_combo['label']} --")
    print("  {:<15}  {:>7}  {:>7}  {:>7}  {:>8}  {:>7}  Score".format(
          "Universe", "Sharpe", "t-stat", "t-p", "boot5%", "perm-p"))
    print("  " + "-" * 71)
    for _uni_name, _prices in UNIVERSES.items():
        _ck = (_tp, _freq, _mw, _uni_name)
        if _ck not in _pret_cache:
            _pret_cache[_ck] = get_period_returns(_prices, _tp, _freq, _mw)
        _r_series, _ppy = _pret_cache[_ck]
        if _r_series is None or len(_r_series) < 5:
            print(f"  {_uni_name:<15}  INSUFFICIENT DATA"); continue
        _annualise = np.sqrt(_ppy); _r_arr = np.array(_r_series)
        _sharpe = _r_arr.mean() / _r_arr.std() * _annualise if _r_arr.std() > 0 else 0.0
        _tt     = ttest_returns(_r_series)
        _rng    = np.random.RandomState(42)
        _boot   = [np.random.RandomState(42).choice(_r_arr, size=len(_r_arr), replace=True) for _ in range(1000)]
        _rng2   = np.random.RandomState(42)
        _boot   = [_rng2.choice(_r_arr, size=len(_r_arr), replace=True) for _ in range(1000)]
        _boot_p5 = float(np.percentile([b.mean()/b.std()*_annualise if b.std()>0 else 0.0 for b in _boot], 5))
        _abs_r  = np.abs(_r_arr); _rng3 = np.random.RandomState(42)
        _count  = sum(1 for _ in range(1000) if
                      (_sh := (_abs_r * _rng3.choice([-1,1], size=len(_abs_r))).mean() /
                               (_abs_r * _rng3.choice([-1,1], size=len(_abs_r))).std() * _annualise
                               if (_abs_r * _rng3.choice([-1,1], size=len(_abs_r))).std() > 0 else 0.0) >= _sharpe)
        # Re-do permutation properly
        _rng3 = np.random.RandomState(42); _count = 0
        for _ in range(1000):
            _sh2 = _abs_r * _rng3.choice([-1,1], size=len(_abs_r))
            _ps  = _sh2.mean()/_sh2.std()*_annualise if _sh2.std()>0 else 0.0
            if _ps >= _sharpe: _count += 1
        _perm_p = _count / 1000; _perm_ok = _perm_p < 0.05
        _n_pass = int(_tt["significant"]) + int(_boot_p5 > 0) + int(_perm_ok)
        print("  {:<15}  {:>7.3f}  {:>7.3f}  {:>7.4f}  {:>+8.3f}  {:>7.4f}  [{}/3]{}".format(
              _uni_name, _sharpe, _tt["t_stat"], _tt["p_value"], _boot_p5, _perm_p,
              _n_pass, "  ***" if _n_pass==3 else ("  **" if _n_pass==2 else "")))

print()
print("=" * 75)
print("Significance tests complete.")
print("=" * 75)
