"""
Quality / Profitability v2 — Novy-Marx Gross Profitability (Real Compustat)
===========================================================================
Enhancement over v1:
- v1 used FF5 RMW factor as a proxy
- v2 uses actual Compustat quarterly fundamentals: GP = (revtq-cogsq)/atq
- S&P 500 universe (CRSP 05_sp500_crsp.parquet), long top GP quintile
- CCM master for gvkey ↔ permno bridge
- Point-in-time: 90-day lag after quarter-end
- Period: 1980-2025

Data pre-processing:
  DuckDB was used to extract needed columns from the 5.4GB Compustat zip
  (652MB compressed) into compustat_filtered.parquet. If that file doesn't
  exist, this script rebuilds it via DuckDB.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import numpy as np, pandas as pd
import pyarrow.parquet as pq
from _backtest_utils import (build_monthly_returns, portfolio_metrics, save_results)

STRATEGY_NAME    = "Quality / Profitability v2 (Novy-Marx, Compustat)"
SAVE_NAME        = "quality_v2"
STARTING_CAPITAL = 100_000
OUTPUT_BASE      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR         = os.path.dirname(OUTPUT_BASE)
WRDS_DIR         = os.path.normpath(os.path.join(
    BASE_DIR, "..", "..", "algo_trading", "data", "wrds"))
# -- fable path bootstrap (Phase C fix: replaces dead session-specific paths) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
_sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
COMPUSTAT_ZIP    = _os.path.join(data_dir('wrds_datasets_raw'),
    "Compustat - Capital IQ [d]", "North America",
    "2. Fundamentals Quaterly", "da9ne81mhdngabgp_csv.zip")
FILTERED_PARQUET = "/tmp/compustat_filtered.parquet"  # session-agnostic local cache

PARAMS = {
    "signal": "Novy-Marx gross profitability = (revtq-cogsq)/atq, long top quintile",
    "universe": "S&P 500 constituents (CRSP 05_sp500_crsp.parquet)",
    "lag_days": 90,
    "rebalance": "monthly (uses latest quarterly signal available)",
    "weighting": "equal-weight top GP quintile (~100 stocks)",
    "note": (
        "Compustat quarterly fundamentals from WRDS snapshot "
        "(da9ne81mhdngabgp_csv.zip, 5.4GB uncompressed, queried via DuckDB). "
        "CCM master gvkey→permno bridge. Point-in-time 90-day lag. "
        "S&P500 constituent daily returns from CRSP 05_sp500_crsp.parquet. "
        "Period: 1980-2025."
    )
}

# ── 1. LOAD COMPUSTAT (from pre-filtered parquet or rebuild) ─────────────────
if os.path.exists(FILTERED_PARQUET):
    print("Loading pre-filtered Compustat parquet...")
    comp = pd.read_parquet(FILTERED_PARQUET)
else:
    print("Building filtered Compustat via DuckDB (one-time setup)...")
    import duckdb, zipfile
    # Extract CSV from zip first
    tmp_csv = "/tmp/compustat_temp.csv"
    if not os.path.exists(tmp_csv):
        with zipfile.ZipFile(COMPUSTAT_ZIP) as z:
            with z.open(z.namelist()[0]) as src, open(tmp_csv, 'wb') as dst:
                while True:
                    chunk = src.read(8*1024*1024)
                    if not chunk: break
                    dst.write(chunk)
    conn = duckdb.connect()
    comp = conn.execute(f"""
        SELECT gvkey, datadate, revtq, cogsq, atq
        FROM read_csv('{tmp_csv}', ignore_errors=true, null_padding=true)
        WHERE indfmt='INDL' AND consol='C' AND popsrc='D' AND datafmt='STD'
          AND datadate >= '1975-01-01'
          AND revtq IS NOT NULL AND cogsq IS NOT NULL
          AND atq IS NOT NULL AND atq > 0
    """).df()
    comp.to_parquet(FILTERED_PARQUET)

print(f"  Compustat rows: {len(comp):,}, dates: {comp['datadate'].min()} -> {comp['datadate'].max()}")

comp['datadate']    = pd.to_datetime(comp['datadate'])
comp['gvkey']       = comp['gvkey'].astype(str).str.zfill(6)
comp['gp']          = (comp['revtq'] - comp['cogsq']) / comp['atq']
comp = comp[comp['gp'].notna()].copy()
comp['signal_date'] = comp['datadate'] + pd.Timedelta(days=90)
comp = comp.sort_values(['gvkey','datadate'])
comp = comp.drop_duplicates(subset=['gvkey','datadate'], keep='last')
print(f"  Valid GP rows: {len(comp):,}")

# ── 2. LOAD CCM MASTER ────────────────────────────────────────────────────────
print("Loading CCM master...")
ccm = pq.read_table(os.path.join(WRDS_DIR, "17_ccm_master.parquet")).to_pandas()
ccm = ccm[ccm['linktype'].isin(['LC','LU','LS']) &
          ccm['linkprim'].isin(['P','C'])].copy()
ccm['gvkey']     = ccm['gvkey'].astype(str).str.zfill(6)
ccm['lpermno']   = pd.to_numeric(ccm['lpermno'], errors='coerce')
ccm['linkdt']    = pd.to_datetime(ccm['linkdt'], errors='coerce')
ccm['linkenddt'] = pd.to_datetime(ccm['linkenddt'], errors='coerce')
ccm['linkenddt'] = ccm['linkenddt'].fillna(pd.Timestamp('2099-12-31'))

# ── 3. JOIN COMP → PERMNO ─────────────────────────────────────────────────────
print("Joining Compustat to permno via CCM...")
comp_ccm = comp[['gvkey','signal_date','gp']].merge(
    ccm[['gvkey','lpermno','linkdt','linkenddt']], on='gvkey', how='inner')
comp_ccm = comp_ccm[
    (comp_ccm['signal_date'] >= comp_ccm['linkdt']) &
    (comp_ccm['signal_date'] <= comp_ccm['linkenddt']) &
    comp_ccm['lpermno'].notna()
].copy()
comp_ccm = comp_ccm.drop_duplicates(subset=['gvkey','signal_date'], keep='first')
comp_ccm['permno'] = comp_ccm['lpermno'].astype(int)
comp_ccm = comp_ccm[['permno','signal_date','gp']].sort_values(
    ['permno','signal_date']).reset_index(drop=True)
print(f"  GP-permno rows: {len(comp_ccm):,}, permnos: {comp_ccm['permno'].nunique()}")

# ── 4. LOAD SP500 MONTHLY RETURNS ─────────────────────────────────────────────
print("Loading SP500 daily returns → building monthly returns...")
sp = pq.read_table(
    os.path.join(WRDS_DIR, "05_sp500_crsp.parquet"),
    columns=['DlyCalDt','PERMNO','DlyRet']
).to_pandas()
sp['DlyCalDt'] = pd.to_datetime(sp['DlyCalDt'])
sp = sp[sp['DlyCalDt'] >= '1979-01-01'].copy()
sp['PERMNO']   = sp['PERMNO'].astype(int)
sp['DlyRet']   = sp['DlyRet'].fillna(0.0)

# Monthly return via compound of daily returns
sp['ym'] = sp['DlyCalDt'].dt.to_period('M')
sp['log1r'] = np.log1p(sp['DlyRet'])
monthly = sp.groupby(['ym','PERMNO'])['log1r'].sum().reset_index()
monthly['ret']      = np.expm1(monthly['log1r'])
monthly['month_end'] = monthly['ym'].dt.to_timestamp('M')
del sp
monthly = monthly[monthly['month_end'] >= '1980-01-01'].copy()
monthly.rename(columns={'PERMNO': 'permno'}, inplace=True)
print(f"  Monthly obs: {len(monthly):,}")

# ── 5. ASSIGN GP SIGNAL PER PERMNO PER MONTH (vectorized merge_asof) ─────────
# For each (permno, month_end), find the most recent signal_date <= month_end
print("Assigning GP signals per permno per month...")

# Build: for each permno, a time series of GP signals → forward-fill to months
# Strategy: merge_asof on permno groups
monthly_sorted = monthly.sort_values(['permno','month_end'])
comp_sorted    = comp_ccm.sort_values(['permno','signal_date'])

# merge_asof requires both sorted by key; do it by permno group
parts = []
for perm, grp_m in monthly_sorted.groupby('permno', sort=False):
    grp_c = comp_sorted[comp_sorted['permno'] == perm]
    if len(grp_c) == 0:
        continue
    merged = pd.merge_asof(
        grp_m[['month_end','ret']].rename(columns={'month_end':'dt'}),
        grp_c[['signal_date','gp']].rename(columns={'signal_date':'dt'}),
        on='dt', direction='backward'
    )
    merged['permno'] = perm
    merged.rename(columns={'dt':'month_end'}, inplace=True)
    parts.append(merged[['permno','month_end','ret','gp']])

panel = pd.concat(parts, ignore_index=True)
panel = panel[panel['gp'].notna()].copy()
print(f"  Panel rows with GP: {len(panel):,}")
del monthly, monthly_sorted, comp_sorted, parts

# ── 6. MONTHLY WEIGHTS: LONG TOP GP QUINTILE ─────────────────────────────────
print("Building monthly weights (top 20% GP)...")
panel['gp_rank'] = panel.groupby('month_end')['gp'].rank(pct=True)
panel['in_top']  = panel['gp_rank'] >= 0.80

# ── 7. COMPUTE PORTFOLIO MONTHLY RETURNS (vectorized) ────────────────────────
# Signal at month t → invest at month t+1
# Portfolio return at t+1 = equal-weighted avg of next-month returns of top GP stocks
top_panel = panel[panel['in_top']].copy()

# Count stocks per month (for equal weighting)
counts = top_panel.groupby('month_end').size().rename('n')
top_panel = top_panel.join(counts, on='month_end')

# Average return per month among top GP stocks
port_ret_by_month = top_panel.groupby('month_end')['ret'].mean()

# Shift: signal at month_end → apply to NEXT month's returns
# port_ret_by_month[t] is the average return of top-GP stocks during month t
# But we want the signal from month t-1 applied to month t returns
# Current: top_panel uses gp available at month_end (signal_date <= month_end)
# so investing in those stocks the NEXT month is correct
port_ret_by_month = port_ret_by_month.sort_index()
port_ret_invested = port_ret_by_month.shift(-1).dropna()  # returns from month+1
port_ret_invested = port_ret_invested[
    port_ret_invested.index >= pd.Timestamp('1980-06-30')]

# ── 8. BUILD EQUITY CURVE ─────────────────────────────────────────────────────
equity_vals = pd.Series(
    STARTING_CAPITAL * (1 + port_ret_invested).cumprod().values,
    index=port_ret_invested.index + pd.offsets.MonthEnd(1)
)
# Forward-fill to daily
daily_equity = equity_vals.resample('D').ffill().dropna()
daily_equity.name = 'equity'
daily_equity.index = pd.to_datetime(daily_equity.index)

print(f"Equity: {daily_equity.index[0].date()} -> {daily_equity.index[-1].date()}")
print(f"  Start={daily_equity.iloc[0]:.0f}, End={daily_equity.iloc[-1]:.0f}")

# ── 9. METRICS AND SAVE ──────────────────────────────────────────────────────
mets = portfolio_metrics(daily_equity)
print(f"CAGR={mets['cagr']}%, Sharpe={mets['sharpe_daily']}, MaxDD={mets['max_dd']}%")

monthly_ret_gross = port_ret_invested
monthly_ret_net   = port_ret_invested - 0.0010   # ~10bps/mo

trades_df = pd.DataFrame({
    'month_end': port_ret_by_month.index,
    'n_stocks_in_top_gp': [
        len(top_panel[top_panel['month_end'] == m])
        for m in port_ret_by_month.index
    ]
})

save_results(STRATEGY_NAME, SAVE_NAME, ["SP500_top_GP_quintile"], PARAMS,
    trades_df, daily_equity, monthly_ret_gross, monthly_ret_net,
    daily_equity.index[0].strftime("%Y-%m-%d"),
    daily_equity.index[-1].strftime("%Y-%m-%d"),
    OUTPUT_BASE)
print("Done.")
