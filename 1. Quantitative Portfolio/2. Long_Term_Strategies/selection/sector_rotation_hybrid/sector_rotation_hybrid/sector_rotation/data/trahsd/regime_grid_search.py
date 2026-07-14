"""
Sector Rotation - Grid Search
==============================
Tests all combinations of:
  - Top N sectors (2, 3, 4, 5, 6)
  - Similarity quantile (10%, 15%, 20%)
  - Long-only vs Long-short
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ── assumes these are already in memory from previous cells ──────────────────
# scores, industries, industries_al, sp500_returns, common_idx
# sharpe(), ann_return(), max_drawdown() functions


# ──────────────────────────────────────────────────────────────────────────────
# 1. Recompute expected returns for different similarity quantiles
# ──────────────────────────────────────────────────────────────────────────────

def compute_sector_expected(scores: pd.DataFrame,
                             industries: pd.DataFrame,
                             quantile: float = 0.20) -> pd.DataFrame:
    """Compute expected sector returns for a given similarity quantile."""
    expected = {}
    for sector in industries.columns:
        sect_ret = industries[sector]
        exp_ret  = {}
        for t in scores.index:
            row = scores.loc[t].dropna()
            row = row[row > 0]
            if len(row) < 10:
                exp_ret[t] = np.nan
                continue
            threshold     = row.quantile(quantile)
            similar_dates = row[row <= threshold].index
            future_rets   = []
            for d in similar_dates:
                future = sect_ret[sect_ret.index > d]
                if len(future) > 0:
                    future_rets.append(future.iloc[0])
            exp_ret[t] = np.mean(future_rets) if future_rets else np.nan
        expected[sector] = pd.Series(exp_ret)
    return pd.DataFrame(expected)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Weight construction functions
# ──────────────────────────────────────────────────────────────────────────────

def long_only_weights(expected_row: pd.Series, top_n: int) -> pd.Series:
    """Hold top N sectors equally weighted."""
    valid = expected_row.dropna()
    if len(valid) == 0:
        return pd.Series(1/len(expected_row), index=expected_row.index)
    weights = pd.Series(0.0, index=expected_row.index)
    weights[valid.nlargest(top_n).index] = 1.0 / top_n
    return weights


def long_short_weights(expected_row: pd.Series,
                        top_n: int,
                        bottom_n: int) -> pd.Series:
    """Long top N, short bottom N, rest zero."""
    valid = expected_row.dropna()
    if len(valid) < top_n + bottom_n:
        return pd.Series(0.0, index=expected_row.index)
    weights = pd.Series(0.0, index=expected_row.index)
    weights[valid.nlargest(top_n).index]   =  1.0 / top_n
    weights[valid.nsmallest(bottom_n).index] = -1.0 / bottom_n
    return weights


def backtest_strategy(expected_df, industries_al, weights_fn) -> pd.Series:
    """Build and backtest a strategy given a weight function."""
    weights   = expected_df.apply(weights_fn, axis=1)
    w_shifted = weights.shift(1).dropna()
    ind       = industries_al.reindex(w_shifted.index)
    return (w_shifted * ind).sum(axis=1)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Benchmarks
# ──────────────────────────────────────────────────────────────────────────────

sp500_rot     = sp500_returns.reindex(industries_al.index).dropna()
equal_sect    = industries_al.reindex(sp500_rot.index).mean(axis=1)

print("=== Benchmarks ===")
print(f"{'Strategy':<35} {'Sharpe':>8} {'Ann Ret':>10} {'Max DD':>10}")
print("-" * 65)
for name, ret in [("S&P 500 Buy & Hold",    sp500_rot),
                   ("Equal Weight Sectors",  equal_sect)]:
    print(f"{name:<35} {sharpe(ret):>8.2f} {ann_return(ret)*100:>9.1f}% {max_drawdown(ret)*100:>9.1f}%")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Grid search: quantile x top_n x strategy type
# ──────────────────────────────────────────────────────────────────────────────

QUANTILES = [0.10, 0.15, 0.20]
TOP_NS    = [2, 3, 4, 5, 6]
BOTTOM_NS = [1, 2, 3]          # for long-short only

results = []

for q in QUANTILES:
    print(f"\nComputing expected returns for quantile={q:.0%}...")
    exp_df = compute_sector_expected(scores_sect, industries, quantile=q)
    exp_df_al = exp_df.reindex(industries_al.index)

    # ── Long-only strategies ──────────────────────────────────────────────────
    for top_n in TOP_NS:
        ret = backtest_strategy(
            exp_df_al, industries_al,
            lambda row, n=top_n: long_only_weights(row, n)
        )
        ret = ret.reindex(sp500_rot.index).dropna()
        results.append({
            "Strategy"   : f"LongOnly Top{top_n}",
            "Quantile"   : f"{q:.0%}",
            "Type"       : "Long-Only",
            "Top N"      : top_n,
            "Bottom N"   : 0,
            "Sharpe"     : round(sharpe(ret), 2),
            "Ann Ret"    : round(ann_return(ret) * 100, 1),
            "Max DD"     : round(max_drawdown(ret) * 100, 1),
        })

    # ── Long-short strategies ─────────────────────────────────────────────────
    for top_n in TOP_NS:
        for bot_n in BOTTOM_NS:
            if bot_n >= top_n:
                continue
            ret = backtest_strategy(
                exp_df_al, industries_al,
                lambda row, n=top_n, b=bot_n: long_short_weights(row, n, b)
            )
            ret = ret.reindex(sp500_rot.index).dropna()
            results.append({
                "Strategy"   : f"L/S Top{top_n}/Bot{bot_n}",
                "Quantile"   : f"{q:.0%}",
                "Type"       : "Long-Short",
                "Top N"      : top_n,
                "Bottom N"   : bot_n,
                "Sharpe"     : round(sharpe(ret), 2),
                "Ann Ret"    : round(ann_return(ret) * 100, 1),
                "Max DD"     : round(max_drawdown(ret) * 100, 1),
            })

results_df = pd.DataFrame(results)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Display results
# ──────────────────────────────────────────────────────────────────────────────

print("\n\n=== LONG-ONLY RESULTS ===")
lo = results_df[results_df["Type"] == "Long-Only"].sort_values("Sharpe", ascending=False)
print(lo[["Strategy", "Quantile", "Top N", "Sharpe", "Ann Ret", "Max DD"]].to_string(index=False))

print("\n\n=== LONG-SHORT RESULTS ===")
ls = results_df[results_df["Type"] == "Long-Short"].sort_values("Sharpe", ascending=False)
print(ls[["Strategy", "Quantile", "Top N", "Bottom N", "Sharpe", "Ann Ret", "Max DD"]].to_string(index=False))

print("\n\n=== TOP 10 OVERALL BY SHARPE ===")
print(f"{'Strategy':<20} {'Quantile':>10} {'Type':<12} {'Sharpe':>8} {'Ann Ret':>10} {'Max DD':>10}")
print("-" * 75)
for _, row in results_df.sort_values("Sharpe", ascending=False).head(10).iterrows():
    print(f"{row['Strategy']:<20} {row['Quantile']:>10} {row['Type']:<12} "
          f"{row['Sharpe']:>8.2f} {row['Ann Ret']:>9.1f}% {row['Max DD']:>9.1f}%")

# save results
results_df.to_csv("regime_grid_search.csv", index=False)
print("\nSaved to regime_grid_search.csv")


# ──────────────────────────────────────────────────────────────────────────────
# 6. Plot best strategy vs benchmarks
# ──────────────────────────────────────────────────────────────────────────────

# find best by Sharpe
best = results_df.sort_values("Sharpe", ascending=False).iloc[0]
print(f"\nBest strategy: {best['Strategy']} at quantile {best['Quantile']}")

# recompute returns for best strategy
best_q    = float(best["Quantile"].strip("%")) / 100
best_exp  = compute_sector_expected(scores_sect, industries, quantile=best_q)
best_exp_al = best_exp.reindex(industries_al.index)

if best["Type"] == "Long-Only":
    best_ret = backtest_strategy(
        best_exp_al, industries_al,
        lambda row: long_only_weights(row, int(best["Top N"]))
    )
else:
    best_ret = backtest_strategy(
        best_exp_al, industries_al,
        lambda row: long_short_weights(row, int(best["Top N"]), int(best["Bottom N"]))
    )

best_ret  = best_ret.reindex(sp500_rot.index).dropna()
idx_align = best_ret.index.intersection(sp500_rot.index).intersection(equal_sect.index)

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(idx_align.to_numpy(), (1 + sp500_rot.reindex(idx_align)).cumprod().to_numpy(),
        label=f"S&P 500 (SR: {sharpe(sp500_rot):.2f}, Ret: {ann_return(sp500_rot)*100:.1f}%)",
        color="steelblue", linewidth=1.5, linestyle="--")
ax.plot(idx_align.to_numpy(), (1 + equal_sect.reindex(idx_align)).cumprod().to_numpy(),
        label=f"Equal Sectors (SR: {sharpe(equal_sect):.2f}, Ret: {ann_return(equal_sect)*100:.1f}%)",
        color="gray", linewidth=1.5)
ax.plot(idx_align.to_numpy(), (1 + best_ret.reindex(idx_align)).cumprod().to_numpy(),
        label=f"Best: {best['Strategy']} q={best['Quantile']} (SR: {best['Sharpe']:.2f}, Ret: {best['Ann Ret']}%)",
        color="darkorange", linewidth=2)
ax.set_title("Sector Rotation Grid Search — Best Strategy vs Benchmarks")
ax.set_ylabel("Cumulative Return")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("regime_grid_best.png", dpi=150, bbox_inches="tight")
plt.show()
