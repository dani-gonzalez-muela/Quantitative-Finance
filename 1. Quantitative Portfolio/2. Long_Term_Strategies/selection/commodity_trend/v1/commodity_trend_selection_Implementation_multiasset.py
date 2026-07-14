# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Sector Momentum — Multi-Asset Implementation
=============================================
Canonical: top_pct=0.25, mom=3m, 6ME
Baskets  : us_sectors, us_factor

Outputs: results/commodity_trend_multiasset_daily_equity/*.csv
         results/commodity_trend_implementations_multiasset.json
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

STRATEGY_NAME    = "commodity_trend"
STARTING_CAPITAL = 100_000
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = data_dir("daily_tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "commodity_trend_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

_FREQ_MONTHS = {"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}

UNIVERSE_SPECS = {
    "commodities": ['GLD', 'SLV', 'DBC', 'USO', 'UNG', 'GDX', 'PDBC'],
    "real_assets": ['VNQ', 'VNQI', 'AMLP', 'XLRE']
}

print("="*70); print("COMMODITY TREND — Multi-Asset Implementation"); print("="*70)

with open(SUMMARY_PATH) as f: summary = json.load(f)
best = summary["best_params"]
CANON_TOP_PCT = float(best["top_pct"]); CANON_MOM_WIN = int(best["mom_window"]); CANON_FREQ = best["freq"]
PASSING_BASKETS = list(summary["universes"].keys())
print(f"\nCanonical: top_pct={CANON_TOP_PCT}, mom={CANON_MOM_WIN}m, freq={CANON_FREQ}")
print(f"Passing  : {PASSING_BASKETS}\n")

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

def compute_momentum(prices_wide, mom_win, freq):
    monthly = prices_wide.resample(freq).last()
    fmon = _FREQ_MONTHS.get(freq,1); skip=1
    wper = max(1, int(round(mom_win/fmon)))
    sig = pd.DataFrame(index=monthly.index, columns=monthly.columns, dtype=float)
    for i in range(len(monthly)):
        pi = i - wper - skip; ri = i - skip
        if pi<0 or ri<0: continue
        sig.iloc[i] = monthly.iloc[ri] / monthly.iloc[pi] - 1
    return sig

def generate_trades(prices_wide, signal_df, top_n, freq):
    rdates = signal_df.dropna(how="all").index.tolist(); trades = []; tc=2*TC_BPS_OW/10_000
    for i, rd in enumerate(rdates):
        scores = signal_df.loc[rd].dropna()
        tops = scores.nlargest(top_n).index.tolist() if top_n<len(scores) else scores.index.tolist()
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
    max_dd = float(dd.min()*100)
    return {"sharpe":round(sharpe,4),"cagr":round(cagr,2),"max_dd":round(max_dd,2)}

ALLOC_VARIANTS = {"simple_85":0.85,"simple_100":1.00}
sleeve_results = {}; combined_daily = {}

for basket_name in PASSING_BASKETS:
    tickers = UNIVERSE_SPECS.get(basket_name,[])
    prices  = load_prices(tickers)
    if prices.empty: print(f"  {basket_name}: no data"); continue
    n = len(prices.columns); top_n = max(1,round(n*CANON_TOP_PCT))
    sig = compute_momentum(prices, CANON_MOM_WIN, CANON_FREQ)
    trades = generate_trades(prices, sig, top_n, CANON_FREQ)
    if trades.empty: print(f"  {basket_name}: no trades"); continue
    daily_prices = {s: prices[s] for s in prices.columns}
    sleeve_results[basket_name] = {}
    print(f"\n  Basket: {basket_name}  ({len(prices.columns)} tickers, top_n={top_n}, {len(trades)} trades)")
    for var_name, alloc in ALLOC_VARIANTS.items():
        res = build_basket_equity(trades, daily_prices, starting_capital=STARTING_CAPITAL, allocation=alloc, include_fees=True)
        eq = res["daily_equity"]; st = compute_stats(eq)
        eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(os.path.join(EQUITY_DIR,f"{basket_name}_{var_name}.csv"),index=False)
        sleeve_results[basket_name][var_name] = {"metrics":{**st,"n_trades":len(trades),"allocation":alloc},"equity_series":eq}
        combined_daily.setdefault(var_name,[]).append(eq)
        print(f"    {var_name:>12}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

print(f"\n{'='*70}\nCOMBINED  (1/N per sleeve)\n{'='*70}")
combined_results = {}
for var_name, series_list in combined_daily.items():
    n_sl = len(series_list); psc = STARTING_CAPITAL/n_sl
    aligned = pd.concat(series_list, axis=1).ffill().dropna()
    norm = pd.DataFrame()
    for i,s in enumerate(series_list):
        sa = s.reindex(aligned.index).ffill(); fv=sa.dropna().iloc[0] if not sa.dropna().empty else 1.0
        norm[f"s{i}"] = sa/fv*psc
    ceq = norm.sum(axis=1); st = compute_stats(ceq)
    ceq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(os.path.join(EQUITY_DIR,f"combined_{var_name}.csv"),index=False)
    combined_results[var_name] = {"n_sleeves":n_sl,"sleeves":PASSING_BASKETS,**st}
    print(f"  {var_name:>12}  n={n_sl}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

out = {"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
       "canonical_params":{"top_pct":CANON_TOP_PCT,"mom_window":CANON_MOM_WIN,"freq":CANON_FREQ},
       "sleeves":{b:{v:d["metrics"] for v,d in vd.items()} for b,vd in sleeve_results.items()},
       "combined":combined_results}
jp = os.path.join(RESULTS_DIR, "commodity_trend_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out, f, indent=2, default=str)
print(f"\n  JSON → {jp}\n  Equity CSVs → {EQUITY_DIR}/\n{'='*70}\nDone.\n{'='*70}")
