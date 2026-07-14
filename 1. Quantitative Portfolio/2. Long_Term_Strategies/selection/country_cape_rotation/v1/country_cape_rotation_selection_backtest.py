"""
Strategy 5: Country CAPE Rotation
Signal: inverse 12m trailing return = cheapest-valuation proxy (Faber Global Value).
Universe: 14 countries from CRSP world country returns.
Long 5 cheapest countries (lowest 12m return = mean-reversion / value signal), monthly rebalance.
Reference: Meb Faber "Global Value" (2012); Asness et al "Value and Momentum Everywhere" (2013).
Data: CRSP 11_world_country_returns.parquet (Compustat global).
"""
import os, json, sys
import numpy as np, pandas as pd
import duckdb
from scipy import stats

SAVE_NAME = "country_cape_rotation"; STRATEGY_NAME = "Country CAPE Rotation"
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

# Load daily country returns (USD total return)
df = con.execute(f"""
    SELECT fic, date, portret FROM '{WRDS}/11_world_country_returns.parquet'
    WHERE date >= '1995-01-01'
    ORDER BY fic, date
""").df()
df['date'] = pd.to_datetime(df['date'])

# Select 14 countries with longest history
counts = df.groupby('fic')['date'].count().sort_values(ascending=False)
TOP_COUNTRIES = counts.head(14).index.tolist()
df = df[df['fic'].isin(TOP_COUNTRIES)].copy()
print(f"Countries: {TOP_COUNTRIES}")

# Pivot to country x date
prices_daily = df.pivot(index='date', columns='fic', values='portret').dropna(how='all')
# Build synthetic price index
prices_idx = (1 + prices_daily.fillna(0)).cumprod()

# Monthly resampling
monthly_ret = prices_daily.resample('ME').apply(lambda x: (1+x).prod()-1)
monthly_idx = prices_idx.resample('ME').last()

# Signal: 12m trailing return — long 5 lowest (cheapest = value proxy)
ret12 = monthly_idx.pct_change(12)

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

monthly_rets_g, monthly_rets_n, trades = [], [], []
months = monthly_ret.index[12:]
for dt in months:
    sig_row = ret12.loc[dt].dropna()
    if len(sig_row) < 5: continue
    selected = sig_row.nsmallest(5).index.tolist()
    idx = monthly_ret.index.get_loc(dt)
    if idx+1 >= len(monthly_ret): continue
    next_dt = monthly_ret.index[idx+1]
    rets = monthly_ret.loc[next_dt, selected].dropna()
    if len(rets)==0: continue
    r_g = float(rets.mean()); r_n = r_g - TC_BPS*2/10000
    monthly_rets_g.append({'date':next_dt,'ret':r_g})
    monthly_rets_n.append({'date':next_dt,'ret':r_n})
    trades.append({'entry_time':dt,'exit_time':next_dt,'direction':'long',
        'instrument':'|'.join(selected[:3])+'...','entry_price':100.0,
        'exit_price':round(100*(1+r_g),4),'pct_return_gross':round(r_g,6),'exit_reason':'monthly_rebalance'})

ret_g_s = pd.DataFrame(monthly_rets_g).set_index('date')['ret']
ret_n_s = pd.DataFrame(monthly_rets_n).set_index('date')['ret']
equity_curve = STARTING_CAPITAL * (1 + ret_g_s).cumprod()
daily_eq = equity_curve.resample('D').ffill()

years=(daily_eq.index[-1]-daily_eq.index[0]).days/365.25
cagr=(daily_eq.iloc[-1]/STARTING_CAPITAL)**(1/years)-1
dr=daily_eq.pct_change().dropna(); sh=dr.mean()/dr.std()*np.sqrt(252)
peak=daily_eq.expanding().max(); mdd=((daily_eq-peak)/peak).min()
mets={"cagr":round(float(cagr*100),2),"total_return":round(float((daily_eq.iloc[-1]/STARTING_CAPITAL-1)*100),2),
      "sharpe_daily":round(float(sh),4),"max_dd":round(float(mdd*100),2)}
sig_g=sig(ret_g_s); sig_n=sig(ret_n_s)
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")

pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":TOP_COUNTRIES,"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"inverse_12m_return (value proxy, cheapest 5 of 14 countries)","top_n":5,
            "rebalance":"monthly","tc_bps":"5 one-way",
            "data_notes":"CRSP world country returns. Shiller CAPE blocked (no internet); 12m trailing return used as Faber-style value proxy."},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")

# ── Save signal.csv for country_cape_rotation_Implementation.py ──
# Signal: NEGATED 12m trailing return per country (lower return = cheaper = higher buy score)
# Negate so that basket_implementations.py "higher score = buy" convention is maintained.
signal_raw = -ret12  # negate: cheapest countries get highest score
signal_raw.index.name = "date"
signal_long = signal_raw.reset_index().melt(id_vars=["date"], var_name="instrument", value_name="score")
signal_long = signal_long.dropna(subset=["score"])
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_long.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_long)} rows, scores negated for buy-low convention)")
