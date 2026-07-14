# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Industry Trend — Selection Backtest v2
=======================================
Pilot for unified strategy architecture (Type 2 → Type 1 structure parity).

Signal: Cross-sectional momentum across SPDR sector ETFs.
        Long top_pct sectors; rebalance at given freq.

This script:
  1. Loads daily price data (local parquet, Alpaca fallback)
  2. Grid searches mom_window × top_pct × rebalance_freq (120 combos)
  3. Displays Sharpe grid + YoY hit rate grid per freq
  4. Displays full ranked table (all 120 combos) sorted by Sharpe
  5. DEFAULT_PARAMS block for user to fill in after reviewing grids
  6. Runs canonical analysis using DEFAULT_PARAMS (significance tests + save)

Trade format for simultaneous basket positions
-----------------------------------------------
Each held sector-period is ONE row in trades.csv. With top_pct=0.33 and monthly
rebalance you get ~3 rows per month sharing the same entry_time / exit_time
but with different instruments. shared/implementations.py's build_basket_equity()
is the correct engine for consumption (see Implementation v2).

DO NOT RUN: no execution in this file. Run from project root.
"""

import sys
import os

# ── Path setup — resolve to long_term/ root so imports work ──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import warnings
import numpy as np
import pandas as pd
from itertools import product

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGY_NAME    = "Industry Trend"
SAVE_NAME        = "industry_trend"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"

# SPDR sector ETFs — full current lineup (XLC added 2018, XLRE added 2015)
SECTORS = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]

OUTPUT_BASE  = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(OUTPUT_BASE, "results")
TC_BPS_OW    = 5  # one-way transaction cost in bps (applied on entry AND exit)

# ── Parameter grid ──
TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
# top_pct=1.0 is the "hold everything" baseline — no selection signal

REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
# ME=monthly, 2ME=bi-monthly, QE=quarterly, 6ME=semi-annual, 12ME=annual

MOM_WINDOWS = [3, 6, 9, 12]
# lookback for momentum signal (months)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("INDUSTRY TREND — Backtest v2")
print("=" * 70)

# ── Try local parquet first, fall back to Alpaca API ──
_PARQUET_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../../../long_term/archived_strategies/output/prices_validated.parquet",
)
_PARQUET_PATH = os.path.normpath(_PARQUET_PATH)

prices_wide = None

if os.path.exists(_PARQUET_PATH):
    print(f"\nLoading prices from local parquet:\n  {_PARQUET_PATH}")
    _raw = pd.read_parquet(_PARQUET_PATH)
    _raw.index = pd.to_datetime(_raw.index)
    _raw = _raw.sort_index()
    # Filter to our sectors (parquet may have extra cols like SPY, TLT, etc.)
    available = [s for s in SECTORS if s in _raw.columns]
    missing   = [s for s in SECTORS if s not in _raw.columns]
    prices_wide = _raw[available].copy()
    prices_wide = prices_wide[
        (prices_wide.index >= START_DATE) & (prices_wide.index <= END_DATE)
    ]
    print(f"Available sectors ({len(available)}): {available}")
    if missing:
        print(f"Missing from parquet (skipped): {missing}")
    print(f"Date range: {prices_wide.index[0].date()} → {prices_wide.index[-1].date()}")
    print(f"Rows: {len(prices_wide):,}")
else:
    print(f"\nParquet not found at {_PARQUET_PATH}")
    print("Falling back to Alpaca API...")
    try:
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        from _shared.loaders_data import fetch_historical_data

        print(f"Fetching daily price data for {len(SECTORS)} sector ETFs...")
        print(f"Period: {START_DATE} → {END_DATE}\n")

        data_dict = fetch_historical_data(
            SECTORS, TimeFrame(1, TimeFrameUnit.Day), START_DATE, END_DATE
        )

        all_data = {}
        for sym in SECTORS:
            try:
                d = data_dict[sym].copy()
                if d.index.tz is None:
                    d.index = d.index.tz_localize("UTC").tz_convert("US/Eastern")
                else:
                    d.index = d.index.tz_convert("US/Eastern")
                d = d.reset_index()
                d["date"] = d["timestamp"].dt.date
                d = d.groupby("date").last().reset_index()
                d["date"] = pd.to_datetime(d["date"])
                d = d[["date", "open", "close"]].sort_values("date").reset_index(drop=True)
                all_data[sym] = d
                print(f"  {sym}: {len(d):,} bars  {d['date'].iloc[0].date()} → {d['date'].iloc[-1].date()}")
            except Exception as e:
                print(f"  {sym}: FAILED — {e}")

        available = [s for s in SECTORS if s in all_data]
        print(f"\nAvailable sectors ({len(available)}): {available}")

        prices_wide = pd.DataFrame(
            {sym: all_data[sym].set_index("date")["close"] for sym in available}
        )
        prices_wide = prices_wide.sort_index()

    except Exception as e:
        raise RuntimeError(f"Both parquet and Alpaca API failed: {e}")

n_instruments = len(available)
print(f"\nGrid: {len(TOP_PCTS)} top_pcts × {len(REBAL_FREQS)} freqs × {len(MOM_WINDOWS)} mom_windows "
      f"= {len(TOP_PCTS) * len(REBAL_FREQS) * len(MOM_WINDOWS)} combinations")
print(f"n_instruments = {n_instruments}  → top_n = max(1, round(n_instruments × top_pct))")
for p in TOP_PCTS:
    tn = max(1, round(n_instruments * p))
    print(f"  top_pct={p:.2f} → top_n={tn}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SIGNAL ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

# Map each pandas offset alias to approximate months per period
_FREQ_MONTHS = {
    "ME":   1,
    "2ME":  2,
    "QE":   3,
    "6ME":  6,
    "12ME": 12,
}


def compute_momentum(prices_wide, mom_window_months, rebalance_freq):
    """
    Compute skip-last-period momentum at each rebalance date.

    Returns
    -------
    signal_df : pd.DataFrame
        Wide format — index=rebalance dates, columns=sector, values=momentum score.
        Score = (price_{t-1p} / price_{t-1p-window_periods}) - 1
        NaN if insufficient history.
    """
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
        past_price   = monthly.iloc[past_idx]
        recent_price = monthly.iloc[recent_idx]
        signal_df.iloc[i] = recent_price / past_price - 1

    return signal_df


def generate_trades(prices_wide, signal_df, top_n, rebalance_freq, tc_bps_ow=TC_BPS_OW):
    """
    Generate standardized 9-column trades DataFrame for a basket strategy.

    Each holding period for each sector is ONE row. Positions within a cohort
    share the same entry_time / exit_time (simultaneous). stop_price is NaN
    (basket strategy; no individual position stops).

    Net return includes round-trip TC: 2 × tc_bps_ow / 10000.

    Returns
    -------
    trades : pd.DataFrame
        Columns: entry_time, exit_time, direction, instrument, entry_price,
                 exit_price, pct_return_gross, exit_reason, stop_price
    """
    rebal_dates = signal_df.dropna(how="all").index.tolist()
    trades = []

    for i, rd in enumerate(rebal_dates):
        scores = signal_df.loc[rd].dropna()
        if top_n >= len(scores):
            # hold everything (baseline or near-baseline)
            top_sectors = scores.index.tolist()
        else:
            top_sectors = scores.nlargest(top_n).index.tolist()

        if not top_sectors:
            continue

        entry_candidates = prices_wide.index[prices_wide.index >= rd]
        if len(entry_candidates) == 0:
            continue
        entry_date = entry_candidates[0]

        if i + 1 < len(rebal_dates):
            next_rd = rebal_dates[i + 1]
            exit_candidates = prices_wide.index[prices_wide.index >= next_rd]
            if len(exit_candidates) == 0:
                continue
            exit_date   = exit_candidates[0]
            exit_reason = "rebalance"
        else:
            exit_date   = prices_wide.index[-1]
            exit_reason = "end_of_data"

        for sym in top_sectors:
            if sym not in prices_wide.columns:
                continue
            entry_px = prices_wide.loc[entry_date, sym]
            exit_px  = prices_wide.loc[exit_date,  sym]
            if pd.isna(entry_px) or pd.isna(exit_px):
                continue
            pct_gross = (exit_px - entry_px) / entry_px
            trades.append({
                "entry_time":       entry_date,
                "exit_time":        exit_date,
                "direction":        "long",
                "instrument":       sym,
                "entry_price":      round(float(entry_px), 4),
                "exit_price":       round(float(exit_px),  4),
                "pct_return_gross": round(float(pct_gross), 6),
                "exit_reason":      exit_reason,
                "stop_price":       np.nan,
            })

    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time", "instrument"]).reset_index(drop=True)


def basket_portfolio_metrics(trades, tc_bps_ow=TC_BPS_OW):
    """
    Compute Sharpe, CAGR, MaxDD, n_trades, YoY_hit_rate from basket trades.

    Equal-weight across held sectors: each period's return = mean of sector returns.
    TC applied once round-trip per rebalance period.
    """
    if trades.empty:
        return {"sharpe": 0.0, "cagr": 0.0, "max_dd": 0.0, "n_trades": 0, "yoy_hit_rate": 0.0}

    tc_rt = 2 * tc_bps_ow / 10_000

    cohort = (
        trades.groupby("entry_time")["pct_return_gross"]
        .mean()
        .reset_index()
        .rename(columns={"pct_return_gross": "period_return_gross"})
    )
    cohort["period_return_net"] = cohort["period_return_gross"] - tc_rt

    r = cohort["period_return_net"]

    gaps = cohort["entry_time"].diff().dropna().dt.days
    median_gap = gaps.median() if len(gaps) > 0 else 30
    periods_per_year = 365 / median_gap if median_gap > 0 else 12

    sharpe = r.mean() / r.std() * np.sqrt(periods_per_year) if r.std() > 0 else 0.0

    eq = STARTING_CAPITAL * (1 + r).cumprod()
    years = (cohort["entry_time"].iloc[-1] - cohort["entry_time"].iloc[0]).days / 365.25
    cagr  = (eq.iloc[-1] / STARTING_CAPITAL) ** (1 / years) - 1 if years > 0 else 0.0
    peak  = eq.expanding().max()
    max_dd = ((eq - peak) / peak).min()

    # Year-over-year hit rate: % of calendar years with positive return
    cohort["year"] = cohort["entry_time"].dt.year
    annual = cohort.groupby("year")["period_return_net"].sum()
    yoy_hit_rate = (annual > 0).mean() if len(annual) > 0 else 0.0

    return {
        "sharpe":        round(float(sharpe), 4),
        "cagr":          round(float(cagr * 100), 2),
        "max_dd":        round(float(max_dd * 100), 2),
        "n_trades":      len(trades),
        "yoy_hit_rate":  round(float(yoy_hit_rate * 100), 1),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 3. GRID SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

all_combos = list(product(TOP_PCTS, REBAL_FREQS, MOM_WINDOWS))

print(f"\n{'='*70}")
print(f"GRID SEARCH — {len(all_combos)} combinations")
print(f"{'='*70}\n")

grid_results = []

for top_pct, freq, mom_win in all_combos:
    top_n = max(1, round(n_instruments * top_pct))
    try:
        signal_df = compute_momentum(prices_wide, mom_win, freq)
        trades    = generate_trades(prices_wide, signal_df, top_n, freq)
        if trades.empty or len(trades) < top_n * 2:
            continue
        mets = basket_portfolio_metrics(trades)
        grid_results.append({
            "top_pct":         top_pct,
            "top_n":           top_n,
            "mom_window":      mom_win,
            "freq":            freq,
            "sharpe":          mets["sharpe"],
            "cagr":            mets["cagr"],
            "max_dd":          mets["max_dd"],
            "n_trades":        mets["n_trades"],
            "yoy_hit_rate":    mets["yoy_hit_rate"],
        })
    except Exception as e:
        print(f"  Skipped top_pct={top_pct}, freq={freq}, mom={mom_win}: {e}")

grid_df = pd.DataFrame(grid_results)
print(f"Completed: {len(grid_results)} / {len(all_combos)} combinations\n")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. GRID DISPLAY — Sharpe and YoY hit rate by freq
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'='*70}")
print("SHARPE GRID  (by rebalance frequency)")
print(f"{'='*70}")
print(f"  5 bps one-way TC | n_instruments={n_instruments}")
print()

for freq in REBAL_FREQS:
    sub = grid_df[grid_df["freq"] == freq]
    if sub.empty:
        continue
    print(f"=== Rebalance: {freq} ===")
    header = f"{'top_pct':>8} | " + "  ".join(f"mom={w:>2}" for w in MOM_WINDOWS)
    print(header)
    print("-" * 9 + "+" + "-" * (len(header) - 10))
    for pct in TOP_PCTS:
        row = sub[sub["top_pct"] == pct]
        top_n_val = max(1, round(n_instruments * pct))
        tag = f" ← baseline (top_n={top_n_val}={n_instruments})" if pct == 1.0 else f" (top_n={top_n_val})"
        vals = []
        for w in MOM_WINDOWS:
            cell = row[row["mom_window"] == w]
            if cell.empty:
                vals.append("  n/a ")
            else:
                vals.append(f"{cell['sharpe'].values[0]:>6.2f}")
        print(f"{pct:>8.2f} | " + "  ".join(vals) + tag)
    print()

print(f"\n{'='*70}")
print("YoY HIT RATE GRID  (% of calendar years with positive return)")
print(f"{'='*70}")
print()

for freq in REBAL_FREQS:
    sub = grid_df[grid_df["freq"] == freq]
    if sub.empty:
        continue
    print(f"=== Rebalance: {freq} ===")
    header = f"{'top_pct':>8} | " + "  ".join(f"mom={w:>2}" for w in MOM_WINDOWS)
    print(header)
    print("-" * 9 + "+" + "-" * (len(header) - 10))
    for pct in TOP_PCTS:
        row = sub[sub["top_pct"] == pct]
        top_n_val = max(1, round(n_instruments * pct))
        tag = f" ← baseline" if pct == 1.0 else f" (top_n={top_n_val})"
        vals = []
        for w in MOM_WINDOWS:
            cell = row[row["mom_window"] == w]
            if cell.empty:
                vals.append("  n/a ")
            else:
                vals.append(f"{cell['yoy_hit_rate'].values[0]:>5.0f}%")
        print(f"{pct:>8.2f} | " + "  ".join(vals) + tag)
    print()

# ═══════════════════════════════════════════════════════════════════════════════
# 5. FULL RANKED TABLE (all combos, sorted by Sharpe descending)
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'='*70}")
print("FULL RANKED TABLE — all combinations sorted by Sharpe ↓")
print(f"{'='*70}")

ranked = grid_df.sort_values("sharpe", ascending=False).reset_index(drop=True)
ranked.index = ranked.index + 1  # 1-based rank

print(f"\n{'Rank':>4}  {'top_pct':>7}  {'top_n':>5}  {'mom_win':>7}  {'freq':>5}  "
      f"{'Sharpe':>7}  {'CAGR%':>6}  {'MaxDD%':>7}  {'YoY_hit%':>9}")
print("-" * 75)
for rank, row in ranked.iterrows():
    print(f"{rank:>4}  {row['top_pct']:>7.2f}  {int(row['top_n']):>5}  "
          f"{int(row['mom_window']):>7}  {row['freq']:>5}  "
          f"{row['sharpe']:>7.3f}  {row['cagr']:>6.1f}  "
          f"{row['max_dd']:>7.1f}  {row['yoy_hit_rate']:>8.0f}%")

print(f"\nTotal shown: {len(ranked)} combinations")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. DEFAULT_PARAMS  — SET AFTER REVIEWING GRID ABOVE
# ═══════════════════════════════════════════════════════════════════════════════

# ─── UPDATE THIS after reviewing the grids above ───────────────────────────
DEFAULT_PARAMS = {
    "top_pct": 0.33,
    "top_n": 3,  # = round(9 * 0.33)
    "mom_window_months": 6,
    "rebalance_freq": "ME",
}
# ───────────────────────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print("DEFAULT_PARAMS (placeholder — update after reviewing grids):")
for k, v in DEFAULT_PARAMS.items():
    print(f"  {k}: {v}")
print(f"{'='*70}")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. CANONICAL RUN — uses DEFAULT_PARAMS
# ═══════════════════════════════════════════════════════════════════════════════

print("\nRunning canonical setup with DEFAULT_PARAMS...")

signal_df_canon = compute_momentum(
    prices_wide,
    DEFAULT_PARAMS["mom_window_months"],
    DEFAULT_PARAMS["rebalance_freq"],
)
trades_canon = generate_trades(
    prices_wide,
    signal_df_canon,
    DEFAULT_PARAMS["top_n"],
    DEFAULT_PARAMS["rebalance_freq"],
)

if trades_canon.empty:
    print("WARNING: canonical run produced no trades. Check DEFAULT_PARAMS.")
else:
    print(f"Total trades (rows): {len(trades_canon)}")
    print(f"Rebalance cohorts  : {trades_canon['entry_time'].nunique()}")
    print(f"Avg sectors / cohort: {len(trades_canon) / max(trades_canon['entry_time'].nunique(), 1):.1f}")
    print(f"Period: {trades_canon['entry_time'].iloc[0].date()} → "
          f"{trades_canon['exit_time'].iloc[-1].date()}")
    print(f"By instrument:\n{trades_canon['instrument'].value_counts().to_string()}")

    canon_mets = basket_portfolio_metrics(trades_canon)
    print(f"\nCanonical stats (net, {TC_BPS_OW} bps one-way TC):")
    print(f"  Sharpe      : {canon_mets['sharpe']:.4f}")
    print(f"  CAGR        : {canon_mets['cagr']:.2f}%")
    print(f"  Max DD      : {canon_mets['max_dd']:.2f}%")
    print(f"  YoY hit rate: {canon_mets['yoy_hit_rate']:.0f}%")
    print(f"  Trades      : {canon_mets['n_trades']}")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. SIGNIFICANCE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

    try:
        from _backtest_utils import (
            ttest_returns,
            bootstrap_sharpe,
            permutation_test,
        )

        print(f"\n{'='*70}")
        print("SIGNIFICANCE TESTS — canonical setup")
        print(f"{'='*70}")

        cohort_returns = (
            trades_canon.groupby("entry_time")["pct_return_gross"]
            .mean()
        )
        tc_rt = 2 * TC_BPS_OW / 10_000
        net_returns = cohort_returns - tc_rt
        r_arr = net_returns.values

        tt = ttest_returns(pd.Series(r_arr))
        print(f"\n1. t-test (returns > 0)")
        print(f"   Mean return:  {tt['mean_return']:.4f}% per period")
        print(f"   t-statistic:  {tt['t_stat']:.4f}")
        print(f"   p-value:      {tt['p_value']:.6f}")
        print(f"   Significant:  {'YES' if tt['significant'] else 'NO'}")

        bs = bootstrap_sharpe(pd.Series(r_arr), n=1000)
        print(f"\n2. Bootstrap Sharpe (95% CI, n=1000)")
        print(f"   Observed Sharpe: {bs['observed_sharpe']:.4f}")
        print(f"   95% CI:          [{bs['ci_lower']:.4f}, {bs['ci_upper']:.4f}]")
        print(f"   Significant:     {'YES' if bs['significant'] else 'NO'}")

        pt = permutation_test(pd.Series(r_arr), n=1000)
        print(f"\n3. Permutation test (random signs, n=1000)")
        print(f"   Observed Sharpe: {pt['observed_sharpe']:.4f}")
        print(f"   p-value:         {pt['p_value']:.6f}")
        print(f"   Significant:     {'YES' if pt['significant'] else 'NO'}")

        passes  = sum([tt["significant"], bs["significant"], pt["significant"]])
        verdict = (
            "SIGNIFICANT (strong)"       if passes == 3 else
            "SIGNIFICANT (moderate)"     if passes == 2 else
            "WEAK (only 1/3 tests pass)" if passes == 1 else
            "NOT SIGNIFICANT"
        )
        print(f"\n{'─'*70}")
        print(f"VERDICT: {verdict} ({passes}/3 tests pass)")
        print(f"{'─'*70}")

        sig_results = {
            "ttest":        tt,
            "bootstrap":    bs,
            "permutation":  pt,
            "tests_passed": f"{passes}/3",
            "verdict":      verdict,
        }

    except ImportError:
        print("\n(Significance tests skipped — _backtest_utils not found)")
        sig_results = {}
        passes  = 0
        verdict = "NOT TESTED"

# ═══════════════════════════════════════════════════════════════════════════════
# 9. SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

    os.makedirs(RESULTS_DIR, exist_ok=True)

    # ─── 9a. Signal CSV — long format: date, instrument, score ───
    signal_long_frames = []
    for rd, row in signal_df_canon.iterrows():
        for sym in available:
            score = row.get(sym, np.nan)
            if not pd.isna(score):
                    signal_long_frames.append({
                        "date":       rd,
                        "instrument": sym,
                        "score":      round(float(score), 6),
                    })

    signal_long = pd.DataFrame(signal_long_frames)
    signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
    signal_long.to_csv(signal_path, index=False)
    print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")

    # 9b. Trades CSV
    std_cols = ["entry_time", "exit_time", "direction", "instrument",
                "entry_price", "exit_price", "pct_return_gross", "exit_reason", "stop_price"]
    trades_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_trades.csv")
    trades_canon[std_cols].to_csv(trades_path, index=False)
    print(f"  trades  → {trades_path}  ({len(trades_canon)} rows, "
          f"{trades_canon['entry_time'].nunique()} cohorts x ~{DEFAULT_PARAMS['top_n']} sectors)")

    # 9c. Summary JSON
    summary = {
        "strategy":         STRATEGY_NAME,
        "instruments":      available,
        "portfolio":        "long_term",
        "type":             "selection",
        "period":           (f"{trades_canon['entry_time'].iloc[0].date()} -> "
                             f"{trades_canon['exit_time'].iloc[-1].date()}"),
        "default_params":   DEFAULT_PARAMS,
        "tc_bps_one_way":   TC_BPS_OW,
        "trades":           len(trades_canon),
        "cohorts":          int(trades_canon["entry_time"].nunique()),
        "stats":            canon_mets,
        "significance":     sig_results,
        "grid_search": {
            "combinations_tested": len(grid_results),
            "top_pcts":    TOP_PCTS,
            "freqs":       REBAL_FREQS,
            "mom_windows": MOM_WINDOWS,
        },
    }
    summary_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  summary -> {summary_path}")

print("\nDone. Review the grids, update DEFAULT_PARAMS, then re-run.\n")
