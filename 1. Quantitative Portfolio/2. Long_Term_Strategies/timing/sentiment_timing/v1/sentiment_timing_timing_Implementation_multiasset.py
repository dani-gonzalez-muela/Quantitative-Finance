# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Sentiment Timing (VIX) — Multi-Asset Implementation
Canonical: vix_low=15, vix_high=25; exposure: <15→0.5x, [15,25]→1.0x, >25→1.5x
Passing instruments: QQQ, XLK
One sleeve per passing instrument; combined 1/N.
Monthly periods; VIX-sized returns.
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)
import json, warnings, numpy as np, pandas as pd, duckdb
from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME="sentiment_timing"; STARTING_CAPITAL=100_000; TC_BPS_OW=5
START_DATE="2016-01-01"; END_DATE="2026-04-01"
HERE=os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR=os.path.join(HERE,"results")
EQUITY_DIR=os.path.join(RESULTS_DIR,f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR=data_dir("daily_tickers")
SUMMARY_PATH=os.path.join(RESULTS_DIR,"sentiment_timing_multiasset_summary.json")
VIX_PARQUET=os.path.join(_ROOT,"data","wrds","15_cboe_vix.parquet")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("="*70); print("SENTIMENT TIMING (VIX) — Multi-Asset Implementation"); print("="*70)
with open(SUMMARY_PATH) as f: summary=json.load(f)
cp=summary["canonical_params"]
VL=float(cp["vix_low"]); VH=float(cp["vix_high"])
EL=float(cp["exp_low"]); EM_=float(cp["exp_mid"]); EH=float(cp["exp_high"])
PASSING=summary["passing_instruments"]
print(f"\nVIX: <{VL}→{EL}x, [{VL},{VH}]→{EM_}x, >{VH}→{EH}x\nPassing: {PASSING}\n")

con=duckdb.connect()
try:
    vix=con.execute(f"SELECT date, vix_close FROM read_parquet('{VIX_PARQUET}') ORDER BY date").fetchdf()
    vix["date"]=pd.to_datetime(vix["date"]); vix=vix.set_index("date").sort_index()
except:
    df_=con.execute(f"SELECT * FROM read_parquet('{VIX_PARQUET}') LIMIT 3").fetchdf()
    dc=[c for c in df_.columns if "date" in c.lower()][0]
    vc=[c for c in df_.columns if "vix" in c.lower() or "close" in c.lower()][-1]
    vix=con.execute(f"SELECT {dc},{vc} FROM read_parquet('{VIX_PARQUET}') ORDER BY {dc}").fetchdf()
    vix["date"]=pd.to_datetime(vix[dc]); vix=vix.rename(columns={vc:"vix_close"}).set_index("date").sort_index()
vix_daily=vix["vix_close"][(vix.index>=START_DATE)&(vix.index<=END_DATE)]
vix_monthly=vix_daily.resample("ME").mean()
print(f"VIX loaded: {len(vix_daily)} days")

def vix_exp(v): return EL if v<VL else (EH if v>VH else EM_)

def load_close(t):
    p=os.path.join(DATA_DIR,f"{t}.csv")
    if not os.path.exists(p): return None
    try:
        df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index()
        df.index=pd.to_datetime(df.index); df=df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df["close"].resample("ME").last() if len(df)>=252 else None
    except: return None

def gen_trades(monthly, ticker):
    ret=monthly.pct_change(); trades=[]
    for i in range(1,len(monthly)):
        d=monthly.index[i]; dp=monthly.index[i-1]
        vm=vix_monthly.get(d, np.nan)
        if pd.isna(vm): continue
        exp=vix_exp(float(vm)); rr=float(ret.iloc[i]) if not pd.isna(ret.iloc[i]) else 0.0
        ep=float(monthly.iloc[i-1]); xp=float(monthly.iloc[i])
        trades.append({"entry_time":dp,"exit_time":d,"direction":"long","instrument":ticker,
                       "entry_price":round(ep,4),"exit_price":round(ep*(1+rr*exp),4),
                       "pct_return_gross":round(rr*exp,6),"exit_reason":"month_end","stop_price":np.nan})
    return pd.DataFrame(trades)

def stats(eq):
    r=eq.pct_change().dropna()
    sh=float(r.mean()/r.std()*np.sqrt(252)) if r.std()>0 else 0.0
    d=(eq.index[-1]-eq.index[0]).days
    cagr=float(((eq.iloc[-1]/eq.iloc[0])**(365.25/d)-1)*100) if d>0 else 0.0
    dd=float(((eq-eq.cummax())/eq.cummax()).min()*100)
    return {"sharpe":round(sh,4),"cagr":round(cagr,2),"max_dd":round(dd,2)}

ALLOC={"simple_85":0.85,"simple_100":1.00}; sr={}; cd={}

# For build_basket_equity we need daily prices too
def load_daily(t):
    p=os.path.join(DATA_DIR,f"{t}.csv")
    if not os.path.exists(p): return None
    try:
        df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index()
        df.index=pd.to_datetime(df.index); df=df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df["close"] if len(df)>=252 else None
    except: return None

for ticker in PASSING:
    monthly=load_close(ticker)
    if monthly is None: print(f"  {ticker}: no data"); continue
    trades=gen_trades(monthly,ticker)
    if trades.empty: print(f"  {ticker}: no trades"); continue
    daily_c=load_daily(ticker)
    if daily_c is None: print(f"  {ticker}: no daily close"); continue
    dp={ticker:daily_c}; sr[ticker]={}
    for vn,al in ALLOC.items():
        res=build_basket_equity(trades,dp,starting_capital=STARTING_CAPITAL,allocation=al,include_fees=True)
        eq=res["daily_equity"]; st=stats(eq)
        eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(os.path.join(EQUITY_DIR,f"{ticker}_{vn}.csv"),index=False)
        sr[ticker][vn]={"metrics":{**st,"n_trades":len(trades),"allocation":al},"equity_series":eq}
        cd.setdefault(vn,[]).append(eq)
    s85=sr[ticker]["simple_85"]["metrics"]
    print(f"  {ticker:<8}  {len(trades):>3} trades  Sharpe={s85['sharpe']:>6.3f}  CAGR={s85['cagr']:>6.2f}%")

print(f"\n{'='*70}\nCOMBINED\n{'='*70}")
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
jp=os.path.join(RESULTS_DIR,"sentiment_timing_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out,f,indent=2,default=str)
print(f"\n  JSON → {jp}\n{'='*70}\nDone.\n{'='*70}")
