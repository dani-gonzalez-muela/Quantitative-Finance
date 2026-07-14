# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Quality / Profitability — Multi-Asset Implementation
=====================================================
Canonical: top_pct=0.50, rmw_window=18, freq=6ME
Basket   : us_equity_broad

RMW signal: cumulative RMW over rmw_window > 0 → quality_on; rank by momentum.
Data: FF5 RMW factor from long_term/selection/regime_factor_rotation/data/ff_factors_monthly.csv

Outputs: results/quality_profitability_multiasset_daily_equity/*.csv
         results/quality_profitability_implementations_multiasset.json
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
from _shared.implementations import build_basket_equity

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "quality_profitability"
STARTING_CAPITAL = 100_000
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = data_dir("daily_tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "quality_profitability_multiasset_summary.json")
FF_PATH      = os.path.join(HERE, "..", "regime_factor_rotation", "data", "ff_factors_monthly.csv")
os.makedirs(EQUITY_DIR, exist_ok=True)

_FREQ_MONTHS = {"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}
UNIVERSE_SPECS = {
    "us_equity_broad": ["SPY","QQQ","IWM","MDY"],
}

print("="*70); print("QUALITY / PROFITABILITY — Multi-Asset Implementation"); print("="*70)

with open(SUMMARY_PATH) as f: summary = json.load(f)
best = summary["best_params"]
CANON_TOP_PCT = float(best["top_pct"])
CANON_RMW_WIN = int(best["rmw_window"])
CANON_FREQ    = best["freq"]
PASSING_BASKETS = list(summary["universes"].keys())
print(f"\nCanonical: top_pct={CANON_TOP_PCT}, rmw_win={CANON_RMW_WIN}, freq={CANON_FREQ}")
print(f"Passing  : {PASSING_BASKETS}\n")

# Load FF RMW factor
ff = pd.read_csv(FF_PATH, parse_dates=["Date"], index_col="Date").sort_index()
rmw = ff["RMW"] / 100
print(f"FF RMW: {rmw.index[0].date()} → {rmw.index[-1].date()}")

def load_prices(tickers):
    frames = {}
    for t in tickers:
        p = os.path.join(DATA_DIR, f"{t}.csv")
        if not os.path.exists(p): continue
        try:
            df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
            df.index = pd.to_datetime(df.index)
            s = df["close"].dropna()
            s = s[(s.index>=START_DATE)&(s.index<=END_DATE)]
            if len(s)>=252: frames[t] = s
        except: pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()

def compute_quality_signal(rmw_series, rmw_window, freq, prices_wide):
    """
    quality_on = cumulative RMW over rmw_window > 0.
    When quality_on: rank ETFs by trailing momentum (12m skip-1).
    When quality_off: equal-weight all.
    """
    fmon = _FREQ_MONTHS.get(freq, 1)
    monthly = prices_wide.resample(freq).last()
    rmw_rebal = (1 + rmw_series).resample(freq).prod() - 1
    wper = max(1, int(round(rmw_window / fmon)))
    skip = 1

    sig = pd.DataFrame(index=monthly.index, columns=monthly.columns, dtype=float)
    for i in range(len(monthly)):
        rd = monthly.index[i]
        rmw_window_end = rmw_rebal.index[rmw_rebal.index <= rd]
        if len(rmw_window_end) < wper + 1: continue
        loc = rmw_rebal.index.get_loc(rmw_window_end[-1])
        if loc < wper: continue
        rmw_cum = (1 + rmw_rebal.iloc[loc - wper: loc]).prod() - 1
        quality_on = float(rmw_cum) > 0
        if quality_on:
            # rank by momentum (12m, skip-1) — same window as industry_trend default
            mom_wper = max(1, int(round(12 / fmon)))
            past_i = i - mom_wper - skip; rec_i = i - skip
            if past_i < 0 or rec_i < 0:
                sig.iloc[i] = pd.Series(1.0, index=monthly.columns)
            else:
                sig.iloc[i] = monthly.iloc[rec_i] / monthly.iloc[past_i] - 1
        else:
            sig.iloc[i] = pd.Series(1.0, index=monthly.columns)  # equal-weight
    return sig

def generate_trades(prices_wide, signal_df, top_n, freq):
    rdates = signal_df.dropna(how="all").index.tolist(); trades = []
    for i, rd in enumerate(rdates):
        scores = signal_df.loc[rd].dropna()
        if scores.empty: continue
        tops = scores.nlargest(min(top_n, len(scores))).index.tolist()
        if not tops: continue
        ec = prices_wide.index[prices_wide.index>=rd]
        if len(ec)==0: continue
        ed = ec[0]
        if i+1<len(rdates):
            xc = prices_wide.index[prices_wide.index>=rdates[i+1]]
            if len(xc)==0: continue
            xd=xc[0]; xr="rebalance"
        else:
            xd=prices_wide.index[-1]; xr="end_of_data"
        for sym in tops:
            if sym not in prices_wide.columns: continue
            ep = float(prices_wide.loc[ed,sym]) if ed in prices_wide.index else np.nan
            xp = float(prices_wide.loc[xd,sym]) if xd in prices_wide.index else np.nan
            if pd.isna(ep) or pd.isna(xp) or ep<=0: continue
            trades.append({"entry_time":ed,"exit_time":xd,"direction":"long","instrument":sym,
                           "entry_price":round(ep,4),"exit_price":round(xp,4),
                           "pct_return_gross":round((xp-ep)/ep,6),
                           "exit_reason":xr,"stop_price":np.nan})
    return pd.DataFrame(trades)

def compute_stats(eq):
    r = eq.pct_change().dropna()
    sharpe = float(r.mean()/r.std()*np.sqrt(252)) if r.std()>0 else 0.0
    days = (eq.index[-1]-eq.index[0]).days
    cagr = float(((eq.iloc[-1]/eq.iloc[0])**(365.25/days)-1)*100) if days>0 else 0.0
    roll = eq.cummax(); dd = (eq-roll)/roll
    return {"sharpe":round(sharpe,4),"cagr":round(cagr,2),"max_dd":round(float(dd.min()*100),2)}

ALLOC_VARIANTS = {"simple_85":0.85,"simple_100":1.00}
sleeve_results = {}; combined_daily = {}

for basket_name in PASSING_BASKETS:
    tickers = UNIVERSE_SPECS.get(basket_name,[])
    prices  = load_prices(tickers)
    if prices.empty: print(f"  {basket_name}: no data"); continue
    n = len(prices.columns); top_n = max(1,round(n*CANON_TOP_PCT))
    sig = compute_quality_signal(rmw, CANON_RMW_WIN, CANON_FREQ, prices)
    trades = generate_trades(prices, sig, top_n, CANON_FREQ)
    if trades.empty: print(f"  {basket_name}: no trades"); continue
    daily_prices = {s: prices[s] for s in prices.columns}
    sleeve_results[basket_name] = {}
    print(f"\n  Basket: {basket_name}  ({len(prices.columns)} tickers, top_n={top_n}, {len(trades)} trades)")
    for var_name, alloc in ALLOC_VARIANTS.items():
        res = build_basket_equity(trades, daily_prices, starting_capital=STARTING_CAPITAL, allocation=alloc, include_fees=True)
        eq = res["daily_equity"]; st = compute_stats(eq)
        eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(
            os.path.join(EQUITY_DIR,f"{basket_name}_{var_name}.csv"),index=False)
        sleeve_results[basket_name][var_name] = {"metrics":{**st,"n_trades":len(trades),"allocation":alloc},"equity_series":eq}
        combined_daily.setdefault(var_name,[]).append(eq)
        print(f"    {var_name:>12}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

print(f"\n{'='*70}\nCOMBINED\n{'='*70}")
combined_results = {}
for var_name, series_list in combined_daily.items():
    if not series_list: continue
    n_sl = len(series_list); psc = STARTING_CAPITAL/n_sl
    aligned = pd.concat(series_list, axis=1).ffill().dropna()
    norm = pd.DataFrame({f"s{i}": s.reindex(aligned.index).ffill() / (s.reindex(aligned.index).ffill().dropna().iloc[0] or 1) * psc for i,s in enumerate(series_list)})
    ceq = norm.sum(axis=1); st = compute_stats(ceq)
    ceq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(
        os.path.join(EQUITY_DIR,f"combined_{var_name}.csv"),index=False)
    combined_results[var_name] = {"n_sleeves":n_sl,"sleeves":list(sleeve_results.keys()),**st}
    print(f"  {var_name:>12}  n={n_sl}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

out = {"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
       "canonical_params":{"top_pct":CANON_TOP_PCT,"rmw_window":CANON_RMW_WIN,"freq":CANON_FREQ},
       "sleeves":{b:{v:d["metrics"] for v,d in vd.items()} for b,vd in sleeve_results.items()},
       "combined":combined_results}
jp = os.path.join(RESULTS_DIR, "quality_profitability_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out, f, indent=2, default=str)
print(f"\n  JSON → {jp}\n  Equity → {EQUITY_DIR}/\n{'='*70}\nDone.\n{'='*70}")
