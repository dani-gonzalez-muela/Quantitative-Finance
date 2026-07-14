"""
Strategy 7: EM/DM Carry
Signal: EM trailing return vs DM trailing return (carry proxy).
EM countries: BRA, MEX, IND, CHN, KOR, THA, MYS, IDN, PHL, POL
DM countries: GBR, AUS, SWE, SGP, CHE, NOR, DNK, NZL, JPN, HKG, TWN
When EM 12m > DM 12m by >1%: long EM basket; else long DM basket.
Reference: Koijen, Moskowitz, Pedersen, Vrugt "Carry" (2018).
Data: CRSP 11_world_country_returns.parquet.
"""
import os, json
import numpy as np, pandas as pd, duckdb
from scipy import stats

SAVE_NAME = "em_dm_carry"; STRATEGY_NAME = "EM/DM Carry"
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
con = duckdb.connect()

df = con.execute(f"""
    SELECT fic, date, portret FROM '{WRDS}/11_world_country_returns.parquet'
    WHERE date >= '2000-01-01' ORDER BY fic, date
""").df()
df['date'] = pd.to_datetime(df['date'])

EM = ['BRA','MEX','IND','CHN','KOR','THA','MYS','IDN','PHL','POL']
DM = ['GBR','AUS','SWE','SGP','CHE','NOR','DNK','NZL','JPN','HKG','TWN']

em_df = df[df['fic'].isin(EM)]; dm_df = df[df['fic'].isin(DM)]

# Equal-weight EM and DM daily returns
em_daily = em_df.groupby('date')['portret'].mean()
dm_daily = dm_df.groupby('date')['portret'].mean()

# Monthly totals
em_m = em_daily.resample('ME').apply(lambda x: (1+x).prod()-1)
dm_m = dm_daily.resample('ME').apply(lambda x: (1+x).prod()-1)

# 12m trailing return as carry proxy
em_12m = em_m.rolling(12).apply(lambda x: (1+x).prod()-1)
dm_12m = dm_m.rolling(12).apply(lambda x: (1+x).prod()-1)

# Signal (lagged 1m): EM carry > DM carry by >1% → long EM, else long DM
carry_spread = (em_12m - dm_12m).shift(1)
signal = (carry_spread > 0.01).astype(float)  # 1=EM, 0=DM

port_ret_g = signal * em_m + (1-signal) * dm_m
port_ret_g = port_ret_g.dropna()
port_ret_n = port_ret_g - TC_BPS*2/10000

equity = STARTING_CAPITAL * (1+port_ret_g).cumprod()
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
sig_g=sig(port_ret_g); sig_n=sig(port_ret_n)
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")
em_pct=round(float(signal.mean()*100),1)
print(f"EM exposure: {em_pct}% of months")

trades=[{"entry_time":port_ret_g.index[i-1] if i>0 else port_ret_g.index[0],"exit_time":port_ret_g.index[i],
    "direction":"long","instrument":"EM_basket" if signal.iloc[i]>0.5 else "DM_basket",
    "entry_price":100.0,"exit_price":round(100*(1+float(port_ret_g.iloc[i])),4),
    "pct_return_gross":round(float(port_ret_g.iloc[i]),6),"exit_reason":"monthly_rebalance"}
    for i in range(len(port_ret_g))]
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":EM+DM,"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"EM_12m_return - DM_12m_return > 1% → long EM basket; else DM","rebalance":"monthly",
            "em_countries":EM,"dm_countries":DM,"tc_bps":"5 one-way","em_pct_months":em_pct},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")

# ── Save signal.csv for em_dm_carry_Implementation.py ──
# Signal: carry spread per "instrument" (EM_basket vs DM_basket)
# EM score = em_12m (higher = stronger EM carry)
# DM score = dm_12m
carry_spread_raw = pd.DataFrame({
    "EM_basket": em_12m,
    "DM_basket": dm_12m,
}, index=em_12m.index)
carry_spread_raw.index.name = "date"
signal_long = carry_spread_raw.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows)")
