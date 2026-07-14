"""
Pure functions for portfolio risk metric computation.

Every function here is pure: typed inputs → typed outputs, no side effects.
All metrics annualized assuming 252 trading days/year.

The daily portfolio return series is computed once via compute_daily_portfolio_returns
and passed downstream — Sharpe, Sortino, drawdown, and win rate all consume it
rather than recomputing from scratch.
"""

from __future__ import annotations

import math
from functools import reduce

import polars as pl
import numpy as np


TRADING_DAYS_PER_YEAR: int = 252


# ── Core: Daily Portfolio Returns ────────────────────────────

def compute_daily_portfolio_returns(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
) -> pl.Series:
    """
    Compute the weighted daily portfolio return series.

    Building block for all portfolio-level metrics. Computed once, passed
    downstream to avoid redundant recalculation.

    Formula: r_portfolio = Σ wᵢ × rᵢ

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights (one per column).

    Returns:
        Series of daily portfolio returns.
    """
    asset_names = returns.columns

    # map: weight each asset column, reduce: sum into a single expression
    weighted_sum_expr = sum(
        pl.col(name) * weight
        for name, weight in zip(asset_names, weights)
    )

    return returns.select(
        weighted_sum_expr.alias("portfolio_return")
    ).to_series()


# ── Asset-Level Metrics ──────────────────────────────────────

def compute_asset_volatilities(returns: pl.DataFrame) -> tuple[float, ...]:
    """
    Compute annualized volatility for each asset independently.

    Formula: σ_annual = std(daily_returns, ddof=1) × √252

    Args:
        returns: DataFrame where each column is an asset's daily returns.

    Returns:
        Tuple of annualized volatilities, one per asset.
    """
    daily_stds = returns.select(pl.all().std())

    annualization_factor = math.sqrt(TRADING_DAYS_PER_YEAR)
    daily_std_values = daily_stds.row(0)

    return tuple(std * annualization_factor for std in daily_std_values)


def compute_correlation_matrix(returns: pl.DataFrame) -> tuple[tuple[float, ...], ...]:
    """
    Compute pairwise Pearson correlation matrix between all assets.

    Args:
        returns: DataFrame where each column is an asset's daily returns.

    Returns:
        Immutable 2D matrix as tuple of tuples.
    """
    # np.corrcoef is stable across versions; Polars' correlation API isn't
    corr_array = np.corrcoef(returns.to_numpy().T)

    if corr_array.ndim == 0:
        corr_array = np.array([[1.0]])

    return tuple(
        tuple(float(val) for val in row)
        for row in corr_array
    )


# ── Portfolio-Level Metrics ──────────────────────────────────

def compute_portfolio_variance(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
) -> float:
    """
    Compute annualized portfolio variance via the covariance matrix.

    Formula: σ²_portfolio = wᵀ Σ w × 252

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights (must match number of columns).

    Returns:
        Annualized portfolio variance.
    """
    returns_matrix = returns.to_numpy()
    cov_matrix = np.cov(returns_matrix.T, ddof=1)

    # np.cov returns a scalar for a single asset
    if returns.width == 1:
        cov_matrix = np.array([[cov_matrix.item()]])

    weights_array = np.array(weights)
    daily_variance = float(weights_array @ cov_matrix @ weights_array)

    return daily_variance * TRADING_DAYS_PER_YEAR


def compute_annualized_return(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
    portfolio_returns: pl.Series | None = None,
) -> float:
    """
    Compute annualized portfolio return from mean daily weighted returns.

    Formula: r_annual = mean(Σ wᵢ × rᵢ) × 252

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights.
        portfolio_returns: Pre-computed daily series (optional, avoids recomputation).

    Returns:
        Annualized portfolio return.
    """
    if portfolio_returns is None:
        portfolio_returns = compute_daily_portfolio_returns(returns, weights)

    return portfolio_returns.mean() * TRADING_DAYS_PER_YEAR


def compute_sharpe_ratio(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
    risk_free_rate: float = 0.0,
    portfolio_returns: pl.Series | None = None,
) -> float:
    """
    Compute annualized Sharpe ratio.

    Formula: Sharpe = (r_annual - r_f) / σ_annual

    Composes compute_annualized_return and compute_portfolio_variance
    rather than reimplementing their logic.

    Returns 0.0 when volatility is zero (avoids division by zero).

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights.
        risk_free_rate: Annualized risk-free rate (default 0.0).
        portfolio_returns: Pre-computed daily series (optional).

    Returns:
        Annualized Sharpe ratio.
    """
    annualized_ret = compute_annualized_return(returns, weights, portfolio_returns)
    annualized_vol = math.sqrt(compute_portfolio_variance(returns, weights))

    if annualized_vol == 0.0:
        return 0.0

    return (annualized_ret - risk_free_rate) / annualized_vol


def compute_max_drawdown(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
    portfolio_returns: pl.Series | None = None,
) -> float:
    """
    Compute maximum drawdown: largest peak-to-trough decline in cumulative returns.

    Uses functools.reduce to carry (cumulative, peak, max_dd) state through the
    return sequence — the FP alternative to a mutable loop variable.

    Expressed as a negative number (e.g., -0.15 = 15% drawdown).
    Returns 0.0 if the portfolio never declines.

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights.
        portfolio_returns: Pre-computed daily series (optional).

    Returns:
        Maximum drawdown as a negative float (or 0.0).
    """
    if portfolio_returns is None:
        portfolio_returns = compute_daily_portfolio_returns(returns, weights)

    daily_returns = portfolio_returns.to_list()
    initial_state = (1.0, 1.0, 0.0)  # (cumulative, peak, max_drawdown)

    def step(state: tuple[float, float, float], r: float) -> tuple[float, float, float]:
        """Pure state transition: one day's return → updated (cumulative, peak, max_dd)."""
        cumulative, peak, max_dd = state
        new_cumulative = cumulative * (1.0 + r)
        new_peak = max(peak, new_cumulative)
        current_dd = (new_cumulative - new_peak) / new_peak
        return (new_cumulative, new_peak, min(max_dd, current_dd))

    _, _, max_drawdown = reduce(step, daily_returns, initial_state)
    return max_drawdown


def compute_sortino_ratio(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
    risk_free_rate: float = 0.0,
    portfolio_returns: pl.Series | None = None,
) -> float:
    """
    Compute annualized Sortino ratio (downside risk-adjusted return).

    Formula: Sortino = (r_annual - r_f) / downside_deviation

    Like Sharpe, but only penalizes downside volatility — better for
    asymmetric return distributions where big up-days shouldn't hurt you.

    Returns 0.0 when downside deviation is zero (no negative returns).

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights.
        risk_free_rate: Annualized risk-free rate (default 0.0).
        portfolio_returns: Pre-computed daily series (optional).

    Returns:
        Annualized Sortino ratio.
    """
    if portfolio_returns is None:
        portfolio_returns = compute_daily_portfolio_returns(returns, weights)

    annualized_ret = compute_annualized_return(returns, weights, portfolio_returns)

    # Declarative filtering via Polars — no intermediate list materialization
    negative_returns = portfolio_returns.filter(portfolio_returns < 0)

    if negative_returns.len() < 2:
        return 0.0

    downside_deviation = negative_returns.std() * math.sqrt(TRADING_DAYS_PER_YEAR)

    if downside_deviation == 0.0:
        return 0.0

    return (annualized_ret - risk_free_rate) / downside_deviation


def compute_win_rate(
    returns: pl.DataFrame,
    weights: tuple[float, ...],
    portfolio_returns: pl.Series | None = None,
) -> float:
    """
    Compute win rate: fraction of days with positive portfolio returns.

    Formula: win_rate = count(daily_return > 0) / total_days

    Zero returns are NOT counted as wins — a flat day isn't a winning day.

    Args:
        returns: DataFrame where each column is an asset's daily returns.
        weights: Asset weights.
        portfolio_returns: Pre-computed daily series (optional).

    Returns:
        Win rate between 0.0 and 1.0.
    """
    if portfolio_returns is None:
        portfolio_returns = compute_daily_portfolio_returns(returns, weights)

    n_positive = portfolio_returns.filter(portfolio_returns > 0).len()
    return n_positive / portfolio_returns.len()
