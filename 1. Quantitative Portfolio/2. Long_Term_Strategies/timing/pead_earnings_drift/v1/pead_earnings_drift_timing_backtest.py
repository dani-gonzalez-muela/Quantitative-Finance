"""
Strategy 13: PEAD - Post-Earnings Announcement Drift
Signal: EPS surprise = epspxq(t) - epspxq(t-4) / |std of prior 8q surprises|
Universe: S&P 500 (CRSP 05_sp500_crsp.parquet) via CCM gvkey->permno bridge.
Long top-quartile SUE stocks after earnings announcement (rdq), hold 1 month.
Reference: Bernard & Thomas (1989); Chan, Jegadeesh & Lakonishok (1996).
Data: Compustat quarterly (partial - 1.3M rows, /tmp/compustat_q.parquet) + SP500 CRSP.
"""
import os, json
import numpy as np, pandas as pd, duckdb
from scipy import stats

SAVE_NAME = "pead_earnings_drift"; STRATEGY_NAME = "PEAD - Post-Earnings Announcement Drift"
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

print("Loading Compustat quarterly...")
cq = pd.read_parquet('/tmp/compustat_q.parquet')
cq['datadate'] = pd.to_datetime(cq['datadate'])
cq['rdq']      = pd.to_datetime(cq['rdq'], errors='coerce')
cq = cq.dropna(subset=['rdq','epspxq'])
cq['gvkey']    = cq['gvkey'].astype(str).str.zfill(6)
cq = cq.sort_values(['gvkey','datadate'])
print(f"CQ rows: {len(cq):,}, gvkeys: {cq.gvkey.nunique():,}")

# Earnings surprise: seasonal random walk (vs same quarter prior year)
cq['eps_lag4'] = cq.groupby('gvkey')['epspxq'].shift(4)
cq['surprise'] = cq['epspxq'] - cq['eps_lag4']
# Standardized unexpected earnings: normalize by rolling std of surprise
cq['sue_std'] = cq.groupby('gvkey')['surprise'].transform(lambda x: x.rolling(8, min_periods=3).std())
cq['sue'] = cq['surprise'] / (cq['sue_std'] + 1e-6)
cq = cq.dropna(subset=['sue'])

# CCM bridge: gvkey -> permno
ccm = con.execute(f"SELECT gvkey, lpermno, linkdt, linkenddt FROM '{WRDS}/17_ccm_master.parquet' WHERE linktype IN ('LU','LC','LS') AND linkprim IN ('P','C')").df()
ccm['gvkey']      = ccm['gvkey'].astype(str).str.zfill(6)
ccm['linkdt']     = pd.to_datetime(ccm['linkdt'])
ccm['linkenddt']  = pd.to_datetime(ccm['linkenddt']).fillna(pd.Timestamp('2030-12-31'))

# Load SP500 monthly returns (aggregate by permno-month)
print("Loading SP500 daily returns...")
sp = con.execute(f"""
    SELECT PERMNO, DlyCalDt AS date, DlyRet AS ret
    FROM '{WRDS}/05_sp500_crsp.parquet'
    WHERE DlyCalDt >= '1990-01-01' AND DlyRet IS NOT NULL
    ORDER BY PERMNO, DlyCalDt
""").df()
sp['date'] = pd.to_datetime(sp['date'])
sp['month'] = sp['date'].dt.to_period('M')
# Monthly return per permno
sp_m = sp.groupby(['PERMNO','month'])['ret'].apply(lambda x: (1+x).prod()-1).reset_index()
sp_m.columns = ['permno','month','ret']
print(f"SP monthly obs: {len(sp_m):,}")

# Join earnings announcements to CRSP
# For each announcement (rdq), the holding period is the NEXT month
cq['rdq_month'] = cq['rdq'].dt.to_period('M')

# Merge gvkey -> permno via CCM
def get_permno(row):
    matches = ccm[(ccm['gvkey']==row['gvkey']) & (ccm['linkdt']<=row['rdq']) & (ccm['linkenddt']>=row['rdq'])]
    if len(matches)==0: return np.nan
    return matches.iloc[0]['lpermno']

# Faster: merge-based approach
cq_sub = cq[['gvkey','rdq','rdq_month','sue']].copy()
# Filter to post-1990
cq_sub = cq_sub[cq_sub['rdq'] >= '1990-01-01']

# Merge CCM
merged = cq_sub.merge(ccm[['gvkey','lpermno','linkdt','linkenddt']], on='gvkey', how='left')
merged = merged[(merged['rdq'] >= merged['linkdt']) & (merged['rdq'] <= merged['linkenddt'])]
merged = merged.drop_duplicates(subset=['gvkey','rdq_month'])
print(f"Matched {len(merged):,} earnings announcements to CRSP permnos")

# For each month t, find announcements in month t, then long top-quartile SUE in month t+1
monthly_rets_g = []; monthly_rets_n = []; trades = []
all_months = sorted(merged['rdq_month'].unique())

for m in all_months:
    month_data = merged[merged['rdq_month']==m].copy()
    if len(month_data) < 10: continue
    # Rank by SUE, take top quartile
    month_data['sue_rank'] = month_data['sue'].rank(pct=True)
    top_q = month_data[month_data['sue_rank'] >= 0.75]['lpermno'].dropna()
    if len(top_q) == 0: continue

    # Next month return for these permnos
    next_m = m + 1
    permnos = top_q.astype(int).tolist()
    stock_rets = sp_m[(sp_m['month']==next_m) & (sp_m['permno'].isin(permnos))]
    if len(stock_rets) == 0: continue
    r_g = float(stock_rets['ret'].mean())
    r_n = r_g - TC_BPS*2/10000
    next_dt = next_m.to_timestamp('M') + pd.offsets.MonthEnd(0)
    monthly_rets_g.append({'date':next_dt,'ret':r_g})
    monthly_rets_n.append({'date':next_dt,'ret':r_n})
    trades.append({'entry_time':m.to_timestamp(),'exit_time':next_dt,'direction':'long',
        'instrument':f'TOP_SUE_Q ({len(stock_rets)} stocks)','entry_price':100.0,
        'exit_price':round(100*(1+r_g),4),'pct_return_gross':round(r_g,6),'exit_reason':'monthly_hold'})

print(f"Portfolio months: {len(monthly_rets_g)}")
ret_g_s = pd.DataFrame(monthly_rets_g).set_index('date')['ret']
ret_n_s = pd.DataFrame(monthly_rets_n).set_index('date')['ret']
equity = STARTING_CAPITAL * (1+ret_g_s).cumprod()
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
sig_g=sig(ret_g_s); sig_n=sig(ret_n_s)
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")

pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["SP500_CRSP","Compustat_Q"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"SUE = (epspxq - epspxq_lag4) / rolling_std_8q","portfolio":"long top-quartile SUE after earnings announcement",
            "hold":"1 month","tc_bps":"5 one-way","universe":"S&P 500 via CRSP + CCM bridge",
            "data_notes":"Compustat quarterly 1.3M rows (~50% coverage due to ZIP streaming limit). Full file is 5.4GB uncompressed."},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for pead_earnings_drift_Implementation.py ──
# NOTE: Single-instrument timing/composite strategy — basket weighting N/A.
# See todo/refactor_discussion_points.md §2.1.
signal_data = pd.DataFrame({
    "date": ret_g.index if "ret_g" in dir() else (ret_g_s.index if "ret_g_s" in dir() else []),
    "instrument": "TOP_SUE_Q_portfolio",
    "score": 1.0,
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
