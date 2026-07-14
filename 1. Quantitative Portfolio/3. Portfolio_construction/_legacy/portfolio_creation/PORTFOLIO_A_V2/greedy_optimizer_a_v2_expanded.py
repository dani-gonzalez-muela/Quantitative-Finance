"""
Greedy Forward Selection — Portfolio A v2 Expanded
Uses Phase 1 v2 multi-asset combined equities for ibs_mean_reversion and vix_mean_reversion.
Phase 3 v2 multi-asset equities included if available (requires intraday data download first).
All other strategies use original single-sleeve equity curves.
Daily Sharpe sqrt(252). Threshold: include unless delta < -0.05.
Saves: greedy_a_v2_expanded_results.md, portfolio_a_v2_expanded_equity.csv
"""
import os, sys, warnings
import numpy as np
import pandas as pd
from itertools import combinations
from datetime import datetime
warnings.filterwarnings("ignore")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..'))
ST   = os.path.join(ROOT, 'short_term')
LT   = os.path.join(ROOT, 'long_term')

# ── Candidate equity paths ────────────────────────────────────────────────────
# NOTE: v2 multi-asset versions take precedence over originals where available.
# Phase 3 v2 versions included only if combined_equity.csv exists (requires data download).
CANDIDATES = {
    # ── v2 multi-asset (daily strategies) ──
    'ibs_mean_reversion_v2':  os.path.join(ST, 'ibs_mean_reversion/results/ibs_mean_reversion_v2_multiasset_daily_equity/combined_equity.csv'),

    # ── v2 multi-asset (intraday) ──
    'ema_crossover_v2':       os.path.join(ST, 'ema_crossover/results/ema_crossover_v2_multiasset_daily_equity/combined_equity.csv'),
    'intraday_momentum_v2':   os.path.join(ST, 'intraday_momentum/results/intraday_momentum_v2_multiasset_daily_equity/combined_equity.csv'),
    'vwap_trend_v2':          os.path.join(ST, 'vwap_trend/results/vwap_trend_v2_multiasset_daily_equity/combined_equity.csv'),

    # ── Overnight v2 (v1-matching filter: enter only after down days) ──
    'overnight_v2':           os.path.join(ST, 'overnight/results/overnight_v2_multiasset_daily_equity/combined_equity.csv'),

    # ── VIX MR v1 (single-asset SVXY — basket framework does not apply) ──
    # NOTE: v2 basket test archived — strategy is inherently single-asset (SVXY).
    'vix_mean_reversion_v1':  os.path.join(ST, 'vix_mean_reversion/results/vix_mean_reversion_daily_equity/asset_vol_10pct_1x.csv'),

    # ── Original single-sleeve (fallback / additional candidates) ──
    'ema_crossover':          os.path.join(ST, 'ema_crossover/results/ema_crossover_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv'),
    'intraday_momentum':      os.path.join(ST, 'intraday_momentum/results/intraday_momentum_daily_equity/intraday_asset_vol_2pct_14d_1x_max.csv'),
    'orb':                    os.path.join(ST, 'orb/results/orb_daily_equity/risk-based_1pct_risk_1x_lev.csv'),
    'vwap_trend':             os.path.join(ST, 'vwap_trend/results/vwap_trend_daily_equity/vol_target_10pct_ann_1x_max_lev.csv'),
    'overnight':              os.path.join(ST, 'overnight/results/overnight_daily_equity/simple_85pct_bet.csv'),
    'congress_s3_quiver':     os.path.join(ST, 'congress_momentum/results/congress_momentum_quiver_open_daily_equity/quiver_open_10pct_1x.csv'),
    'ibs_mean_reversion':     os.path.join(ST, 'ibs_mean_reversion/results/ibs_mean_reversion_daily_equity/simple_bet_85pct_1x.csv'),
    'vix_mean_reversion':     os.path.join(ST, 'vix_mean_reversion/results/vix_mean_reversion_daily_equity/simple_bet_85pct_1x.csv'),
    'vix_etn_dual':           os.path.join(ST, 'vix_etn_dual/results/vix_etn_dual_daily_equity/evrp_boc_sizing_1p0x.csv'),
}

GREEDY_THRESHOLD = -0.05
OUT_MD   = os.path.join(SCRIPT_DIR, 'greedy_a_v2_expanded_results.md')
OUT_CSV  = os.path.join(SCRIPT_DIR, 'portfolio_a_v2_expanded_equity.csv')

# ── Metrics ───────────────────────────────────────────────────────────────────
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

def correlation(r1, r2):
    aligned = pd.concat([r1, r2], axis=1).dropna()
    if len(aligned) < 10: return np.nan
    return aligned.iloc[:, 0].corr(aligned.iloc[:, 1])

def load_equity(path):
    try:
        df = pd.read_csv(path, parse_dates=['date'], index_col='date')
        if 'equity' not in df.columns:
            df.columns = ['equity']
        return df['equity'].dropna()
    except Exception as e:
        return None

def portfolio_metrics(equities):
    """EW combination of equity curves → returns metrics dict."""
    rets = pd.DataFrame({name: eq.pct_change() for name, eq in equities.items()}).dropna(how='all').fillna(0)
    port_ret = rets.mean(axis=1)
    port_eq = (1 + port_ret).cumprod() * 100_000
    sh = sharpe(port_ret)
    return {
        'sharpe': sh,
        'cagr': cagr(port_eq),
        'max_dd': max_drawdown(port_eq),
        'sortino': sortino(port_ret),
        'n_days': len(port_ret),
        'equity': port_eq,
        'returns': port_ret,
    }

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Load all available equity curves
    loaded = {}
    missing = []
    for name, path in CANDIDATES.items():
        eq = load_equity(path)
        if eq is not None and len(eq) > 252:
            loaded[name] = eq
            print(f"  ✓ {name}: {len(eq)} days | Sharpe={sharpe(eq.pct_change().dropna()):.4f}")
        else:
            missing.append(name)
            print(f"  ✗ {name}: not found (skip)")

    if not loaded:
        print("ERROR: no equity curves loaded"); sys.exit(1)

    # Align to common window
    all_rets = pd.DataFrame({n: eq.pct_change() for n, eq in loaded.items()}).dropna(how='all')
    # Common window: first date where all loaded curves have data
    first_dates = {n: eq.index.min() for n, eq in loaded.items()}
    last_dates  = {n: eq.index.max() for n, eq in loaded.items()}
    common_start = max(first_dates.values())
    common_end   = min(last_dates.values())
    print(f"\nCommon window: {common_start.date()} → {common_end.date()}")

    equities_aligned = {}
    for name, eq in loaded.items():
        eq_trim = eq.loc[common_start:common_end]
        if len(eq_trim) > 100:
            equities_aligned[name] = eq_trim
        else:
            print(f"  WARNING: {name} too short after alignment, dropping")

    # Standalone Sharpe for each candidate
    print("\n── Standalone Sharpe (common window) ──")
    standalone = {}
    for name, eq in equities_aligned.items():
        r = eq.pct_change().dropna()
        sh = sharpe(r); ts = tstat(sh, len(r))
        standalone[name] = {'sharpe': sh, 'tstat': ts, 'n': len(r)}
        print(f"  {name}: Sharpe={sh:.4f} t={ts:.2f}")

    standalone_sorted = sorted(standalone.items(), key=lambda x: x[1]['sharpe'], reverse=True)

    # Greedy forward selection
    print("\n── Greedy Selection ──")
    seed = standalone_sorted[0][0]
    selected = {seed: equities_aligned[seed]}
    port_sh = portfolio_metrics(selected)['sharpe']
    print(f"Seed: {seed} (Sharpe={port_sh:.4f})")

    greedy_trace = []
    rejected = {}

    candidates_remaining = [n for n in equities_aligned if n != seed]
    while candidates_remaining:
        best_delta = -np.inf
        best_name = None
        best_sh = None
        for name in candidates_remaining:
            trial = {**selected, name: equities_aligned[name]}
            new_sh = portfolio_metrics(trial)['sharpe']
            delta = new_sh - port_sh
            if delta > best_delta:
                best_delta = delta; best_name = name; best_sh = new_sh

        if best_delta < GREEDY_THRESHOLD:
            # Try all remaining candidates; stop if none passes
            rejected_here = {}
            for name in candidates_remaining:
                trial = {**selected, name: equities_aligned[name]}
                new_sh = portfolio_metrics(trial)['sharpe']
                delta = new_sh - port_sh
                corr = correlation(
                    pd.concat([equities_aligned[n].pct_change() for n in selected], axis=1).mean(axis=1),
                    equities_aligned[name].pct_change()
                )
                rejected_here[name] = {'delta': delta, 'standalone': standalone[name]['sharpe'], 'corr': corr}
            rejected.update(rejected_here)
            break

        corr = correlation(
            pd.concat([equities_aligned[n].pct_change() for n in selected], axis=1).mean(axis=1),
            equities_aligned[best_name].pct_change()
        )
        greedy_trace.append({
            'step': len(greedy_trace) + 1,
            'added': best_name,
            'sharpe_before': port_sh,
            'sharpe_after': best_sh,
            'delta': best_delta,
            'n': len(selected) + 1,
            'corr': corr,
        })
        selected[best_name] = equities_aligned[best_name]
        port_sh = best_sh
        candidates_remaining.remove(best_name)
        print(f"  Step {len(greedy_trace)}: +{best_name} → Sharpe={best_sh:.4f} (Δ={best_delta:+.4f}) corr={corr:.3f}")

    # Update rejected with any remaining candidates
    for name in candidates_remaining:
        if name not in rejected:
            trial = {**selected, name: equities_aligned[name]}
            new_sh = portfolio_metrics(trial)['sharpe']
            delta = new_sh - port_sh
            corr = correlation(
                pd.concat([equities_aligned[n].pct_change() for n in selected], axis=1).mean(axis=1),
                equities_aligned[name].pct_change()
            )
            rejected[name] = {'delta': delta, 'standalone': standalone[name]['sharpe'], 'corr': corr}

    # Final portfolio metrics
    final = portfolio_metrics(selected)
    print(f"\nFinal Portfolio ({len(selected)} strategies): Sharpe={final['sharpe']:.4f} CAGR={final['cagr']:.2%} MaxDD={final['max_dd']:.2%}")

    # Save equity
    final_eq = final['equity'].reset_index()
    final_eq.columns = ['date', 'equity']
    final_eq.to_csv(OUT_CSV, index=False)
    print(f"Saved: {OUT_CSV}")

    # ── Comparison to old Portfolio A ──────────────────────────────────────────
    old_pa_path = os.path.join(SCRIPT_DIR, '..', 'short_term_analysis', 'portfolio_a_v2_selected_returns.csv')
    old_comparison = {}
    if os.path.exists(old_pa_path):
        old_rets = pd.read_csv(old_pa_path, parse_dates=['date'], index_col='date')
        old_rets_aligned = old_rets.loc[common_start:common_end]
        if not old_rets_aligned.empty:
            old_port = old_rets_aligned.mean(axis=1)
            old_eq = (1 + old_port).cumprod() * 100_000
            old_comparison = {
                'sharpe': sharpe(old_port),
                'cagr': cagr(old_eq),
                'max_dd': max_drawdown(old_eq),
                'sortino': sortino(old_port),
            }

    # ── Write markdown results ─────────────────────────────────────────────────
    now = datetime.now().strftime('%Y-%m-%d')
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write(f"# Greedy Forward Selection — Portfolio A v2 Expanded\n\n")
        f.write(f"**Analysis date:** {now}  \n")
        f.write(f"**Common window:** {common_start.date()} → {common_end.date()} ({len(final['returns'])} trading days)  \n")
        f.write(f"**Threshold:** delta >= {GREEDY_THRESHOLD}  \n")
        f.write(f"**New in v2 expanded:** Phase 1 multi-asset (IBS v2, VIX MR v2) + Phase 3 multi-asset if data available  \n\n")
        f.write("---\n\n")

        f.write("## Section 1: All Candidates — Standalone Sharpe\n\n")
        f.write("| Strategy | Sharpe | t-stat | N days | Available |\n")
        f.write("|---|---|---|---|---|\n")
        for name, m in standalone_sorted:
            avail = "✓" if name in equities_aligned else "✗"
            f.write(f"| {name} | {m['sharpe']:.4f} | {m['tstat']:.2f} | {m['n']} | {avail} |\n")
        if missing:
            for name in missing:
                f.write(f"| {name} | — | — | — | ✗ (file missing) |\n")
        f.write("\n---\n\n")

        f.write("## Section 2: Greedy Selection Trace\n\n")
        f.write(f"**Seed:** `{seed}` (Sharpe={standalone[seed]['sharpe']:.4f})  \n\n")
        f.write("| Step | Strategy Added | Sharpe Before | Sharpe After | delta | N | Corr |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for t in greedy_trace:
            f.write(f"| {t['step']} | {t['added']} | {t['sharpe_before']:.4f} | {t['sharpe_after']:.4f} | {t['delta']:+.4f} | {t['n']} | {t['corr']:.3f} |\n")
        f.write("\n---\n\n")

        f.write("## Section 3: Final Portfolio\n\n")
        f.write(f"### Strategies ({len(selected)})\n\n")
        f.write("| Strategy | Sharpe | CAGR | MaxDD |\n")
        f.write("|---|---|---|---|\n")
        for name, eq in selected.items():
            r = eq.pct_change().dropna()
            sh = sharpe(r); ca = cagr(eq); dd = max_drawdown(eq)
            f.write(f"| {name} | {sh:.4f} | {ca:.2%} | {dd:.2%} |\n")
        f.write("\n### Combined EW Portfolio\n\n")
        f.write("| Metric | Value |\n|---|---|\n")
        f.write(f"| Sharpe  | {final['sharpe']:.4f} |\n")
        f.write(f"| CAGR    | {final['cagr']:.2%} |\n")
        f.write(f"| MaxDD   | {final['max_dd']:.2%} |\n")
        f.write(f"| Sortino | {final['sortino']:.4f} |\n")
        f.write("\n---\n\n")

        f.write("## Section 4: Rejected Strategies\n\n")
        f.write("| Strategy | Standalone | delta if Added | Corr | Verdict |\n")
        f.write("|---|---|---|---|---|\n")
        for name, r in sorted(rejected.items(), key=lambda x: x[1]['delta'], reverse=True):
            sa = standalone.get(name, {}).get('sharpe', float('nan'))
            verdict = "Hurts (>0.10)" if r['delta'] < -0.10 else f"Below threshold ({GREEDY_THRESHOLD})"
            f.write(f"| {name} | {sa:.4f} | {r['delta']:+.4f} | {r['corr']:.3f} | {verdict} |\n")
        f.write("\n---\n\n")

        if old_comparison:
            f.write("## Section 5: Comparison\n\n")
            f.write("| Metric | Old Portfolio A (greedy_a_v2) | New v2 Expanded | delta |\n")
            f.write("|---|---|---|---|\n")
            f.write(f"| Sharpe  | {old_comparison['sharpe']:.4f} | {final['sharpe']:.4f} | {final['sharpe']-old_comparison['sharpe']:+.4f} |\n")
            f.write(f"| CAGR    | {old_comparison['cagr']:.2%} | {final['cagr']:.2%} | {final['cagr']-old_comparison['cagr']:+.2%} |\n")
            f.write(f"| MaxDD   | {old_comparison['max_dd']:.2%} | {final['max_dd']:.2%} | {final['max_dd']-old_comparison['max_dd']:+.2%} |\n")
            f.write(f"| Sortino | {old_comparison['sortino']:.4f} | {final['sortino']:.4f} | {final['sortino']-old_comparison['sortino']:+.4f} |\n")
            f.write(f"\n**Old strategies:** {', '.join(old_rets.columns.tolist())}  \n")
            f.write(f"**New strategies:** {', '.join(selected.keys())}  \n")

    print(f"Saved: {OUT_MD}")

if __name__ == '__main__':
    main()
