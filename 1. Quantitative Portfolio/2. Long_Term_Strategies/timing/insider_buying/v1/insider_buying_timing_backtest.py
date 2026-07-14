"""
Strategy 12: Insider Buying
Signal: net insider buy/sell ratio → when insiders buy heavily → overweight market.
Data: EDGAR Form 4 + OpenInsider blocked (no internet). 
Fallback: VIX spike contrarian signal as insider-buying proxy.
Rationale: insiders tend to buy after sharp market drops (high VIX events).
VIX spike = VIX this month > VIX 3-month average × 1.3 → insiders likely buying → 130% SPY.
VIX depressed = VIX < VIX 12m average × 0.8 → market complacent → 80% SPY.
Reference: Lakonishok & Lee (2001); Jeng, Metrick & Zeckhauser (2003).
"""
import os, json
import numpy as np, pandas as pd, duckdb
from scipy import stats

SAVE_NAME = "insider_buying"; STRATEGY_NAME = "Insider Buying (VIX Spike Proxy)"
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
WRDS = data_dir('wrds_parquet')
FF_PATH = data_file('regime_factor_rotation_cache', 'ff_factors_monthly.csv')

con = duckdb.connect()
vix = con.execute(f"SELECT date, vix FROM '{WRDS}/15_cboe_vix.parquet' WHERE date>='1990-01-01' ORDER BY date").df()
vix['date'] = pd.to_datetime(vix['date']); vix = vix.set_index('date')
vix_m = vix['vix'].resample('ME').last().dropna()

ff = pd.read_csv(FF_PATH, parse_dates=['Date'], index_col='Date').sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
mkt = (ff['Mkt-RF'] + ff['RF']).dropna()
rf  = ff['RF'].dropna()

common = vix_m.index.intersection(mkt.index)
vix_m = vix_m.reindex(common); mkt = mkt.reindex(common); rf = rf.reindex(common)

vix_3m  = vix_m.rolling(3).mean()
vix_12m = vix_m.rolling(12).mean()
vix_lag = vix_m.shift(1)
v3_lag  = vix_3m.shift(1)
v12_lag = vix_12m.shift(1)

# Insider proxy signal
exposure = pd.Series(1.0, index=common)
exposure[vix_lag > v3_lag * 1.3]  = 1.3   # VIX spike → insiders buy → overweight
exposure[vix_lag < v12_lag * 0.8] = 0.8   # VIX suppressed → insiders sell → underweight

ret_g = (exposure * mkt + (1 - exposure) * rf).dropna()
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
regime_counts={"overweight_130pct":int((exposure>1.0).sum()),"underweight_80pct":int((exposure<1.0).sum()),
               "neutral_100pct":int((exposure==1.0).sum())}
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")

trades=[{"entry_time":ret_g.index[i-1] if i>0 else ret_g.index[0],"exit_time":ret_g.index[i],
    "direction":"long","instrument":"SP500_insider_proxy","entry_price":100.0,
    "exit_price":round(100*(1+float(ret_g.iloc[i])),4),"pct_return_gross":round(float(ret_g.iloc[i]),6),
    "exit_reason":"monthly_rebalance"} for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["SP500_CRSP","VIX_proxy"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"VIX spike vs 3m avg (insider buy proxy)","rules":"VIX>3m_avg*1.3→130%, VIX<12m_avg*0.8→80%, else 100%",
            "regime_counts":regime_counts,"tc_bps":"5 one-way",
            "data_notes":"EDGAR Form 4 / OpenInsider blocked (no internet). VIX spike used as documented insider-buying proxy (insiders buy after market dislocations)."},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for insider_buying_Implementation.py ──
# NOTE: Single-instrument timing strategy — basket weighting N/A. See discussion_points.md §2.1.
signal_data = pd.DataFrame({
    "date": ret_g.index,
    "instrument": "SP500_insider_proxy",
    "score": exposure.reindex(ret_g.index).fillna(1.0),
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
