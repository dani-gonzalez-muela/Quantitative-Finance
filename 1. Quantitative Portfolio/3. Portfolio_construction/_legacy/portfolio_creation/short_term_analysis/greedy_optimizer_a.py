"""
Greedy Forward Selection Optimizer — Portfolio A (Short-Term Strategies)
Generates:
  - greedy_a_results.md
  - portfolio_a_selected_returns.csv
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
from itertools import combinations

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# BASE should be algo_trading parent, let's build from script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# SCRIPT_DIR = .../algo_trading/portfolio_creation/short_term_analysis
ALGO = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # algo_trading/
ST   = os.path.join(ALGO, "short_term")
LT   = os.path.join(ALGO, "long_term")

CANDIDATES = {
    "ema_crossover":      os.path.join(ST, "ema_crossover/results/ema_crossover_daily_equity/simple_85pct_bet.csv"),
    "intraday_momentum":  os.path.join(ST, "intraday_momentum/results/intraday_momentum_daily_equity/simple_85pct_bet.csv"),
    "orb":                os.path.join(ST, "orb/results/orb_daily_equity/simple_85pct_bet.csv"),
    "overnight":          os.path.join(ST, "overnight/results/overnight_daily_equity/simple_85pct_bet.csv"),
    "vwap_trend":         os.path.join(ST, "vwap_trend/results/vwap_trend_daily_equity/simple_85pct_bet.csv"),
    "congress_s3_quiver": os.path.join(ST, "congress_momentum/results/congress_momentum_quiver_open_daily_equity/quiver_open_10pct_1x.csv"),
    "ibs_mean_reversion": os.path.join(LT, "ibs_mean_reversion/results/ibs_mean_reversion_daily_equity/simple_bet_85pct_1x.csv"),
    "vix_mean_reversion": os.path.join(LT, "vix_mean_reversion/results/vix_mean_reversion_daily_equity/simple_bet_85pct_1x.csv"),
    "vix_etn_dual":       os.path.join(LT, "vix_etn_dual/results/vix_etn_dual_daily_equity/evrp_boc_sizing_1p0x.csv"),
    "turn_of_month":      os.path.join(LT, "turn_of_month/results/turn_of_month_daily_equity/turn_of_month_daily_equity.csv"),
    "overnight_premium":  os.path.join(LT, "overnight_premium/results/overnight_premium_daily_equity/overnight_premium_daily_equity.csv"),
}

EXISTING_PORTFOLIO = os.path.join(SCRIPT_DIR, "portfolio_a_1.0x.csv")
OUT_MD   = os.path.join(SCRIPT_DIR, "greedy_a_results.md")
OUT_CSV  = os.path.join(SCRIPT_DIR, "portfolio_a_selected_returns.csv")

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def sharpe(returns: pd.Series) -> float:
    m, s = returns.mean(), returns.std()
    if s == 0 or np.isnan(s):
        return np.nan
    return m / s * np.sqrt(252)

def tstat(sh: float, n: int) -> float:
    return sh * np.sqrt(n / 252)

def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return np.nan
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return dd.min()

def sortino(returns: pd.Series) -> float:
    downside = returns[returns < 0].std()
    if downside == 0 or np.isnan(downside):
        return np.nan
    return returns.mean() / downside * np.sqrt(252)

def ew_portfolio_returns(returns_df: pd.DataFrame) -> pd.Series:
    return returns_df.mean(axis=1)

def load_equity(path: str) -> pd.Series | None:
    """Load CSV with date,equity columns → equity series with DatetimeIndex."""
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date")
        if "equity" not in df.columns:
            # try first numeric column
            df.columns = ["equity"]
        eq = df["equity"].dropna().sort_index()
        if len(eq) < 100:
            print(f"  WARNING: {path} has only {len(eq)} rows — skipping")
            return None
        return eq
    except Exception as e:
        print(f"  WARNING: Could not load {path}: {e}")
        return None

# ─────────────────────────────────────────────
# Step 1: Load all equity curves → daily returns
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 1: Loading equity curves")
print("="*60)

returns_raw = {}
date_ranges = {}
skipped = {}

for name, path in CANDIDATES.items():
    if not os.path.exists(path):
        # Try fallback: list available CSVs in same directory
        d = os.path.dirname(path)
        if os.path.isdir(d):
            csvs = sorted([f for f in os.listdir(d) if f.endswith(".csv")])
            if csvs:
                path = os.path.join(d, csvs[0])
                print(f"  FALLBACK {name}: using {csvs[0]}")
            else:
                print(f"  SKIP {name}: no CSVs in {d}")
                skipped[name] = "path not found"
                continue
        else:
            print(f"  SKIP {name}: directory missing: {d}")
            skipped[name] = "directory missing"
            continue

    eq = load_equity(path)
    if eq is None:
        skipped[name] = "load failed / too short"
        continue

    ret = eq.pct_change().dropna()
    returns_raw[name] = ret
    date_ranges[name] = (ret.index[0].date(), ret.index[-1].date(), len(ret))
    print(f"  OK  {name:<25} {ret.index[0].date()} → {ret.index[-1].date()}  ({len(ret)} days)")

# Align to common date range (inner join)
if len(returns_raw) < 2:
    print("ERROR: fewer than 2 strategies loaded. Cannot proceed.")
    sys.exit(1)

all_returns = pd.DataFrame(returns_raw)
all_returns = all_returns.dropna(how="all")

# Use inner join dates (all strategies present)
aligned = all_returns.dropna(how="any")
print(f"\nCommon date range (inner join): {aligned.index[0].date()} → {aligned.index[-1].date()}  ({len(aligned)} days)")
print(f"Strategies loaded: {list(aligned.columns)}")

# ─────────────────────────────────────────────
# Step 2: Standalone Sharpe ranking
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 2: Standalone Sharpe ranking (on aligned period)")
print("="*60)

SHARPE_MIN = 0.40
TSTAT_MIN  = 1.5

standalone = []
for name in aligned.columns:
    r = aligned[name]
    sh = sharpe(r)
    ts = tstat(sh, len(r))
    passes = (sh >= SHARPE_MIN) and (ts >= TSTAT_MIN)
    standalone.append({
        "strategy": name,
        "sharpe": sh,
        "tstat": ts,
        "passes": passes,
    })

standalone_df = pd.DataFrame(standalone).sort_values("sharpe", ascending=False).reset_index(drop=True)
print(standalone_df.to_string(index=False))

candidates_filtered = standalone_df[standalone_df["passes"]]["strategy"].tolist()
print(f"\nPassed filter (Sharpe≥{SHARPE_MIN}, t-stat≥{TSTAT_MIN}): {candidates_filtered}")

if not candidates_filtered:
    print("ERROR: No strategies passed the significance filter.")
    sys.exit(1)

# ─────────────────────────────────────────────
# Step 3: Greedy forward selection
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 3: Greedy forward selection")
print("="*60)

IMPROVEMENT_THRESHOLD = 0.02

# Seed: strategy with highest standalone Sharpe among filtered
seed = candidates_filtered[0]
selected = [seed]
remaining = [s for s in candidates_filtered if s != seed]

portfolio_ret = aligned[seed].copy()
current_sharpe = sharpe(portfolio_ret)

greedy_trace = []
print(f"\nSeed: {seed}  (Sharpe = {current_sharpe:.4f})")

# Track rejections for non-selected with reason
greedy_rejected = {}

while remaining:
    best_strategy = None
    best_sharpe = current_sharpe
    best_delta = 0.0
    best_corr = np.nan

    for candidate in remaining:
        trial_ret = ew_portfolio_returns(aligned[selected + [candidate]])
        trial_sharpe = sharpe(trial_ret)
        delta = trial_sharpe - current_sharpe

        if delta > best_delta:
            best_delta = delta
            best_sharpe = trial_sharpe
            best_strategy = candidate
            # correlation of candidate with current EW portfolio
            best_corr = aligned[candidate].corr(portfolio_ret)

    if best_strategy is None or best_delta < IMPROVEMENT_THRESHOLD:
        # No improvement above threshold
        for s in remaining:
            trial_ret = ew_portfolio_returns(aligned[selected + [s]])
            d = sharpe(trial_ret) - current_sharpe
            greedy_rejected[s] = f"failed greedy threshold (Δ={d:.4f} < {IMPROVEMENT_THRESHOLD})"
        break

    # Accept
    greedy_trace.append({
        "step": len(selected),
        "strategy_added": best_strategy,
        "sharpe_before": current_sharpe,
        "sharpe_after": best_sharpe,
        "delta": best_delta,
        "n_sleeves": len(selected) + 1,
        "corr_with_portfolio": best_corr,
    })

    print(f"  Step {len(selected)}: Add {best_strategy}  Sharpe {current_sharpe:.4f} → {best_sharpe:.4f}  Δ={best_delta:.4f}  corr={best_corr:.3f}")

    selected.append(best_strategy)
    portfolio_ret = ew_portfolio_returns(aligned[selected])
    current_sharpe = best_sharpe
    remaining.remove(best_strategy)

# Strategies that failed filter
for _, row in standalone_df[~standalone_df["passes"]].iterrows():
    skipped[row["strategy"]] = f"failed significance filter (Sharpe={row['sharpe']:.3f}, t-stat={row['tstat']:.3f})"

print(f"\nFinal selected portfolio: {selected}")

# ─────────────────────────────────────────────
# Step 4: Compute final portfolio metrics
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("STEP 4: Computing final metrics")
print("="*60)

final_ret = ew_portfolio_returns(aligned[selected])
final_equity = (1 + final_ret).cumprod() * 100000

final_metrics = {
    "sharpe":  sharpe(final_ret),
    "cagr":    cagr(final_equity),
    "max_dd":  max_drawdown(final_equity),
    "sortino": sortino(final_ret),
}

print(f"Portfolio Sharpe:  {final_metrics['sharpe']:.4f}")
print(f"Portfolio CAGR:    {final_metrics['cagr']*100:.2f}%")
print(f"Portfolio MaxDD:   {final_metrics['max_dd']*100:.2f}%")
print(f"Portfolio Sortino: {final_metrics['sortino']:.4f}")

# Per-strategy metrics
strategy_metrics = []
for name in selected:
    r = aligned[name]
    eq = (1 + r).cumprod() * 100000
    strategy_metrics.append({
        "strategy": name,
        "sharpe": sharpe(r),
        "cagr": cagr(eq),
        "max_dd": max_drawdown(eq),
    })

strat_df = pd.DataFrame(strategy_metrics)

# Correlation matrix of selected
corr_matrix = aligned[selected].corr()

# ─────────────────────────────────────────────
# Step 5: Compare to existing Portfolio A
# ─────────────────────────────────────────────
existing_comparison = None
if os.path.exists(EXISTING_PORTFOLIO):
    try:
        ex_eq = load_equity(EXISTING_PORTFOLIO)
        if ex_eq is not None:
            ex_ret = ex_eq.pct_change().dropna()
            # align to same period as greedy result
            common_idx = aligned.index.intersection(ex_ret.index)
            ex_ret_aligned = ex_ret.loc[common_idx]
            gr_ret_aligned = final_ret.loc[common_idx]
            ex_equity = (1 + ex_ret_aligned).cumprod() * 100000
            gr_equity = (1 + gr_ret_aligned).cumprod() * 100000
            existing_comparison = {
                "existing": {
                    "sharpe":  sharpe(ex_ret_aligned),
                    "cagr":    cagr(ex_equity),
                    "max_dd":  max_drawdown(ex_equity),
                    "sortino": sortino(ex_ret_aligned),
                },
                "greedy": {
                    "sharpe":  sharpe(gr_ret_aligned),
                    "cagr":    cagr(gr_equity),
                    "max_dd":  max_drawdown(gr_equity),
                    "sortino": sortino(gr_ret_aligned),
                },
                "period": f"{common_idx[0].date()} → {common_idx[-1].date()}",
            }
            print(f"\nExisting portfolio loaded ({len(common_idx)} common days)")
    except Exception as e:
        print(f"  WARNING: Could not load existing portfolio: {e}")

# ─────────────────────────────────────────────
# Save portfolio_a_selected_returns.csv
# ─────────────────────────────────────────────
aligned[selected].to_csv(OUT_CSV)
print(f"\nSaved returns CSV: {OUT_CSV}")

# ─────────────────────────────────────────────
# Write greedy_a_results.md
# ─────────────────────────────────────────────
def fmt_pct(v):
    return f"{v*100:.2f}%"

def fmt_f(v, decimals=4):
    return f"{v:.{decimals}f}"

lines = []

lines.append("# Greedy Forward Selection — Portfolio A (Short-Term Strategies)\n")
lines.append(f"**Analysis date:** {pd.Timestamp.today().date()}  ")
lines.append(f"**Common date range (inner join):** {aligned.index[0].date()} → {aligned.index[-1].date()} ({len(aligned)} trading days)  ")
lines.append(f"**Significance filter:** Sharpe ≥ {SHARPE_MIN} AND t-stat ≥ {TSTAT_MIN}  ")
lines.append(f"**Greedy improvement threshold:** Δ Sharpe ≥ {IMPROVEMENT_THRESHOLD}  ")
lines.append("")

# ── Section 1: Standalone Sharpe
lines.append("---\n")
lines.append("## Section 1: All Candidates — Standalone Sharpe\n")
lines.append("| Strategy | Sharpe | t-stat | Filter |")
lines.append("|---|---|---|---|")
for _, row in standalone_df.iterrows():
    flag = "✅ PASS" if row["passes"] else "❌ FAIL"
    lines.append(f"| {row['strategy']} | {fmt_f(row['sharpe'])} | {fmt_f(row['tstat'])} | {flag} |")
lines.append("")

# Skipped strategies (path not found)
if skipped:
    lines.append("**Strategies skipped (path/load error):**\n")
    for name, reason in skipped.items():
        if "filter" not in reason and "greedy" not in reason:
            lines.append(f"- `{name}`: {reason}")
    lines.append("")

# ── Section 2: Greedy Selection Trace
lines.append("---\n")
lines.append("## Section 2: Greedy Selection Trace\n")
lines.append(f"**Seed strategy:** `{seed}` (highest standalone Sharpe among filtered candidates)  ")
lines.append("")
if greedy_trace:
    lines.append("| Step | Strategy Added | Sharpe Before | Sharpe After | Δ Sharpe | N Sleeves | Corr w/ Portfolio |")
    lines.append("|---|---|---|---|---|---|---|")
    for t in greedy_trace:
        lines.append(
            f"| {t['step']} | {t['strategy_added']} | {fmt_f(t['sharpe_before'])} | "
            f"{fmt_f(t['sharpe_after'])} | {fmt_f(t['delta'])} | {t['n_sleeves']} | {fmt_f(t['corr_with_portfolio'], 3)} |"
        )
else:
    lines.append("*No additional strategies passed the improvement threshold — seed only.*\n")
lines.append("")
lines.append(f"**Greedy stopped:** no remaining strategy improved Sharpe by ≥ {IMPROVEMENT_THRESHOLD}\n")
lines.append("")

# ── Section 3: Final Portfolio A
lines.append("---\n")
lines.append("## Section 3: Final Portfolio A\n")
lines.append(f"**Selected strategies ({len(selected)}):** {', '.join(f'`{s}`' for s in selected)}\n")

lines.append("### Per-Strategy Metrics (on aligned period)\n")
lines.append("| Strategy | Sharpe | CAGR | MaxDD |")
lines.append("|---|---|---|---|")
for row in strategy_metrics:
    lines.append(f"| {row['strategy']} | {fmt_f(row['sharpe'])} | {fmt_pct(row['cagr'])} | {fmt_pct(row['max_dd'])} |")
lines.append("")

lines.append("### Combined EW Portfolio Metrics\n")
lines.append("| Metric | Value |")
lines.append("|---|---|")
lines.append(f"| Sharpe  | {fmt_f(final_metrics['sharpe'])} |")
lines.append(f"| CAGR    | {fmt_pct(final_metrics['cagr'])} |")
lines.append(f"| MaxDD   | {fmt_pct(final_metrics['max_dd'])} |")
lines.append(f"| Sortino | {fmt_f(final_metrics['sortino'])} |")
lines.append("")

lines.append("### Correlation Matrix (Selected Strategies)\n")
corr_header = "| Strategy | " + " | ".join(selected) + " |"
corr_sep    = "|---|" + "---|" * len(selected)
lines.append(corr_header)
lines.append(corr_sep)
for s in selected:
    row_vals = " | ".join(fmt_f(corr_matrix.loc[s, c], 3) for c in selected)
    lines.append(f"| {s} | {row_vals} |")
lines.append("")

# ── Section 4: Not Selected
lines.append("---\n")
lines.append("## Section 4: Strategies Not Selected\n")
lines.append("| Strategy | Reason |")
lines.append("|---|---|")

not_selected_reasons = {}
# Strategies that failed filter
for _, row in standalone_df[~standalone_df["passes"]].iterrows():
    not_selected_reasons[row["strategy"]] = f"Failed significance filter (Sharpe={row['sharpe']:.3f}, t-stat={row['tstat']:.3f})"
# Strategies that failed greedy threshold
for s, reason in greedy_rejected.items():
    not_selected_reasons[s] = reason.capitalize()
# Strategies that failed to load
for s, reason in skipped.items():
    if s not in not_selected_reasons:
        not_selected_reasons[s] = f"Load/path error: {reason}"

for s, reason in not_selected_reasons.items():
    lines.append(f"| {s} | {reason} |")
lines.append("")

# ── Section 5: Comparison to Existing Portfolio A
lines.append("---\n")
lines.append("## Section 5: Comparison to Existing Portfolio A\n")
if existing_comparison is None:
    lines.append("*`portfolio_a_1.0x.csv` not found or could not be loaded — comparison skipped.*\n")
else:
    e = existing_comparison["existing"]
    g = existing_comparison["greedy"]
    period = existing_comparison["period"]
    lines.append(f"**Comparison period (common dates):** {period}  ")
    lines.append("")
    lines.append("| Metric | Existing Portfolio A | Greedy Portfolio A | Δ |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Sharpe  | {fmt_f(e['sharpe'])} | {fmt_f(g['sharpe'])} | {fmt_f(g['sharpe']-e['sharpe'])} |")
    lines.append(f"| CAGR    | {fmt_pct(e['cagr'])} | {fmt_pct(g['cagr'])} | {fmt_pct(g['cagr']-e['cagr'])} |")
    lines.append(f"| MaxDD   | {fmt_pct(e['max_dd'])} | {fmt_pct(g['max_dd'])} | {fmt_pct(g['max_dd']-e['max_dd'])} |")
    lines.append(f"| Sortino | {fmt_f(e['sortino'])} | {fmt_f(g['sortino'])} | {fmt_f(g['sortino']-e['sortino'])} |")
    lines.append("")
    lines.append(f"**Existing Portfolio A strategies:** see `portfolio_a_1.0x.csv` equity curve  ")
    lines.append(f"**Greedy Portfolio A strategies:** {', '.join(f'`{s}`' for s in selected)}  ")
lines.append("")

md_content = "\n".join(lines)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"Saved report: {OUT_MD}")
print("\nDone.")
