# -*- coding: utf-8 -*-
"""
Quality/Profitability — Multi-Asset Selection Backtest
=======================================================
Adapts quality_profitability_selection_backtest.py (v1) to ETF universes.
Original v1 signal: FF5 RMW 12m cumulative momentum → binary quality tilt.
When quality signal ON: hold us_equity_broad ETFs with quality tilt;
when OFF: hold broad ETFs only.

Multiasset adaptation:
  - Load FF5 RMW factor from local CSV (same source as v1)
  - Compute N-month cumulative RMW (grid parameter: RMW_WINDOW)
  - Quality signal = 1 if RMW_N > 0, else 0
  - Universe: us_equity_broad (SPY, QQQ, IWM, MDY)
  - When quality ON: hold top_pct ETFs by trailing momentum
    (quality stocks outperform → momentum filter selects quality-tilted instruments)
  - When quality OFF: hold equal-weight us_equity_broad
  This tests whether FF RMW timing generalises to ETF-level timing.

  NOTE: v2 needs individual stock data — flagged below.

Grid
----
  RMW_WINDOWS = [6, 9, 12, 18, 24]   (months — RMW cumulative lookback)
  REBAL_FREQS = ['ME', '2ME', 'QE', '6ME', '12ME']
  TOP_PCTS    = [0.25, 0.50, 0.75, 1.00]
  = 100 combos × 1 universe = 100 total runs

SKIPPED (flagged):
  v2 quality_profitability: Requires individual stock profitability data
  (Compustat gross profit / assets). Cannot run on ETFs.

Outputs
-------
  results/quality_profitability_multiasset_grid.csv
  results/quality_profitability_multiasset_summary.json
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

STRATEGY_NAME    = "Quality/Profitability (Multi-Asset, v1 FF-signal)"
SAVE_NAME        = "quality_profitability_multiasset"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

FF_PATH = os.path.join(os.path.dirname(OUTPUT_BASE), "regime_factor_rotation", "data", "ff_factors_monthly.csv")

UNIVERSE_SPECS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
}
MIN_TICKERS = 2

RMW_WINDOWS = [6, 9, 12, 18, 24]
REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
TOP_PCTS    = [0.25, 0.50, 0.75, 1.00]
_FREQ_MONTHS = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

print("=" * 75)
print("QUALITY/PROFITABILITY — Multi-Asset Backtest (v1 FF-signal)")
print("=" * 75)
print(f"Period   : {START_DATE} → {END_DATE}")
print(f"v2 NOTE  : Flagged as SKIPPED — requires individual stock data (Compustat)")
print()

# ── Load FF5 RMW factor ──────────────────────────────────────────────────────

if not os.path.exists(FF_PATH):
    print(f"ERROR: FF factors file not found at {FF_PATH}")
    print("Exiting — cannot run quality signal without FF data.")
    sys.exit(1)

ff = pd.read_csv(FF_PATH, parse_dates=["Date"], index_col="Date").sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
rmw = ff["RMW"] / 100  # convert from % to decimal

print(f"FF RMW data: {rmw.index[0].date()} → {rmw.index[-1].date()}, {len(rmw)} months")


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
print("\nLoading universes:")
for uni_name, tickers in UNIVERSE_SPECS.items():
    wide = load_universe_prices(tickers)
    available = list(wide.columns)
    print(f"  {uni_name:<15}: {len(available):>2}/{len(tickers)} tickers  [{', '.join(available)}]")
    if len(available) >= MIN_TICKERS:
        UNIVERSES[uni_name] = wide
    else:
        print(f"  *** {uni_name} excluded ***")

print(f"\nActive universes ({len(UNIVERSES)}): {list(UNIVERSES.keys())}")


def compute_quality_signal(rmw_series, rmw_window, rebalance_freq, prices_wide):
    """
    Compute binary quality signal at each rebalance date:
      quality_on = 1 if cumulative RMW over rmw_window months > 0, else 0.
    Also compute momentum rank of ETFs for within-universe selection.
    Returns signal_df: index=rebal_dates, cols=tickers, values = score if
    quality_on else 0.
    """
    monthly_prices = prices_wide.resample(rebalance_freq).last()
    months_per_period = _FREQ_MONTHS.get(rebalance_freq, 1)
    rmw_window_periods = max(1, int(round(rmw_window / months_per_period)))

    # Resample RMW to rebalance frequency (compound)
    rmw_rebal = (1 + rmw_series).resample(rebalance_freq).prod() - 1

    signal_df = pd.DataFrame(index=monthly_prices.index, columns=monthly_prices.columns, dtype=float)

    for i in range(len(monthly_prices)):
        rd = monthly_prices.index[i]
        # RMW cumulative signal
        rmw_window_end   = rmw_rebal.index[rmw_rebal.index <= rd]
        if len(rmw_window_end) < rmw_window_periods + 1:
            signal_df.iloc[i] = 0.0
            continue
        rmw_cum = (1 + rmw_rebal.iloc[
            rmw_rebal.index.get_loc(rmw_window_end[-1]) - rmw_window_periods:
            rmw_rebal.index.get_loc(rmw_window_end[-1])
        ]).prod() - 1
        quality_on = float(rmw_cum) > 0

        if not quality_on:
            # Quality off: flat signal (equal-weight handled in generate_trades)
            # Use score = 0 for all → equal-weight fallback below
            signal_df.iloc[i] = 0.0
        else:
            # Quality on: rank ETFs by trailing momentum (skip-1 period)
            past_idx   = i - rmw_window_periods - 1
            recent_idx = i - 1
            if past_idx < 0 or recent_idx < 0:
                signal_df.iloc[i] = 1.0  # equal-weight when no lookback
            else:
                mom = monthly_prices.iloc[recent_idx] / monthly_prices.iloc[past_idx] - 1
                signal_df.iloc[i] = mom.clip(lower=0)  # only positive momentum

    return signal_df


def generate_trades(prices_wide, signal_df, top_n, rebalance_freq):
    """Generate trades. When signal > 0: hold top_n; when all-zero: hold equal-weight."""
    rebal_dates = signal_df.index.tolist()
    trades = []
    for i, rd in enumerate(rebal_dates):
        scores = signal_df.loc[rd]
        if scores.sum() == 0:
            # Quality off or no data: hold equal-weight (all tickers)
            top_t = prices_wide.columns.tolist()
        else:
            # Quality on: hold top_n by momentum score
            pos_scores = scores[scores > 0]
            top_t = pos_scores.nlargest(top_n).index.tolist() if top_n < len(pos_scores) else pos_scores.index.tolist()
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


def basket_sharpe(trades):
    if trades.empty:
        return None
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
    cohort["net"] = cohort["pct_return_gross"] - tc_rt
    r = cohort["net"]
    if len(r) < 5:
        return None
    gaps = cohort["entry_time"].diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    return round(float(r.mean() / r.std() * np.sqrt(ppy)) if r.std() > 0 else 0.0, 4)


def run_single(prices, top_pct, freq, rmw_win):
    n = len(prices.columns); top_n = max(1, round(n * top_pct))
    try:
        sig    = compute_quality_signal(rmw, rmw_win, freq, prices)
        trades = generate_trades(prices, sig, top_n, freq)
        if trades is None or trades.empty or len(trades) < 4:
            return None
        return basket_sharpe(trades)
    except Exception:
        return None


all_combos = list(product(TOP_PCTS, REBAL_FREQS, RMW_WINDOWS))
uni_names  = list(UNIVERSES.keys())

print(f"\n{'='*75}")
print(f"GRID SEARCH — {len(all_combos)} combos × {len(UNIVERSES)} universes = {len(all_combos)*len(UNIVERSES)} runs")
print(f"{'='*75}\n")

results_raw = []
for idx, (top_pct, freq, rmw_win) in enumerate(all_combos, 1):
    row = {"top_pct": top_pct, "freq": freq, "rmw_window": rmw_win}
    sharpes = []
    for uni_name, prices in UNIVERSES.items():
        s = run_single(prices, top_pct, freq, rmw_win)
        row[uni_name] = s
        if s is not None: sharpes.append(s)
    row["median_sharpe"] = round(float(np.median(sharpes)), 4) if sharpes else None
    row["min_sharpe"]    = round(float(np.min(sharpes)), 4) if sharpes else None
    row["n_positive"]    = int(sum(s > 0 for s in sharpes))
    results_raw.append(row)
    if idx % 20 == 0: print(f"  {idx}/{len(all_combos)} done...")
print(f"  {len(all_combos)}/{len(all_combos)} done.\n")

grid_df = pd.DataFrame(results_raw)
grid_df["top_n"] = grid_df["top_pct"].apply(lambda p: max(1, round(len(UNIVERSES[uni_names[0]].columns)*p)))
grid_df_sorted = grid_df.sort_values("median_sharpe", ascending=False).reset_index(drop=True)
grid_df_sorted.index += 1

print(f"{'='*75}\nTOP-20 PARAMETER COMBINATIONS\n{'='*75}")
for rank, row in grid_df_sorted.head(20).iterrows():
    uni_vals = "  ".join(f"{row[u]:>8.3f}" if row[u] is not None else f"{'n/a':>8}" for u in uni_names)
    print(f"{rank:>4}  top_pct={row['top_pct']:.2f}  rmw_win={int(row['rmw_window'])}  "
          f"{row['freq']:>5}  med={row['median_sharpe']:>6.3f}  [{uni_vals}]")

os.makedirs(RESULTS_DIR, exist_ok=True)
best = grid_df_sorted.iloc[0]
col_order = ["top_pct","top_n","freq","rmw_window","median_sharpe","min_sharpe","n_positive"] + uni_names
grid_df[[c for c in col_order if c in grid_df.columns]].sort_values(
    "median_sharpe", ascending=False).to_csv(os.path.join(RESULTS_DIR, "quality_profitability_multiasset_grid.csv"), index=False)

per_universe = {u: {"n_tickers": len(UNIVERSES[u].columns), "tickers": list(UNIVERSES[u].columns),
                     "best_sharpe": round(float(best[u]), 4) if best[u] is not None else None}
                for u in uni_names}
summary = {
    "strategy": STRATEGY_NAME, "period": f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW, "universes": per_universe,
    "signal_notes": {
        "v1": "FF5 RMW factor signal applied as timing overlay on us_equity_broad ETFs",
        "v2_SKIPPED": "Requires individual stock profitability data (Compustat). Cannot run on ETFs.",
    },
    "grid_search": {"top_pcts": TOP_PCTS, "rebal_freqs": REBAL_FREQS, "rmw_windows": RMW_WINDOWS,
                    "combos_per_universe": len(all_combos), "total_runs": len(all_combos)*len(UNIVERSES)},
    "best_params": {
        "top_pct": float(best["top_pct"]), "top_n_primary": int(best["top_n"]),
        "rmw_window": int(best["rmw_window"]), "freq": best["freq"],
        "median_sharpe": float(best["median_sharpe"]) if best["median_sharpe"] is not None else None,
        "min_sharpe": float(best["min_sharpe"]) if best["min_sharpe"] is not None else None,
        "n_positive": int(best["n_positive"]),
        "per_universe_sharpe": {u: (round(float(best[u]),4) if best[u] is not None else None) for u in uni_names},
    },
}
with open(os.path.join(RESULTS_DIR, "quality_profitability_multiasset_summary.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"\n  grid CSV + summary JSON → {RESULTS_DIR}")

# ── Significance tests ────────────────────────────────────────────────────────
from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns

def get_period_returns(prices, top_pct, freq, rmw_win):
    n = len(prices.columns); top_n = max(1, round(n*top_pct))
    try:
        sig    = compute_quality_signal(rmw, rmw_win, freq, prices)
        trades = generate_trades(prices, sig, top_n, freq)
        if trades is None or trades.empty or len(trades) < 4:
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
print("\n"+"="*75+"\nSIGNIFICANCE TESTS\n"+"="*75)
_pret_cache = {}
for _, _rr in _top3.iterrows():
    _tp = float(_rr["top_pct"]); _freq = _rr["freq"]; _rw = int(_rr["rmw_window"])
    print(f"\n  -- top_pct={_tp:.2f}  rmw_win={_rw}  {_freq} --")
    print("  {:<18}  {:>7}  {:>7}  {:>7}  {:>8}  {:>7}  Score".format("Universe","Sharpe","t-stat","t-p","boot5%","perm-p"))
    print("  "+"-"*74)
    for _uni, _prices in UNIVERSES.items():
        _ck = (_tp, _freq, _rw, _uni)
        if _ck not in _pret_cache: _pret_cache[_ck] = get_period_returns(_prices, _tp, _freq, _rw)
        _r_s, _ppy = _pret_cache[_ck]
        if _r_s is None or len(_r_s) < 5:
            print(f"  {_uni:<18}  INSUFFICIENT DATA"); continue
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
        _pp = _cnt/1000
        _np_ = int(_tt["significant"]) + int(_bp5>0) + int(_pp<0.05)
        print("  {:<18}  {:>7.3f}  {:>7.3f}  {:>7.4f}  {:>+8.3f}  {:>7.4f}  [{}/3]{}".format(
              _uni, _sh, _tt["t_stat"], _tt["p_value"], _bp5, _pp, _np_,
              "  ***" if _np_==3 else ("  **" if _np_==2 else "")))

print("\n"+"="*75+"\nSignificance tests complete.\n"+"="*75)
