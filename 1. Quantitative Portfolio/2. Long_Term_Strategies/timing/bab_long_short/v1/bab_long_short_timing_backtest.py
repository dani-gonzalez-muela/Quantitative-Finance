"""
Strategy 14: BAB - Betting Against Beta (Long/Short)
Signal: stock beta from Better Market Betas (bswa32).
Long: low-beta stocks (bottom quintile), Short: high-beta stocks (top quintile).
Beta-neutralize: scale legs so net beta = 0.
Forward return: use CRSP SP500 individual returns + CCM bridge.
Reference: Frazzini & Pedersen (2014) "Betting Against Beta" AQR.
"""
import os, json, zipfile
import numpy as np, pandas as pd, duckdb
from scipy import stats

SAVE_NAME = "bab_long_short"; STRATEGY_NAME = "BAB - Betting Against Beta"
STARTING_CAPITAL = 100_000; TC_BPS = 5
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity")
os.makedirs(RESULTS_DIR, exist_ok=True); os.makedirs(EQUITY_DIR, exist_ok=True)

WRDS = "/sessions/optimistic-fervent-cray/mnt/INVESTMENT PROJECT/algo_trading/data/wrds"
BETA_ZIP = "/sessions/optimistic-fervent-cray/mnt/INVESTMENT PROJECT/AlgoTrading/WRDS_DATASETS/Contributed [done]/3. Better Market Betas/hgyb2bk67ohkn7nm_csv.zip"
FF_PATH  = "/sessions/optimistic-fervent-cray/mnt/INVESTMENT PROJECT/algo_trading/long_term_portfolio/regime_factor_rotation/data/ff_factors_monthly.csv"
con = duckdb.connect()

print("Loading Better Market Betas...")
with zipfile.ZipFile(BETA_ZIP) as z:
    with z.open(z.namelist()[0]) as f:
        betas = pd.read_csv(f, usecols=['permno','yyyymmdd','bswa32'])
betas['date'] = pd.to_datetime(betas['yyyymmdd'])
betas['month'] = betas['date'].dt.to_period('M')
betas = betas.dropna(subset=['bswa32'])
print(f"Beta rows: {len(betas):,}, permnos: {betas.permno.nunique():,}")

# Load SP500 monthly returns
sp = con.execute(f"""
    SELECT PERMNO, DlyCalDt AS date, DlyRet AS ret
    FROM '{WRDS}/05_sp500_crsp.parquet'
    WHERE DlyCalDt >= '1990-01-01' AND DlyRet IS NOT NULL
    ORDER BY PERMNO, DlyCalDt
""").df()
sp['date'] = pd.to_datetime(sp['date'])
sp['month'] = sp['date'].dt.to_period('M')
sp_m = sp.groupby(['PERMNO','month'])['ret'].apply(lambda x: (1+x).prod()-1).reset_index()
sp_m.columns = ['permno','month','ret']

# Load FF for RF
ff = pd.read_csv(FF_PATH, parse_dates=['Date'], index_col='Date').sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
rf = ff['RF'].dropna()

# Merge betas with SP500 returns
beta_m = betas[['permno','month','bswa32']].copy()
merged = sp_m.merge(beta_m, on=['permno','month'], how='inner')
merged = merged.dropna(subset=['bswa32','ret'])
print(f"Merged rows: {len(merged):,}")

monthly_rets_g = []; monthly_rets_n = []; trades = []
months = sorted(merged['month'].unique())

for m in months[1:]:  # skip first month (no prior beta)
    prev_m = m - 1
    # Get betas from PRIOR month (lagged)
    prior_betas = merged[merged['month']==prev_m][['permno','bswa32']].set_index('permno')
    # Get current month returns
    curr_rets   = merged[merged['month']==m][['permno','ret']].set_index('permno')
    # Join
    combined = prior_betas.join(curr_rets, how='inner')
    if len(combined) < 20: continue

    # Rank by beta
    combined['rank'] = combined['bswa32'].rank(pct=True)
    low_beta  = combined[combined['rank'] <= 0.20]  # bottom quintile
    high_beta = combined[combined['rank'] >= 0.80]  # top quintile
    if len(low_beta)==0 or len(high_beta)==0: continue

    # Beta-neutral scaling: scale long leg by beta_H / beta_L
    beta_L = low_beta['bswa32'].mean()
    beta_H = high_beta['bswa32'].mean()
    if beta_L <= 0: continue

    scale = beta_H / beta_L if beta_H > 0 else 1.0
    scale = min(scale, 3.0)  # cap leverage

    # Long low-beta (scaled up), short high-beta
    r_long  = low_beta['ret'].mean()
    r_short = high_beta['ret'].mean()
    rf_m    = float(rf.reindex([m.to_timestamp('M')+pd.offsets.MonthEnd(0)], method='nearest').iloc[0]) if len(rf)>0 else 0

    # BAB return: scale * (r_long - rf) - (r_short - rf)
    r_g = scale * (r_long - rf_m) - (r_short - rf_m)
    r_n = r_g - TC_BPS*4/10000  # round-trip for both legs
    next_dt = m.to_timestamp('M') + pd.offsets.MonthEnd(0)
    monthly_rets_g.append({'date':next_dt,'ret':r_g})
    monthly_rets_n.append({'date':next_dt,'ret':r_n})
    trades.append({'entry_time':prev_m.to_timestamp(),'exit_time':next_dt,'direction':'long_short',
        'instrument':f'LowBeta({len(low_beta)})/HighBeta({len(high_beta)})','entry_price':100.0,
        'exit_price':round(100*(1+r_g),4),'pct_return_gross':round(r_g,6),'exit_reason':'monthly_rebalance',
        'beta_L':round(beta_L,3),'beta_H':round(beta_H,3),'scale':round(scale,3)})

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
summary={"strategy":STRATEGY_NAME,"instruments":["SP500_CRSP_LongShort"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"bswa32 (Better Market Betas Vasicek-shrunk beta)","long":"bottom quintile beta","short":"top quintile beta",
            "neutral":"beta-scaled (scale=beta_H/beta_L, capped 3x)","tc_bps":"5 one-way each leg"},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for bab_long_short_Implementation.py ──
# NOTE: Long/short market-neutral strategy using aggregate returns — basket weighting N/A.
# See todo/refactor_discussion_points.md §2.1, §3.5.
signal_data = pd.DataFrame({
    "date": ret_g_s.index,
    "instrument": "SP500_BAB_LongShort",
    "score": 1.0,
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
