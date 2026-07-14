# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Bollinger Band -- Multi-Asset Implementation v2
===============================================
Loads per-basket canonical params from bollinger_band_v2_multiasset_summary.json.

Logic:
  1. For each PASSING basket (binomial_significant == True), run ALL basket
     instruments using that basket's canonical params.
  2. Size each basket as one sleeve with equal-weight 85% allocation
     (build_basket_equity from shared/implementations.py).
  3. Combined portfolio = 1/N per sleeve across N passing baskets.
  4. Save per-basket and combined daily equity curves.

Outputs
-------
  results/bollinger_band_v2_multiasset_daily_equity/{basket}_equity.csv
  results/bollinger_band_v2_multiasset_daily_equity/combined_equity.csv
  results/bollinger_band_v2_implementations_multiasset.json
"""

import sys, os

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
from _shared.implementations import build_basket_equity, simple_bet, build_daily_equity

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────

STRATEGY_NAME    = "bollinger_band_v2"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
ALLOCATION       = 0.85   # fraction of sleeve equity deployed into basket

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR    = os.path.join(_ROOT, "long_term", "multi_asset_expansion", "data", "tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "bollinger_band_v2_multiasset_summary.json")

os.makedirs(EQUITY_DIR, exist_ok=True)

print("=" * 70)
print("BOLLINGER BAND -- Multi-Asset Implementation v2")
print("=" * 70)

# ── Load canonical params from backtest summary ────────────────────────────────

if not os.path.exists(SUMMARY_PATH):
    raise FileNotFoundError(
        f"Backtest summary not found: {SUMMARY_PATH}\n"
        "Run bollinger_band_timing_Backtest_multiasset_v2.py first."
    )

with open(SUMMARY_PATH) as f:
    summary = json.load(f)

basket_configs = summary["baskets"]
passing_baskets = {
    name: cfg for name, cfg in basket_configs.items()
    if cfg.get("binomial_significant", False)
}

print(f"\n  Baskets tested   : {len(basket_configs)}")
print(f"  Passing baskets  : {len(passing_baskets)}")
for name, cfg in basket_configs.items():
    cp = cfg["canonical_params"]
    status = "PASS" if cfg.get("binomial_significant", False) else "FAIL"
    print(f"    [{status}] {name}: bb_period={cp['bb_period']}, "
          f"bb_std={cp['bb_std']}, hold_days={cp['hold_days']} "
          f"| median Sharpe={cfg['canonical_median_sharpe']:.3f}")

if not passing_baskets:
    print("\n  No baskets passed binomial test -- nothing to implement.")
    sys.exit(0)


# ── Data Loading ───────────────────────────────────────────────────────────────

def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns:
            return None
        return df
    except Exception:
        return None


# ── Signal Generation (identical to Backtest v2) ───────────────────────────────

def generate_bb_trades_v2(df, ticker, bb_period, bb_std, hold_days):
    """
    Bollinger Band mean-reversion trades.
    Entry  : next open after close <= lower band.
    Exit   : close >= upper band  OR  hold_days elapsed (whichever first).
             hold_days=0 => exit only on upper band.
    TC     : 5 bps each way embedded in pct_return_net.
    """
    TC_RT = 2 * TC_BPS_OW / 10_000

    close = df["close"]
    sma   = close.rolling(bb_period).mean()
    sigma = close.rolling(bb_period).std()
    upper = sma + bb_std * sigma
    lower = sma - bb_std * sigma

    trades     = []
    in_trade   = False
    entry_date = None
    entry_price = None
    entry_idx   = None

    for i in range(1, len(df)):
        today = df.index[i]

        if not in_trade:
            if close.iloc[i - 1] <= lower.iloc[i - 1] and not pd.isna(lower.iloc[i - 1]):
                ep = (df["open"].iloc[i]
                      if "open" in df.columns and not pd.isna(df["open"].iloc[i])
                      else close.iloc[i])
                in_trade    = True
                entry_date  = today
                entry_price = float(ep)
                entry_idx   = i
        else:
            days_held = i - entry_idx
            hit_upper = not pd.isna(upper.iloc[i]) and close.iloc[i] >= upper.iloc[i]
            hit_time  = (hold_days > 0) and (days_held >= hold_days)

            if hit_upper or hit_time:
                xp        = float(close.iloc[i])
                gross_ret = (xp - entry_price) / entry_price
                net_ret   = gross_ret - TC_RT
                trades.append({
                    "entry_time":       entry_date,
                    "exit_time":        today,
                    "direction":        "long",
                    "instrument":       ticker,
                    "entry_price":      round(entry_price, 4),
                    "exit_price":       round(xp, 4),
                    "pct_return_gross": round(gross_ret, 6),
                    "pct_return_net":   round(net_ret, 6),
                    "exit_reason":      "upper_band" if hit_upper else "max_hold",
                    "stop_price":       np.nan,
                })
                in_trade = False

    if in_trade and entry_price is not None:
        xp        = float(close.iloc[-1])
        gross_ret = (xp - entry_price) / entry_price
        net_ret   = gross_ret - TC_RT
        trades.append({
            "entry_time":       entry_date,
            "exit_time":        df.index[-1],
            "direction":        "long",
            "instrument":       ticker,
            "entry_price":      round(entry_price, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(gross_ret, 6),
            "pct_return_net":   round(net_ret, 6),
            "exit_reason":      "end_of_data",
            "stop_price":       np.nan,
        })

    _COLS = ["entry_time", "exit_time", "direction", "instrument",
             "entry_price", "exit_price", "pct_return_gross", "pct_return_net",
             "exit_reason", "stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_COLS)


def compute_stats(daily_eq):
    """Standard metrics from a daily equity Series."""
    r = daily_eq.pct_change().dropna()
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    days   = (daily_eq.index[-1] - daily_eq.index[0]).days
    cagr   = float(((daily_eq.iloc[-1] / daily_eq.iloc[0]) ** (365.25 / days) - 1) * 100) if days > 0 else 0.0
    peak   = daily_eq.cummax()
    max_dd = float(((daily_eq - peak) / peak).min() * 100)
    total  = float((daily_eq.iloc[-1] / daily_eq.iloc[0] - 1) * 100)
    return {
        "total_return_pct": round(total, 2),
        "cagr_pct":         round(cagr, 2),
        "sharpe":           round(sharpe, 4),
        "max_dd_pct":       round(max_dd, 2),
    }


# ── Run each passing basket ────────────────────────────────────────────────────

N_passing          = len(passing_baskets)
sleeve_cap         = STARTING_CAPITAL / N_passing    # 1/N per sleeve

basket_results     = {}
sleeve_equity_dict = {}   # basket_name -> daily equity Series

print(f"\n  Sleeve capital : ${sleeve_cap:,.0f} per basket (1/{N_passing} of ${STARTING_CAPITAL:,})")
print(f"  Allocation     : {ALLOCATION:.0%} of sleeve equity deployed")
print()

for basket_name, cfg in passing_baskets.items():
    cp         = cfg["canonical_params"]
    bb_period  = int(cp["bb_period"])
    bb_std     = float(cp["bb_std"])
    hold_days  = int(cp["hold_days"])
    instruments = cfg["instruments"]

    print(f"  {'='*60}")
    print(f"  BASKET: {basket_name}")
    print(f"  Params: bb_period={bb_period}, bb_std={bb_std}, hold_days={hold_days}")
    print(f"  Instruments ({len(instruments)}): {', '.join(instruments)}")
    print()

    inst_data = {}   # ticker -> (trades_df, close_series)

    for ticker in instruments:
        df = load_ohlc(ticker)
        if df is None:
            print(f"    {ticker:<8}: no data -- skipping")
            continue
        trades_inst = generate_bb_trades_v2(df, ticker, bb_period, bb_std, hold_days)
        n_trades = len(trades_inst)
        print(f"    {ticker:<8}: {n_trades:>3} trades")
        inst_data[ticker] = (trades_inst, df["close"])

    n_inst = len(inst_data)
    if n_inst == 0:
        print(f"    No instruments loaded for {basket_name} -- skipping.")
        continue

    # 1/N independent sleeves — each instrument gets a fixed capital slice.
    # Avoids the cohort-size overleveraging bug in build_basket_equity, which
    # was designed for selection strategies (all K enter same rebalance date).
    # For timing strategies each instrument enters independently → cohort=1
    # almost every day → 85% per trade regardless of concurrent open positions.
    inst_capital = sleeve_cap / n_inst
    print(f"\n    Per-instrument capital: ${inst_capital:,.0f}  (1/{n_inst} × ${sleeve_cap:,.0f})")

    inst_daily_curves = {}
    for ticker, (trades_inst, close_series) in inst_data.items():
        if trades_inst.empty:
            dates = pd.bdate_range(START_DATE, END_DATE)
            flat  = pd.Series(inst_capital, index=dates, name="equity")
            flat.index.name = "date"
            inst_daily_curves[ticker] = flat
            continue
        sizing  = simple_bet(trades_inst, bet_size=ALLOCATION,
                             starting_capital=inst_capital, include_fees=True)
        inst_eq = build_daily_equity(trades_inst, sizing["equity_curve"],
                                     inst_capital, daily_prices=close_series)
        inst_daily_curves[ticker] = inst_eq

    # Sum instrument daily curves -> basket equity
    all_dates = sorted(set().union(*[eq.index for eq in inst_daily_curves.values()]))
    all_dates  = pd.to_datetime(all_dates)
    aligned    = {t: eq.reindex(all_dates).ffill().bfill()
                  for t, eq in inst_daily_curves.items()}
    daily_eq   = sum(aligned.values())
    daily_eq.index.name = "date"
    daily_eq.name = "equity"
    stats = compute_stats(daily_eq)

    # Save basket equity CSV
    eq_path = os.path.join(EQUITY_DIR, f"{basket_name}_equity.csv")
    daily_eq.reset_index().rename(columns={"date": "date", "equity": "equity"}).to_csv(
        eq_path, index=False
    )
    print(f"\n    Sharpe={stats['sharpe']:.3f}  CAGR={stats['cagr_pct']:.2f}%  "
          f"MaxDD={stats['max_dd_pct']:.2f}%  TotalRet={stats['total_return_pct']:.2f}%")
    print(f"    Equity -> {eq_path}")

    sleeve_equity_dict[basket_name] = daily_eq
    basket_results[basket_name] = {
        "instruments":    instruments,
        "n_trades":       sum(len(td) for td, _ in inst_data.values()),
        "canonical_params": cp,
        "sleeve_capital": sleeve_cap,
        "allocation":     ALLOCATION,
        "stats":          stats,
    }


# ── Combined Portfolio (1/N per sleeve) ────────────────────────────────────────

print(f"\n{'='*70}")
print(f"COMBINED PORTFOLIO  ({len(sleeve_equity_dict)} passing baskets, equal weight)")
print(f"{'='*70}\n")

if sleeve_equity_dict:
    # Align all sleeve equities to a common date range; forward-fill gaps
    all_dates = sorted(set().union(*[s.index for s in sleeve_equity_dict.values()]))
    all_dates = pd.to_datetime(all_dates)

    aligned = {}
    for name, eq in sleeve_equity_dict.items():
        s = eq.copy()
        s.index = pd.to_datetime(s.index)
        aligned[name] = s.reindex(all_dates).ffill().bfill()

    combined = sum(aligned.values())
    combined.index.name = "date"
    combined.name = "equity"

    combined_stats = compute_stats(combined)
    print(f"  Sharpe   : {combined_stats['sharpe']:.4f}")
    print(f"  CAGR     : {combined_stats['cagr_pct']:.2f}%")
    print(f"  MaxDD    : {combined_stats['max_dd_pct']:.2f}%")
    print(f"  Total Ret: {combined_stats['total_return_pct']:.2f}%")
    print(f"  Period   : {combined.index[0].date()} -> {combined.index[-1].date()}")

    combined_path = os.path.join(EQUITY_DIR, "combined_equity.csv")
    combined.reset_index().to_csv(combined_path, index=False)
    print(f"\n  Combined equity -> {combined_path}")
else:
    combined_stats = {}
    print("  No passing baskets produced equity -- combined is empty.")


# ── Save Implementations JSON ──────────────────────────────────────────────────

impl_json = {
    "strategy":          STRATEGY_NAME,
    "period":            f"{START_DATE} -> {END_DATE}",
    "tc_bps_one_way":    TC_BPS_OW,
    "starting_capital":  STARTING_CAPITAL,
    "allocation":        ALLOCATION,
    "n_passing_baskets": len(passing_baskets),
    "sleeve_capital":    sleeve_cap,
    "baskets":           basket_results,
    "combined_stats":    combined_stats,
}

json_path = os.path.join(RESULTS_DIR, "bollinger_band_v2_implementations_multiasset.json")
with open(json_path, "w") as f:
    json.dump(impl_json, f, indent=2, default=str)

print(f"\n  Implementations JSON -> {json_path}")
print(f"  Equity dir           -> {EQUITY_DIR}/")
print(f"\n{'='*70}\nDone.\n{'='*70}")
