"""
Strategy 17: REIT Dividend Carry
Signal: REIT trailing dividend yield vs 24-month average (carry signal).
Data: CRSP market income return (dlyincret) for indno=1000500 as yield proxy.
When estimated yield > 24m avg yield (above-average carry) → 100% exposure.
When yield < 24m avg yield × 0.70 (overpriced) → 50% exposure.
Also factor in 10yr treasury yield: REIT spread = equity yield - bond yield.
Reference: Fama & French (1988) dividend yield; AQR "Value and Momentum in REITs" (2012).
Data: CRSP SP500 income + total returns. 10yr Treasury from FRED.
"""
import os, json
import numpy as np, pandas as pd, duckdb
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from _shared.loaders_wrds import load_fred_rates
from scipy import stats

SAVE_NAME = "reit_dividend_carry"; STRATEGY_NAME = "REIT Dividend Carry"
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
WRDS  = data_dir('wrds_parquet')
FR_ZIP = _os.path.join(data_dir('wrds_datasets_raw'), "THIRD PARTY [done]/4. Federal Reserve [d]/Interest Rates/Daily/e2fzdw3jkcrhxisb.csv.zip")
FF_PATH = data_file('regime_factor_rotation_cache', 'ff_factors_monthly.csv')

con = duckdb.connect()

# CRSP SP500: use dlyincret (income/dividend component) to estimate yield
print("Loading CRSP SP500 income returns...")
sp = con.execute(f"""
    SELECT dlycaldt AS date, dlytotret AS tot, dlyincret AS inc, dlyprcret AS price
    FROM '{WRDS}/10_crsp_market_portfolios.parquet'
    WHERE indno=1000500 AND dlycaldt>='2004-01-01'
    ORDER BY dlycaldt
""").df()
sp['date'] = pd.to_datetime(sp['date']); sp = sp.set_index('date')

# Monthly totals
sp_m = pd.DataFrame({
    'tot':   sp['tot'].resample('ME').apply(lambda x: (1+x).prod()-1),
    'inc':   sp['inc'].resample('ME').apply(lambda x: (1+x).prod()-1),
}).dropna()

# Annualized dividend yield ≈ 12 × monthly income return
sp_m['div_yield_ann'] = sp_m['inc'] * 12

# 24-month rolling average of dividend yield
sp_m['div_yield_avg24'] = sp_m['div_yield_ann'].rolling(24).mean()

# 10yr Treasury yield from FRED
fr = load_fred_rates(columns=['dgs10'])
fr_m = fr['dgs10'].resample('ME').last() / 100  # annualized

# REIT spread = equity div yield - 10yr treasury yield
combined = sp_m.join(fr_m.rename('bond_yield'), how='inner').dropna()
combined['yield_spread'] = combined['div_yield_ann'] - combined['bond_yield']
combined['spread_avg24'] = combined['yield_spread'].rolling(24).mean()

# Signal (lagged 1m)
signal_lag = combined['yield_spread'].shift(1)
avg_lag     = combined['div_yield_avg24'].shift(1)

# Carry rule:
# yield > avg24 * 1.0 → 100% equity (carry above average)
# yield < avg24 * 0.70 → 50% equity (carry well below average, overpriced)
# else → 75%
exposure = pd.Series(0.75, index=combined.index)
exposure[signal_lag > avg_lag * 1.0]  = 1.0
exposure[signal_lag < avg_lag * 0.70] = 0.5

ff = pd.read_csv(FF_PATH, parse_dates=['Date'], index_col='Date').sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
# Use HML + market as REIT proxy (REITs are high book-to-market)
mkt = ff['Mkt-RF'] + ff['RF']
hml = ff['HML']
reit_proxy = (mkt + 0.5*hml).reindex(combined.index)

ret_g = (exposure * reit_proxy).dropna()
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
regime_counts={"full_100pct":int((exposure>=0.99).sum()),"underweight_50pct":int((exposure<=0.51).sum()),
               "neutral_75pct":int(((exposure>0.51)&(exposure<0.99)).sum())}
sig_g=sig(ret_g); sig_n=sig(ret_n)
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")
print(f"Regimes: {regime_counts}")
print(f"Avg div yield: {combined['div_yield_ann'].mean():.2%}, avg spread: {combined['yield_spread'].mean():.2%}")

trades=[{"entry_time":ret_g.index[i-1] if i>0 else ret_g.index[0],"exit_time":ret_g.index[i],
    "direction":"long","instrument":"REIT_proxy_Mkt+HML","entry_price":100.0,
    "exit_price":round(100*(1+float(ret_g.iloc[i])),4),"pct_return_gross":round(float(ret_g.iloc[i]),6),
    "exit_reason":"monthly_rebalance"} for i in range(len(ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["CRSP_SP500_incomeReturn","DGS10_FRED"],
  "portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"annualized CRSP income return vs 24m avg (REIT carry proxy)",
            "rules":"yield>avg→100%, yield<avg*0.70→50%, else 75%",
            "reit_proxy":"Mkt+0.5*HML (high B/M = REIT characteristic)","tc_bps":"5 one-way",
            "regime_counts":regime_counts,
            "data_notes":"VNQ/XLRE blocked (no internet). CRSP SP500 income return used as dividend yield proxy. FF Mkt+HML as REIT sector proxy."},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for reit_dividend_carry_Implementation.py ──
# NOTE: Single-instrument timing/composite strategy — basket weighting N/A.
# See todo/refactor_discussion_points.md §2.1.
signal_data = pd.DataFrame({
    "date": ret_g.index if "ret_g" in dir() else (ret_g_s.index if "ret_g_s" in dir() else []),
    "instrument": "REIT_proxy_Mkt+HML",
    "score": 1.0,
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
