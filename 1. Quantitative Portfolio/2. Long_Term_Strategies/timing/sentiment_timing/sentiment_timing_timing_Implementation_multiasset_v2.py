# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Sentiment Timing (VIX) — Multi-Asset Implementation v2"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
import duckdb
from _shared.implementations import simple_bet, build_daily_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME    = "sentiment_timing_v2"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
TC_RT            = 2 * TC_BPS_OW / 10_000
ALLOCATION       = 0.85

HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = data_dir("daily_tickers")
VIX_PARQUET  = os.path.join(_ROOT, "data", "wrds", "15_cboe_vix.parquet")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "sentiment_timing_v2_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("=" * 70); print("SENTIMENT TIMING (VIX) -- Multi-Asset Implementation v2"); print("=" * 70)
with open(SUMMARY_PATH) as f: summary = json.load(f)
basket_configs = summary["baskets"]
passing_baskets = {n: c for n, c in basket_configs.items() if c.get("binomial_significant", False)}
print(f"  Baskets tested: {len(basket_configs)}, passing: {len(passing_baskets)}")
for n, c in basket_configs.items():
    cp = c["canonical_params"]
    print(f"  {'PASS' if c.get('binomial_significant') else 'FAIL'} {n}: vix_lo={cp['vix_low']},vix_hi={cp['vix_high']} | medSh={c['canonical_median_sharpe']:.3f}")
if not passing_baskets: print("No passing baskets."); sys.exit(0)

# Load VIX
print("\nLoading VIX...")
con = duckdb.connect()
try:
    vix = con.execute(f"SELECT date, vix_close FROM read_parquet('{VIX_PARQUET}') ORDER BY date").fetchdf()
    vix["date"] = pd.to_datetime(vix["date"]); vix = vix.set_index("date")
except:
    df_ = con.execute(f"SELECT * FROM read_parquet('{VIX_PARQUET}') LIMIT 3").fetchdf()
    dc  = [c for c in df_.columns if "date" in c.lower()][0]
    vc  = [c for c in df_.columns if "vix" in c.lower() or "close" in c.lower()][-1]
    vix = con.execute(f"SELECT {dc},{vc} FROM read_parquet('{VIX_PARQUET}') ORDER BY {dc}").fetchdf()
    vix["date"] = pd.to_datetime(vix[dc]); vix = vix.rename(columns={vc:"vix_close"}).set_index("date")
vix_daily   = vix["vix_close"][(vix.index >= START_DATE) & (vix.index <= END_DATE)]
vix_monthly = vix_daily.resample("ME").mean()
print(f"  VIX loaded: {len(vix_daily)} daily obs")

def load_close(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
    if len(df) < 100 or "close" not in df.columns: return None
    return df["close"]

def generate_vix_trades(close_s, ticker, vix_low, vix_high):
    monthly = close_s.resample("ME").last()
    monthly_ret = monthly.pct_change().dropna()
    trades = []
    for i in range(1, len(monthly)):
        d = monthly.index[i]; dp = monthly.index[i - 1]
        vm = vix_monthly.get(d, np.nan)
        if pd.isna(vm): continue
        exp = 0.5 if float(vm) < vix_low else (1.5 if float(vm) > vix_high else 1.0)
        rr = float(monthly_ret.loc[d]) if d in monthly_ret.index else 0.0
        ep = float(monthly.iloc[i - 1])
        sized_ret = rr * exp
        trades.append({"entry_time": dp, "exit_time": d, "direction": "long",
                        "instrument": ticker, "entry_price": round(ep, 4),
                        "exit_price": round(ep * (1 + sized_ret), 4),
                        "pct_return_gross": round(sized_ret, 6),
                        "pct_return_net": round(sized_ret - TC_RT, 6),
                        "exit_reason": "month_end", "stop_price": np.nan})
    _C = ["entry_time","exit_time","direction","instrument","entry_price","exit_price","pct_return_gross","pct_return_net","exit_reason","stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_C)

def build_daily_equity_from_monthly_trades(daily_close, trades):
    n = len(daily_close)
    if trades.empty: return pd.Series(1.0, index=daily_close.index)
    t2 = trades.copy()
    t2["entry_ts"] = pd.to_datetime(t2["entry_time"])
    t2["exit_ts"]  = pd.to_datetime(t2["exit_time"])
    t2 = t2.sort_values("entry_ts").reset_index(drop=True)
    arr = np.full(n, np.nan); cap = 1.0; prev = -1
    for _, t in t2.iterrows():
        gross_ret = t["pct_return_gross"]
        ei_ = min(int(daily_close.index.searchsorted(t["entry_ts"])), n - 1)
        xi_ = min(int(daily_close.index.searchsorted(t["exit_ts"])),  n - 1)
        if xi_ < ei_: xi_ = ei_
        if prev + 1 < ei_: arr[prev + 1: ei_] = cap
        if xi_ > ei_:
            frac = np.linspace(0, gross_ret, xi_ - ei_ + 1)
            arr[ei_: xi_ + 1] = cap * (1 + frac)
        else:
            arr[xi_] = cap * (1 + gross_ret - TC_RT)
        if xi_ > ei_: cap *= (1 + gross_ret - TC_RT)
        prev = xi_
    if prev + 1 < n: arr[prev + 1:] = cap
    return pd.Series(arr, index=daily_close.index)

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
    cp = cfg["canonical_params"]; vl = int(cp["vix_low"]); vh = int(cp["vix_high"])
    instruments = cfg["instruments"]
    print(f"  {'='*55}\n  BASKET: {basket_name}  |  vix_low={vl}, vix_high={vh}")
    inst_data = {}
    for ticker in instruments:
        cs = load_close(ticker)
        if cs is None: print(f"    {ticker}: no data"); continue
        t = generate_vix_trades(cs, ticker, vl, vh)
        print(f"    {ticker}: {len(t)} trades"); inst_data[ticker] = (t, cs)
    n_inst = len(inst_data)
    if n_inst == 0: continue
    inst_capital = sleeve_cap / n_inst
    print(f"  Per-instrument capital: ${inst_capital:,.0f}")
    inst_curves = {}
    for ticker, (trades_inst, close_s) in inst_data.items():
        if trades_inst.empty:
            inst_curves[ticker] = pd.Series(inst_capital, index=close_s.index); continue
        # For VIX monthly strategy: use build_daily_equity_from_monthly_trades then scale
        raw_unit_eq = build_daily_equity_from_monthly_trades(close_s, trades_inst)
        inst_curves[ticker] = raw_unit_eq * inst_capital
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
    with open(os.path.join(RESULTS_DIR, "sentiment_timing_v2_implementations_multiasset.json"), "w") as f:
        json.dump(impl_json, f, indent=2, default=str)
print(f"\n{'='*70}\nDone.\n{'='*70}")
