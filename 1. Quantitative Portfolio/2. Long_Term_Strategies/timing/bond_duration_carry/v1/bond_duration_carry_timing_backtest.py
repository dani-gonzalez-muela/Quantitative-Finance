"""
Strategy 16: Bond Duration Carry
Signal: DFII10 (10yr TIPS real yield, synthetic) from local CSV.
Real yield > 0% -> bonds have positive real carry -> long duration (20yr, TLT proxy)
Real yield < 0% -> negative real carry -> short duration (2yr, SHY proxy)
Refinement: also use T10Y2Y -- steep + positive real = max duration.
Reference: Ilmanen "Expected Returns" (2011); AQR "Carry" (2018).
Data: synthetic FRED series from ETF price-derived yields (2016+).
"""
import os, json
import numpy as np, pandas as pd
from scipy import stats

SAVE_NAME = "bond_duration_carry"; STRATEGY_NAME = "Bond Duration Carry"
STARTING_CAPITAL = 100_000; TC_BPS = 5
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, "%s_daily_equity" % SAVE_NAME)
os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(EQUITY_DIR, exist_ok=True)

# Load FRED data (synthetic CSV, bypasses stale .pyc)
_ROOT  = os.path.normpath(os.path.join(OUTPUT_BASE, '..', '..', '..'))
_SYNTH = os.path.join(_ROOT, 'data', 'wrds', 'fred_rates_synthetic.csv')
_raw   = pd.read_csv(_SYNTH, parse_dates=['date']).set_index('date').sort_index()
if 'dgs1' not in _raw.columns and 'dgs3m' in _raw.columns:
    _raw['dgs1'] = _raw['dgs3m'] + 0.15
fr = _raw[['dfii10', 't10y2y', 'dgs20', 'dgs10', 'dgs2', 'dgs1']].dropna(how='all')
fr = fr[fr.index >= '2003-01-01']

# Monthly: last business day of month
fr_m = fr.resample('ME').last().dropna(subset=['dfii10'])
print("FR monthly data: %s -> %s, %d months (synthetic)" % (
    fr_m.index[0].date(), fr_m.index[-1].date(), len(fr_m)))

# Duration model
DUR = {'long': 17.0, 'mid': 8.0, 'short': 1.9}
def bond_return(yield_series, duration):
    dy = yield_series.diff()
    price_ret = -duration * dy / 100
    carry = yield_series.shift(1) / 1200
    return (price_ret + carry).dropna()

long_ret  = bond_return(fr_m['dgs20'].fillna(fr_m['dgs10']), DUR['long'])
mid_ret   = bond_return(fr_m['dgs10'], DUR['mid'])
short_ret = bond_return(fr_m['dgs2'].fillna(fr_m['dgs1']), DUR['short'])

# Signal: real yield lagged 1m + yield curve slope
real_yield_lag = fr_m['dfii10'].shift(1)
slope_lag      = fr_m['t10y2y'].shift(1) if 't10y2y' in fr_m.columns else pd.Series(0.5, index=fr_m.index)

# Regime
port_ret = pd.Series(index=fr_m.index, dtype=float)
for dt in fr_m.index:
    ry = real_yield_lag.get(dt, np.nan)
    sl = slope_lag.get(dt, 0.3)
    if pd.isna(ry): continue
    if ry > 1.0 and sl > 0.5:  port_ret[dt] = long_ret.get(dt, np.nan)
    elif ry > 0:               port_ret[dt] = mid_ret.get(dt, np.nan)
    elif ry < -0.5:            port_ret[dt] = short_ret.get(dt, np.nan)
    else:                      port_ret[dt] = mid_ret.get(dt, np.nan)

ret_g = port_ret.dropna(); ret_n = ret_g - TC_BPS*2/10000
equity   = STARTING_CAPITAL * (1+ret_g).cumprod()
daily_eq = equity.resample('D').ffill()

def sig(r):
    r = pd.Series(r).dropna()
    if len(r) < 5: return {"sharpe":0.0,"verdict":"INSUFFICIENT DATA","tests_passed":"0/3"}
    sh = r.mean()/r.std()*np.sqrt(12)
    t1 = sh>0.80; ts,_=stats.ttest_1samp(r,0); t2=ts>1.65
    rng=np.random.RandomState(42); ra=r.values
    bs=[rng.choice(ra,len(ra),replace=True) for _ in range(1000)]
    t3=np.percentile([b.mean()/b.std()*np.sqrt(12) if b.std()>0 else 0 for b in bs],5)>0
    p=sum([t1,t2,t3])
    return {"sharpe":round(float(sh),4),
            "verdict":"SIGNIFICANT (strong)" if p==3 else "SIGNIFICANT (moderate)" if p==2 else "NOT SIGNIFICANT",
            "tests_passed":"%d/3" % p}

years=(daily_eq.index[-1]-daily_eq.index[0]).days/365.25
cagr=(daily_eq.iloc[-1]/STARTING_CAPITAL)**(1/years)-1
dr=daily_eq.pct_change().dropna(); sh=dr.mean()/dr.std()*np.sqrt(252)
peak=daily_eq.expanding().max(); mdd=((daily_eq-peak)/peak).min()
mets={"cagr":round(float(cagr*100),2),"total_return":round(float((daily_eq.iloc[-1]/STARTING_CAPITAL-1)*100),2),
      "sharpe_daily":round(float(sh),4),"max_dd":round(float(mdd*100),2)}

# Regime breakdown
regime_df = pd.Series(index=fr_m.index, dtype=str)
for dt in fr_m.index:
    ry = real_yield_lag.get(dt, np.nan)
    sl = slope_lag.get(dt, 0.3)
    if pd.isna(ry): regime_df[dt]='unknown'
    elif ry>1.0 and sl>0.5: regime_df[dt]='long'
    elif ry>0: regime_df[dt]='mid'
    elif ry<-0.5: regime_df[dt]='short'
    else: regime_df[dt]='mid'
regime_counts = regime_df.value_counts().to_dict()

sig_g=sig(ret_g); sig_n=sig(ret_n)
print("CAGR=%.2f%%  Sharpe=%.4f  MaxDD=%.2f%%" % (mets['cagr'], mets['sharpe_daily'], mets['max_dd']))
print("Gross:", sig_g, "\nNet:  ", sig_n)
print("Regimes:", regime_counts)

trades=[{"entry_time":ret_g.index[i-1] if i>0 else ret_g.index[0],"exit_time":ret_g.index[i],
    "direction":"long","instrument":str(regime_df.iloc[i]) if i<len(regime_df) else "mid",
    "entry_price":100.0,"exit_price":round(100*(1+float(ret_g.iloc[i])),4),
    "pct_return_gross":round(float(ret_g.iloc[i]),6),"exit_reason":"monthly_rebalance"}
    for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,"%s_trades.csv" % SAVE_NAME),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,"%s_daily_equity.csv" % SAVE_NAME),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["20yr_bond_proxy","10yr_bond_proxy","2yr_bond_proxy"],
  "portfolio":"long_term",
  "period":"%s -> %s" % (daily_eq.index[0].strftime('%Y-%m-%d'), daily_eq.index[-1].strftime('%Y-%m-%d')),
  "params":{"signal":"DFII10 (synthetic) + T10Y2Y slope",
            "rules":"ry>1%+steep->long20yr, ry>0->10yr, ry<-0.5%->2yr",
            "duration_model":"-dur*dY/100 + carry","tc_bps":"5 one-way","regime_counts":regime_counts},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,"%s_summary.json" % SAVE_NAME),"w") as f: json.dump(summary,f,indent=2)
print("Done.")

# Save signal.csv
signal_data = pd.DataFrame({
    "date": ret_g.index,
    "instrument": regime_df.reindex(ret_g.index).fillna("mid").values,
    "score": real_yield_lag.reindex(ret_g.index).fillna(0.0).values,
})
signal_path = os.path.join(RESULTS_DIR, "%s_signal.csv" % SAVE_NAME)
signal_data.to_csv(signal_path, index=False)
print("  signal -> %s  (%d rows)" % (signal_path, len(signal_data)))
