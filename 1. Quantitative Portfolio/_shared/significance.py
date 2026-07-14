"""
shared.significance — Statistical significance tests for trading strategies.

Three practical tests to answer: "Is this strategy's edge real?"

1. t-test:      Are mean per-trade returns significantly different from zero?
2. Bootstrap:   What's the 95% confidence interval on the Sharpe ratio?
3. Permutation: If we randomly shuffle trade P&L, how often do we get
                a Sharpe this high by chance? (empirical p-value)
"""

import numpy as np
import pandas as pd
from scipy import stats


def ttest_returns(trades_df):
    """
    One-sample t-test: are mean per-trade returns significantly > 0?

    Parameters
    ----------
    trades_df : pd.DataFrame — must have 'net_pnl' and 'equity_before'.

    Returns
    -------
    dict with t_stat, p_value, mean_return, n_trades, significant (at 5%).
    """
    returns = trades_df["net_pnl"] / trades_df["equity_before"]
    t_stat, p_value_two = stats.ttest_1samp(returns, 0)

    # One-sided: we care if returns > 0
    p_value = p_value_two / 2 if t_stat > 0 else 1 - p_value_two / 2

    return {
        "test":        "t-test (returns > 0)",
        "t_stat":      round(t_stat, 4),
        "p_value":     round(p_value, 6),
        "mean_return":  round(returns.mean() * 100, 4),
        "n_trades":    len(returns),
        "significant": p_value < 0.05,
    }


def bootstrap_sharpe(trades_df, n_bootstrap=10000, confidence=0.95, seed=42):
    """
    Bootstrap the Sharpe ratio to get a confidence interval.

    Resamples trades with replacement and computes Sharpe each time.

    Parameters
    ----------
    trades_df    : pd.DataFrame — must have 'net_pnl' and 'equity_before'.
    n_bootstrap  : int   — number of bootstrap samples.
    confidence   : float — confidence level (e.g. 0.95).
    seed         : int   — random seed for reproducibility.

    Returns
    -------
    dict with observed_sharpe, ci_lower, ci_upper, pct_below_zero.
    """
    rng = np.random.RandomState(seed)
    returns = (trades_df["net_pnl"] / trades_df["equity_before"]).values
    n = len(returns)

    observed = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

    bootstrap_sharpes = np.empty(n_bootstrap)
    for i in range(n_bootstrap):
        sample = rng.choice(returns, size=n, replace=True)
        std = sample.std()
        bootstrap_sharpes[i] = sample.mean() / std * np.sqrt(252) if std > 0 else 0

    alpha = (1 - confidence) / 2
    ci_lower = np.percentile(bootstrap_sharpes, alpha * 100)
    ci_upper = np.percentile(bootstrap_sharpes, (1 - alpha) * 100)
    pct_below_zero = (bootstrap_sharpes < 0).mean() * 100

    return {
        "test":             "Bootstrap Sharpe (95% CI)",
        "observed_sharpe":  round(observed, 4),
        "ci_lower":         round(ci_lower, 4),
        "ci_upper":         round(ci_upper, 4),
        "pct_below_zero":   round(pct_below_zero, 2),
        "significant":      ci_lower > 0,
    }


def permutation_test(trades_df, n_permutations=10000, seed=42):
    """
    Permutation test: randomly shuffle trade signs and compare Sharpe.

    Under the null hypothesis (no edge), long/short assignment is random.
    We shuffle the signs of P&L and compute Sharpe each time. The p-value
    is the fraction of permuted Sharpes that exceed the observed one.

    Parameters
    ----------
    trades_df      : pd.DataFrame — must have 'net_pnl' and 'equity_before'.
    n_permutations : int   — number of random permutations.
    seed           : int   — random seed.

    Returns
    -------
    dict with observed_sharpe, p_value, significant.
    """
    rng = np.random.RandomState(seed)
    returns = (trades_df["net_pnl"] / trades_df["equity_before"]).values
    n = len(returns)

    observed = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

    count_exceeding = 0
    abs_returns = np.abs(returns)

    for _ in range(n_permutations):
        # Randomly flip signs
        signs = rng.choice([-1, 1], size=n)
        shuffled = abs_returns * signs
        std = shuffled.std()
        perm_sharpe = shuffled.mean() / std * np.sqrt(252) if std > 0 else 0
        if perm_sharpe >= observed:
            count_exceeding += 1

    p_value = count_exceeding / n_permutations

    return {
        "test":            "Permutation test (random signs)",
        "observed_sharpe": round(observed, 4),
        "p_value":         round(p_value, 6),
        "n_permutations":  n_permutations,
        "significant":     p_value < 0.05,
    }


def full_significance_report(trades_df, strategy_name="Strategy"):
    """
    Run all three significance tests and return a summary.

    Parameters
    ----------
    trades_df     : pd.DataFrame — standardized trades with net_pnl, equity_before.
    strategy_name : str

    Returns
    -------
    dict with all test results and an overall verdict.
    """
    t = ttest_returns(trades_df)
    b = bootstrap_sharpe(trades_df)
    p = permutation_test(trades_df)

    # Verdict: require at least 2 out of 3 tests to pass
    passes = sum([t["significant"], b["significant"], p["significant"]])

    verdict = "NOT SIGNIFICANT"
    if passes == 3:
        verdict = "SIGNIFICANT (strong)"
    elif passes == 2:
        verdict = "SIGNIFICANT (moderate)"
    elif passes == 1:
        verdict = "WEAK (only 1/3 tests pass)"

    return {
        "strategy":    strategy_name,
        "ttest":       t,
        "bootstrap":   b,
        "permutation": p,
        "verdict":     verdict,
        "tests_passed": f"{passes}/3",
    }


def print_significance_report(report):
    """Pretty-print a full significance report."""
    print(f"\n{'=' * 70}")
    print(f"STATISTICAL SIGNIFICANCE — {report['strategy']}")
    print(f"{'=' * 70}")

    t = report["ttest"]
    print(f"\n1. {t['test']}")
    print(f"   Mean return:  {t['mean_return']}% per trade")
    print(f"   t-statistic:  {t['t_stat']}")
    print(f"   p-value:      {t['p_value']}")
    print(f"   Significant:  {'YES' if t['significant'] else 'NO'}")

    b = report["bootstrap"]
    print(f"\n2. {b['test']}")
    print(f"   Observed Sharpe:   {b['observed_sharpe']}")
    print(f"   95% CI:            [{b['ci_lower']}, {b['ci_upper']}]")
    print(f"   % below zero:      {b['pct_below_zero']}%")
    print(f"   Significant:       {'YES' if b['significant'] else 'NO'}")

    p = report["permutation"]
    print(f"\n3. {p['test']}")
    print(f"   Observed Sharpe:   {p['observed_sharpe']}")
    print(f"   p-value:           {p['p_value']}")
    print(f"   Significant:       {'YES' if p['significant'] else 'NO'}")

    print(f"\n{'─' * 70}")
    print(f"VERDICT: {report['verdict']} ({report['tests_passed']} tests pass)")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════════
# SERIES-BASED VARIANTS (monthly returns) — consolidated from
# long_term/_backtest_utils.py (fable run 2026-07-02, refactor_discussion_
# points.md §2.1: two sources of truth for the same statistics).
# long_term/_backtest_utils.py now delegates here; import from shared.
# ═══════════════════════════════════════════════════════════════════════

def ttest_returns_series(returns):
    """One-sided t-test on a returns Series (monthly convention)."""
    t_stat, p_two = stats.ttest_1samp(returns, 0)
    p = p_two / 2 if t_stat > 0 else 1 - p_two / 2
    return {"t_stat": round(float(t_stat), 4), "p_value": round(float(p), 6),
            "mean_return": round(float(np.mean(returns) * 100), 4),
            "n": len(returns), "significant": bool(p < 0.05)}


def bootstrap_sharpe_series(returns, n=10000, seed=42):
    """Bootstrap 95% CI on annualized (sqrt(12)) Sharpe of a returns Series."""
    rng = np.random.RandomState(seed)
    r = np.array(returns)
    obs = r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else 0
    boot = []
    for _ in range(n):
        s = rng.choice(r, size=len(r), replace=True)
        boot.append(s.mean() / s.std() * np.sqrt(12) if s.std() > 0 else 0)
    boot = np.array(boot)
    ci_lo = np.percentile(boot, 2.5)
    return {"observed_sharpe": round(float(obs), 4), "ci_lower": round(float(ci_lo), 4),
            "ci_upper": round(float(np.percentile(boot, 97.5)), 4),
            "significant": bool(ci_lo > 0)}


def permutation_test_series(returns, n=10000, seed=42):
    """Sign-randomization permutation test on a returns Series (sqrt(12))."""
    rng = np.random.RandomState(seed)
    r = np.array(returns)
    obs = r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else 0
    abs_r = np.abs(r)
    count = 0
    for _ in range(n):
        shuffled = abs_r * rng.choice([-1, 1], size=len(abs_r))
        ps = shuffled.mean() / shuffled.std() * np.sqrt(12) if shuffled.std() > 0 else 0
        if ps >= obs:
            count += 1
    return {"observed_sharpe": round(float(obs), 4), "p_value": round(count / n, 6),
            "significant": bool(count / n < 0.05)}
