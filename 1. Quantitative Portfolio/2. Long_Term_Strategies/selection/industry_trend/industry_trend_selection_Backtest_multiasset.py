# -*- coding: utf-8 -*-
"""
Industry Trend — Multi-Asset Selection Backtest
================================================
Extends industry_trend_selection_Backtest_v2.py to run the same
cross-sectional momentum signal across 3 coherent sub-universes
simultaneously, using the standardized Backtest format.

Universes
---------
  us_sectors  — 11 SPDR sector ETFs
  us_factor   — 7 factor ETFs
  em_country  — 11 EM/DM country ETFs

Grid
----
  TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]   (6)
  REBAL_FREQS = ['ME', '2ME', 'QE', '6ME', '12ME']       (5)
  MOM_WINDOWS = [3, 6, 9, 12]                             (4)
  = 120 combos × 3 universes = 360 runs total

Objective: find ONE set of params that maximises median_sharpe across
all universes simultaneously (no per-universe re-optimisation).

Reference: single-asset v2 canonical = top_pct=0.33, mom=6, ME, Sharpe≈0.88 on us_sectors

DO NOT RUN: no execution in this file. Run from project root.
"""

import sys
import os

# ── Path setup — algo_trading root on sys.path ──
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

STRATEGY_NAME    = "Industry Trend (Multi-Asset)"
SAVE_NAME        = "industry_trend_multiasset"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5   # one-way transaction cost in bps

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

# ── Universe definitions ──
UNIVERSE_SPECS = {
    "us_sectors": ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
    "us_factor":  ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"],
    "em_country": ["EEM","INDA","EWZ","EWJ","EWG","EWU","EWA","EWC","EWP","EWI","EWL"],
}
MIN_TICKERS_PER_UNIVERSE = 5

# ── Parameter grid (identical to v2) ──
TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
MOM_WINDOWS = [3, 6, 9, 12]

# v2 single-asset canonical (for comparison annotation)
V2_CANONICAL = {"top_pct": 0.33, "mom_window": 6, "freq": "ME", "sharpe_us_sectors": 0.88}

# ── Frequency → months per period ──
_FREQ_MONTHS = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

# ═══════════════════════════════════════════════════════════════════════════════
# 1. DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 75)
print("INDUSTRY TREND — Multi-Asset Backtest")
print("=" * 75)
print(f"\nData dir : {DATA_DIR}")
print(f"Period   : {START_DATE} → {END_DATE}")
print()

def load_universe_prices(tickers):
    """Load close prices for a list of tickers from individual CSVs.
    Returns wide DataFrame indexed by date. Skips missing tickers."""
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
        except Exception as e:
            print(f"  {ticker}: load error — {e}")
    if not frames:
        return pd.DataFrame()
    wide = pd.DataFrame(frames).sort_index()
    return wide

# Load each universe
UNIVERSES = {}
print("Loading universes:")
for uni_name, tickers in UNIVERSE_SPECS.items():
    wide = load_universe_prices(tickers)
    available = list(wide.columns)
    missing   = [t for t in tickers if t not in available]
    print(f"  {uni_name:<15}: {len(available):>2}/{len(tickers)} tickers available"
          f"  [{', '.join(available)}]")
    if missing:
        print(f"               skipped: {missing}")
    if len(available) >= MIN_TICKERS_PER_UNIVERSE:
        UNIVERSES[uni_name] = wide
    else:
        print(f"  *** {uni_name} excluded — fewer than {MIN_TICKERS_PER_UNIVERSE} tickers ***")

print(f"\nActive universes ({len(UNIVERSES)}): {list(UNIVERSES.keys())}")
print(f"Grid: {len(TOP_PCTS)} top_pcts × {len(REBAL_FREQS)} freqs × {len(MOM_WINDOWS)} mom_windows"
      f" = {len(TOP_PCTS)*len(REBAL_FREQS)*len(MOM_WINDOWS)} combos"
      f" × {len(UNIVERSES)} universes = "
      f"{len(TOP_PCTS)*len(REBAL_FREQS)*len(MOM_WINDOWS)*len(UNIVERSES)} total runs")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SIGNAL ENGINE  (identical logic to Backtest v2 — copied, not imported)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_momentum(prices_wide, mom_window_months, rebalance_freq):
    """
    Cross-sectional momentum with skip-last-period.

    Returns wide DataFrame: index=rebalance dates, cols=tickers, values=momentum score.
    Score = (price_{t-1p} / price_{t-1p-window_periods}) - 1
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
    Generate standardised 9-col trades DataFrame.
    Each held ticker × holding period = ONE row.
    Net return includes round-trip TC: 2 × tc_bps_ow / 10000.
    """
    rebal_dates = signal_df.dropna(how="all").index.tolist()
    trades = []
    for i, rd in enumerate(rebal_dates):
        scores = signal_df.loc[rd].dropna()
        top_sectors = scores.nlargest(top_n).index.tolist() if top_n < len(scores) else scores.index.tolist()
        if not top_sectors:
            continue
        entry_cands = prices_wide.index[prices_wide.index >= rd]
        if len(entry_cands) == 0:
            continue
        entry_date = entry_cands[0]
        if i + 1 < len(rebal_dates):
            next_rd    = rebal_dates[i + 1]
            exit_cands = prices_wide.index[prices_wide.index >= next_rd]
            if len(exit_cands) == 0:
                continue
            exit_date   = exit_cands[0]
            exit_reason = "rebalance"
        else:
            exit_date   = prices_wide.index[-1]
            exit_reason = "end_of_data"
        for sym in top_sectors:
            if sym not in prices_wide.columns:
                continue
            ep = prices_wide.loc[entry_date, sym]
            xp = prices_wide.loc[exit_date,  sym]
            if pd.isna(ep) or pd.isna(xp):
                continue
            trades.append({
                "entry_time":       entry_date,
                "exit_time":        exit_date,
                "direction":        "long",
                "instrument":       sym,
                "entry_price":      round(float(ep), 4),
                "exit_price":       round(float(xp), 4),
                "pct_return_gross": round(float((xp - ep) / ep), 6),
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
    Compute Sharpe, CAGR, MaxDD, n_trades, yoy_hit_rate from basket trades.
    Equal-weight within each period; TC applied once round-trip per period.
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
    eq   = STARTING_CAPITAL * (1 + r).cumprod()
    yrs  = (cohort["entry_time"].iloc[-1] - cohort["entry_time"].iloc[0]).days / 365.25
    cagr = (eq.iloc[-1] / STARTING_CAPITAL) ** (1 / yrs) - 1 if yrs > 0 else 0.0
    peak = eq.expanding().max()
    max_dd = ((eq - peak) / peak).min()
    cohort["year"] = cohort["entry_time"].dt.year
    annual = cohort.groupby("year")["period_return_net"].sum()
    yoy_hit_rate = (annual > 0).mean() if len(annual) > 0 else 0.0
    return {
        "sharpe":       round(float(sharpe), 4),
        "cagr":         round(float(cagr * 100), 2),
        "max_dd":       round(float(max_dd * 100), 2),
        "n_trades":     len(trades),
        "yoy_hit_rate": round(float(yoy_hit_rate * 100), 1),
    }


def run_single_universe(prices_wide, top_pct, freq, mom_win):
    """Run one (top_pct, freq, mom_win) combo on a single universe prices_wide.
    Returns sharpe or None on failure."""
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
# 3. GRID SEARCH — all 360 runs
# ═══════════════════════════════════════════════════════════════════════════════

all_combos = list(product(TOP_PCTS, REBAL_FREQS, MOM_WINDOWS))
uni_names  = list(UNIVERSES.keys())

print(f"\n{'='*75}")
print(f"GRID SEARCH — {len(all_combos)} combos × {len(UNIVERSES)} universes = "
      f"{len(all_combos)*len(UNIVERSES)} runs")
print(f"{'='*75}\n")

# results_raw: list of dicts with per-combo per-universe sharpes
results_raw = []

for idx, (top_pct, freq, mom_win) in enumerate(all_combos, 1):
    row = {"top_pct": top_pct, "freq": freq, "mom_window": mom_win}
    sharpes = []
    for uni_name, prices in UNIVERSES.items():
        s = run_single_universe(prices, top_pct, freq, mom_win)
        row[uni_name] = s
        if s is not None:
            sharpes.append(s)
    if sharpes:
        row["median_sharpe"] = round(float(np.median(sharpes)), 4)
        row["min_sharpe"]    = round(float(np.min(sharpes)), 4)
        row["n_positive"]    = int(sum(s > 0 for s in sharpes))
    else:
        row["median_sharpe"] = None
        row["min_sharpe"]    = None
        row["n_positive"]    = 0
    results_raw.append(row)
    if idx % 30 == 0:
        print(f"  {idx}/{len(all_combos)} combos done...")

print(f"  {len(all_combos)}/{len(all_combos)} combos done.\n")

# Build grid_df
grid_df = pd.DataFrame(results_raw)
# top_n per universe
for uni_name, prices in UNIVERSES.items():
    n = len(prices.columns)
    grid_df[f"top_n_{uni_name}"] = grid_df["top_pct"].apply(lambda p: max(1, round(n * p)))

# ── Stability metric ──────────────────────────────────────────────────────────
# For each combo, find all immediate ±1 neighbours in (top_pct, freq, mom_window)
# stability = mean(median_sharpe of neighbours) / combo median_sharpe

top_pct_list = TOP_PCTS
freq_list    = REBAL_FREQS
mom_list     = MOM_WINDOWS

# Build lookup: (top_pct, freq, mom_window) -> median_sharpe
lookup = {}
for _, r in grid_df.iterrows():
    lookup[(r["top_pct"], r["freq"], r["mom_window"])] = r["median_sharpe"]

def get_neighbors(top_pct, freq, mom_win):
    """Return list of (top_pct, freq, mom_win) immediate ±1 neighbors."""
    i_tp  = top_pct_list.index(top_pct)
    i_fr  = freq_list.index(freq)
    i_mw  = mom_list.index(mom_win)
    nbrs  = []
    for di in [-1, 1]:
        ni = i_tp + di
        if 0 <= ni < len(top_pct_list):
            nbrs.append((top_pct_list[ni], freq, mom_win))
    for dj in [-1, 1]:
        nj = i_fr + dj
        if 0 <= nj < len(freq_list):
            nbrs.append((top_pct, freq_list[nj], mom_win))
    for dk in [-1, 1]:
        nk = i_mw + dk
        if 0 <= nk < len(mom_list):
            nbrs.append((top_pct, freq, mom_list[nk]))
    return nbrs

stability_scores = []
neighbor_avg_sharpes = []
for _, row in grid_df.iterrows():
    nbrs = get_neighbors(row["top_pct"], row["freq"], row["mom_window"])
    nbr_sharpes = [lookup.get(k) for k in nbrs]
    nbr_sharpes = [s for s in nbr_sharpes if s is not None]
    if nbr_sharpes and row["median_sharpe"] and row["median_sharpe"] != 0:
        nbr_avg = float(np.mean(nbr_sharpes))
        stab    = nbr_avg / row["median_sharpe"]
    else:
        nbr_avg = None
        stab    = None
    neighbor_avg_sharpes.append(round(nbr_avg, 4) if nbr_avg is not None else None)
    stability_scores.append(round(stab, 4) if stab is not None else None)

grid_df["neighbor_avg_sharpe"] = neighbor_avg_sharpes
grid_df["stability"]           = stability_scores

# Add top_n column for the primary (first) universe
primary_uni = uni_names[0]
primary_prices = UNIVERSES[primary_uni]
n_primary = len(primary_prices.columns)
grid_df["top_n"] = grid_df["top_pct"].apply(lambda p: max(1, round(n_primary * p)))

# Sort by median_sharpe
grid_df_sorted = grid_df.sort_values("median_sharpe", ascending=False).reset_index(drop=True)
grid_df_sorted.index = grid_df_sorted.index + 1  # 1-based rank

# ═══════════════════════════════════════════════════════════════════════════════
# 4. DISPLAY RESULTS
# ═══════════════════════════════════════════════════════════════════════════════

# ── 4a. Top-20 ranked table ───────────────────────────────────────────────────
print(f"\n{'='*75}")
print("TOP-20 PARAMETER COMBINATIONS  (sorted by median_sharpe across all universes)")
print(f"{'='*75}")
print(f"  Reference: v2 canonical — top_pct=0.33, mom=6, ME → us_sectors Sharpe≈{V2_CANONICAL['sharpe_us_sectors']}")
print()

# Header
uni_headers = "  ".join(f"{u[:12]:>12}" for u in uni_names)
hdr = (f"{'rank':>4}  {'top_pct':>7}  {'top_n':>5}  {'mom':>3}  {'freq':>5}  "
       f"{'med_sharpe':>10}  {'min_sharpe':>10}  {'n_pos':>5}  {'stability':>9}  "
       + uni_headers)
print(hdr)
print("-" * len(hdr))

for rank, row in grid_df_sorted.head(20).iterrows():
    uni_vals = "  ".join(
        f"{row[u]:>12.3f}" if row[u] is not None else f"{'n/a':>12}"
        for u in uni_names
    )
    flag = " ← v2 ref" if (
        row["top_pct"] == V2_CANONICAL["top_pct"] and
        row["mom_window"] == V2_CANONICAL["mom_window"] and
        row["freq"] == V2_CANONICAL["freq"]
    ) else ""
    stab_str = f"{row['stability']:>9.3f}" if row['stability'] is not None else f"{'n/a':>9}"
    print(
        f"{rank:>4}  {row['top_pct']:>7.2f}  {int(row['top_n']):>5}  "
        f"{int(row['mom_window']):>3}  {row['freq']:>5}  "
        f"{row['median_sharpe']:>10.3f}  {row['min_sharpe']:>10.3f}  "
        f"{int(row['n_positive']):>5}  {stab_str}  "
        + uni_vals + flag
    )

# ── 4b. Sharpe heatmaps per universe ─────────────────────────────────────────
print(f"\n{'='*75}")
print("SHARPE HEATMAPS — top_pct × mom_window at BEST rebal frequency per universe")
print(f"{'='*75}")
print(f"  (5 bps one-way TC; 'best freq' = freq maximising median Sharpe for that universe)\n")

for uni_name in uni_names:
    sub = grid_df[grid_df[uni_name].notna()].copy()
    if sub.empty:
        continue
    # Best freq for this universe
    best_freq = (
        sub.groupby("freq")[uni_name].mean().idxmax()
    )
    sub_freq = sub[sub["freq"] == best_freq]
    n_tickers = len(UNIVERSES[uni_name].columns)

    print(f"--- {uni_name.upper()}  (n={n_tickers} tickers, best_freq={best_freq}) ---")
    header_line = f"{'top_pct':>8} | " + "  ".join(f"mom={w:>2}" for w in MOM_WINDOWS)
    print(header_line)
    print("-" * 9 + "+" + "-" * (len(header_line) - 10))
    for pct in TOP_PCTS:
        row_vals = []
        for w in MOM_WINDOWS:
            cell = sub_freq[(sub_freq["top_pct"] == pct) & (sub_freq["mom_window"] == w)]
            if cell.empty or cell[uni_name].isna().all():
                row_vals.append("  n/a ")
            else:
                row_vals.append(f"{cell[uni_name].values[0]:>6.3f}")
        top_n_val = max(1, round(n_tickers * pct))
        tag = f"  (top_n={top_n_val})"
        # annotate v2 ref if us_sectors
        if uni_name == "us_sectors" and pct == V2_CANONICAL["top_pct"] and best_freq == V2_CANONICAL["freq"]:
            tag += " ← v2 ref row"
        print(f"{pct:>8.2f} | " + "  ".join(row_vals) + tag)
    print()

# ── 4c. Full grid by frequency (sharpe heatmap) ───────────────────────────────
print(f"\n{'='*75}")
print("MEDIAN-SHARPE GRID BY FREQUENCY  (median across universes)")
print(f"{'='*75}\n")
for freq in REBAL_FREQS:
    sub = grid_df[grid_df["freq"] == freq]
    if sub.empty:
        continue
    print(f"=== Rebalance: {freq} ===")
    header_line = f"{'top_pct':>8} | " + "  ".join(f"mom={w:>2}" for w in MOM_WINDOWS)
    print(header_line)
    print("-" * 9 + "+" + "-" * (len(header_line) - 10))
    for pct in TOP_PCTS:
        row_vals = []
        for w in MOM_WINDOWS:
            cell = sub[(sub["top_pct"] == pct) & (sub["mom_window"] == w)]
            if cell.empty or cell["median_sharpe"].isna().all():
                row_vals.append("  n/a ")
            else:
                row_vals.append(f"{cell['median_sharpe'].values[0]:>6.3f}")
        flag = " ← v2 ref" if (pct == 0.33 and freq == "ME") else ""
        print(f"{pct:>8.2f} | " + "  ".join(row_vals) + flag)
    print()

# ── 4d. Best combo summary ────────────────────────────────────────────────────
best_row = grid_df_sorted.iloc[0]
print(f"\n{'='*75}")
print("BEST CROSS-UNIVERSE PARAMS")
print(f"{'='*75}")
print(f"  top_pct    = {best_row['top_pct']}")
print(f"  mom_window = {int(best_row['mom_window'])} months")
print(f"  freq       = {best_row['freq']}")
print(f"  median_sharpe = {best_row['median_sharpe']:.4f}")
print(f"  min_sharpe    = {best_row['min_sharpe']:.4f}")
print(f"  n_positive    = {int(best_row['n_positive'])}/{len(uni_names)}")
stab = best_row['stability']
print(f"  stability     = {stab:.4f}" if stab is not None else "  stability     = n/a")
for u in uni_names:
    v = best_row[u]
    print(f"  {u:<20} Sharpe = {v:.4f}" if v is not None else f"  {u:<20} Sharpe = n/a")
print(f"\n  v2 canonical comparison:")
v2_row = grid_df[
    (grid_df["top_pct"] == V2_CANONICAL["top_pct"]) &
    (grid_df["mom_window"] == V2_CANONICAL["mom_window"]) &
    (grid_df["freq"] == V2_CANONICAL["freq"])
]
if not v2_row.empty:
    vr = v2_row.iloc[0]
    print(f"  top_pct=0.33, mom=6, ME  → median_sharpe={vr['median_sharpe']:.4f}, "
          f"min_sharpe={vr['min_sharpe']:.4f}, n_pos={int(vr['n_positive'])}/{len(uni_names)}")
    for u in uni_names:
        v = vr[u]
        print(f"    {u:<20} Sharpe = {v:.4f}" if v is not None else f"    {u:<20} Sharpe = n/a")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

os.makedirs(RESULTS_DIR, exist_ok=True)

# ── 5a. Full grid CSV ─────────────────────────────────────────────────────────
# Column order
col_order = (
    ["top_pct", "top_n", "freq", "mom_window", "median_sharpe", "min_sharpe",
     "n_positive", "neighbor_avg_sharpe", "stability"]
    + uni_names
    + [f"top_n_{u}" for u in uni_names]
)
col_order = [c for c in col_order if c in grid_df.columns]

csv_path = os.path.join(RESULTS_DIR, "industry_trend_multiasset_grid.csv")
grid_df[col_order].sort_values("median_sharpe", ascending=False).to_csv(csv_path, index=False)
print(f"\n  grid CSV  → {csv_path}  ({len(grid_df)} rows)")

# ── 5b. Summary JSON ──────────────────────────────────────────────────────────
best = grid_df_sorted.iloc[0]
v2_ref = v2_row.iloc[0] if not v2_row.empty else None

per_universe = {}
for u in uni_names:
    best_sharpe = best[u]
    per_universe[u] = {
        "n_tickers":      len(UNIVERSES[u].columns),
        "tickers":        list(UNIVERSES[u].columns),
        "best_sharpe":    round(float(best_sharpe), 4) if best_sharpe is not None else None,
    }

summary = {
    "strategy":         STRATEGY_NAME,
    "period":           f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way":   TC_BPS_OW,
    "universes":        per_universe,
    "grid_search": {
        "top_pcts":           TOP_PCTS,
        "rebal_freqs":        REBAL_FREQS,
        "mom_windows":        MOM_WINDOWS,
        "combos_per_universe": len(all_combos),
        "total_runs":         len(all_combos) * len(UNIVERSES),
    },
    "best_params": {
        "top_pct":        float(best["top_pct"]),
        "top_n_primary":  int(best["top_n"]),
        "mom_window":     int(best["mom_window"]),
        "freq":           best["freq"],
        "median_sharpe":  float(best["median_sharpe"]) if best["median_sharpe"] is not None else None,
        "min_sharpe":     float(best["min_sharpe"])    if best["min_sharpe"] is not None else None,
        "n_positive":     int(best["n_positive"]),
        "stability":      float(best["stability"])     if best["stability"] is not None else None,
        "per_universe_sharpe": {
            u: (round(float(best[u]), 4) if best[u] is not None else None)
            for u in uni_names
        },
    },
    "v2_canonical_comparison": {
        "params":       {"top_pct": 0.33, "mom_window": 6, "freq": "ME"},
        "median_sharpe": round(float(v2_ref["median_sharpe"]), 4) if v2_ref is not None and v2_ref["median_sharpe"] is not None else None,
        "min_sharpe":    round(float(v2_ref["min_sharpe"]),    4) if v2_ref is not None and v2_ref["min_sharpe"] is not None else None,
        "per_universe_sharpe": {
            u: (round(float(v2_ref[u]), 4) if v2_ref is not None and v2_ref[u] is not None else None)
            for u in uni_names
        } if v2_ref is not None else {},
    },
}

json_path = os.path.join(RESULTS_DIR, "industry_trend_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"  summary JSON → {json_path}")

print(f"\n{'='*75}")
print("Done. Results saved to:", RESULTS_DIR)
print(f"{'='*75}\n")

# ==============================================================================
# 6. SIGNIFICANCE TESTS
# ==============================================================================

from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test

# --- Helper: extract period returns series ------------------------------------

def get_period_returns(prices_wide, top_pct, freq, mom_win, tc_bps_ow=TC_BPS_OW):
    """Return (pd.Series of net period returns indexed by entry_time, periods_per_year)."""
    n = len(prices_wide.columns)
    top_n = max(1, round(n * top_pct))
    try:
        sig    = compute_momentum(prices_wide, mom_win, freq)
        trades = generate_trades(prices_wide, sig, top_n, freq)
        if trades.empty or len(trades) < top_n * 2:
            return None, None
        tc_rt  = 2 * tc_bps_ow / 10_000
        cohort = (
            trades.groupby("entry_time")["pct_return_gross"]
            .mean()
            .reset_index()
            .rename(columns={"pct_return_gross": "period_return_gross"})
        )
        cohort["period_return_net"] = cohort["period_return_gross"] - tc_rt
        r    = cohort.set_index("entry_time")["period_return_net"]
        gaps = cohort["entry_time"].diff().dropna().dt.days
        median_gap       = gaps.median() if len(gaps) > 0 else 30
        periods_per_year = 365 / median_gap if median_gap > 0 else 12
        return r, periods_per_year
    except Exception:
        return None, None


# --- Select combos to test ----------------------------------------------------
_top3_rows = grid_df_sorted.head(3)

_baseline_1_rows = grid_df[grid_df["top_pct"] == 1.0].sort_values(
    "median_sharpe", ascending=False
)
_baseline_row = _baseline_1_rows.iloc[0] if not _baseline_1_rows.empty else None

_test_combos = []
for _, _r in _top3_rows.iterrows():
    _test_combos.append({
        "label":      "top_pct={:.2f}  mom={}  {}".format(_r["top_pct"], int(_r["mom_window"]), _r["freq"]),
        "top_pct":    float(_r["top_pct"]),
        "freq":       _r["freq"],
        "mom_window": int(_r["mom_window"]),
        "is_baseline": False,
    })
if _baseline_row is not None:
    _test_combos.append({
        "label":      "BASELINE  top_pct=1.00  mom={}  {}".format(int(_baseline_row["mom_window"]), _baseline_row["freq"]),
        "top_pct":    1.0,
        "freq":       _baseline_row["freq"],
        "mom_window": int(_baseline_row["mom_window"]),
        "is_baseline": True,
    })

print("\n" + "=" * 75)
print("SECTION 6 -- SIGNIFICANCE TESTS")
print("=" * 75)
print("Combos: top-3 by median Sharpe  +  best top_pct=1.0 equal-weight baseline")
print("Per combo x universe:")
print("  (1) t-test: mean period return > 0               [p < 0.05 = pass]")
print("  (2) Bootstrap Sharpe 1000 resamples, 5th pct > 0 [pass if > 0]")
print("  (3) Permutation test 1000 shuffles               [p < 0.05 = pass]")
print()

_pret_cache = {}   # (top_pct, freq, mom_win, uni_name) -> (r_series, ppy)

for _combo in _test_combos:
    _label = _combo["label"]
    _tp    = _combo["top_pct"]
    _freq  = _combo["freq"]
    _mw    = _combo["mom_window"]

    print("\n  -- {} --".format(_label))
    print("  {:<15}  {:>7}  {:>7}  {:>7}  {:>8}  {:>7}  Score".format(
          "Universe", "Sharpe", "t-stat", "t-p", "boot5%", "perm-p"))
    print("  " + "-" * 71)

    for _uni_name, _prices in UNIVERSES.items():
        _ck = (_tp, _freq, _mw, _uni_name)
        if _ck not in _pret_cache:
            _pret_cache[_ck] = get_period_returns(_prices, _tp, _freq, _mw)
        _r_series, _ppy = _pret_cache[_ck]

        if _r_series is None or len(_r_series) < 5:
            print("  {:<15}  INSUFFICIENT DATA".format(_uni_name))
            continue

        _annualise = np.sqrt(_ppy)
        _r_arr     = np.array(_r_series)
        _sharpe    = _r_arr.mean() / _r_arr.std() * _annualise if _r_arr.std() > 0 else 0.0

        # (1) t-test
        _tt = ttest_returns(_r_series)

        # (2) Bootstrap Sharpe -- 5th percentile > 0  (1000 resamples)
        _rng  = np.random.RandomState(42)
        _boot = []
        for _ in range(1000):
            _s = _rng.choice(_r_arr, size=len(_r_arr), replace=True)
            _boot.append(_s.mean() / _s.std() * _annualise if _s.std() > 0 else 0.0)
        _boot_p5 = float(np.percentile(_boot, 5))
        _boot_ok = _boot_p5 > 0

        # (3) Permutation test -- 1000 shuffles
        _abs_r = np.abs(_r_arr)
        _rng2  = np.random.RandomState(42)
        _count = 0
        for _ in range(1000):
            _sh = _abs_r * _rng2.choice([-1, 1], size=len(_abs_r))
            _ps = _sh.mean() / _sh.std() * _annualise if _sh.std() > 0 else 0.0
            if _ps >= _sharpe:
                _count += 1
        _perm_p  = _count / 1000
        _perm_ok = _perm_p < 0.05

        _n_pass = int(_tt["significant"]) + int(_boot_ok) + int(_perm_ok)
        _score  = "{}/3".format(_n_pass)
        _flag   = "  ***" if _n_pass == 3 else ("  **" if _n_pass == 2 else "")

        print("  {:<15}  {:>7.3f}  {:>7.3f}  {:>7.4f}  {:>+8.3f}  {:>7.4f}  [{}]{}".format(
              _uni_name, _sharpe,
              _tt["t_stat"], _tt["p_value"],
              _boot_p5, _perm_p,
              _score, _flag))


print()
print("=" * 75)
print("Significance tests complete.")
print("=" * 75)


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
                    ticker_data[_t]["close"], generate_industry_trend_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "industry_trend_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
