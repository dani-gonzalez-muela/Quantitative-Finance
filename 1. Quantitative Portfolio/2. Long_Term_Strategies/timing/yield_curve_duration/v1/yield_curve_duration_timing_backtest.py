"""
Strategy 6: Yield Curve Duration Strategy
Signal: T10Y2Y spread -> duration regime.
Rule: T10Y2Y > 0.5%  -> long duration  (20yr bond, proxy: dgs20)
      T10Y2Y < 0%    -> short duration  (2yr,  proxy: dgs2)
      Else           -> intermediate    (10yr, proxy: dgs10)
Bond price return ~ -duration * dYield/100 + carry.
Duration: 20yr~17, 10yr~8, 2yr~1.9 years.
Reference: Fama & Bliss (1987); Cochrane & Piazzesi (2005).
Data: synthetic FRED series from ETF price-derived yields (2016+).
"""
import os, json
import numpy as np, pandas as pd
from scipy import stats

SAVE_NAME = "yield_curve_duration"; STRATEGY_NAME = "Yield Curve Duration"
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
fr = _raw[['t10y2y','dgs10','dgs2','dgs20','dgs1']].dropna(subset=['t10y2y','dgs10'])
fr = fr[fr.index >= '2003-01-01']
print("FR data: %s -> %s (synthetic)" % (fr.index[0].date(), fr.index[-1].date()))

# Monthly resample
monthly = fr.resample('ME').last().dropna(subset=['t10y2y'])

# Bond price return from yield change: dPrice ~ -duration * dYield/100
# Approximate durations: 20yr -> 17yr; 10yr -> 8yr; 2yr -> 1.9yr
DUR = {'long': 17.0, 'mid': 8.0, 'short': 1.9}

def bond_return(yield_series, duration):
    """Monthly price return from yield change, plus carry (current yield/12)."""
    dy = yield_series.diff()
    price_ret = -duration * dy / 100
    carry = yield_series.shift(1) / 1200
    return price_ret + carry

long_ret  = bond_return(monthly['dgs20'].fillna(monthly['dgs10']), DUR['long'])
mid_ret   = bond_return(monthly['dgs10'], DUR['mid'])
short_ret = bond_return(monthly['dgs2'].fillna(monthly['dgs1']), DUR['short'])

spread = monthly['t10y2y'].shift(1)  # lag 1 month to avoid look-ahead
regime = pd.cut(spread, bins=[-np.inf, 0.0, 0.5, np.inf], labels=['short','mid','long'])

port_ret = pd.Series(index=monthly.index, dtype=float)
for dt in monthly.index:
    r = regime.loc[dt]
    if r == 'long':    port_ret.loc[dt] = long_ret.loc[dt]
    elif r == 'mid':   port_ret.loc[dt] = mid_ret.loc[dt]
    elif r == 'short': port_ret.loc[dt] = short_ret.loc[dt]

ret_g = port_ret.dropna()
ret_n = ret_g - TC_BPS*2/10000

equity   = STARTING_CAPITAL * (1 + ret_g).cumprod()
daily_eq = equity.resample('D').ffill()

def sig(r):
    r = pd.Series(r).dropna()
    if len(r) < 5: return {"sharpe":0.0,"verdict":"INSUFFICIENT DATA","tests_passed":"0/3"}
    sh = r.mean()/r.std()*np.sqrt(12)
    t1 = sh > 0.80
    ts,_ = stats.ttest_1samp(r, 0); t2 = ts > 1.65
    rng = np.random.RandomState(42); ra = r.values
    bs  = [rng.choice(ra, len(ra), replace=True) for _ in range(1000)]
    t3  = np.percentile([b.mean()/b.std()*np.sqrt(12) if b.std()>0 else 0 for b in bs], 5) > 0
    p   = sum([t1,t2,t3])
    return {"sharpe":round(float(sh),4),
            "verdict":"SIGNIFICANT (strong)" if p==3 else "SIGNIFICANT (moderate)" if p==2 else "NOT SIGNIFICANT",
            "tests_passed":"%d/3" % p}

years=(daily_eq.index[-1]-daily_eq.index[0]).days/365.25
cagr=(daily_eq.iloc[-1]/STARTING_CAPITAL)**(1/years)-1
dr=daily_eq.pct_change().dropna(); sh=dr.mean()/dr.std()*np.sqrt(252)
peak=daily_eq.expanding().max(); mdd=((daily_eq-peak)/peak).min()
mets={"cagr":round(float(cagr*100),2),"total_return":round(float((daily_eq.iloc[-1]/STARTING_CAPITAL-1)*100),2),
      "sharpe_daily":round(float(sh),4),"max_dd":round(float(mdd*100),2)}
sig_g=sig(ret_g); sig_n=sig(ret_n)
print("CAGR=%.2f%%  Sharpe=%.4f  MaxDD=%.2f%%" % (mets['cagr'], mets['sharpe_daily'], mets['max_dd']))
print("Gross:", sig_g, "\nNet:  ", sig_n)

regime_counts = regime.dropna().value_counts().to_dict()
trades = [{"entry_time":ret_g.index[i-1] if i>0 else ret_g.index[0],"exit_time":ret_g.index[i],
    "direction":"long","instrument":str(regime.iloc[i]) if i<len(regime) else "mid",
    "entry_price":100.0,"exit_price":round(100*(1+float(ret_g.iloc[i])),4),
    "pct_return_gross":round(float(ret_g.iloc[i]),6),"exit_reason":"monthly_rebalance"}
    for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,"%s_trades.csv" % SAVE_NAME),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,"%s_daily_equity.csv" % SAVE_NAME),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["TLT_proxy","IEF_proxy","SHY_proxy"],"portfolio":"long_term",
  "period":"%s -> %s" % (daily_eq.index[0].strftime('%Y-%m-%d'), daily_eq.index[-1].strftime('%Y-%m-%d')),
  "params":{"signal":"T10Y2Y spread (synthetic FRED)","rules":"T10Y2Y>0.5%->long(20yr), <0%->short(2yr), else->mid(10yr)",
            "duration_model":"price_return = -dur * dYield/100 + carry","tc_bps":"5 one-way",
            "regime_counts":regime_counts},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,"%s_summary.json" % SAVE_NAME),"w") as f: json.dump(summary,f,indent=2)
print("Done.")

# Save signal.csv
signal_data = pd.DataFrame({
    "date": ret_g.index,
    "instrument": regime.reindex(ret_g.index).fillna("mid").astype(str).values,
    "score": spread.reindex(ret_g.index).fillna(0.0).values,
})
signal_path = os.path.join(RESULTS_DIR, "%s_signal.csv" % SAVE_NAME)
signal_data.to_csv(signal_path, index=False)
print("  signal -> %s  (%d rows)" % (signal_path, len(signal_data)))
