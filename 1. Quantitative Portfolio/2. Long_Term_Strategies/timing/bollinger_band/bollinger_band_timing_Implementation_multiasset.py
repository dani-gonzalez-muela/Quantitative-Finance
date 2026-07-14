# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Bollinger Band — Multi-Asset Implementation
============================================
Canonical: bb_period=30, bb_std=2.0, min_hold_days=30
Loads passing instruments from bollinger_band_multiasset_summary.json.
One sleeve per passing instrument; combined 1/N capital weighting.

Outputs: results/bollinger_band_multiasset_daily_equity/*.csv
         results/bollinger_band_implementations_multiasset.json
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

STRATEGY_NAME    = "bollinger_band"
STARTING_CAPITAL = 100_000
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = os.path.join(_ROOT, "long_term", "multi_asset_expansion", "data", "tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "bollinger_band_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("="*70); print("BOLLINGER BAND — Multi-Asset Implementation"); print("="*70)

with open(SUMMARY_PATH) as f: summary = json.load(f)
cp = summary["canonical_params"]
BB_PERIOD     = int(cp["bb_period"])
BB_STD        = float(cp["bb_std"])
MIN_HOLD_DAYS = int(cp["min_hold_days"])
PASSING       = summary["passing_instruments"]
print(f"\nCanonical: bb_period={BB_PERIOD}, bb_std={BB_STD}, min_hold={MIN_HOLD_DAYS}")
print(f"Passing  : {PASSING} ({len(PASSING)} instruments)\n")

def load_ohlc(ticker):
    p = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(p): return None
    try:
        df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df if len(df)>=252 and "close" in df.columns else None
    except: return None

def generate_bb_trades(df, ticker):
    close = df["close"]; sma = close.rolling(BB_PERIOD).mean()
    sigma = close.rolling(BB_PERIOD).std()
    upper = sma + BB_STD*sigma; lower = sma - BB_STD*sigma
    trades=[]; in_trade=False; ep=ed=ei=None
    for i in range(1, len(df)):
        today=df.index[i]
        if not in_trade:
            if close.iloc[i-1]<=lower.iloc[i-1] and not pd.isna(lower.iloc[i-1]):
                ep_val = df["open"].iloc[i] if "open" in df.columns and not pd.isna(df["open"].iloc[i]) else close.iloc[i]
                in_trade=True; ed=today; ep=float(ep_val); ei=i
        else:
            dh=i-ei
            if dh>=MIN_HOLD_DAYS and close.iloc[i]>=upper.iloc[i] and not pd.isna(upper.iloc[i]):
                xp=float(close.iloc[i])
                trades.append({"entry_time":ed,"exit_time":today,"direction":"long","instrument":ticker,
                               "entry_price":round(ep,4),"exit_price":round(xp,4),
                               "pct_return_gross":round((xp-ep)/ep,6),"exit_reason":"upper_band","stop_price":np.nan})
                in_trade=False
    if in_trade and ep:
        xp=float(close.iloc[-1])
        trades.append({"entry_time":ed,"exit_time":df.index[-1],"direction":"long","instrument":ticker,
                       "entry_price":round(ep,4),"exit_price":round(xp,4),
                       "pct_return_gross":round((xp-ep)/ep,6),"exit_reason":"end_of_data","stop_price":np.nan})
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

for ticker in PASSING:
    df = load_ohlc(ticker)
    if df is None: print(f"  {ticker}: no data"); continue
    trades = generate_bb_trades(df, ticker)
    if trades.empty: print(f"  {ticker}: no trades"); continue
    daily_prices = {ticker: df["close"]}
    sleeve_results[ticker] = {}
    for var_name, alloc in ALLOC_VARIANTS.items():
        res = build_basket_equity(trades, daily_prices, starting_capital=STARTING_CAPITAL, allocation=alloc, include_fees=True)
        eq = res["daily_equity"]; st = compute_stats(eq)
        eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(
            os.path.join(EQUITY_DIR,f"{ticker}_{var_name}.csv"),index=False)
        sleeve_results[ticker][var_name] = {"metrics":{**st,"n_trades":len(trades),"allocation":alloc},"equity_series":eq}
        combined_daily.setdefault(var_name,[]).append(eq)
    st85 = sleeve_results[ticker]["simple_85"]["metrics"]
    print(f"  {ticker:<8}  {len(trades):>3} trades  Sharpe={st85['sharpe']:>6.3f}  CAGR={st85['cagr']:>6.2f}%")

print(f"\n{'='*70}\nCOMBINED  (1/N per instrument)\n{'='*70}")
combined_results = {}
for var_name, series_list in combined_daily.items():
    if not series_list: continue
    n_sl=len(series_list); psc=STARTING_CAPITAL/n_sl
    aligned=pd.concat(series_list,axis=1).ffill().dropna()
    norm=pd.DataFrame({f"s{i}":s.reindex(aligned.index).ffill()/(s.reindex(aligned.index).ffill().dropna().iloc[0] or 1)*psc for i,s in enumerate(series_list)})
    ceq=norm.sum(axis=1); st=compute_stats(ceq)
    ceq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(
        os.path.join(EQUITY_DIR,f"combined_{var_name}.csv"),index=False)
    combined_results[var_name]={"n_sleeves":n_sl,"instruments":PASSING,**st}
    print(f"  {var_name:>12}  n={n_sl}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

out={"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
     "canonical_params":{"bb_period":BB_PERIOD,"bb_std":BB_STD,"min_hold_days":MIN_HOLD_DAYS},
     "passing_instruments":PASSING,
     "sleeves":{t:{v:d["metrics"] for v,d in vd.items()} for t,vd in sleeve_results.items()},
     "combined":combined_results}
jp=os.path.join(RESULTS_DIR,"bollinger_band_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out,f,indent=2,default=str)
print(f"\n  JSON → {jp}\n  Equity → {EQUITY_DIR}/\n{'='*70}\nDone.\n{'='*70}")
