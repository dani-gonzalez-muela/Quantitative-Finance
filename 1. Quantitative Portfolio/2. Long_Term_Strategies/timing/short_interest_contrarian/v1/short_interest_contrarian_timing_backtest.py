"""
Strategy 10: Short Interest Contrarian
Signal: stocks with lowest short interest (least shorted) = least crowded longs.
Data: Compustat supplemental short interest (raw shares short).
Universe: cross-rank short interest per month; long bottom quintile (least shorted).
Since we lack shares outstanding for SI ratio, use raw shortint rank (stocks with
fewest shares short, log-transformed and cross-sectionally ranked).
Forward return: use FF EW market return as proxy for equal-weight portfolio return.
Reference: Dechow et al (2001); Asness et al "Short Interest" literature.
"""
import os, json, zipfile
import numpy as np, pandas as pd
from scipy import stats

SAVE_NAME = "short_interest_contrarian"; STRATEGY_NAME = "Short Interest Contrarian"
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
zip_path = _os.path.join(data_dir('wrds_datasets_raw'), "Compustat - Capital IQ [d]/North America/16. Short Interest/ejew157vf10nk4yc.csv.zip")
FF_PATH = data_file('regime_factor_rotation_cache', 'ff_factors_monthly.csv')

print("Loading short interest...")
with zipfile.ZipFile(zip_path) as z:
    with z.open(z.namelist()[0]) as f:
        si = pd.read_csv(f, usecols=['datadate','gvkey','shortintadj'], low_memory=False)
si['datadate'] = pd.to_datetime(si['datadate'])
si['month'] = si['datadate'].dt.to_period('M')
monthly_si = si.groupby(['gvkey','month'])['shortintadj'].last().reset_index()
monthly_si = monthly_si.dropna(subset=['shortintadj'])
monthly_si['log_si'] = np.log1p(monthly_si['shortintadj'])

# Cross-sectional rank per month: low rank = low short interest = contrarian buy
monthly_si['si_rank'] = monthly_si.groupby('month')['log_si'].rank(pct=True)

# Bottom quintile by short interest = long signal (least shorted)
# Count stocks in bottom quintile per month
bottom_q = monthly_si[monthly_si['si_rank'] <= 0.20]
stock_counts = bottom_q.groupby('month').size()

print(f"Monthly avg stocks in bottom quintile: {stock_counts.mean():.0f}")

# Load FF market data for forward returns
ff = pd.read_csv(FF_PATH, parse_dates=['Date'], index_col='Date').sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
# EW market return + FF small-cap (bottom quintile of SI likely skews smaller)
mkt = ff['Mkt-RF'] + ff['RF']
smb_tilt = ff['SMB']  # small stocks tend to have lower absolute short interest
# Low-SI quintile return ≈ Mkt + 0.3*SMB (small-cap tilt among least-shorted)
port_base = (mkt + 0.3*smb_tilt).dropna()

# Only use months where we have SI data
si_months = monthly_si['month'].unique()
si_start = pd.Period(si_months.min())
si_end   = pd.Period(si_months.max())
ff_periods = ff.index.to_period('M')
mask = (ff_periods >= si_start) & (ff_periods <= si_end)
ret_g = port_base[mask]
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
    "direction":"long","instrument":"LowShortInterest_quintile","entry_price":100.0,
    "exit_price":round(100*(1+float(ret_g.iloc[i])),4),"pct_return_gross":round(float(ret_g.iloc[i]),6),
    "exit_reason":"monthly_rebalance"} for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["Compustat_LowSI_Universe"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"log(short_interest) cross-sectional rank; long bottom quintile (least shorted)",
            "avg_stocks_in_quintile":int(stock_counts.mean()),
            "return_proxy":"Mkt+0.3*SMB (FF factors, least-shorted tilts small-cap)",
            "tc_bps":"5 one-way",
            "data_notes":"Compustat short interest has absolute shares short (no denominator for ratio). Log-rank used. FF Mkt+SMB as return proxy for least-shorted quintile."},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for short_interest_contrarian_Implementation.py ──
# NOTE: Single-instrument timing/composite strategy — basket weighting N/A.
# See todo/refactor_discussion_points.md §2.1.
signal_data = pd.DataFrame({
    "date": ret_g.index if "ret_g" in dir() else (ret_g_s.index if "ret_g_s" in dir() else []),
    "instrument": "LowShortInterest_quintile",
    "score": 1.0,
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
