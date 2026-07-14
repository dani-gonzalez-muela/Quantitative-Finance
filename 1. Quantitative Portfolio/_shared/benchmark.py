"""
shared.benchmark — Buy-and-hold benchmark construction.

Builds a benchmark equity curve from daily close prices so strategy
performance can be compared against "just hold QQQ."
"""

import pandas as pd
import numpy as np


def build_benchmark(daily_data, starting_capital, start_date=None, end_date=None):
    """
    Build a buy-and-hold equity curve from daily close prices.

    Parameters
    ----------
    daily_data       : pd.DataFrame — must have 'close' column, indexed by timestamp.
    starting_capital : float        — initial investment.
    start_date       : str or None  — filter start (inclusive).
    end_date         : str or None  — filter end (inclusive).

    Returns
    -------
    pd.DataFrame with columns: date, close, daily_return, equity.
    """
    df = daily_data[["close"]].copy()
    df["date"] = df.index.date

    # One row per day (use last close)
    daily = df.groupby("date")["close"].last().to_frame()
    daily.index = pd.to_datetime(daily.index)

    if start_date:
        daily = daily[daily.index >= pd.to_datetime(start_date)]
    if end_date:
        daily = daily[daily.index <= pd.to_datetime(end_date)]

    daily["daily_return"] = daily["close"].pct_change().fillna(0)
    daily["equity"] = starting_capital * (1 + daily["daily_return"]).cumprod()

    return daily.reset_index().rename(columns={"index": "date"})


def benchmark_metrics(benchmark_df, starting_capital):
    """
    Compute summary metrics for a buy-and-hold benchmark.

    Parameters
    ----------
    benchmark_df     : pd.DataFrame — output of build_benchmark.
    starting_capital : float

    Returns
    -------
    dict with key metrics.
    """
    final = benchmark_df["equity"].iloc[-1]
    total_return = (final / starting_capital) - 1
    days = (benchmark_df["date"].iloc[-1] - benchmark_df["date"].iloc[0]).days
    annualized = (1 + total_return) ** (252 / max(days, 1)) - 1

    returns = benchmark_df["daily_return"]
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0

    downside = returns[returns < 0]
    sortino = returns.mean() / downside.std() * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0

    cum_max = benchmark_df["equity"].expanding().max()
    max_dd = ((benchmark_df["equity"] - cum_max) / cum_max).min()

    # Yearly returns
    benchmark_df = benchmark_df.copy()
    benchmark_df["year"] = benchmark_df["date"].dt.year
    yearly = {}
    for year in sorted(benchmark_df["year"].unique()):
        yr = benchmark_df[benchmark_df["year"] == year]
        yr_ret = (yr["equity"].iloc[-1] / yr["equity"].iloc[0]) - 1
        yearly[int(year)] = round(yr_ret * 100, 2)

    return {
        "Strategy":      "QQQ Buy & Hold",
        "Total Return":  round(total_return * 100, 2),
        "Annualized":    round(annualized * 100, 2),
        "Max Drawdown":  round(max_dd * 100, 2),
        "Sharpe":        round(sharpe, 2),
        "Sortino":       round(sortino, 2),
        "Final Equity":  round(final, 2),
        "Yearly Returns": yearly,
    }
