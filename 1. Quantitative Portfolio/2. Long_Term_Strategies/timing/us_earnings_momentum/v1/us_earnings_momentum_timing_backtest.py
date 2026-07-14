"""
Strategy 3: US Earnings Momentum
Signal: avg rank of ret_1_0 + ret_3_1 (short-term price momentum as PEAD proxy).
Proxy: Mkt + 0.4*Mom + 0.2*RMW — short-term momentum tilt + profitability quality.
Reference: Bernard & Thomas (1989) PEAD; Chan, Jegadeesh & Lakonishok (1996).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
from scipy import stats

SAVE_NAME = "us_earnings_momentum"; STRATEGY_NAME = "US Earnings Momentum"
STARTING_CAPITAL = 100_000; TC_BPS = 5
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(EQUITY_DIR, exist_ok=True)

FF_PATH = os.path.join(os.path.dirname(OUTPUT_BASE), "regime_factor_rotation", "data", "ff_factors_monthly.csv")
ff = pd.read_csv(FF_PATH, parse_dates=["Date"], index_col="Date").sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
ff = ff[ff.index >= "1990-01-01"]
mkt = ff["Mkt-RF"] + ff["RF"]; mom = ff["Mom"]; rmw = ff["RMW"]; rf = ff["RF"]

# Short-term + earnings momentum: Mkt + 0.4*Mom + 0.2*RMW
ret_g = (mkt + 0.4*mom + 0.2*rmw).dropna()
ret_n = (ret_g - TC_BPS*2/10000).dropna()

equity = STARTING_CAPITAL * (1 + ret_g).cumprod()
daily_eq = equity.resample("D").ffill()

def sig(r):
    r = pd.Series(r).dropna()
    if len(r)<5: return {"sharpe":0.0,"verdict":"INSUFFICIENT DATA","tests_passed":"0/3"}
    sh = r.mean()/r.std()*np.sqrt(12)
    t1 = sh > 0.80
    ts,_ = stats.ttest_1samp(r,0); t2 = ts > 1.65
    rng = np.random.RandomState(42); ra = r.values
    bs = [rng.choice(ra,len(ra),replace=True) for _ in range(1000)]
    t3 = np.percentile([b.mean()/b.std()*np.sqrt(12) if b.std()>0 else 0 for b in bs],5) > 0
    p = sum([t1,t2,t3])
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
         "direction":"long","instrument":"US_TopDecile_EarningsMom","entry_price":100.0,
         "exit_price":round(100*(1+float(ret_g.iloc[i])),4),"pct_return_gross":round(float(ret_g.iloc[i]),6),
         "exit_reason":"monthly_rebalance"} for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["FF_Mkt","FF_Mom","FF_RMW"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"avg_rank(ret_1_0, ret_3_1)","implementation":"Mkt+0.4*Mom+0.2*RMW","tc_bps":"5 one-way",
            "data_notes":"FF factors used as proxy for short-term price+earnings momentum composite"},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for us_earnings_momentum_Implementation.py ──
# NOTE: Single-instrument timing/composite strategy — basket weighting N/A.
# See todo/refactor_discussion_points.md §2.1.
signal_data = pd.DataFrame({
    "date": ret_g.index if "ret_g" in dir() else (ret_g_s.index if "ret_g_s" in dir() else []),
    "instrument": "US_TopDecile_EarningsMom",
    "score": 1.0,
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
