"""
Strategy 8: Turn-of-Month Effect
Signal: calendar — last 3 + first 3 trading days of month = invested in SP500.
Other days: earn risk-free rate (CRSP RF from FF factors / FRED).
Reference: Ariel (1987); Lakonishok & Smidt (1988).
Data: CRSP market portfolio indno=1000500 (SP500 VW) daily returns + FF RF.
"""
import os, json
import numpy as np, pandas as pd, duckdb
from scipy import stats

SAVE_NAME = "turn_of_month"; STRATEGY_NAME = "Turn of Month"
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
sp = con.execute(f"""
    SELECT dlycaldt AS date, dlytotret AS ret
    FROM '{WRDS}/10_crsp_market_portfolios.parquet'
    WHERE indno=1000500 AND dlycaldt>='2000-01-01' AND dlytotret IS NOT NULL
    ORDER BY dlycaldt
""").df()
sp['date'] = pd.to_datetime(sp['date'])
sp = sp.set_index('date').sort_index()

# Daily RF: FF monthly / 21 trading days
ff = pd.read_csv(FF_PATH, parse_dates=['Date'], index_col='Date').sort_index()
ff.index = ff.index + pd.offsets.MonthEnd(0)
rf_m = ff['RF'].reindex(sp.index, method='ffill') / 21  # daily rf approx

# Label trading days by month-position
sp['month'] = sp.index.to_period('M')
sp['day_rank'] = sp.groupby('month').cumcount() + 1  # 1 = first trading day
sp['rev_rank'] = sp.groupby('month')['ret'].transform('count') - sp.groupby('month').cumcount()  # last day = 1

# Invested: first 3 OR last 3 trading days of month
sp['invested'] = ((sp['day_rank'] <= 3) | (sp['rev_rank'] <= 3)).astype(float)
sp['rf_daily'] = rf_m.reindex(sp.index).fillna(0)

# Strategy return
sp['strat_ret'] = sp['invested'] * sp['ret'] + (1 - sp['invested']) * sp['rf_daily']
sp['strat_ret_n'] = sp['strat_ret'] - sp['invested'] * TC_BPS * 2 / 10000 / 21  # approx TC per trade

ret_g = sp['strat_ret'].dropna()
ret_n = sp['strat_ret_n'].dropna()

equity = STARTING_CAPITAL * (1 + ret_g).cumprod()
daily_eq = equity.rename('equity')

# Monthly returns for significance
ret_g_m = daily_eq.resample('ME').last().pct_change().dropna()
ret_n_m = (STARTING_CAPITAL * (1 + ret_n).cumprod()).resample('ME').last().pct_change().dropna()

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
sig_g=sig(ret_g_m); sig_n=sig(ret_n_m)
invested_pct=round(float(sp['invested'].mean()*100),1)
print(f"Invested {invested_pct}% of days")
print(f"CAGR={mets['cagr']}%  Sharpe={mets['sharpe_daily']}  MaxDD={mets['max_dd']}%")
print(f"Gross: {sig_g}\nNet:   {sig_n}")

# Trades: one per month
monthly_groups = sp[sp['invested']==1].groupby('month')
trades = []
for m, g in monthly_groups:
    entry=g.index[0]; exit_=g.index[-1]
    gross=float((1+g['ret']).prod()-1)
    trades.append({"entry_time":entry,"exit_time":exit_,"direction":"long","instrument":"SP500_TOM",
        "entry_price":100.0,"exit_price":round(100*(1+gross),4),"pct_return_gross":round(gross,6),"exit_reason":"end_of_window"})
pd.DataFrame(trades).to_csv(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_trades.csv"),index=False)
eq_df=daily_eq.reset_index(); eq_df.columns=["date","equity"]
eq_df.to_csv(os.path.join(EQUITY_DIR,f"{SAVE_NAME}_daily_equity.csv"),index=False)
summary={"strategy":STRATEGY_NAME,"instruments":["SP500_CRSP"],"portfolio":"long_term",
  "period":f"{daily_eq.index[0].strftime('%Y-%m-%d')} -> {daily_eq.index[-1].strftime('%Y-%m-%d')}",
  "params":{"signal":"calendar: last 3 + first 3 trading days/month","invested_pct_days":invested_pct,
            "cash_return":"FF risk-free rate","tc_bps":"5 one-way"},
  "trades":len(trades),"stats":mets,
  "significance":{"gross":{"sharpe":sig_g["sharpe"],"verdict":sig_g["verdict"],"tests_passed":sig_g["tests_passed"]},
                  "net":  {"sharpe":sig_n["sharpe"],"verdict":sig_n["verdict"],"tests_passed":sig_n["tests_passed"]}}}
with open(os.path.join(RESULTS_DIR,f"{SAVE_NAME}_summary.json"),"w") as f: json.dump(summary,f,indent=2)
print("Done.")


# ── Save signal.csv for turn_of_month_Implementation.py ──
# NOTE: Single-instrument timing strategy — basket weighting N/A. See discussion_points.md §2.1, §3.12.
signal_data = pd.DataFrame({
    "date": [t["entry_time"] for t in trades],
    "instrument": "SP500_TOM",
    "score": 1.0,  # always invested when signal fires
})
signal_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_signal.csv")
signal_data.to_csv(signal_path, index=False)
print(f"  signal  → {signal_path}  ({len(signal_data)} rows)")
