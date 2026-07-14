# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Quality/Profitability — Implementation v2 (TYPE 2 SELECTION). Uses build_basket_equity."""
import sys, os
_FILE_DIR=os.path.dirname(os.path.abspath(__file__)); _ROOT=os.path.normpath(os.path.join(_FILE_DIR,"..","..",".."))
if _ROOT not in sys.path: sys.path.insert(0,_ROOT)
import json, warnings; import numpy as np, pandas as pd
from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")
STRATEGY_NAME="quality_profitability_v2"; STARTING_CAPITAL=100_000
START_DATE="2016-01-01"; END_DATE="2026-04-01"; TC_BPS_OW=5; ALLOCATION=0.85
HERE=os.path.dirname(os.path.abspath(__file__)); RESULTS_DIR=os.path.join(HERE,"results")
EQUITY_DIR=os.path.join(RESULTS_DIR,f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR=data_dir("daily_tickers")
SUMMARY_PATH=os.path.join(RESULTS_DIR,"quality_profitability_v2_multiasset_summary.json")
FF_PATH=os.path.join(os.path.dirname(HERE),"regime_factor_rotation","data","ff_factors_monthly.csv")
os.makedirs(EQUITY_DIR,exist_ok=True)
_FREQ_MONTHS={"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}
UNIVERSE_SPECS={"us_equity_broad":["SPY","QQQ","IWM","MDY"]}

print("="*70); print("QUALITY/PROFITABILITY — Implementation v2  (TYPE 2 SELECTION)"); print("="*70)
if not os.path.exists(SUMMARY_PATH): raise FileNotFoundError(f"Run backtest v2 first: {SUMMARY_PATH}")
with open(SUMMARY_PATH) as f: summary=json.load(f)
basket_cfgs=summary["baskets"]; passing={n:c for n,c in basket_cfgs.items() if c.get("binomial_significant",False)}
print(f"  Baskets: {len(basket_cfgs)}  Passing: {len(passing)}")
for n,c in basket_cfgs.items():
    print(f"    [{'PASS' if c.get('binomial_significant') else 'FAIL'}] {n}  med={c['canonical_median_sharpe']:.3f}")
if not passing: import sys; sys.exit(0)

ff=pd.read_csv(FF_PATH,parse_dates=["Date"],index_col="Date").sort_index()
ff.index=ff.index+pd.offsets.MonthEnd(0); rmw=ff["RMW"]/100

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

def compute_quality_signal(rmw_series,rmw_window,freq,prices_wide):
    monthly=prices_wide.resample(freq).last(); fm=_FREQ_MONTHS.get(freq,1)
    rwper=max(1,int(round(rmw_window/fm)))
    rmw_rebal=(1+rmw_series).resample(freq).prod()-1
    sig=pd.DataFrame(index=monthly.index,columns=monthly.columns,dtype=float)
    for i in range(len(monthly)):
        rd=monthly.index[i]
        rmw_end=rmw_rebal.index[rmw_rebal.index<=rd]
        if len(rmw_end)<rwper+1: sig.iloc[i]=0.0; continue
        rmw_cum=(1+rmw_rebal.iloc[rmw_rebal.index.get_loc(rmw_end[-1])-rwper:rmw_rebal.index.get_loc(rmw_end[-1])]).prod()-1
        quality_on=float(rmw_cum)>0
        if not quality_on: sig.iloc[i]=0.0
        else:
            pi=i-rwper-1; ri=i-1
            if pi<0 or ri<0: sig.iloc[i]=1.0
            else:
                mom=monthly.iloc[ri]/monthly.iloc[pi]-1
                sig.iloc[i]=mom.clip(lower=0)
    return sig

def generate_trades(prices,sig,top_n,freq):
    rdates=sig.index.tolist(); trades=[]
    for i,rd in enumerate(rdates):
        scores=sig.loc[rd]
        if scores.sum()==0: tops=prices.columns.tolist()
        else: pos=scores[scores>0]; tops=pos.nlargest(top_n).index.tolist() if top_n<len(pos) else pos.index.tolist()
        if not tops: continue
        ec=prices.index[prices.index>=rd]
        if len(ec)==0: continue
        ed=ec[0]
        if i+1<len(rdates):
            xc=prices.index[prices.index>=rdates[i+1]]
            if len(xc)==0: continue
            xd=xc[0]; xr="rebalance"
        else: xd=prices.index[-1]; xr="end_of_data"
        for sym in tops:
            if sym not in prices.columns: continue
            ep=prices.loc[ed,sym]; xp=prices.loc[xd,sym]
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
    cp=cfg["canonical_params"]; rmw_window=int(cp["rmw_window"]); freq=cp["freq"]; top_pct=float(cp["top_pct"])
    tickers=UNIVERSE_SPECS.get(bname,cfg.get("instruments",[]))
    prices=load_prices(tickers)
    if prices.empty: continue
    top_n=max(1,round(len(prices.columns)*top_pct)); sig=compute_quality_signal(rmw,rmw_window,freq,prices)
    trades=generate_trades(prices,sig,top_n,freq)
    print(f"  BASKET: {bname}  rmw_win={rmw_window} top_n={top_n} {freq}  {len(trades)} trades")
    if trades.empty: continue
    daily_prices={s: prices[s] for s in prices.columns}
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
jp=os.path.join(RESULTS_DIR,"quality_profitability_v2_implementations_multiasset.json")
with open(jp,"w") as f: json.dump({"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
           "starting_capital":STARTING_CAPITAL,"allocation":ALLOCATION,"n_passing_baskets":N_passing,
           "sleeve_capital":sleeve_cap,"baskets":basket_results,"combined_stats":cst},f,indent=2,default=str)
print(f"  JSON → {jp}")
