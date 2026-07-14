# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Donchian Channel — Multi-Asset Implementation
Canonical: channel_period=20, min_hold_days=30, stop_loss=-0.08
One sleeve per passing instrument; combined 1/N.
Outputs: results/donchian_channel_multiasset_daily_equity/  +  JSON metrics
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)
import json, warnings, numpy as np, pandas as pd
from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME="donchian_channel"; STARTING_CAPITAL=100_000; TC_BPS_OW=5
START_DATE="2016-01-01"; END_DATE="2026-04-01"
HERE=os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR=os.path.join(HERE,"results")
EQUITY_DIR=os.path.join(RESULTS_DIR,f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR=data_dir("daily_tickers")
SUMMARY_PATH=os.path.join(RESULTS_DIR,"donchian_channel_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("="*70); print("DONCHIAN CHANNEL — Multi-Asset Implementation"); print("="*70)
with open(SUMMARY_PATH) as f: summary=json.load(f)
cp=summary["canonical_params"]
CH=int(cp["channel_period"]); MH=int(cp["min_hold_days"]); SL=float(cp["stop_loss"])
PASSING=summary["passing_instruments"]
print(f"\nCanonical: ch={CH}, min_hold={MH}, stop={SL}\nPassing  : {PASSING}\n")

def load_ohlc(t):
    p=os.path.join(DATA_DIR,f"{t}.csv")
    if not os.path.exists(p): return None
    try:
        df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index()
        df.index=pd.to_datetime(df.index)
        df=df[(df.index>=START_DATE)&(df.index<=END_DATE)]
        return df if len(df)>=252 and "close" in df.columns else None
    except: return None

def gen_trades(df, ticker):
    close=df["close"]; rh=close.shift(1).rolling(CH).max(); rl=close.shift(1).rolling(CH).min()
    trades=[]; in_t=False; ep=ed=ei=None
    for i in range(CH+1,len(df)):
        today=df.index[i]; cp_=float(close.iloc[i])
        if not in_t:
            if not pd.isna(rh.iloc[i]) and cp_>float(rh.iloc[i]):
                epv=df["open"].iloc[i] if "open" in df.columns and not pd.isna(df["open"].iloc[i]) else cp_
                in_t=True; ed=today; ep=float(epv); ei=i
        else:
            dh=i-ei; pr=(cp_-ep)/ep if ep else 0.0; xr=None
            if pr<=SL: xr="stop_loss"
            elif not pd.isna(rl.iloc[i]) and cp_<float(rl.iloc[i]) and dh>=MH: xr="lower_channel"
            elif dh>=MH*3: xr="max_hold"
            if xr:
                trades.append({"entry_time":ed,"exit_time":today,"direction":"long","instrument":ticker,
                               "entry_price":round(ep,4),"exit_price":round(cp_,4),
                               "pct_return_gross":round(pr,6),"exit_reason":xr,"stop_price":round(ep*(1+SL),4)})
                in_t=False
    if in_t and ep:
        cp_=float(close.iloc[-1])
        trades.append({"entry_time":ed,"exit_time":df.index[-1],"direction":"long","instrument":ticker,
                       "entry_price":round(ep,4),"exit_price":round(cp_,4),
                       "pct_return_gross":round((cp_-ep)/ep,6),"exit_reason":"end_of_data","stop_price":round(ep*(1+SL),4)})
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
    df=load_ohlc(ticker)
    if df is None: print(f"  {ticker}: no data"); continue
    trades=gen_trades(df,ticker)
    if trades.empty: print(f"  {ticker}: no trades"); continue
    dp={ticker:df["close"]}; sr[ticker]={}
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
     "canonical_params":{"channel_period":CH,"min_hold_days":MH,"stop_loss":SL},
     "passing_instruments":PASSING,
     "sleeves":{t:{v:d["metrics"] for v,d in vd.items()} for t,vd in sr.items()},
     "combined":cr}
jp=os.path.join(RESULTS_DIR,"donchian_channel_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out,f,indent=2,default=str)
print(f"\n  JSON → {jp}\n{'='*70}\nDone.\n{'='*70}")
