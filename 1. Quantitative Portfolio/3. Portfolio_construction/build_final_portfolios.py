"""
build_final_portfolios.py
=========================
Builds the FINAL TWO portfolios (restructure 2026-07-10; previously 3 sleeves):

    SHORT-TERM : top-N along the greedy diversification path over the ONE merged
                 pool of all 9 short-term strategies (5 intraday session +
                 overnight + 3 daily). Overnight is a normal blended member —
                 the old "overnight additive" trick applied only to the retired
                 standalone intraday book.
    LONG-TERM  : unchanged method — top-9 along the greedy path over the
                 LT timing+selection pool.

    SHORT_TERM_N = 5   # judgment: greedy strict peak is 4 (Sharpe 6.44);
                       # the 5th (Congress_Quiver, 6.21) is kept per the
                       # 2026-07-10 plan (~5 sleeves, diversification story:
                       # 3 intraday + overnight + 1 daily... re-derived post-fee:
                       # ema, overnight, IBS, orb, Congress).
    LONGTERM_N   = 9   # unchanged (incl. bond_trend + yield_curve_duration,
                       # both 0/3 gates - kept as diversifiers)

Also reports a book-level 50/50 combined blend of the two finished portfolios
(reporting only, NOT a re-pool).

Reuses helpers from portfolio_analysis.py (no re-implementation).

Outputs (results/):
  final_portfolios.md
  short_term_portfolio_equity.csv, long_term_portfolio_equity.csv,
  combined_2book_equity.csv
"""
import os
import numpy as np
import pandas as pd

from portfolio_analysis import (
    ROOT, RESULTS, _first, load_returns, sharpe_m, stats_monthly, stats_daily,
    greedy_with_threshold, SHORT_TERM_CANDIDATES,
    EX_DAILY_LT_TREE, LT_TIMING, LT_SELECTION, lt_timing_paths, lt_selection_paths,
)

SHORT_TERM_N = 5
LONGTERM_N = 9
STARTING_CAPITAL = 100_000

def _load_dict(spec):
    out = {}
    for label, paths in spec.items():
        p = _first(*paths)
        if p is None:
            continue
        r = load_returns(p, monthly=True)
        if len(r) >= 24:
            out[label] = r
    return out

def ordered_selection(rets_dict, n):
    res = greedy_with_threshold(rets_dict, "sleeve", threshold=0.0)
    if res is None:
        return [], None
    order = [c for c, _ in res["path"]]
    return order[:n], res

# ═══════════════ SHORT-TERM portfolio (merged pool of 9) ═══════════════
st_rets = _load_dict(SHORT_TERM_CANDIDATES)
st_sel, st_res = ordered_selection(st_rets, SHORT_TERM_N)
st_R = st_res["R"]
st_port_m = st_R[st_sel].mean(axis=1).dropna()
st_stats = stats_monthly(st_port_m)
st_eq = (1 + st_port_m).cumprod() * STARTING_CAPITAL
st_eq.rename("equity").to_csv(os.path.join(RESULTS, "short_term_portfolio_equity.csv"), index_label="date")

# daily-frequency view of the same blend
st_daily = {}
for label in st_sel:
    p = _first(*SHORT_TERM_CANDIDATES[label])
    st_daily[label] = load_returns(p, monthly=False)
st_blend_d = pd.DataFrame(st_daily).dropna(how="all").fillna(0).mean(axis=1)
st_stats_d = stats_daily(st_blend_d)

# ═══════════════ LONG-TERM portfolio (unchanged method) ═══════════════
lt_rets = {}
for s in LT_TIMING:
    p = _first(*lt_timing_paths(s))
    if p:
        r = load_returns(p, monthly=True)
        if len(r) >= 24:
            lt_rets[s] = r
for s in LT_SELECTION:
    p = _first(*lt_selection_paths(s))
    if p:
        r = load_returns(p, monthly=True)
        if len(r) >= 24:
            lt_rets[s] = r
# ex-daily timing names (user decision 2026-07-10: LT pool members)
for s, paths in EX_DAILY_LT_TREE.items():
    p = _first(*paths)
    if p:
        r = load_returns(p, monthly=True)
        if len(r) >= 24:
            lt_rets[s] = r
lt_sel, lt_res = ordered_selection(lt_rets, LONGTERM_N)
lt_R = lt_res["R"]
lt_port_m = lt_R[lt_sel].mean(axis=1).dropna()
lt_stats = stats_monthly(lt_port_m)
lt_eq = (1 + lt_port_m).cumprod() * STARTING_CAPITAL
lt_eq.rename("equity").to_csv(os.path.join(RESULTS, "long_term_portfolio_equity.csv"), index_label="date")

# ═══════════════ COMBINED 2-book blend (reporting only, NOT a re-pool) ═══════════════
book_m = pd.DataFrame({
    "short_term": st_eq.resample("ME").last().pct_change(),
    "long_term":  lt_eq.resample("ME").last().pct_change(),
}).dropna()
comb_m = book_m.mean(axis=1)
comb_stats = stats_monthly(comb_m)
comb_eq = (1 + comb_m).cumprod() * STARTING_CAPITAL
comb_eq.rename("equity").to_csv(os.path.join(RESULTS, "combined_2book_equity.csv"), index_label="date")
book_corr = float(book_m.corr().iloc[0, 1])

# ═══════════════ report ═══════════════
def greedy_path_table(res, n):
    out = ["| Step | Added | Cumulative Sharpe |", "|---|---|---|"]
    for i, (c, s) in enumerate(res["path"]):
        tag = " <- selected stop" if i == n - 1 else (" (strict peak)" if i == res["peak_i"] and i != n - 1 else "")
        out.append(f"| {i+1} | {c} | {s:.3f}{tag} |")
    return "\n".join(out)

md = ["# Final Portfolios — 2-book structure (2026-07-10)", "",
      f"SHORT-TERM: evaluated **{len(st_rets)}** merged candidates, selected **{len(st_sel)}** "
      f"(top-{SHORT_TERM_N} on the greedy path; strict Sharpe peak was step {st_res['peak_i']+1}).  ",
      f"LONG-TERM: unchanged method, top-{LONGTERM_N} of {len(lt_rets)} candidates.",
      "",
      "## SHORT-TERM portfolio",
      "",
      f"Selected: **{', '.join(st_sel)}**",
      "",
      f"**Sharpe(m) {st_stats[0]} | Sharpe(d) {st_stats_d[0]} | CAGR {st_stats[1]}% | "
      f"MaxDD {st_stats[2]}%**  "
      f"(window {st_R.index[0].date()} -> {st_R.index[-1].date()}, {len(st_R)}m)",
      "",
      greedy_path_table(st_res, SHORT_TERM_N),
      "",
      "_Fees: intraday legs at $0.005/share slippage (2026-07-10 rerun); vwap_trend "
      "(slippage-0 canonical, cost-fragile) was evaluated in the pool and NOT selected._",
      "",
      "## LONG-TERM portfolio",
      "",
      f"Selected: **{', '.join(lt_sel)}**",
      "",
      f"**Sharpe(m) {lt_stats[0]} | CAGR {lt_stats[1]}% | MaxDD {lt_stats[2]}%**  "
      f"(window {lt_R.index[0].date()} -> {lt_R.index[-1].date()}, {len(lt_R)}m)",
      "",
      greedy_path_table(lt_res, LONGTERM_N),
      "",
      "_Note: LT includes bond_trend and yield_curve_duration, 0/3 on gates — kept "
      "deliberately as low-correlation diversifiers._",
      "",
      "## Combined 2-book blend (50/50, monthly rebalanced — reporting only)",
      "",
      f"**Sharpe(m) {comb_stats[0]} | CAGR {comb_stats[1]}% | MaxDD {comb_stats[2]}%**  "
      f"(common window {book_m.index[0].date()} -> {book_m.index[-1].date()}, {len(book_m)}m; "
      f"book correlation {book_corr:.2f})",
      "",
      "_Leverage caveat: never size the short-vol names (VIX_MR, VIX_ETN) aggressively — left-tail risk._",
      ""]

text = "\n".join(md)
with open(os.path.join(RESULTS, "final_portfolios.md"), "w", encoding="utf-8") as f:
    f.write(text)
print(text)
print(f"\nSaved -> {os.path.join(RESULTS, 'final_portfolios.md')}")
