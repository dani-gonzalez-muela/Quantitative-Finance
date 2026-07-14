# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Turn of Month — Multi-Asset Implementation
Canonical: n_days_before=3, n_days_after=3 (last 3 + first 3 trading days of month)
Passing instruments: QQQ, XLV, XLRE, XLC
One sleeve per passing instrument; combined 1/N.
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)
import json, warnings, numpy as np, pandas as pd
from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME="turn_of_month"; STARTING_CAPITAL=100_000; TC_BPS_OW=5
START_DATE="2016-01-01"; END_DATE="2026-04-01"
HERE=os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR=os.path.join(HERE,"results")
EQUITY_DIR=os.path.join(RESULTS_DIR,f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR=data_dir("daily_tickers")
SUMMARY_PATH=os.path.join(RESULTS_DIR,"turn_of_month_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("="*70); print("TURN OF MONTH — Multi-Asset Implementation"); print("="*70)
with open(SUMMARY_PATH) as f: summary=json.load(f)
cp=summary["canonical_params"]
NB=int(cp["n_days_before"]); NA=int(cp["n_days_after"])
PASSING=summary["passing_instruments"]
print(f"\nCanonical: last_{NB} + first_{NA} trading days\nPassing  : {PASSING}\n")

def load_close(t):
    p=os.path.join(DATA_DIR,f"{t}.csv")
    if not os.path.exists(p): return None
    try:
        df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index()
        df.index=pd.to_datetime(df.index)
        df=df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df["close"] if len(df)>=252 and "close" in df.columns else None
    except: return None

def build_tom_mask(dates, nb, na):
    months=dates.to_period("M"); mask=pd.Series(False,index=dates)
    for m in months.unique():
        md=dates[months==m]
        if len(md)==0: continue
        for d in md[-nb:]: mask[d]=True
        for d in md[:na]: mask[d]=True
    return mask

def gen_trades(close, ticker):
    dates=close.index; mask=build_tom_mask(dates,NB,NA)
    trades=[]; in_w=False; ep=ed=None
    for i in range(1,len(dates)):
        if not in_w and mask.iloc[i]:
            ep=float(close.iloc[i-1]); ed=dates[i]; in_w=True
        elif in_w and not mask.iloc[i]:
            xp=float(close.iloc[i-1])
            trades.append({"entry_time":ed,"exit_time":dates[i],"direction":"long","instrument":ticker,
                           "entry_price":round(ep,4),"exit_price":round(xp,4),
                           "pct_return_gross":round((xp-ep)/ep,6),"exit_reason":"tom_end","stop_price":np.nan})
            in_w=False
    if in_w and ep:
        xp=float(close.iloc[-1])
        trades.append({"entry_time":ed,"exit_time":dates[-1],"direction":"long","instrument":ticker,
                       "entry_price":round(ep,4),"exit_price":round(xp,4),
                       "pct_return_gross":round((xp-ep)/ep,6),"exit_reason":"end_of_data","stop_price":np.nan})
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
    close=load_close(ticker)
    if close is None: print(f"  {ticker}: no data"); continue
    trades=gen_trades(close,ticker)
    if trades.empty: print(f"  {ticker}: no trades"); continue
    dp={ticker:close}; sr[ticker]={}
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
     "canonical_params":{"n_days_before":NB,"n_days_after":NA},
     "passing_instruments":PASSING,
     "sleeves":{t:{v:d["metrics"] for v,d in vd.items()} for t,vd in sr.items()},
     "combined":cr}
jp=os.path.join(RESULTS_DIR,"turn_of_month_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out,f,indent=2,default=str)
print(f"\n  JSON → {jp}\n{'='*70}\nDone.\n{'='*70}")
