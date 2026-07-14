# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Credit Carry — Multi-Asset Implementation
Canonical: mom_window=12m, benchmark=IEF
Passing instrument: BIL (hold when 12m return > IEF 12m return)
Single sleeve; no combination needed.
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)
import json, warnings, numpy as np, pandas as pd
from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME="credit_carry"; STARTING_CAPITAL=100_000; TC_BPS_OW=5
START_DATE="2016-01-01"; END_DATE="2026-04-01"
HERE=os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR=os.path.join(HERE,"results")
EQUITY_DIR=os.path.join(RESULTS_DIR,f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR=data_dir("daily_tickers")
SUMMARY_PATH=os.path.join(RESULTS_DIR,"credit_carry_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("="*70); print("CREDIT CARRY — Multi-Asset Implementation"); print("="*70)
with open(SUMMARY_PATH) as f: summary=json.load(f)
cp=summary["canonical_params"]
MW=int(cp["mom_window_months"]); BENCH=cp["benchmark"]
PASSING=summary["passing_instruments"]
print(f"\nCanonical: mom_window={MW}m, benchmark={BENCH}\nPassing  : {PASSING}\n")

def load_monthly(t):
    p=os.path.join(DATA_DIR,f"{t}.csv")
    if not os.path.exists(p): return None
    try:
        df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index()
        df.index=pd.to_datetime(df.index); df=df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df["close"].resample("ME").last() if len(df)>=252 else None
    except: return None

def load_daily(t):
    p=os.path.join(DATA_DIR,f"{t}.csv")
    if not os.path.exists(p): return None
    try:
        df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index()
        df.index=pd.to_datetime(df.index); df=df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df["close"] if len(df)>=252 else None
    except: return None

bench_m=load_monthly(BENCH)
if bench_m is None: print("ERROR: benchmark not found"); import sys; sys.exit(1)
bench_mom=bench_m.pct_change(MW).shift(1)

def gen_trades(etf_m, ticker):
    etf_ret=etf_m.pct_change(); etf_mom=etf_m.pct_change(MW).shift(1)
    trades=[]
    for i in range(1,len(etf_m)):
        d=etf_m.index[i]; dp=etf_m.index[i-1]
        em=etf_mom.get(d,np.nan); bm=bench_mom.get(d,np.nan)
        if pd.isna(em) or pd.isna(bm): continue
        if em<=bm: continue
        rr=float(etf_ret.iloc[i]) if not pd.isna(etf_ret.iloc[i]) else 0.0
        ep=float(etf_m.iloc[i-1]); xp=float(etf_m.iloc[i])
        trades.append({"entry_time":dp,"exit_time":d,"direction":"long","instrument":ticker,
                       "entry_price":round(ep,4),"exit_price":round(xp,4),
                       "pct_return_gross":round(rr,6),"exit_reason":"month_end","stop_price":np.nan})
    return pd.DataFrame(trades)

def stats(eq):
    r=eq.pct_change().dropna()
    sh=float(r.mean()/r.std()*np.sqrt(252)) if r.std()>0 else 0.0
    d=(eq.index[-1]-eq.index[0]).days
    cagr=float(((eq.iloc[-1]/eq.iloc[0])**(365.25/d)-1)*100) if d>0 else 0.0
    dd=float(((eq-eq.cummax())/eq.cummax()).min()*100)
    return {"sharpe":round(sh,4),"cagr":round(cagr,2),"max_dd":round(dd,2)}

ALLOC={"simple_85":0.85,"simple_100":1.00}; sr={}; cd={}
for ticker in PASSING:
    etf_m=load_monthly(ticker)
    if etf_m is None: print(f"  {ticker}: no data"); continue
    trades=gen_trades(etf_m,ticker)
    if trades.empty: print(f"  {ticker}: no trades"); continue
    daily_c=load_daily(ticker)
    if daily_c is None: print(f"  {ticker}: no daily"); continue
    dp={ticker:daily_c}; sr[ticker]={}
    for vn,al in ALLOC.items():
        res=build_basket_equity(trades,dp,starting_capital=STARTING_CAPITAL,allocation=al,include_fees=True)
        eq=res["daily_equity"]; st=stats(eq)
        eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(os.path.join(EQUITY_DIR,f"{ticker}_{vn}.csv"),index=False)
        sr[ticker][vn]={"metrics":{**st,"n_trades":len(trades),"allocation":al},"equity_series":eq}
        cd.setdefault(vn,[]).append(eq)
    s85=sr[ticker]["simple_85"]["metrics"]
    print(f"  {ticker:<8}  {len(trades):>3} trades  Sharpe={s85['sharpe']:>6.3f}  CAGR={s85['cagr']:>6.2f}%")

cr={}
for vn,sl in cd.items():
    n=len(sl); psc=STARTING_CAPITAL/n
    al=pd.concat(sl,axis=1).ffill().dropna()
    nm=pd.DataFrame({f"s{i}":s.reindex(al.index).ffill()/(s.reindex(al.index).ffill().dropna().iloc[0] or 1)*psc for i,s in enumerate(sl)})
    ceq=nm.sum(axis=1); st=stats(ceq)
    ceq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(os.path.join(EQUITY_DIR,f"combined_{vn}.csv"),index=False)
    cr[vn]={"n_sleeves":n,"instruments":PASSING,**st}
    print(f"  {vn:>12}  n={n}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

out={"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
     "canonical_params":dict(cp),"passing_instruments":PASSING,
     "sleeves":{t:{v:d["metrics"] for v,d in vd.items()} for t,vd in sr.items()},"combined":cr}
jp=os.path.join(RESULTS_DIR,"credit_carry_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out,f,indent=2,default=str)
print(f"\n  JSON → {jp}\n{'='*70}\nDone.\n{'='*70}")
