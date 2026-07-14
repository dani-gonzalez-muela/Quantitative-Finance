# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
Industry Trend — Implementation v2
====================================
Loads results/industry_trend_trades.csv and daily prices from
long_term/archived_strategies/output/prices_validated.parquet, then runs
3 sizing variants via build_basket_equity().

Variants
--------
  simple_85        : allocation = 0.85 (fixed)
  simple_100       : allocation = 1.00 (fixed)
  vol_targeted_10pct : walk-forward allocation targeting 10% annualised vol,
                       capped at 1.5.  Per-cohort allocation implemented
                       manually since build_basket_equity takes a scalar.

Outputs
-------
  results/industry_trend_daily_equity/{variant}.csv
  results/industry_trend_implementations.json
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import json, warnings
import numpy as np
import pandas as pd

from _shared.implementations import build_basket_equity, calculate_fees, SLIPPAGE_PER_SHARE

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGY_NAME    = "industry_trend"
STARTING_CAPITAL = 100_000

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_daily_equity")

PRICES_PATH = os.path.join(HERE, "../../archived_strategies/output/prices_validated.parquet")
TRADES_PATH = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_trades.csv")

# ═══════════════════════════════════════════════════════════════════════════════
# 1. LOAD TRADES
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("INDUSTRY TREND — Implementation v2")
print("=" * 70)

trades = pd.read_csv(TRADES_PATH, parse_dates=["entry_time", "exit_time"])
print(f"\nLoaded {len(trades)} trades  |  {trades['entry_time'].nunique()} cohorts")
print(f"Period   : {trades['entry_time'].min().date()} → {trades['exit_time'].max().date()}")
print(f"Avg K    : {len(trades)/trades['entry_time'].nunique():.1f} positions/cohort")

instruments = sorted(trades["instrument"].unique().tolist())

# ═══════════════════════════════════════════════════════════════════════════════
# 2. LOAD DAILY PRICES FROM PARQUET
# ═══════════════════════════════════════════════════════════════════════════════

prices_df = pd.read_parquet(os.path.normpath(PRICES_PATH))
prices_df.index = pd.to_datetime(prices_df.index).normalize()

daily_prices = {}
missing = []
for sym in instruments:
    if sym in prices_df.columns:
        daily_prices[sym] = prices_df[sym].dropna()
    else:
        missing.append(sym)

if missing:
    print(f"WARNING: instruments not found in price data: {missing}")

print(f"\nLoaded prices for {len(daily_prices)}/{len(instruments)} instruments "
      f"from prices_validated.parquet")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. VOL-TARGETED MANUAL SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════

def compute_cohort_allocations(trades, target_vol=0.10, lookback_months=6, max_alloc=1.5):
    """
    Walk-forward per-cohort allocations targeting `target_vol` annualised vol.
    Uses trailing `lookback_months` equal-weight basket monthly returns.
    Returns a dict {entry_date: allocation}.
    """
    cohort_ret = (trades.groupby("entry_time")["pct_return_gross"]
                  .mean()
                  .sort_index())
    cohort_dates = cohort_ret.index.tolist()

    # periods_per_year from median gap
    gaps = pd.Series(cohort_dates).diff().dropna().dt.days
    ppy  = 365.0 / gaps.median() if len(gaps) > 0 else 12.0

    alloc_dict = {}
    default    = 0.85

    for i, dt in enumerate(cohort_dates):
        if i < lookback_months:
            alloc_dict[dt] = default
        else:
            past_rets  = cohort_ret.iloc[i - lookback_months: i].values
            basket_vol = float(np.std(past_rets, ddof=1)) * np.sqrt(ppy)
            if basket_vol > 0:
                alloc = min(target_vol / basket_vol, max_alloc)
            else:
                alloc = default
            alloc_dict[dt] = round(alloc, 4)

    return alloc_dict


def build_basket_equity_variable(trades, daily_prices, cohort_allocations,
                                  starting_capital=100_000, include_fees=True,
                                  slippage=SLIPPAGE_PER_SHARE):
    """
    Like build_basket_equity() but with per-cohort allocation.
    `cohort_allocations` is a dict {entry_date (Timestamp): float}.
    """
    def _to_ts(series):
        dt = pd.to_datetime(series)
        if hasattr(dt, 'dt'):
            if dt.dt.tz is not None:
                dt = dt.dt.tz_convert(None)
            return dt.dt.normalize()
        if hasattr(dt, 'tz') and dt.tz is not None:
            dt = dt.tz_convert(None)
        return dt.normalize()

    trades = trades.copy()
    trades["entry_date"] = _to_ts(trades["entry_time"])
    trades["exit_date"]  = _to_ts(trades["exit_time"])
    trades = trades.sort_values(["entry_date", "instrument"]).reset_index(drop=True)
    trades["_orig_idx"]  = trades.index

    # Normalize alloc keys to Timestamps
    cohort_alloc_norm = {
        pd.Timestamp(k).normalize(): v for k, v in cohort_allocations.items()
    }

    first_date = trades["entry_date"].min()
    last_date  = trades["exit_date"].max()
    all_days   = pd.bdate_range(first_date, last_date)

    prices_norm = {}
    for sym, s in daily_prices.items():
        s = s.copy()
        s.index = pd.to_datetime(s.index).normalize()
        s = s[~s.index.duplicated(keep="last")]
        s = s.reindex(all_days).ffill().bfill()
        prices_norm[sym] = s

    cohort_size = trades.groupby("entry_date").size().to_dict()

    shares_per_trade            = [0]   * len(trades)
    sized_returns               = [0.0] * len(trades)
    per_trade_pnl               = [0.0] * len(trades)
    per_trade_equity_at_entry   = [0.0] * len(trades)

    cash           = starting_capital
    open_positions = []
    daily_values   = {}

    for day in all_days:
        # 1. Close positions exiting today
        still_open = []
        for pos in open_positions:
            if pos["exit_date"] <= day:
                if pos["direction"] == "long":
                    proceeds  = pos["shares"] * pos["exit_price"]
                    gross_pnl = pos["shares"] * (pos["exit_price"] - pos["entry_price"])
                else:
                    proceeds  = pos["shares"] * (2 * pos["entry_price"] - pos["exit_price"])
                    gross_pnl = pos["shares"] * (pos["entry_price"] - pos["exit_price"])
                fees = (calculate_fees(pos["shares"], pos["entry_price"],
                                       pos["exit_price"], pos["direction"],
                                       slippage=slippage)
                        if include_fees else 0.0)
                net_pnl = gross_pnl - fees
                cash += proceeds - fees
                idx = pos["trade_idx"]
                per_trade_pnl[idx] = net_pnl
                eq_at_entry = per_trade_equity_at_entry[idx]
                sized_returns[idx] = (net_pnl / eq_at_entry) if eq_at_entry > 0 else 0.0
            else:
                still_open.append(pos)
        open_positions = still_open

        # 2. Current equity (cash + MTM open positions)
        position_value = 0.0
        for pos in open_positions:
            series = prices_norm.get(pos["instrument"])
            px = series.loc[day] if series is not None and day in series.index else np.nan
            if pd.isna(px):
                px = pos["entry_price"]
            if pos["direction"] == "long":
                position_value += pos["shares"] * px
            else:
                position_value += pos["shares"] * (2 * pos["entry_price"] - px)
        equity_now = cash + position_value

        # 3. Open new positions — use per-cohort allocation
        day_trades = trades[trades["entry_date"] == day]
        if not day_trades.empty:
            k     = cohort_size[day]
            alloc = cohort_alloc_norm.get(day, 0.85)
            per_pos_notional = equity_now * alloc / k
            for _, t in day_trades.iterrows():
                shares = int(per_pos_notional / t["entry_price"])
                if shares <= 0:
                    shares_per_trade[t["_orig_idx"]] = 0
                    per_trade_equity_at_entry[t["_orig_idx"]] = equity_now
                    continue
                cost = shares * t["entry_price"]
                if t["direction"] == "long":
                    cash -= cost
                else:
                    cash += cost
                shares_per_trade[t["_orig_idx"]] = shares
                per_trade_equity_at_entry[t["_orig_idx"]] = equity_now
                open_positions.append({
                    "shares":      shares,
                    "entry_price": t["entry_price"],
                    "exit_price":  t["exit_price"],
                    "exit_date":   t["exit_date"],
                    "direction":   t["direction"],
                    "instrument":  t["instrument"],
                    "trade_idx":   t["_orig_idx"],
                })

        # 4. Record daily equity
        position_value = 0.0
        for pos in open_positions:
            series = prices_norm.get(pos["instrument"])
            px = series.loc[day] if series is not None and day in series.index else np.nan
            if pd.isna(px):
                px = pos["entry_price"]
            if pos["direction"] == "long":
                position_value += pos["shares"] * px
            else:
                position_value += pos["shares"] * (2 * pos["entry_price"] - px)
        daily_values[day] = cash + position_value

    # Close remaining open positions
    for pos in open_positions:
        if pos["direction"] == "long":
            proceeds  = pos["shares"] * pos["exit_price"]
            gross_pnl = pos["shares"] * (pos["exit_price"] - pos["entry_price"])
        else:
            proceeds  = pos["shares"] * (2 * pos["entry_price"] - pos["exit_price"])
            gross_pnl = pos["shares"] * (pos["entry_price"] - pos["exit_price"])
        fees = (calculate_fees(pos["shares"], pos["entry_price"],
                               pos["exit_price"], pos["direction"],
                               slippage=slippage)
                if include_fees else 0.0)
        net_pnl = gross_pnl - fees
        cash += proceeds - fees
        idx = pos["trade_idx"]
        per_trade_pnl[idx] = net_pnl
        eq_at_entry = per_trade_equity_at_entry[idx]
        sized_returns[idx] = (net_pnl / eq_at_entry) if eq_at_entry > 0 else 0.0

    daily_eq = pd.Series(daily_values).sort_index()
    daily_eq = daily_eq.reindex(all_days, method="ffill").fillna(starting_capital)
    daily_eq.index.name = "date"
    daily_eq.name       = "equity"

    # Stats (same logic as build_basket_equity)
    blew_up      = (daily_eq.iloc[-1] <= 0) or (daily_eq.min() <= 0)
    daily_returns = daily_eq.pct_change().dropna()
    if blew_up:
        total_return = max((daily_eq.iloc[-1] / starting_capital - 1) * 100, -100.0)
        sharpe = cagr = float("nan")
        max_dd = -100.0
    else:
        total_return = (daily_eq.iloc[-1] / starting_capital - 1) * 100
        sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                  if daily_returns.std() > 0 else 0.0)
        peak   = daily_eq.expanding().max()
        max_dd = ((daily_eq - peak) / peak).min() * 100
        years  = (daily_eq.index[-1] - daily_eq.index[0]).days / 365.25
        cagr   = ((daily_eq.iloc[-1] / starting_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    stats = {
        "sharpe":  round(sharpe, 2)  if not blew_up else sharpe,
        "cagr":    round(cagr,   2)  if not blew_up else cagr,
        "max_dd":  round(max_dd, 2),
    }
    return {"daily_equity": daily_eq, "stats": stats}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RUN VARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(EQUITY_DIR,  exist_ok=True)

print(f"\nRunning variants ...")
results = {}

# ── simple_85 ──────────────────────────────────────────────────────────────────
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    r = build_basket_equity(trades, daily_prices,
                             starting_capital=STARTING_CAPITAL,
                             allocation=0.85, include_fees=True)
results["simple_85"] = {
    "daily_equity": r["daily_equity"],
    "stats":        {k: r["stats"][k] for k in ("sharpe", "cagr", "max_dd")},
    "extra":        {"allocation": 0.85},
}
print("  simple_85       done")

# ── simple_100 ─────────────────────────────────────────────────────────────────
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    r = build_basket_equity(trades, daily_prices,
                             starting_capital=STARTING_CAPITAL,
                             allocation=1.00, include_fees=True)
results["simple_100"] = {
    "daily_equity": r["daily_equity"],
    "stats":        {k: r["stats"][k] for k in ("sharpe", "cagr", "max_dd")},
    "extra":        {"allocation": 1.0},
}
print("  simple_100      done")

# ── vol_targeted_10pct ─────────────────────────────────────────────────────────
cohort_allocs = compute_cohort_allocations(trades, target_vol=0.10,
                                            lookback_months=6, max_alloc=1.5)
avg_alloc = round(float(np.mean(list(cohort_allocs.values()))), 4)
print(f"  vol_targeted: avg_allocation = {avg_alloc:.4f}")

r = build_basket_equity_variable(trades, daily_prices,
                                  cohort_allocs,
                                  starting_capital=STARTING_CAPITAL,
                                  include_fees=True)
results["vol_targeted_10pct"] = {
    "daily_equity": r["daily_equity"],
    "stats":        r["stats"],
    "extra":        {"target_vol": 0.10, "avg_allocation": avg_alloc},
}
print("  vol_targeted    done")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SAVE OUTPUTS
# ═══════════════════════════════════════════════════════════════════════════════

# ─ Daily equity CSVs ───────────────────────────────────────────────────────────
for name, v in results.items():
    path = os.path.join(EQUITY_DIR, f"{name}.csv")
    v["daily_equity"].to_csv(path)

print(f"\nSaved daily equity CSVs → {EQUITY_DIR}/")

# ─ implementations.json ────────────────────────────────────────────────────────
variants_json = {}
for name, v in results.items():
    entry = {**v["stats"], **v["extra"]}
    variants_json[name] = entry

impl_json = {
    "strategy": STRATEGY_NAME,
    "canonical_params": {
        "top_pct": 0.33,
        "top_n": 3,
        "mom_window_months": 6,
        "rebalance_freq": "ME",
    },
    "variants": variants_json,
}

impl_path = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_implementations.json")
with open(impl_path, "w") as f:
    json.dump(impl_json, f, indent=2)

print(f"Saved implementations.json → {impl_path}")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. COMPARISON TABLE
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("VARIANT COMPARISON")
print("=" * 70)

header = f"{'Variant':<22} {'Sharpe':>8} {'CAGR%':>8} {'MaxDD%':>8} {'AvgAlloc':>10}"
print(header)
print("-" * len(header))

for name, v in results.items():
    s = v["stats"]
    avg = v["extra"].get("avg_allocation", v["extra"].get("allocation", float("nan")))
    sharpe = s.get("sharpe", float("nan"))
    cagr   = s.get("cagr",   float("nan"))
    max_dd = s.get("max_dd", float("nan"))
    print(f"{name:<22} {sharpe:>8.2f} {cagr:>8.2f} {max_dd:>8.2f} {avg:>10.4f}")

print()
