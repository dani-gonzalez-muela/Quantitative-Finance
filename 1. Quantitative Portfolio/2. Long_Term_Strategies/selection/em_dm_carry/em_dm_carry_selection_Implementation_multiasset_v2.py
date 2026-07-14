# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""EM/DM Carry — Implementation v2 (TYPE 2 SELECTION). Uses build_basket_equity."""
import sys, os
_FILE_DIR=os.path.dirname(os.path.abspath(__file__)); _ROOT=os.path.normpath(os.path.join(_FILE_DIR,"..","..",".."))
if _ROOT not in sys.path: sys.path.insert(0,_ROOT)
import json, warnings; import numpy as np, pandas as pd
from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")
STRATEGY_NAME="em_dm_carry_v2"; STARTING_CAPITAL=100_000
START_DATE="2016-01-01"; END_DATE="2026-04-01"; TC_BPS_OW=5; ALLOCATION=0.85
HERE=os.path.dirname(os.path.abspath(__file__)); RESULTS_DIR=os.path.join(HERE,"results")
EQUITY_DIR=os.path.join(RESULTS_DIR,f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR=data_dir("daily_tickers")
SUMMARY_PATH=os.path.join(RESULTS_DIR,"em_dm_carry_v2_multiasset_summary.json")
os.makedirs(EQUITY_DIR,exist_ok=True)
_FREQ_MONTHS={"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}
EM_TICKERS=["EEM","INDA","EWZ","EWJ","EWG","EWU","EWA","EWC","EWP","EWI","EWL"]
DM_TICKERS=["SPY","QQQ","IWM","MDY"]

print("="*70); print("EM/DM CARRY — Implementation v2  (TYPE 2 SELECTION)"); print("="*70)
if not os.path.exists(SUMMARY_PATH): raise FileNotFoundError(f"Run backtest v2 first: {SUMMARY_PATH}")
with open(SUMMARY_PATH) as f: summary=json.load(f)
basket_cfgs=summary["baskets"]; passing={n:c for n,c in basket_cfgs.items() if c.get("binomial_significant",False)}
print(f"  Baskets: {len(basket_cfgs)}  Passing: {len(passing)}")
for n,c in basket_cfgs.items():
    print(f"    [{'PASS' if c.get('binomial_significant') else 'FAIL'}] {n}  med={c['canonical_median_sharpe']:.3f}  p={c['binomial_pvalue']:.4f}")
if not passing: import sys; sys.exit(0)

def load_prices(tickers):
    frames={}
    for t in tickers:
        p=os.path.join(DATA_DIR,f"{t}.csv")
        if not os.path.exists(p): continue
        try:
            df=pd.read_csv(p,parse_dates=["date"],index_col="date").sort_index(); df.index=pd.to_datetime(df.index)
            s=df["close"].dropna(); s=s[(s.index>=START_DATE)&(s.index<=END_DATE)]
            if len(s)>=252: frames[t]=s
        except: pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()

em_prices=load_prices(EM_TICKERS); dm_prices=load_prices(DM_TICKERS)
all_prices=pd.concat([em_prices,dm_prices],axis=1).ffill().dropna(how="all")
all_prices=all_prices[(all_prices.index>=START_DATE)&(all_prices.index<=END_DATE)]
em_avail=[t for t in EM_TICKERS if t in all_prices.columns]; dm_avail=[t for t in DM_TICKERS if t in all_prices.columns]

def compute_em_dm_signal(carry_win,freq,threshold,top_pct):
    monthly=all_prices.resample(freq).last(); fm=_FREQ_MONTHS.get(freq,1); wper=max(1,int(round(carry_win/fm)))
    em_m=monthly[em_avail].mean(axis=1); dm_m=monthly[dm_avail].mean(axis=1)
    n_em=max(1,round(len(em_avail)*top_pct)); n_dm=max(1,round(len(dm_avail)*top_pct))
    sig=pd.DataFrame(0.0,index=monthly.index,columns=all_prices.columns)
    for i in range(len(monthly)):
        if i<wper+1: continue
        em_ret=float(em_m.iloc[i-1]/em_m.iloc[i-1-wper]-1) if em_m.iloc[i-1-wper]!=0 else 0.0
        dm_ret=float(dm_m.iloc[i-1]/dm_m.iloc[i-1-wper]-1) if dm_m.iloc[i-1-wper]!=0 else 0.0
        if em_ret-dm_ret>threshold:
            sub=monthly[em_avail]; mom=sub.iloc[i-1]/sub.iloc[i-1-wper]-1
            tops=mom.nlargest(n_em).index.tolist()
            for sym in tops: sig.iloc[i][sym]=float(mom[sym])+1e-9
        else:
            sub=monthly[dm_avail]; mom=sub.iloc[i-1]/sub.iloc[i-1-wper]-1
            tops=mom.nlargest(n_dm).index.tolist()
            for sym in tops: sig.iloc[i][sym]=float(mom[sym])+1e-9
    return sig

def generate_trades(sig,freq):
    rdates=sig.index.tolist(); trades=[]
    for i,rd in enumerate(rdates):
        tops=sig.loc[rd][sig.loc[rd]>0].index.tolist()
        if not tops: continue
        ec=all_prices.index[all_prices.index>=rd]
        if len(ec)==0: continue
        ed=ec[0]
        if i+1<len(rdates):
            xc=all_prices.index[all_prices.index>=rdates[i+1]]
            if len(xc)==0: continue
            xd=xc[0]; xr="rebalance"
        else: xd=all_prices.index[-1]; xr="end_of_data"
        for sym in tops:
            if sym not in all_prices.columns: continue
            ep=all_prices.loc[ed,sym]; xp=all_prices.loc[xd,sym]
            if pd.isna(ep) or pd.isna(xp): continue
            trades.append({"entry_time":ed,"exit_time":xd,"direction":"long","instrument":sym,
                           "entry_price":round(float(ep),4),"exit_price":round(float(xp),4),
                           "pct_return_gross":round(float((xp-ep)/ep),6),"exit_reason":xr,"stop_price":np.nan})
    if not trades: return pd.DataFrame()
    df=pd.DataFrame(trades); df["entry_time"]=pd.to_datetime(df["entry_time"]); df["exit_time"]=pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time","instrument"]).reset_index(drop=True)

def compute_stats(eq):
    r=eq.pct_change().dropna(); sh=float(r.mean()/r.std()*np.sqrt(252)) if r.std()>0 else 0.0
    days=(eq.index[-1]-eq.index[0]).days; cagr=float(((eq.iloc[-1]/eq.iloc[0])**(365.25/days)-1)*100) if days>0 else 0.0
    peak=eq.cummax(); dd=(eq-peak)/peak
    return {"sharpe":round(sh,4),"cagr_pct":round(cagr,2),"max_dd_pct":round(float(dd.min()*100),2)}

N_passing=len(passing); sleeve_cap=STARTING_CAPITAL/N_passing; basket_results={}; sleeve_eq_dict={}
for bname,cfg in passing.items():
    cp=cfg["canonical_params"]; top_pct=float(cp["top_pct"]); freq=cp["freq"]; cw=int(cp["carry_window"]); th=float(cp["threshold"])
    sig=compute_em_dm_signal(cw,freq,th,top_pct); trades=generate_trades(sig,freq)
    print(f"  BASKET: {bname}  top_pct={top_pct} cw={cw} th={th} {freq}  {len(trades)} trades")
    if trades.empty: continue
    daily_prices={s: all_prices[s] for s in all_prices.columns}
    res=build_basket_equity(trades,daily_prices,starting_capital=sleeve_cap,allocation=ALLOCATION,include_fees=True)
    eq=res["daily_equity"]; st=compute_stats(eq)
    eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(os.path.join(EQUITY_DIR,f"{bname}_equity.csv"),index=False)
    print(f"    Sharpe={st['sharpe']:.3f}  CAGR={st['cagr_pct']:.2f}%  MaxDD={st['max_dd_pct']:.2f}%")
    sleeve_eq_dict[bname]=eq; basket_results[bname]={"canonical_params":cp,"n_trades":len(trades),"sleeve_capital":sleeve_cap,"allocation":ALLOCATION,"stats":st}

if sleeve_eq_dict:
    all_dates=pd.to_datetime(sorted(set().union(*[s.index for s in sleeve_eq_dict.values()])))
    aligned={n: eq.reindex(all_dates).ffill().bfill() for n,eq in sleeve_eq_dict.items()}
    combined=sum(aligned.values()); combined.index.name="date"; combined.name="equity"
    cst=compute_stats(combined); print(f"  COMBINED: Sharpe={cst['sharpe']:.4f}  CAGR={cst['cagr_pct']:.2f}%  MaxDD={cst['max_dd_pct']:.2f}%")
    combined.reset_index().to_csv(os.path.join(EQUITY_DIR,"combined_equity.csv"),index=False)
else: cst={}
jp=os.path.join(RESULTS_DIR,"em_dm_carry_v2_implementations_multiasset.json")
with open(jp,"w") as f: json.dump({"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
           "starting_capital":STARTING_CAPITAL,"allocation":ALLOCATION,"n_passing_baskets":N_passing,
           "sleeve_capital":sleeve_cap,"baskets":basket_results,"combined_stats":cst},f,indent=2,default=str)
print(f"  JSON → {jp}")
