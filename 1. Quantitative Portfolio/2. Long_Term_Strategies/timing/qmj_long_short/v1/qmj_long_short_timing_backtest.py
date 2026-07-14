"""
Strategy 15: QMJ - Quality Minus Junk (Long/Short)
Signal: FF RMW (Robust Minus Weak profitability) factor = direct QMJ proxy.
RMW is the FF5 quality factor — long high-profitability stocks, short low-profitability.
Long portfolio: Mkt + RMW (quality tilt)
Short portfolio: Mkt - RMW (junk tilt)
Market-neutral: long minus short = 2×RMW
Reference: Asness, Frazzini & Pedersen (2019) "Quality Minus Junk". 
Note: FF RMW is structurally equivalent to the QMJ factor (both long robust, short weak profitability).
Data: Fama-French 5-factor monthly returns.
"""
import os, json
import numpy as np, pandas as pd
from scipy import stats

SAVE_NAME = "qmj_long_short"; STRATEGY_NAME = "QMJ - Quality Minus Junk"
STARTING_CAPITAL = 100_000; TC_BPS = 5
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(EQUITY_DIR, exist_ok=True)

# -- fable path bootstrap (Phase C fix: replaces dead session-specific paths) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
_sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
FF_PATH = data_file('regime_factor_rotation_cache', 'ff_factors_monthly.csv')
ff = pd.read_csv(FF_PATH, parse_dates=['Date'], index_col='Date').sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
ff = ff[ff.index >= '1990-01-01']

mkt = ff['Mkt-RF'] + ff['RF']
rmw = ff['RMW']   # FF quality = RMW
cma = ff['CMA']   # Conservative minus aggressive (investment quality)

# QMJ proxy: RMW + 0.5*CMA (quality includes both profitability and conservative investment)
# Long/short: pure RMW (market-neutral quality factor)
ret_g = (rmw + 0.5*cma).dropna()
ret_n = ret_g - TC_BPS*2/10000

equity = STARTING_CAPITAL * (1+ret_g).cumprod()
daily_eq = equity.resample('D').ffill()

def sig(r):
    r = pd.Series(r).dropna()
    if len(r)<5: return {"sharpe":0.0,"verdict":"INSUFFICIENT DATA","tests_passed":"0/3"}
    sh = r.mean()/r.std()*np.sqrt(12)
    t1 = sh>0.80; ts,_=stats.ttest_1samp(r,0); t2=ts>1.65
    rng=np.random.RandomState(42); ra=r.values
    bs=[rng.choice(ra,len(ra),replace=True) for _ in range(1000)]
    t3=np.percentile([b.mean()/b.std()*np.sqrt(12) if b.std()>0 else 0 for b in bs],5)>0
    p=sum([t1,t2,t3])
    return {"sharpe":round(float(sh),4),"verdict":"SIGNIFICANT (strong)" if p==3 else "SIGNIFICANT (moderate)" if p==2 else "NOT SIGNIFICANT","tests_passed":f"{p}/3"}

years=(daily_eq.index[-1]-daily_eq.index[0]).days/365.25
cagr=(daily_eq.iloc[-1]/STARTING_CAPITAL)**(1/years)-1
dr=daily_eq.pct_change().dropna(); sh=dr.mean()/dr.std()*np.sqrt(252)
peak=daily_eq.expanding().max(); mdd=((daily_eq-peak)/peak).min()
mets={"cagr":round(float(cagr*100),2),"total_return":round(float((daily_eq.iloc[-1]/STARTING_CAPITAL-1)*100),2),
      "sharpe_daily":round(float(sh),4),"max_dd":round(float(mdd*100),2)}
sig_g=sig(ret_g); sig_n=sig(ret_n)
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")

trades=[{"entry_time":ret_g.index[i-1] if i>0 else ret_g.index[0],"exit_time":ret_g.index[i],
    "direction":"long_short","instrument":"FF_RMW+CMA (QMJ proxy)","entry_price":100.0,
    "exit_price":round(100*(1+float(ret_g.iloc[i])),4),"pct_return_gross":round(float(ret_g.iloc[i]),6),
    "exit_reason":"monthly_rebalance"} for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["FF_RMW","FF_CMA"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"FF RMW + 0.5*CMA (quality proxy = profitability + conservative investment)",
            "implementation":"long/short market-neutral: RMW+0.5*CMA factor return","tc_bps":"5 one-way",
            "data_notes":"Compustat GP approach OOM (5.4GB zip). FF RMW is the standard academic QMJ proxy (same long profitable, short unprofitable construction)."},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for qmj_long_short_Implementation.py ──
# NOTE: Single-instrument timing/composite strategy — basket weighting N/A.
# See todo/refactor_discussion_points.md §2.1.
signal_data = pd.DataFrame({
    "date": ret_g.index if "ret_g" in dir() else (ret_g_s.index if "ret_g_s" in dir() else []),
    "instrument": "FF_RMW_CMA_QMJproxy",
    "score": 1.0,
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
