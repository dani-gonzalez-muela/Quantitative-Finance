# -*- coding: utf-8 -*-
"""
Industry Trend — Multi-Asset Implementation
============================================
Loads results/industry_trend_multiasset_summary.json to identify passing
baskets, re-runs the cross-sectional momentum signal on each basket with
canonical params (top_pct=0.25, mom=12m, 6ME), then builds equity curves
via build_basket_equity() with simple_85 and simple_100 variants.

One sleeve per passing basket × 2 allocation variants = up to 6 equity curves.
Combined equity: 1/N capital per sleeve (equal weighting of sleeves).

Outputs
-------
  results/industry_trend_multiasset_daily_equity/{sleeve}_{variant}.csv
  results/industry_trend_implementations_multiasset.json
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

from _shared.implementations import build_basket_equity

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGY_NAME    = "industry_trend"
STARTING_CAPITAL = 100_000
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR    = data_dir("daily_tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "industry_trend_multiasset_summary.json")

os.makedirs(EQUITY_DIR, exist_ok=True)

# ── Frequency → months per period ──
_FREQ_MONTHS = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

print("=" * 70)
print("INDUSTRY TREND — Multi-Asset Implementation")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD SUMMARY — canonical params + passing baskets
# ═══════════════════════════════════════════════════════════════════════════════

with open(SUMMARY_PATH) as f:
    summary = json.load(f)

best = summary["best_params"]
CANON_TOP_PCT   = float(best["top_pct"])
CANON_MOM_WIN   = int(best["mom_window"])
CANON_FREQ      = best["freq"]
PASSING_BASKETS = list(summary["universes"].keys())

print(f"\nCanonical params : top_pct={CANON_TOP_PCT}, mom={CANON_MOM_WIN}m, freq={CANON_FREQ}")
print(f"Passing baskets  : {PASSING_BASKETS}")
print(f"Period           : {START_DATE} → {END_DATE}")
print()

# ═══════════════════════════════════════════════════════════════════════════════
# 2. SIGNAL ENGINE  (same logic as Backtest_multiasset)
# ═══════════════════════════════════════════════════════════════════════════════

def load_prices(tickers, start=START_DATE, end=END_DATE):
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
            s = s[(s.index >= start) & (s.index <= end)]
            if len(s) >= 252:
                frames[ticker] = s
        except Exception as e:
            print(f"  {ticker}: load error — {e}")
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames).sort_index()


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
        past_price   = monthly.iloc[past_idx]
        recent_price = monthly.iloc[recent_idx]
        signal_df.iloc[i] = recent_price / past_price - 1
    return signal_df


def generate_trades(prices_wide, signal_df, top_n, rebalance_freq):
    rebal_dates = signal_df.dropna(how="all").index.tolist()
    trades = []
    tc_rt  = 2 * TC_BPS_OW / 10_000
    for i, rd in enumerate(rebal_dates):
        scores = signal_df.loc[rd].dropna()
        top_tickers = scores.nlargest(top_n).index.tolist() if top_n < len(scores) else scores.index.tolist()
        if not top_tickers:
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
        for sym in top_tickers:
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


def compute_stats(daily_equity):
    """Compute Sharpe, CAGR, MaxDD from a daily equity pd.Series."""
    eq  = daily_equity.dropna()
    if len(eq) < 20:
        return {"sharpe": None, "cagr": None, "max_dd": None}
    dr  = eq.pct_change().dropna()
    sh  = float(dr.mean() / dr.std() * np.sqrt(252)) if dr.std() > 0 else 0.0
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0.0
    peak = eq.expanding().max()
    mdd  = float(((eq - peak) / peak).min()) * 100
    return {"sharpe": round(sh, 4), "cagr": round(cagr, 2), "max_dd": round(mdd, 2)}

# ═══════════════════════════════════════════════════════════════════════════════
# 3. RUN PER SLEEVE
# ═══════════════════════════════════════════════════════════════════════════════

ALLOCATION_VARIANTS = {"simple_85": 0.85, "simple_100": 1.00}

sleeve_results  = {}   # {sleeve_name: {"variant": {"metrics": ..., "equity": pd.Series}}}
combined_daily  = {}   # {variant: list of daily equity series}

for basket_name in PASSING_BASKETS:
    tickers = summary["universes"][basket_name]["tickers"]
    prices  = load_prices(tickers)
    if prices.empty or len(prices.columns) < 3:
        print(f"  *** {basket_name}: insufficient price data — skipping ***")
        continue

    n      = len(prices.columns)
    top_n  = max(1, round(n * CANON_TOP_PCT))
    signal = compute_momentum(prices, CANON_MOM_WIN, CANON_FREQ)
    trades = generate_trades(prices, signal, top_n, CANON_FREQ)

    if trades.empty or len(trades) < top_n * 2:
        print(f"  *** {basket_name}: no trades generated — skipping ***")
        continue

    print(f"\n  {basket_name}  ({len(prices.columns)} tickers, top_n={top_n}, {len(trades)} trades)")

    # Build daily_prices dict for build_basket_equity
    daily_prices = {sym: prices[sym] for sym in prices.columns}

    sleeve_results[basket_name] = {}

    for var_name, alloc in ALLOCATION_VARIANTS.items():
        result = build_basket_equity(
            trades,
            daily_prices,
            starting_capital=STARTING_CAPITAL,
            allocation=alloc,
            include_fees=True,
        )
        daily_eq = result["daily_equity"]
        stats    = compute_stats(daily_eq)

        # Save per-sleeve equity CSV
        csv_name = f"{basket_name}_{var_name}.csv"
        eq_df    = daily_eq.reset_index()
        eq_df.columns = ["date", "equity"]
        eq_df.to_csv(os.path.join(EQUITY_DIR, csv_name), index=False)

        sleeve_results[basket_name][var_name] = {
            "metrics": {
                "sharpe":  stats["sharpe"],
                "cagr":    stats["cagr"],
                "max_dd":  stats["max_dd"],
                "n_trades": len(trades),
                "n_tickers": len(prices.columns),
                "top_n":   top_n,
                "allocation": alloc,
            },
            "equity_series": daily_eq,  # keep in memory for combined
        }

        # Accumulate for combined
        if var_name not in combined_daily:
            combined_daily[var_name] = []
        combined_daily[var_name].append(daily_eq)

        print(f"    {var_name:>12}  Sharpe={stats['sharpe']:>6.3f}  "
              f"CAGR={stats['cagr']:>6.2f}%  MaxDD={stats['max_dd']:>6.2f}%")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. COMBINED EQUITY — 1/N capital per sleeve
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'='*70}")
print("COMBINED EQUITY  (1/N capital per sleeve)")
print(f"{'='*70}")

combined_results = {}

for var_name, series_list in combined_daily.items():
    if not series_list:
        continue
    n_sleeves = len(series_list)

    # Align all equity series on common business dates, ffill gaps
    aligned = pd.concat(series_list, axis=1)
    aligned.columns = [f"sleeve_{i}" for i in range(n_sleeves)]
    aligned = aligned.ffill().dropna()

    # Each sleeve gets 1/N of starting capital; normalise each to STARTING_CAPITAL/n_sleeves
    per_sleeve_cap = STARTING_CAPITAL / n_sleeves
    normalised = pd.DataFrame()
    for col, s in zip(aligned.columns, series_list):
        # Reindex to aligned index, ffill
        s_aligned = s.reindex(aligned.index).ffill()
        # Normalise: start at per_sleeve_cap
        first_valid = s_aligned.dropna().iloc[0] if not s_aligned.dropna().empty else 1.0
        normalised[col] = s_aligned / first_valid * per_sleeve_cap

    combined_eq = normalised.sum(axis=1)
    stats = compute_stats(combined_eq)

    # Save combined equity CSV
    csv_name = f"combined_{var_name}.csv"
    cdf      = combined_eq.reset_index()
    cdf.columns = ["date", "equity"]
    cdf.to_csv(os.path.join(EQUITY_DIR, csv_name), index=False)

    combined_results[var_name] = {
        "n_sleeves":   n_sleeves,
        "sleeves":     PASSING_BASKETS,
        "sharpe":      stats["sharpe"],
        "cagr":        stats["cagr"],
        "max_dd":      stats["max_dd"],
    }

    print(f"  {var_name:>12}  n_sleeves={n_sleeves}  "
          f"Sharpe={stats['sharpe']:>6.3f}  CAGR={stats['cagr']:>6.2f}%  "
          f"MaxDD={stats['max_dd']:>6.2f}%")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SAVE JSON
# ═══════════════════════════════════════════════════════════════════════════════

# Strip in-memory equity series from sleeve_results before JSON dump
output = {
    "strategy":          STRATEGY_NAME,
    "period":            f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way":    TC_BPS_OW,
    "canonical_params": {
        "top_pct":    CANON_TOP_PCT,
        "mom_window": CANON_MOM_WIN,
        "freq":       CANON_FREQ,
    },
    "sleeves": {},
    "combined": combined_results,
}

for basket_name, var_dict in sleeve_results.items():
    output["sleeves"][basket_name] = {}
    for var_name, d in var_dict.items():
        output["sleeves"][basket_name][var_name] = d["metrics"]

json_path = os.path.join(RESULTS_DIR, "industry_trend_implementations_multiasset.json")
with open(json_path, "w") as f:
    json.dump(output, f, indent=2, default=str)

print(f"\n  JSON → {json_path}")
print(f"  Equity CSVs → {EQUITY_DIR}/")
print(f"\n{'='*70}")
print("Done.")
print(f"{'='*70}\n")
