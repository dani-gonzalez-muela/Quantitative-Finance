"""
Property-based tests using Hypothesis.

Instead of checking specific inputs against hand-calculated outputs,
these define invariants that must hold for ANY valid input. Hypothesis
generates hundreds of random portfolios to try to break them.
"""

import math

import polars as pl
import numpy as np
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from portfolio_risk.metrics import (
    compute_daily_portfolio_returns,
    compute_portfolio_variance,
    compute_annualized_return,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_max_drawdown,
    compute_asset_volatilities,
    compute_correlation_matrix,
    compute_win_rate,
)
from portfolio_risk.validators import validate_weights


# ── Strategies ───────────────────────────────────────────────

# Daily returns in a realistic range; avoids floating point edge cases
daily_return = st.floats(min_value=-0.10, max_value=0.10, allow_nan=False, allow_infinity=False)


def valid_portfolio(min_assets=2, max_assets=5, min_days=10, max_days=100):
    """Generate a valid (returns DataFrame, normalized weights) pair."""
    @st.composite
    def _build(draw):
        n_assets = draw(st.integers(min_value=min_assets, max_value=max_assets))
        n_days = draw(st.integers(min_value=min_days, max_value=max_days))

        data = {
            f"ASSET_{i:02d}": draw(st.lists(daily_return, min_size=n_days, max_size=n_days))
            for i in range(n_assets)
        }
        df = pl.DataFrame(data)

        # Dirichlet-like: draw positive floats, normalize to sum=1.0
        raw_weights = draw(st.lists(
            st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=n_assets, max_size=n_assets,
        ))
        total = sum(raw_weights)
        weights = tuple(w / total for w in raw_weights)

        return df, weights

    return _build()


# ── Variance ─────────────────────────────────────────────────

class TestVarianceProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=200)
    def test_variance_is_non_negative(self, portfolio):
        returns, weights = portfolio
        assert compute_portfolio_variance(returns, weights) >= 0.0

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_variance_is_finite(self, portfolio):
        returns, weights = portfolio
        assert math.isfinite(compute_portfolio_variance(returns, weights))


# ── Max Drawdown ─────────────────────────────────────────────

class TestDrawdownProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=200)
    def test_drawdown_between_minus_one_and_zero(self, portfolio):
        returns, weights = portfolio
        result = compute_max_drawdown(returns, weights)
        assert -1.0 <= result <= 0.0

    @given(data=st.lists(
        st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
        min_size=5, max_size=50,
    ))
    def test_all_positive_returns_no_drawdown(self, data):
        returns = pl.DataFrame({"ASSET_00": data})
        assert compute_max_drawdown(returns, (1.0,)) == 0.0


# ── Win Rate ─────────────────────────────────────────────────

class TestWinRateProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=200)
    def test_win_rate_between_zero_and_one(self, portfolio):
        returns, weights = portfolio
        assert 0.0 <= compute_win_rate(returns, weights) <= 1.0


# ── Sharpe ───────────────────────────────────────────────────

class TestSharpeProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_sharpe_is_finite(self, portfolio):
        returns, weights = portfolio
        assert math.isfinite(compute_sharpe_ratio(returns, weights, risk_free_rate=0.0))

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_higher_risk_free_rate_lowers_sharpe(self, portfolio):
        returns, weights = portfolio
        sharpe_low = compute_sharpe_ratio(returns, weights, risk_free_rate=0.0)
        sharpe_high = compute_sharpe_ratio(returns, weights, risk_free_rate=0.10)

        if sharpe_low == 0.0 and sharpe_high == 0.0:
            return  # zero-vol edge case, both return 0.0

        assert sharpe_high <= sharpe_low + 1e-10


# ── Sortino ──────────────────────────────────────────────────

class TestSortinoProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_sortino_is_finite(self, portfolio):
        returns, weights = portfolio
        assert math.isfinite(compute_sortino_ratio(returns, weights, risk_free_rate=0.0))


# ── Asset Volatilities ──────────────────────────────────────

class TestVolatilityProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_volatilities_are_non_negative(self, portfolio):
        returns, _ = portfolio
        assert all(v >= 0.0 for v in compute_asset_volatilities(returns))

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_volatility_count_matches_assets(self, portfolio):
        returns, _ = portfolio
        assert len(compute_asset_volatilities(returns)) == returns.width


# ── Correlation Matrix ───────────────────────────────────────
# Edge case discovered by Hypothesis: all-zero returns → NaN correlations
# because np.corrcoef divides by zero std. We skip those with assume().

class TestCorrelationProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_diagonal_is_one(self, portfolio):
        returns, _ = portfolio
        assume(all(v > 0.0 for v in compute_asset_volatilities(returns)))
        corr = compute_correlation_matrix(returns)
        for i in range(len(corr)):
            assert corr[i][i] == pytest.approx(1.0, abs=1e-10)

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_matrix_is_symmetric(self, portfolio):
        returns, _ = portfolio
        assume(all(v > 0.0 for v in compute_asset_volatilities(returns)))
        corr = compute_correlation_matrix(returns)
        n = len(corr)
        for i in range(n):
            for j in range(i + 1, n):
                assert corr[i][j] == pytest.approx(corr[j][i], abs=1e-10)

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_correlations_in_valid_range(self, portfolio):
        returns, _ = portfolio
        assume(all(v > 0.0 for v in compute_asset_volatilities(returns)))
        corr = compute_correlation_matrix(returns)
        for row in corr:
            for val in row:
                assert -1.0 - 1e-10 <= val <= 1.0 + 1e-10


# ── Weight Renormalization ───────────────────────────────────

class TestWeightValidationProperties:

    @given(
        raw_weights=st.lists(
            st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=2, max_size=5,
        ),
        drop_index=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=200)
    def test_renormalized_weights_sum_to_one(self, raw_weights, drop_index):
        """After dropping any asset and renormalizing, weights must sum to 1.0."""
        n = len(raw_weights)
        assume(drop_index < n and n >= 3)

        total = sum(raw_weights)
        weights = tuple(w / total for w in raw_weights)

        original = tuple(f"ASSET_{i:02d}" for i in range(n))
        surviving = tuple(a for i, a in enumerate(original) if i != drop_index)

        result = validate_weights(weights, original, surviving)
        assert result.is_valid is True
        assert sum(result.config.weights) == pytest.approx(1.0, abs=1e-10)


# ── Daily Portfolio Returns ──────────────────────────────────

class TestDailyPortfolioReturnsProperties:

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_length_matches_input(self, portfolio):
        returns, weights = portfolio
        assert compute_daily_portfolio_returns(returns, weights).len() == returns.height

    @given(portfolio=valid_portfolio())
    @settings(max_examples=100)
    def test_returns_are_finite(self, portfolio):
        returns, weights = portfolio
        series = compute_daily_portfolio_returns(returns, weights)
        assert series.is_nan().sum() == 0
        assert series.is_infinite().sum() == 0
