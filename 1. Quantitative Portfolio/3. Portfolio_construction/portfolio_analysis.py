"""
portfolio_analysis.py  (companion to build_portfolios.py)
=========================================================
Produces the three per-portfolio CANDIDATE tables (Daily, LongTerm, Intraday)
with Sharpe / t-stat / gates(0-3) / CAGR / MaxDD / #baskets / #instruments,
PLUS the greedy selection for each — using a diversification THRESHOLD so the
greedy keeps adding strategies past the strict Sharpe peak as long as the
cumulative Sharpe stays within THRESHOLD of the peak.

Decisions baked in (agreed with user, 2026-07-05):
  * VIX_MR_v2 path fixed -> results/vix_mean_reversion_v2_multiasset_daily_equity/combined_equity.csv
  * LongTerm split into TIMING vs SELECTION tables.
  * Gates: computed with the SAME 3-gate test as shared/basket_significance.py
    (gate1 one-sided t p<a; gate2 bootstrap 5th-pct Sharpe>0; gate3 sign-perm
    p<a), seed=42, on each candidate's own monthly combined-equity curve. This
    reproduces Long_Term_Strategies/results/basket_bonferroni_validation.json
    for the LT names and extends the same test to Daily/Intraday.
  * Intraday: greedy over the 4 true session strats (ema/imom/orb/vwap); the
    final intraday sleeve = greedy blend + overnight (additive, non-overlapping).
    vol_overlay EXCLUDED from the intraday greedy (it is a continuous SPY beta
    overlay, self-labelled portfolio=long_term) but shown for reference.
  * THRESHOLD default 0.1.

Output: results/portfolio_candidate_tables.md  (+ printed to console)
Run:    double-click RUN_candidate_stats.bat   (or: python portfolio_analysis.py [threshold])
"""
import os, sys, json, glob
import numpy as np
import pandas as pd

try:
    from scipy import stats as _st
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False

# ---- locate project root exactly like build_portfolios.py ----
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root not found - place at algo_trading root'
    _d = _p
ROOT = _d
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, 'results')
os.makedirs(RESULTS, exist_ok=True)

THRESHOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
ALPHA = 0.05
N_BOOT = 5000
SEED = 42

# 2026-07-10: repointed to the merged short-term tree (old root-level
# Intraday_Strategies/ and Daily_Strategies/ no longer exist) and consolidated
# to TWO portfolios: SHORT-TERM (merged 9-strategy pool) + LONG-TERM.
ST = '1. Short_Term_Strategies'
LT = '2. Long_Term_Strategies'
IS = ST  # kept as aliases so downstream imports don't break
DS = ST

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
    r = pd.Series(r).dropna()
    return float(r.mean()/r.std()*np.sqrt(12)) if r.std() > 0 else np.nan

def stats_monthly(r):
    r = pd.Series(r).dropna()
    sh = sharpe_m(r)
    eq = (1 + r).cumprod()
    yrs = (r.index[-1]-r.index[0]).days/365.25
    cagr = float(eq.iloc[-1])**(1/max(yrs, 0.5)) - 1
    mdd = float(((eq - eq.cummax())/eq.cummax()).min())
    return round(sh, 3), round(cagr*100, 2), round(mdd*100, 2)

def stats_daily(r):
    r = pd.Series(r).dropna()
    sh = r.mean()/r.std()*np.sqrt(252) if r.std() > 0 else np.nan
    eq = (1 + r).cumprod()
    yrs = (r.index[-1]-r.index[0]).days/365.25
    cagr = float(eq.iloc[-1])**(1/max(yrs, 0.5)) - 1
    mdd = float(((eq - eq.cummax())/eq.cummax()).min())
    return round(float(sh), 3), round(cagr*100, 2), round(mdd*100, 2)

def t_stat(monthly_returns):
    r = pd.Series(monthly_returns).dropna().values
    if len(r) < 3 or r.std(ddof=1) == 0:
        return np.nan
    return float(r.mean()/(r.std(ddof=1)/np.sqrt(len(r))))

def gates(monthly_returns, alpha=ALPHA, n_boot=N_BOOT, seed=SEED):
    """3-gate test (matches shared/basket_significance.gates_at_alpha).
    Returns dict with t, gate1_p, gate2_boot5, gate3_p, passed(0-3)."""
    r = pd.Series(monthly_returns).dropna().values
    if len(r) < 12 or r.std() == 0:
        return {"t": np.nan, "g1": np.nan, "g2": np.nan, "g3": np.nan, "passed": 0, "n": len(r)}
    t = r.mean()/(r.std(ddof=1)/np.sqrt(len(r)))
    if _HAVE_SCIPY:
        _, p2 = _st.ttest_1samp(r, 0)
        g1 = float(p2/2 if t > 0 else 1 - p2/2)
    else:  # normal approximation fallback
        from math import erf, sqrt
        cdf = 0.5*(1+erf(t/sqrt(2)))
        g1 = float(1-cdf if t > 0 else cdf)
    rng = np.random.RandomState(seed)
    obs = r.mean()/r.std()*np.sqrt(12)
    boots = [ (s.mean()/s.std()*np.sqrt(12) if s.std() > 0 else 0.0)
              for s in (rng.choice(r, size=len(r), replace=True) for _ in range(n_boot)) ]
    g2 = float(np.percentile(boots, 5))
    cnt = 0
    for _ in range(n_boot):
        s = r*rng.choice([-1, 1], len(r))
        if (s.mean()/s.std()*np.sqrt(12) if s.std() > 0 else 0.0) >= obs:
            cnt += 1
    g3 = float(cnt/n_boot)
    passed = int(g1 < alpha) + int(g2 > 0) + int(g3 < alpha)
    return {"t": float(t), "g1": round(g1, 4), "g2": round(g2, 3), "g3": round(g3, 4),
            "passed": passed, "n": len(r)}

# ---- best-effort #baskets / #instruments from a strategy's implementations JSON ----
def counts_for(*dir_globs):
    for g in dir_globs:
        for jp in glob.glob(os.path.join(ROOT, g)):
            try:
                with open(jp) as f:
                    d = json.load(f)
            except Exception:
                continue
            nb = d.get("n_passing_baskets")
            baskets = d.get("baskets") if isinstance(d.get("baskets"), dict) else {}
            if nb is None and baskets:
                nb = len(baskets)
            ninstr = None
            if baskets:
                tot = 0; ok = False
                for _, cfg in baskets.items():
                    if isinstance(cfg, dict) and isinstance(cfg.get("instruments"), list):
                        tot += len(cfg["instruments"]); ok = True
                if ok:
                    ninstr = tot
            if nb is not None or ninstr is not None:
                return nb, ninstr
    return None, None

# ═════════════════ candidate definitions (from build_portfolios.py) ═════════════════

# ONE merged short-term pool: all 9 short-term strategies (5 intraday session
# + overnight + 3 daily). Overnight is a NORMAL blended member (the old
# "additive overnight" trick applied only to the retired standalone intraday book).
# VIX_MR_v2 path bug fixed 2026-07-10: the old first choice pointed at the
# superseded wrong equity-regime version (vix_mean_reversion_v2_multiasset_daily_equity);
# canonical is now the notebook sizing curve, standardized to results/equity/combined_equity_final.csv.
SHORT_TERM_CANDIDATES = {
    'ema_crossover':     [f'{ST}/ema_crossover/results/equity/combined_equity_final.csv'],
    'intraday_momentum': [f'{ST}/intraday_momentum/results/equity/combined_equity_final.csv'],
    'orb':               [f'{ST}/orb/results/equity/combined_equity_final.csv'],
    'vwap_trend':        [f'{ST}/vwap_trend/results/equity/combined_equity_final.csv'],
    'overnight':         [f'{ST}/overnight/results/equity/combined_equity_final.csv'],
    'IBS_v2':            [f'{ST}/ibs_mean_reversion/results/equity/combined_equity_simple.csv',
                          f'{ST}/ibs_mean_reversion/results/equity/combined_equity_final.csv'],
    'VIX_MR_v2':         [f'{ST}/vix_mean_reversion/results/equity/combined_equity_final.csv',
                          f'{ST}/vix_mean_reversion/results/vix_mean_reversion_daily_equity/asset_vol_10pct_1x.csv'],
    'VIX_ETN_Dual':      [f'{ST}/vix_etn_dual/results/equity/combined_equity_1p0x.csv',
                          f'{ST}/vix_etn_dual/results/equity/combined_equity_final.csv'],
    'Congress_Quiver':   [f'{ST}/congress_momentum/results/equity/combined_equity_base_10pct.csv',
                          f'{ST}/congress_momentum/results/equity/combined_equity_final.csv'],
}
DAILY_CANDIDATES = SHORT_TERM_CANDIDATES  # backwards-compat alias

# Ex-"daily pool" names that physically live in the LT tree. NOT in the short-term
# pool (plan 2026-07-10: ST universe = the 9 above). User decision 2026-07-10:
# these ARE candidates of the LONG-TERM pool (greedy decides).
EX_DAILY_LT_TREE = {
    'Congress_TFT':    [f'{LT}/timing/congress_trade_for_trade/results/congress_trade_for_trade_daily_equity/total_nav_3pct_d180_min30d_1x.csv'],
    'Bollinger':       [f'{LT}/timing/bollinger_band/results/bollinger_band_v2_multiasset_daily_equity/combined_equity.csv',
                        f'{LT}/timing/bollinger_band/results/bollinger_band_multiasset_daily_equity/combined_equity.csv'],
    'Turn_of_Month':   [f'{LT}/timing/turn_of_month/results/turn_of_month_v2_multiasset_daily_equity/combined_equity.csv',
                        f'{LT}/timing/turn_of_month/results/turn_of_month_multiasset_daily_equity/combined_equity.csv'],
    'Donchian':        [f'{LT}/timing/donchian_channel/results/donchian_channel_v2_multiasset_daily_equity/combined_equity.csv',
                        f'{LT}/timing/donchian_channel/results/donchian_channel_multiasset_daily_equity/combined_equity.csv'],
}
DAILY_JSONKEY = {'Congress_TFT': 'congress_trade_for_trade', 'Bollinger': 'bollinger_band',
                 'Turn_of_Month': 'turn_of_month', 'Donchian': 'donchian_channel'}

LT_TIMING = ['credit_carry', 'yield_curve_duration', 'bab_long_short', 'insider_buying',
             'overnight_premium', 'qmj_long_short', 'reit_dividend_carry',
             'short_interest_contrarian', 'us_cross_sectional_momentum',
             'us_earnings_momentum', 'us_return_seasonality', 'us_shareholder_yield',
             'low_volatility', 'pead_earnings_drift', 'bond_duration_carry']
LT_SELECTION = ['gtaa', 'sector_momentum', 'bond_trend', 'commodity_carry',
                'commodity_trend', 'country_cape_rotation', 'cross_asset_carry',
                'em_dm_carry', 'industry_trend', 'quality_profitability']

def lt_timing_paths(s):
    return [f'{LT}/timing/{s}/results/{s}_v2_multiasset_daily_equity/combined_equity.csv',
            f'{LT}/timing/{s}/results/{s}_multiasset_daily_equity/combined_equity.csv',
            f'{LT}/timing/{s}/results/{s}_daily_equity/{s}_daily_equity.csv',
            f'{LT}/timing/{s}/results/low_vol_v2_daily_equity/low_vol_v2_daily_equity.csv']

def lt_selection_paths(s):
    return [f'{LT}/selection/{s}/results/{s}_v2_multiasset_daily_equity/combined_equity.csv',
            f'{LT}/selection/{s}/results/{s}_multiasset_daily_equity/combined_equity.csv',
            f'{LT}/selection/{s}/results/{s}_daily_equity/{s}_daily_equity.csv']

# Legacy aliases (intraday sleeve retired 2026-07-10; kept for import-compat)
INTRADAY_SESSION = {k: SHORT_TERM_CANDIDATES[k] for k in
                    ('ema_crossover', 'intraday_momentum', 'orb', 'vwap_trend')}
OVERNIGHT_PATH = SHORT_TERM_CANDIDATES['overnight']
# vol_overlay extracted to Regime_Classification/ (own project, 2026-07-10) - no longer referenced

def cagr_at_target_vol(monthly_returns, target=0.10):
    """Leverage-normalized CAGR: scale monthly returns to `target` annualized vol
    (k = target/realized_vol, no financing-cost adjustment) and report the CAGR.
    Lets strategies with different natural vols be compared at equal risk."""
    r = pd.Series(monthly_returns).dropna()
    if len(r) < 12 or r.std() == 0:
        return np.nan
    k = target / (r.std() * np.sqrt(12))
    rl = r * k
    eq = (1 + rl).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return round((float(eq.iloc[-1]) ** (1 / max(yrs, 0.5)) - 1) * 100, 2)

# ═════════════════ greedy with diversification threshold ═════════════════

def greedy_with_threshold(rets_dict, name, threshold=THRESHOLD, min_window=60):
    """rets_dict: label -> monthly returns series. Reproduces build_portfolios'
    common-window trimming + additive-mean greedy, then extends past the strict
    Sharpe peak while cumulative Sharpe stays within `threshold` of the peak."""
    rets = {k: v for k, v in rets_dict.items() if v is not None and len(v) >= 24}
    R = pd.DataFrame(rets)
    if R.shape[1] == 0:
        return None
    starts = {c: R[c].dropna().index[0] for c in R.columns}
    ends   = {c: R[c].dropna().index[-1] for c in R.columns}
    keep = list(R.columns)
    end_target = pd.Series(list(ends.values())).quantile(0.75)
    for c in list(keep):
        if ends[c] < end_target - pd.DateOffset(months=18):
            keep.remove(c)
    while keep:
        w_start, w_end = max(starts[c] for c in keep), min(ends[c] for c in keep)
        if (w_end.year - w_start.year)*12 + (w_end.month - w_start.month) >= min_window:
            break
        worst = max(keep, key=lambda c: starts[c]); keep.remove(worst)
    R = R[keep].dropna()
    if R.shape[1] == 0 or len(R) == 0:
        return None
    ind = {c: sharpe_m(R[c]) for c in R.columns}
    path, selected = [], []
    remaining = [c for c in R.columns if not np.isnan(ind[c])]
    while remaining:
        best_c, best_sh = None, -np.inf
        for c in remaining:
            sh = sharpe_m(R[selected + [c]].mean(axis=1))
            if not np.isnan(sh) and sh > best_sh:
                best_sh, best_c = sh, c
        if best_c is None:
            break
        selected.append(best_c); remaining.remove(best_c); path.append((best_c, best_sh))
    if not path:
        return None
    peak_sh = max(s for _, s in path)
    peak_i = int(np.argmax([s for _, s in path]))
    # threshold extension: last step whose cumulative Sharpe stays within threshold of peak
    final_i = peak_i
    for i in range(peak_i, len(path)):
        if path[i][1] >= peak_sh - threshold:
            final_i = i
        else:
            break
    final = [c for c, _ in path[:final_i+1]]
    port = R[final].mean(axis=1).dropna()
    return {"R": R, "ind": ind, "path": path, "peak_i": peak_i, "final_i": final_i,
            "final": final, "port_stats": stats_monthly(port),
            "window": (R.index[0].date(), R.index[-1].date(), len(R))}

# ═════════════════ table building ═════════════════

def candidate_row(label, paths, jsonkey=None, counts_globs=None):
    p = _first(*paths)
    if p is None:
        return {"label": label, "ok": False, "note": "NO EQUITY FILE"}
    try:
        rm = load_returns(p, monthly=True)
        sh, cagr, mdd = stats_monthly(rm)
        g = gates(rm)
        nb, ninstr = counts_for(*counts_globs) if counts_globs else (None, None)
        return {"label": label, "ok": True, "sh": sh, "cagr": cagr, "mdd": mdd,
                "t": g["t"], "passed": g["passed"], "n": len(rm),
                "start": rm.index[0].date(), "end": rm.index[-1].date(),
                "nb": nb, "ninstr": ninstr, "rm": rm,
                "note": "" if len(rm) >= 24 else "<24m (greedy drops)"}
    except Exception as e:
        return {"label": label, "ok": False, "note": f"ERROR: {e}"}

def fmt_candidate_table(title, rows, freq_label="Sharpe(m)"):
    rows2 = sorted(rows, key=lambda r: (not r.get("ok"), -(r.get("sh") if r.get("ok") and r.get("sh") is not None else -9)))
    out = [f"### {title}", "",
           f"| Strategy | {freq_label} | t-stat | Gates | CAGR % | MaxDD % | #Baskets | #Instr | Months | Start | End | Note |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows2:
        if not r.get("ok"):
            out.append(f"| {r['label']} | - | - | - | - | - | - | - | - | - | {r['note']} |")
        else:
            t = f"{r['t']:.2f}" if r['t'] == r['t'] else "-"   # nan check
            nb = r['nb'] if r['nb'] is not None else "-"
            ni = r['ninstr'] if r['ninstr'] is not None else "-"
            out.append(f"| {r['label']} | {r['sh']:.3f} | {t} | {r['passed']}/3 | {r['cagr']:.2f} | "
                       f"{r['mdd']:.2f} | {nb} | {ni} | {r['n']} | {r['start']} | {r['end']} | {r['note']} |")
    out.append("")
    return "\n".join(out)

def fmt_greedy(name, res, freq="Sharpe(m)"):
    if res is None:
        return f"**{name} greedy:** no candidates with >=24m.\n"
    w0, w1, wm = res["window"]
    sh, cagr, mdd = res["port_stats"]
    out = [f"**{name} greedy** (threshold {THRESHOLD}, common window {w0} -> {w1}, {wm}m)  ",
           f"Selected **{len(res['final'])}/{len(res['R'].columns)}**: {', '.join(res['final'])}  ",
           f"Portfolio {freq} **{sh}** | CAGR {cagr}% | MaxDD {mdd}%", "",
           "| Step | Added | Cumulative Sharpe |", "|---|---|---|"]
    for i, (c, s) in enumerate(res["path"]):
        tag = ""
        if i == res["peak_i"]:
            tag = " (strict peak)"
        if i == res["final_i"] and res["final_i"] != res["peak_i"]:
            tag += " <- threshold stop"
        elif i == res["final_i"]:
            tag += " <- selected stop"
        out.append(f"| {i+1} | {c} | {s:.3f}{tag} |")
    out.append("")
    return "\n".join(out)

# ═════════════════ main ═════════════════

if __name__ == '__main__':
    print(f"ROOT={ROOT}\nthreshold={THRESHOLD} alpha={ALPHA} scipy={_HAVE_SCIPY}\n")
    md = [f"# Portfolio Candidate Tables & Greedy Selection",
          "",
          f"Threshold **{THRESHOLD}** (greedy keeps adding past the strict Sharpe peak "
          f"while cumulative Sharpe stays within {THRESHOLD} of it). Gates = 3-gate test "
          f"(t-test / bootstrap Sharpe / sign-permutation) at alpha={ALPHA}, seed={SEED}, "
          f"on each candidate's monthly combined-equity curve — same test as "
          f"basket_significance.py; reproduces basket_bonferroni_validation.json for LT names."
          + ("" if _HAVE_SCIPY else "  NOTE: scipy not installed - gate1 p uses a normal approximation."),
          ""]

    # ---------- SHORT-TERM (merged 9-strategy pool) ----------
    print("== SHORT-TERM (merged pool of 9) ==")
    st_rows, st_monthly, st_daily = [], {}, {}
    for label, paths in SHORT_TERM_CANDIDATES.items():
        p = _first(*paths)
        if p is None:
            st_rows.append({"label": label, "ok": False, "note": "NO EQUITY FILE"})
            print(f"  {label:18} NO EQUITY FILE"); continue
        rd = load_returns(p, monthly=False); rm = load_returns(p, monthly=True)
        shm, cagr, mdd = stats_monthly(rm)
        shd = stats_daily(rd)[0]
        g = gates(rm)
        st_rows.append({"label": label, "ok": True, "shm": shm, "shd": shd,
                        "cagr": cagr, "mdd": mdd,
                        "t": g["t"], "passed": g["passed"], "n": len(rm),
                        "start": rm.index[0].date(), "end": rm.index[-1].date(), "note": ""})
        st_monthly[label] = rm; st_daily[label] = rd
        print(f"  {label:18} ok")
    md.append("## SHORT-TERM portfolio (one merged pool — 5 intraday session + overnight + 3 daily)")
    md.append("")
    md.append("| Strategy | Sharpe(m) | Sharpe(d) | t-stat | Gates | CAGR % | MaxDD % | Months | Start | End | Note |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in sorted(st_rows, key=lambda x: (not x.get("ok"), -(x.get("shm") or -9))):
        if not r.get("ok"):
            md.append(f"| {r['label']} | - | - | - | - | - | - | - | - | - | {r['note']} |")
        else:
            t = f"{r['t']:.2f}" if r['t'] == r['t'] else "-"
            md.append(f"| {r['label']} | {r['shm']:.3f} | {r['shd']:.3f} | {t} | {r['passed']}/3 | "
                      f"{r['cagr']:.2f} | {r['mdd']:.2f} | {r['n']} | {r['start']} | {r['end']} | {r['note']} |")
    md.append("")
    st_res = greedy_with_threshold(st_monthly, "ShortTerm")
    md.append(fmt_greedy("SHORT-TERM (merged pool, overnight = normal member)", st_res))
    if st_res is not None:
        sel = st_res["final"]
        # correlation matrix (monthly, common window)
        md.append("**Correlation matrix (monthly, common window):**\n")
        try:
            md.append(st_res["R"].corr().round(2).to_markdown())
        except Exception:
            md.append("```\n" + st_res["R"].corr().round(2).to_string() + "\n```")
        md.append("")
        # daily-frequency stats + leverage-normalized CAGR of the selected blend
        blend_d = pd.DataFrame({k: st_daily[k] for k in sel}).dropna(how='all').fillna(0).mean(axis=1)
        shd, cad, mdd_d = stats_daily(blend_d)
        port_m = st_res["R"][sel].mean(axis=1).dropna()
        md.append(f"**Selected blend ({len(sel)} strats):** Sharpe(m) {st_res['port_stats'][0]} | "
                  f"Sharpe(d) {shd} | CAGR {cad}% | MaxDD(d) {mdd_d}%\n")

    # ---------- LONGTERM ----------
    print("== LONGTERM ==")
    lt_rets = {}
    timing_rows, selection_rows = [], []
    for s in LT_TIMING:
        r = candidate_row(s, lt_timing_paths(s),
                          counts_globs=[f'{LT}/timing/{s}/results/*implementations*.json'])
        timing_rows.append(r)
        if r.get("ok") and r.get("rm") is not None:
            lt_rets[s] = r["rm"]
        print(f"  [T] {s:28} {'ok' if r.get('ok') else r['note']}")
    for s in LT_SELECTION:
        r = candidate_row(s, lt_selection_paths(s),
                          counts_globs=[f'{LT}/selection/{s}/results/*implementations*.json'])
        selection_rows.append(r)
        if r.get("ok") and r.get("rm") is not None:
            lt_rets[s] = r["rm"]
        print(f"  [S] {s:28} {'ok' if r.get('ok') else r['note']}")
    # ex-daily timing names (user decision 2026-07-10: LT pool members)
    for s, paths in EX_DAILY_LT_TREE.items():
        jk = DAILY_JSONKEY.get(s)
        r = candidate_row(s, paths,
                          counts_globs=[f'{LT}/timing/{jk}/results/*implementations*.json'] if jk else None)
        r["note"] = (r.get("note") or "") + " ex-daily"
        timing_rows.append(r)
        if r.get("ok") and r.get("rm") is not None:
            lt_rets[s] = r["rm"]
        print(f"  [X] {s:28} {'ok' if r.get('ok') else r['note']}")
    md.append("## LongTerm portfolio")
    md.append(fmt_candidate_table(f"LongTerm - TIMING candidates ({len(timing_rows)})", timing_rows))
    md.append(fmt_candidate_table(f"LongTerm - SELECTION candidates ({len(selection_rows)})", selection_rows))
    md.append("_Greedy runs over the combined timing+selection pool, as in build_portfolios.py._\n")
    md.append(fmt_greedy("LongTerm", greedy_with_threshold(lt_rets, "LongTerm")))

    # (Intraday sleeve retired 2026-07-10 - merged into the SHORT-TERM pool above.)

    text = "\n".join(md)
    outpath = os.path.join(RESULTS, 'portfolio_candidate_tables.md')
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(text)
    print("\n" + text)
    print(f"\nSaved -> {outpath}")
