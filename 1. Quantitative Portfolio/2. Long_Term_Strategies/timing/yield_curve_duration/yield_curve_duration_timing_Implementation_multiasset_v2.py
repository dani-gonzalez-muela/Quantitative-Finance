# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Yield Curve Duration — Multi-Asset Implementation v2"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
from _shared.implementations import simple_bet, build_daily_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME    = "yield_curve_duration_v2"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
TC_RT            = 2 * TC_BPS_OW / 10_000
ALLOCATION       = 0.85

REGIME_MAP = {"TLT": "long", "IEF": "long", "LQD": "long", "HYG": "long",
              "TIP": "long", "SHY": "short", "BIL": "short"}

HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = data_dir("daily_tickers")
SYNTH_CSV    = os.path.join(_ROOT, "data", "wrds", "fred_rates_synthetic.csv")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "yield_curve_duration_v2_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("=" * 70); print("YIELD CURVE DURATION -- Multi-Asset Implementation v2"); print("=" * 70)
with open(SUMMARY_PATH) as f: summary = json.load(f)
basket_configs = summary["baskets"]
passing_baskets = {n: c for n, c in basket_configs.items() if c.get("binomial_significant", False)}
print(f"  Baskets tested: {len(basket_configs)}, passing: {len(passing_baskets)}")
for n, c in basket_configs.items():
    cp = c["canonical_params"]
    print(f"  {'PASS' if c.get('binomial_significant') else 'FAIL'} {n}: steep={cp['steep_thresh']},flat={cp['flat_thresh']} | medSh={c['canonical_median_sharpe']:.3f}")
if not passing_baskets: print("No passing baskets."); sys.exit(0)

# Load FRED synthetic
fr = pd.read_csv(SYNTH_CSV, parse_dates=["date"]).set_index("date").sort_index()
fr = fr[(fr.index >= START_DATE) & (fr.index <= END_DATE)]
fr_m = fr.resample("ME").last()
spread_lag = fr_m["t10y2y"].shift(1)

def load_close(ticker, monthly=False):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
    if len(df) < 100 or "close" not in df.columns: return None
    cs = df["close"]
    return cs.resample("ME").last() if monthly else cs

def classify_regime(spread, steep_thresh, flat_thresh):
    if pd.isna(spread): return "unknown"
    if spread > steep_thresh: return "long"
    if spread < flat_thresh:  return "short"
    return "flat"

def generate_yc_trades(ticker, etf_monthly, daily_close, steep_thresh, flat_thresh):
    fav_regime = REGIME_MAP.get(ticker, "long")
    etf_ret = etf_monthly.pct_change().dropna()
    trades = []
    for dt in etf_ret.index:
        sp  = spread_lag.get(dt, np.nan)
        reg = classify_regime(sp, steep_thresh, flat_thresh)
        if reg != fav_regime: continue
        idx = etf_monthly.index.get_loc(dt)
        ep  = float(etf_monthly.iloc[idx - 1]) if idx > 0 else float(etf_monthly.iloc[0])
        xp  = float(etf_monthly.loc[dt])
        pr  = (xp - ep) / ep
        entry_date = etf_monthly.index[max(idx-1, 0)]
        trades.append({"entry_time": entry_date, "exit_time": dt,
                        "direction": "long", "instrument": ticker,
                        "entry_price": round(ep, 4), "exit_price": round(xp, 4),
                        "pct_return_gross": round(pr, 6), "pct_return_net": round(pr - TC_RT, 6),
                        "exit_reason": "month_end", "stop_price": np.nan})
    _C = ["entry_time","exit_time","direction","instrument","entry_price","exit_price","pct_return_gross","pct_return_net","exit_reason","stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_C)

def compute_stats(eq):
    eq_clean = eq.dropna()
    if len(eq_clean) < 2: return {"sharpe": 0.0, "cagr_pct": 0.0, "max_dd_pct": 0.0}
    r = eq_clean.pct_change().dropna()
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    d = (eq_clean.index[-1] - eq_clean.index[0]).days
    cagr = float(((eq_clean.iloc[-1] / eq_clean.iloc[0]) ** (365.25 / d) - 1) * 100) if d > 0 else 0.0
    dd = float(((eq_clean - eq_clean.cummax()) / eq_clean.cummax()).min() * 100)
    return {"sharpe": round(sh, 4), "cagr_pct": round(cagr, 2), "max_dd_pct": round(dd, 2)}

N_passing = len(passing_baskets); sleeve_cap = STARTING_CAPITAL / N_passing
basket_results = {}; sleeve_equity_dict = {}
print(f"\n  Sleeve capital: ${sleeve_cap:,.0f} per basket\n")

for basket_name, cfg in passing_baskets.items():
    cp = cfg["canonical_params"]; st = float(cp["steep_thresh"]); ft = float(cp["flat_thresh"])
    instruments = cfg["instruments"]
    print(f"  {'='*55}\n  BASKET: {basket_name}  |  steep={st}, flat={ft}")
    inst_data = {}
    for ticker in instruments:
        cs_m = load_close(ticker, monthly=True)
        cs_d = load_close(ticker, monthly=False)
        if cs_m is None or cs_d is None: print(f"    {ticker}: no data"); continue
        t = generate_yc_trades(ticker, cs_m, cs_d, st, ft)
        print(f"    {ticker}: {len(t)} trades"); inst_data[ticker] = (t, cs_d)
    n_inst = len(inst_data)
    if n_inst == 0: continue
    inst_capital = sleeve_cap / n_inst
    print(f"  Per-instrument capital: ${inst_capital:,.0f}")
    inst_curves = {}
    for ticker, (trades_inst, close_s) in inst_data.items():
        if trades_inst.empty:
            inst_curves[ticker] = pd.Series(inst_capital, index=close_s.index); continue
        sizing = simple_bet(trades_inst, bet_size=ALLOCATION, starting_capital=inst_capital, include_fees=True)
        inst_curves[ticker] = build_daily_equity(trades_inst, sizing["equity_curve"], inst_capital, daily_prices=close_s)
    all_dates = pd.to_datetime(sorted(set().union(*[eq.index for eq in inst_curves.values()])))
    aligned = {t: eq.reindex(all_dates).ffill().bfill() for t, eq in inst_curves.items()}
    daily_eq = sum(aligned.values()); daily_eq.index.name = "date"; daily_eq.name = "equity"
    stats = compute_stats(daily_eq)
    daily_eq.reset_index().to_csv(os.path.join(EQUITY_DIR, f"{basket_name}_equity.csv"), index=False)
    print(f"  Sharpe={stats['sharpe']:.3f}  CAGR={stats['cagr_pct']:.2f}%  MaxDD={stats['max_dd_pct']:.2f}%")
    sleeve_equity_dict[basket_name] = daily_eq
    basket_results[basket_name] = {"canonical_params": cp, "n_instruments": n_inst, "stats": stats}

print(f"\n{'='*70}\nCOMBINED PORTFOLIO\n{'='*70}")
if sleeve_equity_dict:
    all_dates = pd.to_datetime(sorted(set().union(*[s.index for s in sleeve_equity_dict.values()])))
    combined = sum(eq.reindex(all_dates).ffill().bfill() for eq in sleeve_equity_dict.values())
    combined.index.name = "date"; combined.name = "equity"
    cs = compute_stats(combined)
    print(f"  Sharpe={cs['sharpe']:.4f}  CAGR={cs['cagr_pct']:.2f}%  MaxDD={cs['max_dd_pct']:.2f}%")
    combined.reset_index().to_csv(os.path.join(EQUITY_DIR, "combined_equity.csv"), index=False)
    impl_json = {"strategy": STRATEGY_NAME, "n_passing_baskets": N_passing,
                 "baskets": basket_results, "combined_stats": cs}
    with open(os.path.join(RESULTS_DIR, "yield_curve_duration_v2_implementations_multiasset.json"), "w") as f:
        json.dump(impl_json, f, indent=2, default=str)
print(f"\n{'='*70}\nDone.\n{'='*70}")
