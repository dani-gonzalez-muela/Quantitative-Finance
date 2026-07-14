# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Quality/Profitability — Multi-Asset Selection Backtest v2
FF5 RMW signal timing on us_equity_broad ETFs. n_boot=500.
Outputs: results/quality_profitability_v2_multiasset_summary.json
"""
import sys, os
_FILE_DIR=os.path.dirname(os.path.abspath(__file__)); _ROOT=os.path.normpath(os.path.join(_FILE_DIR,"..","..",".."))
if _ROOT not in sys.path: sys.path.insert(0,_ROOT)
import json, warnings, itertools
import numpy as np, pandas as pd
from scipy.stats import binom
warnings.filterwarnings("ignore")

STRATEGY_NAME="Quality/Profitability v2 (Multi-Asset)"; SAVE_NAME="quality_profitability"
START_DATE="2016-01-01"; END_DATE="2026-04-01"; TC_BPS_OW=5; N_BOOT=500
DATA_DIR=data_dir("daily_tickers")
HERE=os.path.dirname(os.path.abspath(__file__)); RESULTS_DIR=os.path.join(HERE,"results")
FF_PATH=os.path.join(os.path.dirname(HERE),"regime_factor_rotation","data","ff_factors_monthly.csv")

UNIVERSE_SPECS={"us_equity_broad":["SPY","QQQ","IWM","MDY"]}
MIN_TICKERS=2
RMW_WINDOWS=[6,9,12,18,24]; REBAL_FREQS=["ME","2ME","QE","6ME","12ME"]; TOP_PCTS=[0.25,0.50,0.75,1.00]
ALL_COMBOS=list(itertools.product(RMW_WINDOWS,REBAL_FREQS,TOP_PCTS))
_FREQ_MONTHS={"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}

print("="*75); print(f"{STRATEGY_NAME} — Backtest v2")
print(f"Grid: {len(ALL_COMBOS)} combos | Period: {START_DATE} → {END_DATE}\n")

if not os.path.exists(FF_PATH):
    print(f"ERROR: FF factors not found: {FF_PATH}"); import sys; sys.exit(1)
ff=pd.read_csv(FF_PATH,parse_dates=["Date"],index_col="Date").sort_index()
ff.index=ff.index+pd.offsets.MonthEnd(0); rmw=ff["RMW"]/100
print(f"FF RMW: {rmw.index[0].date()} → {rmw.index[-1].date()}, {len(rmw)} months")

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

UNIVERSES={}
for uni,tickers in UNIVERSE_SPECS.items():
    w=load_prices(tickers)
    if len(w.columns)>=MIN_TICKERS: UNIVERSES[uni]=w; print(f"  {uni}: {len(w.columns)} tickers")

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

def run_trades(prices,combo):
    rw,freq,tp=combo; top_n=max(1,round(len(prices.columns)*tp))
    try:
        sig=compute_quality_signal(rmw,rw,freq,prices); return generate_trades(prices,sig,top_n,freq)
    except: return pd.DataFrame()

def basket_sharpe(trades):
    if trades is None or trades.empty: return None
    tc_rt=2*TC_BPS_OW/10_000; cohort=trades.groupby("entry_time")["pct_return_gross"].mean(); r=cohort-tc_rt
    if len(r)<5 or r.std()==0: return None
    gaps=pd.to_datetime(cohort.index).to_series().diff().dropna().dt.days
    ppy=365/gaps.median() if len(gaps)>0 else 12
    return round(float(r.mean()/r.std()*np.sqrt(ppy)),4)

def basket_sig3(trades,n_boot=N_BOOT):
    if trades is None or trades.empty: return 0,0.0,{}
    tc_rt=2*TC_BPS_OW/10_000; cohort=trades.groupby("entry_time")["pct_return_gross"].mean()
    r=(cohort-tc_rt).values
    if len(r)<5 or r.std()==0: return 0,0.0,{}
    gaps=pd.to_datetime(cohort.index).to_series().diff().dropna().dt.days
    ann=np.sqrt(365/gaps.median() if len(gaps)>0 else 12); sh=float(r.mean()/r.std()*ann)
    from scipy.stats import ttest_1samp
    t,t2=ttest_1samp(r,0); tp2=float(t2/2) if t>0 else 1.0; g1=tp2<0.05
    rng=np.random.RandomState(42); bs=[rng.choice(r,size=len(r),replace=True) for _ in range(n_boot)]
    bp5=float(np.percentile([b.mean()/b.std()*ann if b.std()>0 else 0.0 for b in bs],5)); g2=bp5>0
    rng2=np.random.RandomState(42); ar=np.abs(r); cnt=0
    for _ in range(n_boot):
        s2=ar*rng2.choice([-1,1],size=len(ar))
        if (s2.mean()/s2.std()*ann if s2.std()>0 else 0.0)>=sh: cnt+=1
    pp=cnt/n_boot; g3=pp<0.05
    return int(g1)+int(g2)+int(g3),round(sh,4),{"t_p":round(tp2,4),"boot_p5":round(bp5,4),"perm_p":round(pp,4)}

def combo_to_params(c): rw,freq,tp=c; return {"rmw_window":int(rw),"freq":freq,"top_pct":float(tp)}

uni_names=list(UNIVERSES.keys()); N_baskets=len(uni_names)
print(f"\nPhase 1: Grid ({len(ALL_COMBOS)} combos × {N_baskets} baskets)...")
grid_sh={(u,ci): basket_sharpe(run_trades(UNIVERSES[u],c)) for u in uni_names for ci,c in enumerate(ALL_COMBOS)}
combo_meds=[]
for ci in range(len(ALL_COMBOS)):
    vals=[grid_sh.get((u,ci)) for u in uni_names]; vals=[v for v in vals if v is not None]
    combo_meds.append(float(np.median(vals)) if vals else float("nan"))
valid=[(i,m) for i,m in enumerate(combo_meds) if not np.isnan(m)]
canon_idx=max(valid,key=lambda x:x[1])[0]; canon_combo=ALL_COMBOS[canon_idx]
print(f"  Canonical: {combo_to_params(canon_combo)}  med={combo_meds[canon_idx]:.4f}")

print(f"\nPhase 2: Significance (n_boot={N_BOOT})...")
canon_pass=0; canon_sh=[]; canon_det={}
for u,prices in UNIVERSES.items():
    tr=run_trades(prices,canon_combo); ng,sh,det=basket_sig3(tr)
    canon_sh.append(sh); canon_det[u]={**det,"sharpe":sh,"gates":ng}
    if ng>=2: canon_pass+=1
    print(f"  [{'PASS' if ng>=2 else 'FAIL'}] {u:<20} sharpe={sh:.3f}  gates={ng}/3")

binom_p=float(binom.sf(canon_pass-1,N_baskets,0.05)); verdict="STRATEGY EXISTS" if binom_p<0.05 else "NO EVIDENCE OF EFFECT"
med_sh=float(np.median([s for s in canon_sh if s!=0.0])) if canon_sh else 0.0; params=combo_to_params(canon_combo)
print(f"\n  Binomial: N={N_baskets}, k={canon_pass}, p={binom_p:.6f} → {verdict}")

os.makedirs(RESULTS_DIR,exist_ok=True)
summary_baskets={}
for u,prices in UNIVERSES.items():
    summary_baskets[u]={"instruments":list(prices.columns),"n_instruments":len(prices.columns),
        "canonical_params":params,"canonical_median_sharpe":round(med_sh,4),
        "canonical_basket_sharpe":round(canon_det[u]["sharpe"],4),
        "pass_count_at_canon":canon_pass,"n_baskets_tested":N_baskets,
        "binomial_pvalue":round(binom_p,6),"binomial_significant":bool(binom_p<0.05),
        "verdict":verdict,"basket_details":canon_det}
out={"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
     "n_boot":N_BOOT,"n_combos":len(ALL_COMBOS),"canonical_params":params,
     "canonical_median_sharpe":round(med_sh,4),"binomial_pvalue":round(binom_p,6),
     "binomial_significant":bool(binom_p<0.05),"verdict":verdict,"baskets":summary_baskets}
jp=os.path.join(RESULTS_DIR,f"{SAVE_NAME}_v2_multiasset_summary.json")
with open(jp,"w") as f: json.dump(out,f,indent=2,default=str)
print(f"\n  JSON → {jp}\n{'='*75}\nDone.\n{'='*75}")


# ── Tier 2: INTEGRATED Bonferroni rescue (fable refactor 2026-07-02) ─────────
# Runs after Tier 1 on the NEXT execution of this script; on-disk results
# remain canonical until then. Engine: shared/basket_significance.py.
# Requires: summary_per_basket dict + per-instrument best combos + a
# (ticker, combo) -> monthly returns callable. Wire the lambda below to this
# script's own signal/equity functions if the auto-detected name is wrong.
try:
    from _shared.basket_significance import bonferroni_rescue
    if "summary_per_basket" in dir() and "instrument_best" in dir():
        bonferroni_rescue(
            summary_per_basket=summary_per_basket,
            instrument_best=instrument_best,
            monthly_returns_fn=lambda _t, _c: compute_monthly_returns(
                build_daily_equity_from_trades(
                    ticker_data[_t]["close"], generate_quality_profitability_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "quality_profitability_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
