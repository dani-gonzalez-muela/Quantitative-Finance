"""
Greedy Forward Selection Optimizer — Portfolio A v2
Fixes: uses correct strategy variants (matching Portfolio_A_Analysis.ipynb selections)
Threshold: include strategy unless delta Sharpe < -0.05
"""

import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))   # algo_trading/
ST   = os.path.join(ROOT, "short_term")
LT   = os.path.join(ROOT, "long_term")
BL   = os.path.join(ROOT, "borderline_timeframes")

CANDIDATES = {
    "ema_crossover":      os.path.join(ST, "ema_crossover/results/ema_crossover_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv"),
    "vwap_trend":         os.path.join(ST, "vwap_trend/results/vwap_trend_daily_equity/vol_target_10pct_ann_1x_max_lev.csv"),
    "orb":                os.path.join(ST, "orb/results/orb_daily_equity/risk-based_1pct_risk_1x_lev.csv"),
    "overnight":          os.path.join(ST, "overnight/results/overnight_daily_equity/simple_85pct_bet.csv"),
    "intraday_momentum":  os.path.join(ST, "intraday_momentum/results/intraday_momentum_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv"),
    "congress_s3_quiver": os.path.join(ST, "congress_momentum/results/congress_momentum_quiver_open_daily_equity/quiver_open_10pct_1x.csv"),
    "ibs_mean_reversion": os.path.join(ST, "ibs_mean_reversion/results/ibs_mean_reversion_daily_equity/simple_bet_85pct_1x.csv"),
    "vix_mean_reversion": os.path.join(ST, "vix_mean_reversion/results/vix_mean_reversion_daily_equity/simple_bet_85pct_1x.csv"),
    "vix_etn_dual":       os.path.join(ST, "vix_etn_dual/results/vix_etn_dual_daily_equity/evrp_boc_sizing_1p0x.csv"),
    "turn_of_month":      os.path.join(BL, "turn_of_month/results/turn_of_month_daily_equity/turn_of_month_daily_equity.csv"),
    "overnight_premium":  os.path.join(BL, "overnight_premium/results/overnight_premium_daily_equity/overnight_premium_daily_equity.csv"),
}

EXISTING_PORTFOLIO = os.path.join(SCRIPT_DIR, "portfolio_a_1.0x.csv")
OUT_MD  = os.path.join(SCRIPT_DIR, "greedy_a_v2_results.md")
OUT_CSV = os.path.join(SCRIPT_DIR, "portfolio_a_v2_selected_returns.csv")

GREEDY_THRESHOLD = -0.05

def sharpe(returns):
    m, s = returns.mean(), returns.std()
    return m / s * np.sqrt(252) if s > 0 else np.nan

def tstat(sh, n):
    return sh * np.sqrt(n / 252)

def cagr(equity):
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

def max_drawdown(equity):
    return ((equity - equity.cummax()) / equity.cummax()).min()

def sortino(returns):
    downside = returns[returns < 0].std()
    return returns.mean() / downside * np.sqrt(252) if downside > 0 else np.nan

def load_equity(path):
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date")
        if "equity" not in df.columns:
            df.columns = ["equity"]
        eq = df["equity"].dropna().sort_index()
        return eq if len(eq) >= 100 else None
    except:
        return None

print("\n" + "="*60)
print("GREEDY OPTIMIZER — Portfolio A v2 (correct variants)")
print(f"Threshold: delta >= {GREEDY_THRESHOLD}")
print("="*60)

loaded = {}
for name, path in CANDIDATES.items():
    eq = load_equity(path)
    if eq is not None:
        loaded[name] = eq.pct_change().dropna()
        print(f"  OK  {name:<25} Sharpe={sharpe(loaded[name]):.4f}")
    else:
        print(f"  FAIL {name} -> {path}")

common = None
for r in loaded.values():
    common = r.index if common is None else common.intersection(r.index)
common = common.sort_values()
N = len(common)
print(f"\nCommon window: {common[0].date()} -> {common[-1].date()} ({N} days)")

ret_df = pd.DataFrame({k: v.reindex(common) for k, v in loaded.items()})
standalone = {k: sharpe(ret_df[k]) for k in ret_df.columns}

print("\n--- Standalone Sharpe (sorted) ---")
for k, s in sorted(standalone.items(), key=lambda x: -x[1]):
    print(f"  {k:<25} Sharpe={s:.4f}  t={tstat(s,N):.2f}")

seed = max(standalone, key=standalone.get)
selected = [seed]
remaining = [k for k in ret_df.columns if k != seed]
port_sh = sharpe(ret_df[selected].mean(axis=1))

print(f"\nSeed: {seed} (Sharpe={port_sh:.4f})")
print("\n--- Greedy Trace ---")

trace = []
while remaining:
    best_delta = -999
    best_strat = None
    best_sh_val = None
    for k in remaining:
        trial = selected + [k]
        sh_trial = sharpe(ret_df[trial].mean(axis=1))
        delta = sh_trial - port_sh
        if delta > best_delta:
            best_delta = delta
            best_strat = k
            best_sh_val = sh_trial

    if best_delta >= GREEDY_THRESHOLD:
        selected.append(best_strat)
        remaining.remove(best_strat)
        corr = ret_df[best_strat].corr(ret_df[selected[:-1]].mean(axis=1))
        trace.append((best_strat, port_sh, best_sh_val, best_delta, len(selected), corr))
        print(f"  Step {len(trace)}: +{best_strat:<25} {port_sh:.4f} -> {best_sh_val:.4f}  delta={best_delta:+.4f}  corr={corr:.3f}")
        port_sh = best_sh_val
    else:
        print(f"  STOP: best '{best_strat}' delta={best_delta:.4f} < {GREEDY_THRESHOLD}")
        break

port_rets = ret_df[selected].mean(axis=1)
eq_final = (1 + port_rets).cumprod() * 100_000

final_sh      = sharpe(port_rets)
final_cagr    = cagr(eq_final)
final_dd      = max_drawdown(eq_final)
final_sortino = sortino(port_rets)

print(f"\n=== FINAL PORTFOLIO ({len(selected)} strategies) ===")
for k in selected:
    print(f"  {k}")
print(f"  Sharpe:  {final_sh:.4f}")
print(f"  CAGR:    {final_cagr*100:.2f}%")
print(f"  MaxDD:   {final_dd*100:.2f}%")
print(f"  Sortino: {final_sortino:.4f}")

print("\n--- Rejected ---")
for k in remaining:
    trial_sh = sharpe(ret_df[selected + [k]].mean(axis=1))
    delta = trial_sh - port_sh
    corr_k = ret_df[k].corr(port_rets)
    print(f"  {k:<25} delta={delta:+.4f}  corr={corr_k:.3f}")

corr_mat = ret_df[selected].corr()

print("\n--- Comparison to existing Portfolio A ---")
try:
    ex = pd.read_csv(EXISTING_PORTFOLIO, parse_dates=["date"], index_col="date")
    if "equity" not in ex.columns: ex.columns = ["equity"]
    ex_rets = ex["equity"].pct_change().dropna()
    cx = common.intersection(ex_rets.index)
    ex_c  = ex_rets.reindex(cx)
    new_c = port_rets.reindex(cx)
    eq_ex  = (1 + ex_c).cumprod() * 100_000
    eq_new = (1 + new_c).cumprod() * 100_000
    print(f"  Window: {cx[0].date()} -> {cx[-1].date()}")
    for mname, ev, nv in [
        ("Sharpe",  sharpe(ex_c),           sharpe(new_c)),
        ("CAGR%",   cagr(eq_ex)*100,        cagr(eq_new)*100),
        ("MaxDD%",  max_drawdown(eq_ex)*100, max_drawdown(eq_new)*100),
        ("Sortino", sortino(ex_c),          sortino(new_c)),
    ]:
        print(f"  {mname:<10} Existing={ev:.4f}  v2={nv:.4f}  delta={nv-ev:+.4f}")
except Exception as e:
    print(f"  Could not load existing: {e}")

ret_df[selected].to_csv(OUT_CSV)
print(f"\nReturns saved -> {OUT_CSV}")

# ── Markdown report ──────────────────────────────────────────────────────────
variant_labels = {
    "ema_crossover":      "intraday_asset_vol_2pct_14d_1x_max",
    "vwap_trend":         "vol_target_10pct_ann_1x_max_lev",
    "orb":                "risk-based_1pct_risk_1x_lev",
    "overnight":          "simple_85pct_bet",
    "intraday_momentum":  "intraday_asset_vol_2pct_14d_1x_max",
    "congress_s3_quiver": "quiver_open_10pct_1x",
    "ibs_mean_reversion": "simple_bet_85pct_1x",
    "vix_mean_reversion": "simple_bet_85pct_1x",
    "vix_etn_dual":       "evrp_boc_sizing_1p0x",
    "turn_of_month":      "turn_of_month_daily_equity",
    "overnight_premium":  "overnight_premium_daily_equity",
}

lines = [
    f"# Greedy Forward Selection — Portfolio A v2 (Correct Variants)\n",
    f"**Analysis date:** 2026-06-19  ",
    f"**Common window:** {common[0].date()} -> {common[-1].date()} ({N} trading days)  ",
    f"**Threshold:** delta >= {GREEDY_THRESHOLD} (include unless it strongly hurts)  ",
    f"**Fix from v1:** Correct sizing variants per strategy (matching Portfolio_A_Analysis.ipynb)  \n",
    "\n---\n",
    "## Section 0: Variant Fix vs v1\n",
    "| Strategy | v1 (wrong) | v2 (correct) | Sharpe v1 | Sharpe v2 |",
    "|---|---|---|---|---|",
    "| ema_crossover | simple_85pct_bet | intraday_asset_vol_2pct_14d_1x_max | 1.94 | {:.4f} |".format(standalone.get("ema_crossover",0)),
    "| intraday_momentum | simple_85pct_bet | intraday_asset_vol_2pct_14d_1x_max | 0.98 | {:.4f} |".format(standalone.get("intraday_momentum",0)),
    "| vwap_trend | simple_85pct_bet | vol_target_10pct_ann_1x_max_lev | 0.61 | {:.4f} |".format(standalone.get("vwap_trend",0)),
    "| orb | simple_85pct_bet | risk-based_1pct_risk_1x_lev | 0.84 | {:.4f} |".format(standalone.get("orb",0)),
    "\n---\n",
    "## Section 1: All Candidates — Standalone Sharpe\n",
    "| Strategy | Sharpe | t-stat | Variant |",
    "|---|---|---|---|",
]
for k, s in sorted(standalone.items(), key=lambda x: -x[1]):
    lines.append(f"| {k} | {s:.4f} | {tstat(s,N):.2f} | {variant_labels.get(k,'—')} |")

lines += [
    "\n---\n",
    "## Section 2: Greedy Selection Trace\n",
    f"**Seed:** `{seed}` (Sharpe={standalone[seed]:.4f})  \n",
    "| Step | Strategy Added | Sharpe Before | Sharpe After | delta | N | Corr |",
    "|---|---|---|---|---|---|---|",
]
for i, (strat, before, after, delta, n_sel, corr) in enumerate(trace):
    lines.append(f"| {i+1} | {strat} | {before:.4f} | {after:.4f} | {delta:+.4f} | {n_sel} | {corr:.3f} |")

lines += [
    "\n---\n",
    f"## Section 3: Final Portfolio ({len(selected)} strategies)\n",
    "### Per-Strategy Metrics\n",
    "| Strategy | Sharpe | CAGR | MaxDD |",
    "|---|---|---|---|",
]
for k in selected:
    r = ret_df[k]
    eq_k = (1 + r).cumprod() * 100_000
    lines.append(f"| {k} | {sharpe(r):.4f} | {cagr(eq_k)*100:.2f}% | {max_drawdown(eq_k)*100:.2f}% |")

lines += [
    "\n### Combined EW Portfolio\n",
    "| Metric | Value |",
    "|---|---|",
    f"| Sharpe  | {final_sh:.4f} |",
    f"| CAGR    | {final_cagr*100:.2f}% |",
    f"| MaxDD   | {final_dd*100:.2f}% |",
    f"| Sortino | {final_sortino:.4f} |",
    "\n---\n",
    "## Section 4: Rejected Strategies\n",
    "| Strategy | Standalone | delta if Added | Corr | Verdict |",
    "|---|---|---|---|---|",
]
for k in remaining:
    trial_sh = sharpe(ret_df[selected + [k]].mean(axis=1))
    delta = trial_sh - port_sh
    corr_k = ret_df[k].corr(port_rets)
    verdict = "Strongly hurts (>0.10)" if delta < -0.10 else f"Below threshold ({GREEDY_THRESHOLD})"
    lines.append(f"| {k} | {standalone[k]:.4f} | {delta:+.4f} | {corr_k:.3f} | {verdict} |")

lines += ["\n---\n", "## Section 5: Comparison to Existing Portfolio A\n"]
try:
    ex = pd.read_csv(EXISTING_PORTFOLIO, parse_dates=["date"], index_col="date")
    if "equity" not in ex.columns: ex.columns = ["equity"]
    ex_rets = ex["equity"].pct_change().dropna()
    cx = common.intersection(ex_rets.index)
    ex_c  = ex_rets.reindex(cx)
    new_c = port_rets.reindex(cx)
    eq_ex  = (1 + ex_c).cumprod() * 100_000
    eq_new = (1 + new_c).cumprod() * 100_000
    lines += [
        f"**Window:** {cx[0].date()} -> {cx[-1].date()}  \n",
        "| Metric | Existing A (5 strat) | Greedy v2 ({} strat) | delta |".format(len(selected)),
        "|---|---|---|---|",
    ]
    for mname, ev, nv in [
        ("Sharpe",  sharpe(ex_c),            sharpe(new_c)),
        ("CAGR",    cagr(eq_ex)*100,         cagr(eq_new)*100),
        ("MaxDD",   max_drawdown(eq_ex)*100,  max_drawdown(eq_new)*100),
        ("Sortino", sortino(ex_c),           sortino(new_c)),
    ]:
        lines.append(f"| {mname} | {ev:.4f} | {nv:.4f} | {nv-ev:+.4f} |")
    lines += [
        f"\n**Existing strategies:** EMA, VWAP Trend, ORB, Overnight, Intraday Mom  ",
        f"\n**Greedy v2 strategies:** {', '.join(selected)}  ",
    ]
except Exception as e:
    lines.append(f"Error: {e}")

with open(OUT_MD, "w") as f:
    f.write("\n".join(lines))
print(f"Report saved -> {OUT_MD}")
