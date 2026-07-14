"""
Portfolio B Impact Analysis
===========================
Tests each enhanced strategy as a 6th sleeve added to Portfolio B.
Baseline: 5 sleeves (IBS MR, Donchian, VIX MR, GTAA, Vol Overlay)
  Sharpe=1.87, CAGR=11.5%, MaxDD=-8.8%

For each new strategy:
  - Equal-weight 6-sleeve portfolio on common date window
  - Report: Sharpe, CAGR, MaxDD, Sortino, corr(new strat, existing portfolio)
  - Flag: Sharpe up/down, MaxDD stays below -15%?

Also test: all significant new strategies together.
"""

import os, json
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
LT   = os.path.dirname(BASE)

# ── BASELINE 5 SLEEVES ────────────────────────────────────────────────────────
SLEEVE_FILES = {
    "IBS MR":     (LT, "ibs_mean_reversion",  "results/ibs_mean_reversion_daily_equity/simple_bet_85pct_1x.csv"),
    "Donchian":   (LT, "donchian_channel",     "results/donchian_channel_daily_equity/simple_bet_85pct_1x.csv"),
    "VIX MR":     (LT, "vix_mean_reversion",   "results/vix_mean_reversion_daily_equity/simple_bet_85pct_1x.csv"),
    "GTAA":       (LT, "gtaa",                 "results/gtaa_daily_equity/simple_bet_85pct_1x.csv"),
    "Vol Overlay":(LT, "vol_overlay",          "results/vol_overlay_daily_equity/overlay_1p0x.csv"),
}

NEW_STRATEGY_FILES = {
    "Industry Trend v2":  (LT, "industry_trend",       "results/industry_trend_v2_daily_equity/industry_trend_v2_daily_equity.csv"),
    "Quality v2":         (LT, "quality_profitability", "results/quality_v2_daily_equity/quality_v2_daily_equity.csv"),
    "Low Vol v2":         (LT, "low_volatility",        "results/low_vol_v2_daily_equity/low_vol_v2_daily_equity.csv"),
    "Commodity Carry":    (LT, "commodity_carry",       "results/commodity_carry_daily_equity/commodity_carry_daily_equity.csv"),
    "Commodity Trend":    (LT, "commodity_trend",       "results/commodity_trend_daily_equity/commodity_trend_daily_equity.csv"),
}

# Significance flags (3/3 = include in "all significant" batch)
SIGNIFICANT = {
    "Industry Trend v2": True,
    "Quality v2":        True,
    "Low Vol v2":        True,
    "Commodity Carry":   True,    # 3/3 from previous run
    "Commodity Trend":   False,   # 2/3 from previous run
}

# ── HELPERS ───────────────────────────────────────────────────────────────────
def load_equity(base_dir, folder, relpath):
    """Load a daily equity CSV → Series indexed by date."""
    path = os.path.join(base_dir, folder, relpath)
    df   = pd.read_csv(path, index_col=0, parse_dates=True)
    # First column is equity
    s = df.iloc[:, 0].dropna()
    s.index = pd.to_datetime(s.index)
    return s.sort_index()

def daily_returns(equity):
    return equity.pct_change().dropna()

def portfolio_metrics(equity, rf=0.0):
    """Compute metrics from a daily equity series (rf=0 matches _backtest_utils)."""
    rets  = daily_returns(equity)
    days  = (equity.index[-1] - equity.index[0]).days
    years = days / 365.25

    # CAGR anchored at 100k start (first value after normalization)
    cagr     = (equity.iloc[-1] / equity.iloc[0]) ** (1/years) - 1
    sharpe   = rets.mean() / rets.std() * np.sqrt(252)   # rf=0, matches backtest_utils
    roll_max = equity.expanding().max()
    dd       = (equity - roll_max) / roll_max
    max_dd   = dd.min()
    # Sortino (rf=0 downside)
    down    = rets[rets < 0]
    sortino = rets.mean() / down.std() * np.sqrt(252) if len(down) > 0 else np.nan
    return {
        "cagr":    round(cagr * 100, 2),
        "sharpe":  round(sharpe, 4),
        "max_dd":  round(max_dd * 100, 2),
        "sortino": round(sortino, 4),
        "years":   round(years, 2),
    }

def equal_weight_portfolio(eq_dict):
    """Combine equity series dict into equal-weight portfolio on common dates."""
    df = pd.DataFrame(eq_dict)
    df = df.dropna()   # common date window
    # Normalize each sleeve to start at 1.0
    normed = df.divide(df.iloc[0])
    # Equal-weight average
    port = normed.mean(axis=1)
    # Scale to 100k
    port = port * 100_000
    return port, df.index[0], df.index[-1]

# ── LOAD BASELINE SLEEVES ─────────────────────────────────────────────────────
print("Loading baseline sleeves...")
baseline = {}
for name, (base_dir, folder, relpath) in SLEEVE_FILES.items():
    try:
        baseline[name] = load_equity(base_dir, folder, relpath)
        print(f"  {name}: {baseline[name].index[0].date()} -> {baseline[name].index[-1].date()}")
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

# Baseline portfolio
port_base, win_start, win_end = equal_weight_portfolio(baseline)
base_mets = portfolio_metrics(port_base)
print(f"\nBaseline (5 sleeves): {win_start.date()} -> {win_end.date()}")
print(f"  Sharpe={base_mets['sharpe']}, CAGR={base_mets['cagr']}%, MaxDD={base_mets['max_dd']}%")

# ── LOAD NEW STRATEGIES ───────────────────────────────────────────────────────
print("\nLoading new strategies...")
new_equities = {}
for name, (base_dir, folder, relpath) in NEW_STRATEGY_FILES.items():
    try:
        new_equities[name] = load_equity(base_dir, folder, relpath)
        s = new_equities[name]
        print(f"  {name}: {s.index[0].date()} -> {s.index[-1].date()}")
    except Exception as e:
        print(f"  {name}: ERROR - {e}")

# ── 6-SLEEVE TESTS ───────────────────────────────────────────────────────────
print("\n=== 6-SLEEVE IMPACT TESTS ===")
results = {}

for new_name, new_eq in new_equities.items():
    combined = {**baseline, new_name: new_eq}
    try:
        port6, s6, e6 = equal_weight_portfolio(combined)
        mets6 = portfolio_metrics(port6)

        # Correlation of new strategy vs baseline portfolio on common window
        base_on_window = port_base.reindex(port6.index, method='ffill')
        new_on_window  = new_eq.reindex(port6.index, method='ffill')
        corr_new_base  = daily_returns(new_on_window).corr(daily_returns(base_on_window))

        delta_sharpe = mets6['sharpe'] - base_mets['sharpe']
        delta_maxdd  = mets6['max_dd'] - base_mets['max_dd']
        verdict = ("✓ IMPROVES" if delta_sharpe > 0 else "✗ HURTS") + \
                  (" | MaxDD OK" if mets6['max_dd'] > -15 else " | MaxDD WARNING")

        results[new_name] = {
            "window": f"{s6.date()} → {e6.date()}",
            "window_years": round((e6 - s6).days / 365.25, 2),
            "n_sleeves": 6,
            "sharpe": mets6['sharpe'],
            "cagr": mets6['cagr'],
            "max_dd": mets6['max_dd'],
            "sortino": mets6['sortino'],
            "corr_with_portfolio": round(corr_new_base, 3),
            "vs_baseline": {
                "delta_sharpe": round(delta_sharpe, 4),
                "delta_maxdd":  round(delta_maxdd, 2),
                "verdict": verdict,
            },
            "significant": SIGNIFICANT.get(new_name, False),
        }
        sig_tag = "★ 3/3" if SIGNIFICANT.get(new_name) else "  2/3"
        print(f"\n  {new_name} [{sig_tag}] ({s6.date()} → {e6.date()}):")
        print(f"    Sharpe={mets6['sharpe']} (Δ{delta_sharpe:+.4f}), "
              f"CAGR={mets6['cagr']}%, MaxDD={mets6['max_dd']}%")
        print(f"    Sortino={mets6['sortino']}, Corr(new,portfolio)={corr_new_base:.3f}")
        print(f"    → {verdict}")
    except Exception as e:
        print(f"  {new_name}: ERROR - {e}")
        results[new_name] = {"error": str(e)}

# ── ALL-SIGNIFICANT BATCH TEST ────────────────────────────────────────────────
print("\n=== ALL SIGNIFICANT STRATEGIES BATCH ===")
sig_names = [n for n, s in SIGNIFICANT.items() if s]
sig_equities = {n: new_equities[n] for n in sig_names if n in new_equities}
all_sig = {**baseline, **sig_equities}
print(f"  Sleeves: {list(all_sig.keys())}")

try:
    port_all, s_all, e_all = equal_weight_portfolio(all_sig)
    mets_all = portfolio_metrics(port_all)
    n_all = len(all_sig)
    delta_sharpe_all = mets_all['sharpe'] - base_mets['sharpe']
    verdict_all = ("✓ IMPROVES" if delta_sharpe_all > 0 else "✗ HURTS") + \
                  (" | MaxDD OK" if mets_all['max_dd'] > -15 else " | MaxDD WARNING")
    print(f"  Window: {s_all.date()} → {e_all.date()}")
    print(f"  Sharpe={mets_all['sharpe']} (Δ{delta_sharpe_all:+.4f}), "
          f"CAGR={mets_all['cagr']}%, MaxDD={mets_all['max_dd']}%")
    print(f"  Sortino={mets_all['sortino']}")
    print(f"  → {verdict_all}")

    results["ALL_SIGNIFICANT_BATCH"] = {
        "sleeves": list(all_sig.keys()),
        "n_sleeves": n_all,
        "window": f"{s_all.date()} → {e_all.date()}",
        "window_years": round((e_all - s_all).days / 365.25, 2),
        "sharpe": mets_all['sharpe'],
        "cagr": mets_all['cagr'],
        "max_dd": mets_all['max_dd'],
        "sortino": mets_all['sortino'],
        "vs_baseline": {
            "delta_sharpe": round(delta_sharpe_all, 4),
            "delta_maxdd":  round(mets_all['max_dd'] - base_mets['max_dd'], 2),
            "verdict": verdict_all,
        }
    }
except Exception as e:
    print(f"  ERROR: {e}")
    results["ALL_SIGNIFICANT_BATCH"] = {"error": str(e)}

# ── SAVE JSON ─────────────────────────────────────────────────────────────────
output = {
    "baseline_5_sleeve": {
        "window": f"{win_start.date()} → {win_end.date()}",
        "sharpe": base_mets['sharpe'],
        "cagr":   base_mets['cagr'],
        "max_dd": base_mets['max_dd'],
        "sortino": base_mets['sortino'],
    },
    "new_strategy_tests": results,
}
json_path = os.path.join(BASE, "new_strategies_portfolio_impact.json")
with open(json_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved: {json_path}")

# ── SAVE MARKDOWN TABLE ───────────────────────────────────────────────────────
md_lines = [
    "# Portfolio B — New Strategy Impact Analysis",
    "",
    "## Baseline",
    f"**5 sleeves**: IBS MR, Donchian, VIX MR, GTAA, Vol Overlay",
    f"**Window**: {win_start.date()} → {win_end.date()} ({base_mets['years']} yrs)",
    f"**Sharpe**: {base_mets['sharpe']} | **CAGR**: {base_mets['cagr']}% | **MaxDD**: {base_mets['max_dd']}% | **Sortino**: {base_mets['sortino']}",
    "",
    "## 6-Sleeve Tests",
    "",
    "| Configuration | Sleeves | Window | Sharpe | CAGR | MaxDD | Sortino | Corr(new,port) | ΔSharpe | Verdict |",
    "|---|---|---|---|---|---|---|---|---|---|",
    f"| **Baseline** | 5 | {win_start.date()}→{win_end.date()} | **{base_mets['sharpe']}** | {base_mets['cagr']}% | {base_mets['max_dd']}% | {base_mets['sortino']} | — | — | — |",
]

for name, r in results.items():
    if name == "ALL_SIGNIFICANT_BATCH":
        continue
    if "error" in r:
        md_lines.append(f"| + {name} | 6 | ERROR | — | — | — | — | — | — | {r['error']} |")
        continue
    sig = "★" if r['significant'] else " "
    md_lines.append(
        f"| {sig} + {name} | 6 | {r['window']} | {r['sharpe']} | {r['cagr']}% | "
        f"{r['max_dd']}% | {r['sortino']} | {r['corr_with_portfolio']} | "
        f"{r['vs_baseline']['delta_sharpe']:+.4f} | {r['vs_baseline']['verdict']} |"
    )

# Batch row
if "ALL_SIGNIFICANT_BATCH" in results and "error" not in results["ALL_SIGNIFICANT_BATCH"]:
    r = results["ALL_SIGNIFICANT_BATCH"]
    md_lines += [
        "",
        "## Batch: All Significant Strategies Together",
        "",
        f"**{r['n_sleeves']} sleeves**: {', '.join(r['sleeves'])}",
        f"**Window**: {r['window']} ({r['window_years']} yrs)",
        "",
        "| Configuration | Sleeves | Window | Sharpe | CAGR | MaxDD | Sortino | ΔSharpe | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| **Baseline** | 5 | {win_start.date()}→{win_end.date()} | {base_mets['sharpe']} | {base_mets['cagr']}% | {base_mets['max_dd']}% | {base_mets['sortino']} | — | — |",
        f"| **All Significant** | {r['n_sleeves']} | {r['window']} | **{r['sharpe']}** | {r['cagr']}% | {r['max_dd']}% | {r['sortino']} | {r['vs_baseline']['delta_sharpe']:+.4f} | {r['vs_baseline']['verdict']} |",
    ]

md_lines += [
    "",
    "---",
    "★ = 3/3 significance tests passed",
    f"*Generated: {pd.Timestamp.now().date()}*",
]
md_path = os.path.join(BASE, "new_strategies_portfolio_impact.md")
with open(md_path, "w", encoding="utf-8") as fout:
    fout.write("\n".join(md_lines))
print("Saved: " + md_path)
print("Done.")
