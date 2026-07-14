# -*- coding: utf-8 -*-
"""
Overnight Premium — Multi-Asset Implementation v2
=================================================
TYPE 1 TIMING: 1/N sleeves with simple_bet + build_daily_equity.
Loads per-basket results from overnight_premium_v2_multiasset_summary.json.

Only uses passing baskets (binomial_significant == True).
Within each basket sleeve: 1/N_instruments equal allocation.

Outputs
-------
  results/overnight_premium_v2_multiasset_daily_equity/{basket}_equity.csv
  results/overnight_premium_v2_multiasset_daily_equity/combined_equity.csv
  results/overnight_premium_v2_implementations_multiasset.json
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
from _shared.implementations import simple_bet, build_daily_equity

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "overnight_premium_v2"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
ALLOCATION       = 0.85

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR    = data_dir("daily_tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "overnight_premium_v2_multiasset_summary.json")

os.makedirs(EQUITY_DIR, exist_ok=True)

print("=" * 70)
print("OVERNIGHT PREMIUM — Multi-Asset Implementation v2  (TYPE 1 TIMING)")
print("=" * 70)

if not os.path.exists(SUMMARY_PATH):
    raise FileNotFoundError(f"Run backtest v2 first: {SUMMARY_PATH}")

with open(SUMMARY_PATH) as f:
    summary = json.load(f)

basket_configs  = summary["baskets"]
passing_baskets = {n: c for n, c in basket_configs.items() if c.get("binomial_significant", False)}

print(f"\n  Baskets tested  : {len(basket_configs)}")
print(f"  Passing baskets : {len(passing_baskets)}")
for n, c in basket_configs.items():
    status = "PASS" if c.get("binomial_significant") else "FAIL"
    print(f"    [{status}] {n}  med_sharpe={c['canonical_median_sharpe']:.3f}  "
          f"binom_p={c['binomial_pvalue']:.4f}")

if not passing_baskets:
    print("\n  No baskets passed — nothing to implement.")
    sys.exit(0)


def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns or "open" not in df.columns:
            return None
        return df
    except Exception:
        return None


def make_overnight_trades(df, ticker):
    """Build a standardized trades DF for overnight strategy (close → next open)."""
    tc_rt = 2 * TC_BPS_OW / 10_000
    close = df["close"]
    open_ = df["open"]
    rows  = []
    for i in range(1, len(df)):
        ep = float(close.iloc[i - 1])
        xp = float(open_.iloc[i])
        if ep <= 0 or xp <= 0:
            continue
        gross = (xp - ep) / ep
        rows.append({
            "entry_time":       df.index[i - 1],
            "exit_time":        df.index[i],
            "direction":        "long",
            "instrument":       ticker,
            "entry_price":      round(ep, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(gross, 6),
            "pct_return_net":   round(gross - tc_rt, 6),
            "exit_reason":      "next_open",
            "stop_price":       np.nan,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def compute_stats(daily_eq):
    r = daily_eq.pct_change().dropna()
    sharpe = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    days   = (daily_eq.index[-1] - daily_eq.index[0]).days
    cagr   = float(((daily_eq.iloc[-1] / daily_eq.iloc[0]) ** (365.25 / days) - 1) * 100) if days > 0 else 0.0
    peak   = daily_eq.cummax()
    max_dd = float(((daily_eq - peak) / peak).min() * 100)
    total  = float((daily_eq.iloc[-1] / daily_eq.iloc[0] - 1) * 100)
    return {"total_return_pct": round(total, 2), "cagr_pct": round(cagr, 2),
            "sharpe": round(sharpe, 4), "max_dd_pct": round(max_dd, 2)}


N_passing      = len(passing_baskets)
sleeve_cap     = STARTING_CAPITAL / N_passing
basket_results = {}
sleeve_equity_dict = {}

print(f"\n  Sleeve capital : ${sleeve_cap:,.0f} per basket (1/{N_passing})")
print(f"  Allocation     : {ALLOCATION:.0%}\n")

for basket_name, cfg in passing_baskets.items():
    instruments = cfg["instruments"]
    print(f"  {'='*60}")
    print(f"  BASKET: {basket_name}  ({len(instruments)} instruments)")

    inst_data = {}
    for ticker in instruments:
        df = load_ohlc(ticker)
        if df is None:
            print(f"    {ticker:<8}: no data — skip")
            continue
        trades_inst = make_overnight_trades(df, ticker)
        print(f"    {ticker:<8}: {len(trades_inst):>4} trades")
        inst_data[ticker] = (trades_inst, df["close"])

    n_inst = len(inst_data)
    if n_inst == 0:
        print(f"    No data for {basket_name} — skipping.")
        continue

    # TYPE 1: 1/N sleeves, simple_bet + build_daily_equity per instrument
    inst_capital = sleeve_cap / n_inst
    print(f"\n    Per-instrument capital: ${inst_capital:,.0f}  (1/{n_inst} of ${sleeve_cap:,.0f})")

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

    all_dates = sorted(set().union(*[eq.index for eq in inst_daily_curves.values()]))
    all_dates  = pd.to_datetime(all_dates)
    aligned    = {t: eq.reindex(all_dates).ffill().bfill()
                  for t, eq in inst_daily_curves.items()}
    daily_eq   = sum(aligned.values())
    daily_eq.index.name = "date"
    daily_eq.name = "equity"
    stats = compute_stats(daily_eq)

    eq_path = os.path.join(EQUITY_DIR, f"{basket_name}_equity.csv")
    daily_eq.reset_index().to_csv(eq_path, index=False)
    print(f"\n    Sharpe={stats['sharpe']:.3f}  CAGR={stats['cagr_pct']:.2f}%  "
          f"MaxDD={stats['max_dd_pct']:.2f}%")
    print(f"    Equity → {eq_path}")

    sleeve_equity_dict[basket_name] = daily_eq
    basket_results[basket_name] = {
        "instruments":    instruments,
        "n_trades":       sum(len(td) for td, _ in inst_data.values()),
        "sleeve_capital": sleeve_cap,
        "allocation":     ALLOCATION,
        "stats":          stats,
    }


# ── Combined portfolio ────────────────────────────────────────────────────────

print(f"\n{'='*70}")
print(f"COMBINED PORTFOLIO  ({len(sleeve_equity_dict)} passing baskets)")
print(f"{'='*70}\n")

if sleeve_equity_dict:
    all_dates = sorted(set().union(*[s.index for s in sleeve_equity_dict.values()]))
    all_dates  = pd.to_datetime(all_dates)
    aligned    = {n: eq.reindex(all_dates).ffill().bfill()
                  for n, eq in sleeve_equity_dict.items()}
    combined   = sum(aligned.values())
    combined.index.name = "date"
    combined.name = "equity"
    combined_stats = compute_stats(combined)
    print(f"  Sharpe   : {combined_stats['sharpe']:.4f}")
    print(f"  CAGR     : {combined_stats['cagr_pct']:.2f}%")
    print(f"  MaxDD    : {combined_stats['max_dd_pct']:.2f}%")
    print(f"  Total Ret: {combined_stats['total_return_pct']:.2f}%")
    combined_path = os.path.join(EQUITY_DIR, "combined_equity.csv")
    combined.reset_index().to_csv(combined_path, index=False)
    print(f"\n  Combined equity → {combined_path}")
else:
    combined_stats = {}

# ── Save JSON ─────────────────────────────────────────────────────────────────

impl_json = {
    "strategy":          STRATEGY_NAME,
    "period":            f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way":    TC_BPS_OW,
    "starting_capital":  STARTING_CAPITAL,
    "allocation":        ALLOCATION,
    "n_passing_baskets": N_passing,
    "sleeve_capital":    sleeve_cap,
    "baskets":           basket_results,
    "combined_stats":    combined_stats,
}

json_path = os.path.join(RESULTS_DIR, "overnight_premium_v2_implementations_multiasset.json")
with open(json_path, "w") as f:
    json.dump(impl_json, f, indent=2, default=str)

print(f"\n  Implementations JSON → {json_path}")
print(f"  Equity dir           → {EQUITY_DIR}/")
print(f"\n{'='*70}\nDone.\n{'='*70}")
