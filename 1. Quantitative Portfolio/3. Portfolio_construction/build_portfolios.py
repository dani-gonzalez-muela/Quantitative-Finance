"""SUPERSEDED 2026-07-10 - do not run. Replaced by portfolio_analysis.py + build_final_portfolios.py (2-portfolio structure). Contains stale pre-reorg paths (Intraday_Strategies/, Daily_Strategies/). Kept for reference only."""
"""
build_portfolios.py  (canonical v3 - fable run 2, 2026-07-02)
=============================================================
Builds the THREE portfolios + the COMBINED portfolio per
PORTFOLIO_CONSTRUCTION_METHODOLOGY.md (v5). Portfolio A/B retired.

  INTRADAY  - fixed additive structure (NOT greedy): capital works two
              non-overlapping sessions/day, so returns are additive:
                portfolio = mean(EMA, IMOM, ORB, VWAP) + overnight
  DAILY     - full-path greedy on EW monthly Sharpe over sub-monthly
              candidates (frequency-classified), natural-peak stop,
              COMMON WINDOW (stale candidates dropped, not truncating).
  LONGTERM  - same greedy over monthly-rebalance strategies.
  COMBINED  - 1/3 capital to each sleeve, monthly-rebalanced EW of the
              three portfolio return streams on their common window.

v3 changes vs v2: folder names updated to the 2026-07 layout
(Intraday_Strategies / Daily_Strategies / Long_Term_Strategies);
COMBINED portfolio added; outputs under results/.

Mixing convention (methodology section 3): SIMPLE full-notional curves,
not risk-tuned finals - EW-of-returns silently vol-weights otherwise.

Outputs: results/{intraday,daily,longterm,combined}_portfolio_{results.md,equity.csv}
         results/{daily,longterm}_portfolio_selected_returns.csv
         results/daily_portfolio_diversified_equity.csv (judgment option)
"""
import os, sys
import numpy as np
import pandas as pd

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root not found - place at algo_trading root'
    _d = _p
ROOT = _d
sys.path.insert(0, ROOT)

HERE    = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
os.makedirs(RESULTS, exist_ok=True)

THRESHOLD = float(sys.argv[1]) if len(sys.argv) > 1 else -0.02

def _first(*rels):
    for rel in rels:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            return p
    return None

def load_returns(path, monthly=False):
    df = pd.read_csv(path)
    dcol = df.columns[0]
    df[dcol] = pd.to_datetime(df[dcol], utc=True).dt.tz_convert(None)
    df = df.set_index(dcol).sort_index()
    eq = pd.to_numeric(df.select_dtypes(include=[np.number]).iloc[:, 0], errors='coerce').dropna()
    if monthly:
        return eq.resample('ME').last().pct_change().dropna()
    return eq.pct_change().fillna(0)

def sharpe_m(r):
    return float(r.mean()/r.std()*np.sqrt(12)) if r.std() > 0 else np.nan

def stats_daily(r):
    r = r.dropna()
    sh = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else np.nan
    eq = (1 + r).cumprod()
    yrs = (r.index[-1]-r.index[0]).days/365.25
    cagr = float(eq.iloc[-1])**(1/max(yrs, 0.5)) - 1
    mdd = float(((eq - eq.cummax())/eq.cummax()).min())
    return round(float(sh),3), round(cagr*100,2), round(mdd*100,2)

def stats_monthly(r):
    sh = sharpe_m(r)
    eq = (1 + r).cumprod()
    yrs = (r.index[-1]-r.index[0]).days/365.25
    cagr = float(eq.iloc[-1])**(1/max(yrs, 0.5)) - 1
    mdd = float(((eq - eq.cummax())/eq.cummax()).min())
    return round(sh,3), round(cagr*100,2), round(mdd*100,2)

# ═════════════════ INTRADAY (fixed additive) ═════════════════

IS = 'Intraday_Strategies'
DS = 'Daily_Strategies'
LT = 'Long_Term_Strategies'

def build_intraday():
    comps = {k: _first(f'{IS}/{k}/results/equity/combined_equity_final.csv')
             for k in ('ema_crossover', 'intraday_momentum', 'orb', 'vwap_trend')}
    on_path = _first(f'{IS}/overnight/results/equity/combined_equity_final.csv')
    missing = [k for k, p in comps.items() if p is None] + ([] if on_path else ['overnight'])
    if missing:
        print(f"[Intraday] missing equity for {missing} - build after intraday re-run"); return None
    rets = {k: load_returns(p) for k, p in comps.items()}
    on = load_returns(on_path)
    R = pd.DataFrame(rets).dropna(how='all').fillna(0)
    day_comp = R.mean(axis=1)
    cal = day_comp.index.union(on.index)
    port = day_comp.reindex(cal).fillna(0) + on.reindex(cal).fillna(0)
    port = port[port.index >= max(R.index[0], on.index[0])]
    sp, cp, dp = stats_daily(port)
    eq = (1 + port).cumprod() * 100_000
    eq.rename('equity').to_csv(os.path.join(RESULTS, 'intraday_portfolio_equity.csv'), index_label='date')
    with open(os.path.join(RESULTS, 'intraday_portfolio_results.md'), 'w') as f:
        f.write(f"# Intraday Portfolio (fixed additive)\n\nportfolio = mean(EMA,IMOM,ORB,VWAP) + overnight "
                f"(non-overlapping sessions)\n\n**Sharpe(d) {sp} | CAGR {cp}% | MaxDD {dp}%**\n\n"
                "Components = each strategy's v2 best-by-Sharpe combined_equity_final.csv.\n\n"
                "Correlations (daily):\n\n" + R.corr().round(2).to_markdown() + "\n")
    print(f"[Intraday] Sharpe(d)={sp} CAGR={cp}% MaxDD={dp}%")
    return port

# ═════════════════ DAILY / LONGTERM (greedy) ═════════════════

DAILY_CANDIDATES = {
    'IBS_v2':          [f'{DS}/ibs_mean_reversion/results/equity/combined_equity_simple.csv',
                        f'{DS}/ibs_mean_reversion/results/equity/combined_equity_final.csv'],
    'VIX_MR_v2':       [f'{DS}/vix_mean_reversion/results/equity/combined_equity_simple.csv',
                        f'{DS}/vix_mean_reversion/results/equity/combined_equity_final.csv'],
    'VIX_ETN_Dual':    [f'{DS}/vix_etn_dual/results/equity/combined_equity_1p0x.csv',
                        f'{DS}/vix_etn_dual/results/equity/combined_equity_final.csv'],
    'Congress_Quiver': [f'{DS}/congress_momentum/results/equity/combined_equity_base_10pct.csv',
                        f'{DS}/congress_momentum/results/equity/combined_equity_final.csv'],
    'Congress_TFT':    [f'{LT}/timing/congress_trade_for_trade/results/congress_trade_for_trade_daily_equity/total_nav_3pct_d180_min30d_1x.csv'],
    'Bollinger':       [f'{LT}/timing/bollinger_band/results/bollinger_band_v2_multiasset_daily_equity/combined_equity.csv',
                        f'{LT}/timing/bollinger_band/results/bollinger_band_multiasset_daily_equity/combined_equity.csv'],
    'Turn_of_Month':   [f'{LT}/timing/turn_of_month/results/turn_of_month_v2_multiasset_daily_equity/combined_equity.csv',
                        f'{LT}/timing/turn_of_month/results/turn_of_month_multiasset_daily_equity/combined_equity.csv'],
    'Donchian':        [f'{LT}/timing/donchian_channel/results/donchian_channel_v2_multiasset_daily_equity/combined_equity.csv',
                        f'{LT}/timing/donchian_channel/results/donchian_channel_multiasset_daily_equity/combined_equity.csv'],
}

LT_TIMING = ['credit_carry', 'yield_curve_duration', 'bab_long_short', 'insider_buying',
             'overnight_premium', 'qmj_long_short', 'reit_dividend_carry',
             'short_interest_contrarian', 'us_cross_sectional_momentum',
             'us_earnings_momentum', 'us_return_seasonality', 'us_shareholder_yield',
             'low_volatility', 'pead_earnings_drift', 'bond_duration_carry']
LT_SELECTION = ['gtaa', 'sector_momentum', 'bond_trend', 'commodity_carry',
                'commodity_trend', 'country_cape_rotation', 'cross_asset_carry',
                'em_dm_carry', 'industry_trend', 'quality_profitability']
# sentiment_timing EXCLUDED (known equity-construction bug - methodology v5 open item 3)

def lt_candidates():
    C = {}
    for s in LT_TIMING:
        C[s] = [f'{LT}/timing/{s}/results/{s}_v2_multiasset_daily_equity/combined_equity.csv',
                f'{LT}/timing/{s}/results/{s}_multiasset_daily_equity/combined_equity.csv',
                f'{LT}/timing/{s}/results/{s}_daily_equity/{s}_daily_equity.csv',
                f'{LT}/timing/{s}/results/low_vol_v2_daily_equity/low_vol_v2_daily_equity.csv']
    for s in LT_SELECTION:
        C[s] = [f'{LT}/selection/{s}/results/{s}_v2_multiasset_daily_equity/combined_equity.csv',
                f'{LT}/selection/{s}/results/{s}_multiasset_daily_equity/combined_equity.csv',
                f'{LT}/selection/{s}/results/{s}_daily_equity/{s}_daily_equity.csv']
    return C

def greedy_full_path(name, cand_paths):
    rets = {}
    for label, paths in cand_paths.items():
        p = _first(*paths)
        if p is None:
            print(f"  [{name}] skip {label}: no equity file"); continue
        r = load_returns(p, monthly=True)
        if len(r) >= 24:
            rets[label] = r
    R = pd.DataFrame(rets)
    # common window: drop stale enders (>18m before family end), then late starters
    starts = {c: R[c].dropna().index[0] for c in R.columns}
    ends   = {c: R[c].dropna().index[-1] for c in R.columns}
    keep = list(R.columns)
    end_target = pd.Series(list(ends.values())).quantile(0.75)
    for c in list(keep):
        if ends[c] < end_target - pd.DateOffset(months=18):
            print(f"  [{name}] drop {c}: STALE (ends {ends[c].date()})"); keep.remove(c)
    while keep:
        w_start, w_end = max(starts[c] for c in keep), min(ends[c] for c in keep)
        if (w_end.year - w_start.year)*12 + (w_end.month - w_start.month) >= 60:
            break
        worst = max(keep, key=lambda c: starts[c])
        print(f"  [{name}] drop {worst}: late start {starts[worst].date()}"); keep.remove(worst)
    R = R[keep].dropna()
    print(f"  [{name}] common window {R.index[0].date()} -> {R.index[-1].date()} ({len(R)}m, {len(keep)} candidates)")
    ind = {c: sharpe_m(R[c].dropna()) for c in R.columns}

    path, selected = [], []
    remaining = [c for c in R.columns if not np.isnan(ind[c])]
    while remaining:
        best_c, best_sh = None, -np.inf
        for c in remaining:
            sh = sharpe_m(R[selected + [c]].mean(axis=1).dropna())
            if not np.isnan(sh) and sh > best_sh:
                best_sh, best_c = sh, c
        if best_c is None:
            break
        selected.append(best_c); remaining.remove(best_c); path.append((best_c, best_sh))
    peak_i = int(np.argmax([s for _, s in path]))
    final = [c for c, _ in path[:peak_i+1]]
    port_m = R[final].mean(axis=1).dropna()
    sh, cagr, mdd = stats_monthly(port_m)

    lines = [f"# {name} Portfolio", "",
             f"Full-path greedy, natural-peak stop, common window {R.index[0].date()} -> {R.index[-1].date()}.",
             "", f"**Selected {len(final)}/{len(R.columns)}** | Sharpe(m) **{sh}** | CAGR {cagr}% | MaxDD {mdd}%",
             "", "| Step | Added | Sharpe |", "|---|---|---|"]
    for i, (c, s) in enumerate(path):
        lines.append(f"| {i+1} | {c} | {s:.3f}{' **<- peak**' if i == peak_i else ''} |")
    lines += ["", "Individual Sharpes: " + ", ".join(f"{c} {s:+.2f}" for c, s in
              sorted(ind.items(), key=lambda x: -(x[1] if not np.isnan(x[1]) else -9)))]
    if len(final) <= 2 and len(path) >= 4:
        alt_i = 3 + int(np.argmax([s for _, s in path[3:]]))
        alt = [c for c, _ in path[:alt_i+1]]
        a_port = R[alt].mean(axis=1).dropna()
        a_sh, a_cagr, a_mdd = stats_monthly(a_port)
        (1 + a_port).cumprod().mul(100_000).rename('equity').to_csv(
            os.path.join(RESULTS, f'{name.lower()}_portfolio_diversified_equity.csv'), index_label='date')
        lines += ["", f"**Diversified alternative:** {', '.join(alt)} - Sharpe {a_sh}, CAGR {a_cagr}%, MaxDD {a_mdd}%"]
    tag = name.lower()
    with open(os.path.join(RESULTS, f'{tag}_portfolio_results.md'), 'w') as f:
        f.write('\n'.join(lines))
    R[final].to_csv(os.path.join(RESULTS, f'{tag}_portfolio_selected_returns.csv'), index_label='date')
    eq = (1 + port_m).cumprod() * 100_000
    eq.rename('equity').to_csv(os.path.join(RESULTS, f'{tag}_portfolio_equity.csv'), index_label='date')
    print(f"[{name}] {len(final)}/{len(R.columns)}: {final} | Sharpe(m)={sh} CAGR={cagr}% MaxDD={mdd}%")
    return port_m

# ═════════════════ COMBINED (1/3 each sleeve) ═════════════════

def build_combined():
    eqs = {}
    for p in ('intraday', 'daily', 'longterm'):
        f = os.path.join(RESULTS, f'{p}_portfolio_equity.csv')
        if os.path.exists(f):
            eqs[p] = pd.read_csv(f, parse_dates=['date']).set_index('date')['equity']
    if len(eqs) < 3:
        print(f"[Combined] only {list(eqs)} available - build after all three exist"); return
    # monthly returns per sleeve on the common window, EW (= 1/3 capital, monthly rebal)
    mrets = pd.DataFrame({k: v.resample('ME').last().pct_change() for k, v in eqs.items()}).dropna()
    port = mrets.mean(axis=1)
    sh, cagr, mdd = stats_monthly(port)
    eq = (1 + port).cumprod() * 100_000
    eq.rename('equity').to_csv(os.path.join(RESULTS, 'combined_portfolio_equity.csv'), index_label='date')
    with open(os.path.join(RESULTS, 'combined_portfolio_results.md'), 'w') as f:
        f.write(f"# Combined Portfolio (1/3 Intraday + 1/3 Daily + 1/3 LongTerm)\n\n"
                f"Monthly-rebalanced EW of the three sleeve return streams, common window "
                f"{mrets.index[0].date()} -> {mrets.index[-1].date()} ({len(mrets)} months).\n\n"
                f"**Sharpe(m) {sh} | CAGR {cagr}% | MaxDD {mdd}%**\n\n"
                "Sleeve correlations (monthly):\n\n" + mrets.corr().round(2).to_markdown() +
                "\n\nNote: intraday Sharpe dominates; equal capital (not equal risk) is the "
                "methodology's allocation. A risk-parity weighting is a possible v6 refinement.\n")
    print(f"[Combined] Sharpe(m)={sh} CAGR={cagr}% MaxDD={mdd}%")

if __name__ == '__main__':
    build_intraday()
    greedy_full_path('Daily', DAILY_CANDIDATES)
    greedy_full_path('LongTerm', lt_candidates())
    build_combined()
    print(f"\nSaved -> {RESULTS}")
