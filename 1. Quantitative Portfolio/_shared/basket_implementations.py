"""
shared.basket_implementations — Weighting implementations for basket/Type 2 strategies.

Takes a signal DataFrame (date × instrument scores, wide format) and applies
different weighting methods. Analogous to shared.implementations but for
selection-based / basket strategies.

Signal convention
-----------------
signal_df : pd.DataFrame
    Index = dates (monthly), columns = instrument names, values = signal scores.
    Higher score = stronger signal (rank ascending = buy for momentum/carry).
    For CAPE rotation (buy cheapest), negate scores before passing in, or use
    the ``ascending=False`` parameter in individual functions.

Functions
---------
equal_weight(signal_df, top_n)
    Select top_n instruments by score each period, weight equally.

inverse_vol_weight(signal_df, prices, top_n)
    Select top_n, weight inversely proportional to realized volatility.

signal_strength_weight(signal_df, top_n)
    Select top_n, weight proportional to signal score magnitude.

compare_basket_implementations(signal_df, prices, starting_capital, tc_bps)
    Run all three methods across top_n variants, return dict for implementations.json.

Internal helpers
----------------
_build_equity_from_weights(daily_prices, monthly_weights, starting_capital)
    Build daily equity from monthly rebalance weights. (Mirrors _backtest_utils logic.)

_basket_stats(daily_equity, starting_capital)
    Standard performance metrics from daily equity.
"""

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _build_equity_from_weights(daily_prices: pd.DataFrame,
                                monthly_weights: pd.DataFrame,
                                starting_capital: float = 100_000) -> pd.Series:
    """
    Build daily equity Series from monthly rebalance weights.

    Mirrors long_term/_backtest_utils.build_equity_from_weights.
    Weights are assumed to be end-of-month — they are shifted 1 day to avoid
    look-ahead before being applied to daily prices.

    Parameters
    ----------
    daily_prices     : DataFrame, columns=tickers, index=dates (business days)
    monthly_weights  : DataFrame, columns=tickers, index=month-end dates, values in [0, 1]
    starting_capital : float

    Returns
    -------
    pd.Series  daily equity, index=dates
    """
    daily_prices = daily_prices.copy()
    daily_prices.index = pd.to_datetime(daily_prices.index)
    monthly_weights = monthly_weights.copy()
    monthly_weights.index = pd.to_datetime(monthly_weights.index)

    # Forward-fill month-end weights to daily, then shift 1 day (no look-ahead)
    weights_daily = (monthly_weights
                     .reindex(daily_prices.index, method="ffill")
                     .shift(1)
                     .fillna(0))

    daily_ret = daily_prices.pct_change().fillna(0)
    port_ret = (daily_ret * weights_daily).sum(axis=1)
    equity = starting_capital * (1 + port_ret).cumprod()
    return equity


def _basket_stats(daily_equity: pd.Series,
                  starting_capital: float = 100_000) -> dict:
    """Standard performance metrics from a daily equity Series."""
    eq = daily_equity.dropna()
    if len(eq) < 2:
        return {"total_return": 0, "cagr": 0, "sharpe": 0,
                "sortino": 0, "max_dd": 0, "profit_factor": 0}

    total_ret = (eq.iloc[-1] / starting_capital - 1) * 100
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = ((eq.iloc[-1] / starting_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    daily_rets = eq.pct_change().dropna()
    sharpe = (daily_rets.mean() / daily_rets.std() * np.sqrt(252)
              if daily_rets.std() > 0 else 0)
    downside = daily_rets[daily_rets < 0]
    sortino = (daily_rets.mean() / downside.std() * np.sqrt(252)
               if len(downside) > 0 and downside.std() > 0 else 0)

    peak = eq.expanding().max()
    max_dd = ((eq - peak) / peak).min() * 100

    wins = daily_rets[daily_rets > 0].sum()
    losses = -daily_rets[daily_rets < 0].sum()
    pf = wins / losses if losses > 0 else float("inf")

    return {
        "total_return":  round(float(total_ret), 2),
        "cagr":          round(float(cagr), 2),
        "sharpe":        round(float(sharpe), 2),
        "sortino":       round(float(sortino), 2),
        "max_dd":        round(float(max_dd), 2),
        "profit_factor": round(float(pf), 2) if np.isfinite(pf) else 999.0,
    }


def _resolve_prices(signal_df: pd.DataFrame, prices) -> pd.DataFrame:
    """
    Ensure prices is a daily-indexed DataFrame with the same columns as signal_df.
    Accepts:
    - pd.DataFrame with columns matching signal_df
    - dict {ticker: pd.Series}
    - None (returns None — caller handles the N/A case)
    """
    if prices is None:
        return None
    if isinstance(prices, dict):
        prices = pd.DataFrame(prices)
    prices = prices.copy()
    prices.index = pd.to_datetime(prices.index)
    # Keep only tickers present in signal
    common = [c for c in signal_df.columns if c in prices.columns]
    if common:
        prices = prices[common]
    return prices


# ═══════════════════════════════════════════════════════════════════════
# WEIGHTING METHODS
# ═══════════════════════════════════════════════════════════════════════


def equal_weight(signal_df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """
    Equal-weight the top_n instruments by signal score each period.

    Parameters
    ----------
    signal_df : DataFrame  index=dates, columns=instruments, values=scores
                (higher score = stronger signal = buy)
    top_n     : int  number of instruments to hold each period

    Returns
    -------
    pd.DataFrame  same shape as signal_df, values = weights (0 or 1/top_n)
    """
    def _row_weights(row):
        valid = row.dropna()
        if len(valid) == 0:
            return pd.Series(0.0, index=row.index)
        k = min(top_n, len(valid))
        selected = valid.nlargest(k).index
        w = pd.Series(0.0, index=row.index)
        w[selected] = 1.0 / k
        return w

    return signal_df.apply(_row_weights, axis=1)


def inverse_vol_weight(signal_df: pd.DataFrame,
                       prices,
                       top_n: int = 3,
                       vol_lookback: int = 63) -> pd.DataFrame:
    """
    Select top_n instruments, weight inversely proportional to realized volatility.

    Parameters
    ----------
    signal_df    : DataFrame  index=dates, columns=instruments, values=scores
    prices       : DataFrame or dict  daily prices, columns=instruments
                   (used to compute realized vol; if None, falls back to equal_weight)
    top_n        : int
    vol_lookback : int  rolling window in business days for vol estimate

    Returns
    -------
    pd.DataFrame  same shape as signal_df, values = weights
    """
    prices_df = _resolve_prices(signal_df, prices)

    if prices_df is None or prices_df.empty:
        # Fallback to equal weight
        return equal_weight(signal_df, top_n)

    # Rolling 63-day realized vol (annualized)
    daily_ret = prices_df.pct_change()
    rolling_vol = daily_ret.rolling(vol_lookback, min_periods=vol_lookback // 2).std()

    # Resample vol to match signal dates (month-end)
    signal_dates = pd.to_datetime(signal_df.index)
    vol_at_signal = rolling_vol.reindex(signal_dates, method="ffill")

    weights_list = []
    for i, date in enumerate(signal_dates):
        row = signal_df.iloc[i]
        valid = row.dropna()
        if len(valid) == 0:
            weights_list.append(pd.Series(0.0, index=signal_df.columns))
            continue

        k = min(top_n, len(valid))
        selected = valid.nlargest(k).index

        # Inverse-vol weights for selected instruments
        vols = vol_at_signal.loc[date, selected].dropna()
        if len(vols) == 0 or (vols == 0).all():
            # Fallback to equal weight if vol unavailable
            w = pd.Series(0.0, index=signal_df.columns)
            w[selected] = 1.0 / k
        else:
            inv_vol = 1.0 / vols.replace(0, np.nan).dropna()
            inv_vol = inv_vol / inv_vol.sum()
            w = pd.Series(0.0, index=signal_df.columns)
            for sym, wgt in inv_vol.items():
                w[sym] = wgt

        weights_list.append(w)

    return pd.DataFrame(weights_list, index=signal_df.index)


def signal_strength_weight(signal_df: pd.DataFrame,
                           top_n: int = 3) -> pd.DataFrame:
    """
    Select top_n instruments, weight proportional to signal score magnitude.

    Scores are min-max normalized within each period before weighting so
    large outlier scores don't dominate.

    Note: for binary signals (0/1), this collapses to equal_weight.

    Parameters
    ----------
    signal_df : DataFrame  index=dates, columns=instruments, values=scores
    top_n     : int

    Returns
    -------
    pd.DataFrame  same shape as signal_df, values = weights
    """
    def _row_weights(row):
        valid = row.dropna()
        if len(valid) == 0:
            return pd.Series(0.0, index=row.index)
        k = min(top_n, len(valid))
        selected = valid.nlargest(k)

        # Min-max normalize within selected group
        mn, mx = selected.min(), selected.max()
        if mx == mn:
            # All scores equal → equal weight
            w = pd.Series(0.0, index=row.index)
            w[selected.index] = 1.0 / k
            return w

        norm = (selected - mn) / (mx - mn)
        norm_sum = norm.sum()
        w = pd.Series(0.0, index=row.index)
        if norm_sum > 0:
            w[selected.index] = norm / norm_sum
        else:
            w[selected.index] = 1.0 / k
        return w

    return signal_df.apply(_row_weights, axis=1)


# ═══════════════════════════════════════════════════════════════════════
# COMPARISON / OUTPUT
# ═══════════════════════════════════════════════════════════════════════


def compare_basket_implementations(signal_df: pd.DataFrame,
                                   prices,
                                   starting_capital: float = 100_000,
                                   tc_bps: float = 1.0,
                                   top_n_values: list = None) -> dict:
    """
    Run all three weighting methods across top_n variants and return a dict
    formatted for `{name}_implementations.json`.

    Parameters
    ----------
    signal_df        : DataFrame  index=month-end dates, columns=instruments, values=scores
                       (higher = buy signal; for value/CAPE strategies, negate before passing)
    prices           : DataFrame or dict  daily prices, columns=instruments
                       (needed for inverse_vol_weight and equity simulation)
    starting_capital : float
    tc_bps           : float  transaction cost in basis points (applied as flat deduction)
    top_n_values     : list of int  top_n values to test. Default: [1, 3, 5] clipped to
                       the number of available instruments.

    Returns
    -------
    dict  {variant_key: stats_dict, ..., "_recommended": label_str}
          Compatible with {name}_implementations.json.

    Notes
    -----
    - If prices is None or doesn't cover the instruments, inverse_vol_weight falls
      back to equal_weight and a warning is printed.
    - Single-instrument signal_dfs (1 column) will produce identical results for all
      methods. This is expected behaviour — the caller should note this.
    """
    prices_df = _resolve_prices(signal_df, prices)
    n_instruments = signal_df.shape[1]

    if top_n_values is None:
        candidates = [1, 3, 5]
        top_n_values = [n for n in candidates if n <= n_instruments]
        if not top_n_values:
            top_n_values = [n_instruments]

    # Monthly TC: subtract from each period's return
    tc_monthly = tc_bps * 2 / 10_000  # round-trip TC per rebalance

    results = {}
    all_items = []

    for top_n in top_n_values:
        methods = {
            f"equal_weight_top{top_n}":          equal_weight(signal_df, top_n),
            f"inv_vol_weight_top{top_n}":         inverse_vol_weight(signal_df, prices_df, top_n),
            f"signal_strength_weight_top{top_n}": signal_strength_weight(signal_df, top_n),
        }

        labels = {
            f"equal_weight_top{top_n}":          f"Equal weight (top {top_n})",
            f"inv_vol_weight_top{top_n}":         f"Inverse-vol weight (top {top_n})",
            f"signal_strength_weight_top{top_n}": f"Signal-strength weight (top {top_n})",
        }

        for key, weights_df in methods.items():
            label = labels[key]

            if prices_df is not None and not prices_df.empty:
                # Align prices and weights to common columns
                common_cols = [c for c in weights_df.columns if c in prices_df.columns]
                if common_cols:
                    eq = _build_equity_from_weights(
                        prices_df[common_cols],
                        weights_df[common_cols],
                        starting_capital
                    )
                else:
                    # No price data available for any instrument — skip simulation
                    print(f"  WARNING: no price data for any instrument in {key}; skipping equity build.")
                    stats = {"total_return": 0, "cagr": 0, "sharpe": 0,
                             "sortino": 0, "max_dd": 0, "profit_factor": 0}
                    stats["label"] = label
                    stats["note"] = "price data unavailable for equity simulation"
                    results[key] = stats
                    continue
            else:
                # No prices at all — can't simulate equity; record stub
                stats = {"total_return": 0, "cagr": 0, "sharpe": 0,
                         "sortino": 0, "max_dd": 0, "profit_factor": 0}
                stats["label"] = label
                stats["note"] = "price data not provided; equity simulation skipped"
                results[key] = stats
                continue

            # Apply TC: deduct from monthly periods
            daily_ret = eq.pct_change()
            # Identify rebalance dates (first trading day after month-end weight change)
            rebal_dates = pd.to_datetime(weights_df.index)
            rebal_bdays = []
            for rd in rebal_dates:
                # first business day >= rd
                possible = eq.index[eq.index >= rd]
                if len(possible) > 0:
                    rebal_bdays.append(possible[0])

            tc_adj = daily_ret.copy()
            for rd in rebal_bdays:
                if rd in tc_adj.index:
                    tc_adj.loc[rd] -= tc_monthly

            eq_tc = starting_capital * (1 + tc_adj).cumprod()
            stats = _basket_stats(eq_tc, starting_capital)
            stats["label"] = label
            results[key] = stats
            all_items.append((key, stats))

    # Recommend: best Sharpe with MaxDD > -50%
    viable = [(k, s) for k, s in all_items if s.get("max_dd", -100) > -50]
    if viable:
        best_key, best_stats = max(viable, key=lambda x: x[1].get("sharpe", 0))
        results["_recommended"] = best_stats["label"]
        print(f"  Recommended: {best_stats['label']} "
              f"(Sharpe={best_stats['sharpe']}, MaxDD={best_stats['max_dd']}%)")
    elif all_items:
        # All blew up — recommend least-bad MaxDD
        best_key, best_stats = max(all_items, key=lambda x: x[1].get("max_dd", -100))
        results["_recommended"] = best_stats["label"] + " [all variants have MaxDD > 50%]"

    return results


def print_basket_comparison(results: dict) -> None:
    """Print a summary table of basket implementation results."""
    print(f"\n{'Variant':<45} {'Return':>8} {'CAGR':>7} {'Sharpe':>8} "
          f"{'Sortino':>8} {'MaxDD':>7}")
    print("=" * 85)
    for key, stats in results.items():
        if key.startswith("_"):
            continue
        label = stats.get("label", key)
        print(f"{label:<45} {stats.get('total_return', 0):>7.1f}%  "
              f"{stats.get('cagr', 0):>6.1f}%  "
              f"{stats.get('sharpe', 0):>7.2f}  "
              f"{stats.get('sortino', 0):>7.2f}  "
              f"{stats.get('max_dd', 0):>6.1f}%")
    if "_recommended" in results:
        print(f"\nRecommended: {results['_recommended']}")
