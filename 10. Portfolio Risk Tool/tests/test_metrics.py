"""
Test suite for portfolio risk metrics.

Each test uses simple, hand-calculable data so expected values can be
verified on paper.

Conventions:
    - 252 trading days/year for annualization
    - Zero volatility → Sharpe returns 0.0
    - Max drawdown expressed as negative (e.g., -0.15 = 15% drawdown)
"""

import pytest
import polars as pl

from portfolio_risk.metrics import (
    compute_portfolio_variance,
    compute_annualized_return,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_max_drawdown,
    compute_asset_volatilities,
    compute_correlation_matrix,
    compute_win_rate,
)


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def basic_returns() -> pl.DataFrame:
    """2 assets, 4 days. Small enough to verify by hand."""
    return pl.DataFrame({
        "ASSET_01": [0.01, 0.03, -0.01, 0.02],
        "ASSET_02": [0.02, 0.04, 0.01, -0.01],
    })


@pytest.fixture
def basic_weights() -> tuple:
    """60/40 allocation."""
    return (0.6, 0.4)


@pytest.fixture
def single_asset_returns() -> pl.DataFrame:
    return pl.DataFrame({"ASSET_01": [0.01, 0.03, -0.01, 0.02]})


@pytest.fixture
def zero_returns() -> pl.DataFrame:
    return pl.DataFrame({
        "ASSET_01": [0.0, 0.0, 0.0],
        "ASSET_02": [0.0, 0.0, 0.0],
    })


@pytest.fixture
def identical_assets_returns() -> pl.DataFrame:
    """Two assets with identical returns — correlation should be exactly 1.0."""
    return pl.DataFrame({
        "ASSET_01": [0.01, 0.03, -0.01, 0.02],
        "ASSET_02": [0.01, 0.03, -0.01, 0.02],
    })


# ── Portfolio Variance ───────────────────────────────────────
# σ²_portfolio = wᵀ Σ w × 252

class TestPortfolioVariance:

    def test_basic_two_assets(self, basic_returns, basic_weights):
        result = compute_portfolio_variance(basic_returns, basic_weights)
        assert result == pytest.approx(0.058044, rel=1e-4)

    def test_single_asset(self, single_asset_returns):
        result = compute_portfolio_variance(single_asset_returns, (1.0,))
        assert result == pytest.approx(0.0735, rel=1e-4)

    def test_zero_returns(self, zero_returns):
        result = compute_portfolio_variance(zero_returns, (0.5, 0.5))
        assert result == 0.0

    def test_equal_weights(self, basic_returns):
        result = compute_portfolio_variance(basic_returns, (0.5, 0.5))
        assert result == pytest.approx(0.060375, rel=1e-4)

    def test_negative_weights_short_position(self, basic_returns):
        """Short positions should still produce valid variance."""
        result = compute_portfolio_variance(basic_returns, (1.2, -0.2))
        assert result == pytest.approx(0.09610, rel=1e-4)


# ── Annualized Return ────────────────────────────────────────
# mean(daily portfolio returns) × 252

class TestAnnualizedReturn:

    def test_basic_two_assets(self, basic_returns, basic_weights):
        # Daily returns: [0.014, 0.034, -0.002, 0.008], mean=0.0135, ×252=3.402
        result = compute_annualized_return(basic_returns, basic_weights)
        assert result == pytest.approx(3.402, rel=1e-4)

    def test_zero_returns(self, zero_returns):
        result = compute_annualized_return(zero_returns, (0.5, 0.5))
        assert result == 0.0

    def test_single_asset(self, single_asset_returns):
        # mean([0.01, 0.03, -0.01, 0.02]) = 0.0125, × 252 = 3.15
        result = compute_annualized_return(single_asset_returns, (1.0,))
        assert result == pytest.approx(3.15, rel=1e-4)


# ── Sharpe Ratio ─────────────────────────────────────────────
# (annualized_return - risk_free_rate) / annualized_volatility

class TestSharpeRatio:

    def test_basic_zero_risk_free(self, basic_returns, basic_weights):
        result = compute_sharpe_ratio(basic_returns, basic_weights, risk_free_rate=0.0)
        assert result == pytest.approx(14.1207, rel=1e-3)

    def test_with_risk_free_rate(self, basic_returns, basic_weights):
        result = compute_sharpe_ratio(basic_returns, basic_weights, risk_free_rate=0.02)
        assert result == pytest.approx(14.0377, rel=1e-3)

    def test_zero_volatility_returns_zero(self):
        """Constant returns → vol=0 → Sharpe=0.0 by convention."""
        constant = pl.DataFrame({"ASSET_01": [0.01, 0.01, 0.01, 0.01]})
        result = compute_sharpe_ratio(constant, (1.0,), risk_free_rate=0.0)
        assert result == 0.0

    def test_zero_returns(self, zero_returns):
        result = compute_sharpe_ratio(zero_returns, (0.5, 0.5), risk_free_rate=0.0)
        assert result == 0.0

    def test_negative_average_return(self):
        """Losing money on average → negative Sharpe."""
        returns = pl.DataFrame({"ASSET_01": [-0.02, -0.03, 0.01, -0.04, -0.01]})
        result = compute_sharpe_ratio(returns, (1.0,), risk_free_rate=0.0)
        assert result < 0.0

    def test_returns_below_risk_free_rate(self):
        """Positive but tiny returns with high risk-free rate → negative Sharpe."""
        returns = pl.DataFrame({"ASSET_01": [0.0001, 0.0002, 0.0001, 0.0003, 0.0001]})
        result = compute_sharpe_ratio(returns, (1.0,), risk_free_rate=0.10)
        assert result < 0.0

    def test_negative_weights_short_position(self, basic_returns):
        result = compute_sharpe_ratio(basic_returns, (1.2, -0.2), risk_free_rate=0.0)
        assert result == pytest.approx(9.755, rel=1e-3)


# ── Max Drawdown ─────────────────────────────────────────────
# Largest peak-to-trough decline in cumulative returns

class TestMaxDrawdown:

    def test_basic_two_assets(self, basic_returns, basic_weights):
        # Cumulative: [1.014, 1.04848, 1.04638, 1.05475]
        # Drawdown at day 3: (1.04638 - 1.04848) / 1.04848 ≈ -0.002
        result = compute_max_drawdown(basic_returns, basic_weights)
        assert result == pytest.approx(-0.002, abs=1e-4)

    def test_always_positive_returns(self):
        returns = pl.DataFrame({"ASSET_01": [0.01, 0.02, 0.03, 0.01]})
        result = compute_max_drawdown(returns, (1.0,))
        assert result == 0.0

    def test_always_negative_returns(self):
        # Cumulative: [0.95, 0.9215, 0.88464, 0.86695]
        returns = pl.DataFrame({"ASSET_01": [-0.05, -0.03, -0.04, -0.02]})
        result = compute_max_drawdown(returns, (1.0,))
        assert result == pytest.approx(-0.13305, rel=1e-3)

    def test_zero_returns(self, zero_returns):
        result = compute_max_drawdown(zero_returns, (0.5, 0.5))
        assert result == 0.0

    def test_recovery_then_worse_drawdown(self):
        """Two drawdowns: -15% then recovery, then -25%. Should find the worst."""
        returns = pl.DataFrame({"ASSET_01": [0.10, -0.15, 0.20, -0.25, 0.05]})
        result = compute_max_drawdown(returns, (1.0,))
        assert result == pytest.approx(-0.25, rel=1e-3)
        assert result < -0.20

    def test_total_loss(self):
        """A -100% return means total loss → drawdown = -1.0."""
        returns = pl.DataFrame({"ASSET_01": [0.05, -1.0, 0.05]})
        result = compute_max_drawdown(returns, (1.0,))
        assert result == pytest.approx(-1.0)

    def test_negative_weights_short_position(self, basic_returns):
        """Short positions should produce a valid drawdown in [-1, 0]."""
        result = compute_max_drawdown(basic_returns, (1.2, -0.2))
        assert -1.0 <= result <= 0.0


# ── Asset Volatilities ───────────────────────────────────────
# std(daily_returns, ddof=1) × √252

class TestAssetVolatilities:

    def test_basic_two_assets(self, basic_returns):
        result = compute_asset_volatilities(basic_returns)
        assert result[0] == pytest.approx(0.27111, rel=1e-3)
        assert result[1] == pytest.approx(0.33045, rel=1e-3)

    def test_single_asset(self, single_asset_returns):
        result = compute_asset_volatilities(single_asset_returns)
        assert len(result) == 1
        assert result[0] == pytest.approx(0.27111, rel=1e-3)

    def test_zero_returns(self, zero_returns):
        result = compute_asset_volatilities(zero_returns)
        assert all(v == 0.0 for v in result)


# ── Correlation Matrix ───────────────────────────────────────

class TestCorrelationMatrix:

    def test_basic_two_assets(self, basic_returns):
        result = compute_correlation_matrix(basic_returns)
        assert len(result) == 2
        assert len(result[0]) == 2
        # Diagonal = 1.0
        assert result[0][0] == pytest.approx(1.0)
        assert result[1][1] == pytest.approx(1.0)
        # Off-diagonal
        assert result[0][1] == pytest.approx(0.32817, rel=1e-3)
        # Symmetric
        assert result[0][1] == pytest.approx(result[1][0])

    def test_identical_assets(self, identical_assets_returns):
        result = compute_correlation_matrix(identical_assets_returns)
        assert result[0][1] == pytest.approx(1.0)

    def test_single_asset(self, single_asset_returns):
        result = compute_correlation_matrix(single_asset_returns)
        assert len(result) == 1
        assert result[0][0] == pytest.approx(1.0)


# ── Large Dataset ────────────────────────────────────────────

class TestLargeDataset:

    def test_five_years_of_data(self):
        """1260 days (~5 years) should compute without issues."""
        import numpy as np
        rng = np.random.default_rng(42)
        n_days = 1260
        returns = pl.DataFrame({
            "ASSET_01": rng.normal(0.0003, 0.01, n_days).tolist(),
            "ASSET_02": rng.normal(0.0002, 0.015, n_days).tolist(),
            "ASSET_03": rng.normal(0.0001, 0.02, n_days).tolist(),
        })
        weights = (0.5, 0.3, 0.2)

        assert compute_portfolio_variance(returns, weights) == pytest.approx(0.01589, rel=1e-2)
        assert compute_sharpe_ratio(returns, weights) == pytest.approx(0.037, rel=1e-1)
        assert compute_max_drawdown(returns, weights) == pytest.approx(-0.3208, rel=1e-2)


# ── Sortino Ratio ────────────────────────────────────────────
# (annualized_return - risk_free_rate) / downside_deviation

class TestSortinoRatio:

    def test_with_multiple_negative_returns(self):
        """Hand-calculated: neg returns [-0.03, -0.02, -0.01], downside std=0.01."""
        returns = pl.DataFrame({"ASSET_01": [0.02, -0.03, 0.01, -0.02, 0.04, -0.01]})
        result = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.0)
        assert result == pytest.approx(2.6457, rel=1e-2)

    def test_no_negative_returns(self):
        """No negative returns → downside deviation is 0 → Sortino = 0.0."""
        returns = pl.DataFrame({"ASSET_01": [0.01, 0.02, 0.03, 0.01]})
        result = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.0)
        assert result == 0.0

    def test_single_negative_return(self):
        """Exactly 1 negative return → std(ddof=1) undefined for n=1 → Sortino = 0.0."""
        returns = pl.DataFrame({"ASSET_01": [0.01, -0.01, 0.02, 0.03]})
        result = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.0)
        assert result == 0.0

    def test_all_negative_returns(self):
        returns = pl.DataFrame({"ASSET_01": [-0.02, -0.03, -0.01, -0.04]})
        result = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.0)
        assert result < 0.0

    def test_higher_than_sharpe_with_upside_skew(self):
        """Positive skew: most vol is upside → Sortino > Sharpe."""
        returns = pl.DataFrame({
            "ASSET_01": [-0.005, -0.003, 0.05, -0.002, -0.004, 0.06, -0.001, 0.04],
        })
        sharpe = compute_sharpe_ratio(returns, (1.0,), risk_free_rate=0.0)
        sortino = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.0)
        assert sortino > sharpe

    def test_with_risk_free_rate(self):
        """Higher risk-free rate should reduce Sortino."""
        returns = pl.DataFrame({"ASSET_01": [0.02, -0.03, 0.01, -0.02, 0.04, -0.01]})
        sortino_zero = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.0)
        sortino_high = compute_sortino_ratio(returns, (1.0,), risk_free_rate=0.05)
        assert sortino_high < sortino_zero

    def test_zero_returns(self, zero_returns):
        result = compute_sortino_ratio(zero_returns, (0.5, 0.5), risk_free_rate=0.0)
        assert result == 0.0

    def test_negative_weights_short_position(self):
        """Short positions should produce a valid finite Sortino."""
        returns = pl.DataFrame({
            "ASSET_01": [0.02, -0.03, 0.01, -0.02, 0.04, -0.01],
            "ASSET_02": [-0.01, 0.02, -0.02, 0.03, -0.01, 0.02],
        })
        import math
        result = compute_sortino_ratio(returns, (1.2, -0.2), risk_free_rate=0.0)
        assert math.isfinite(result)


# ── Win Rate ─────────────────────────────────────────────────
# count(daily_return > 0) / total_days

class TestWinRate:

    def test_basic_two_assets(self, basic_returns, basic_weights):
        # Daily returns: [0.014, 0.034, -0.002, 0.008] → 3/4 positive
        result = compute_win_rate(basic_returns, basic_weights)
        assert result == pytest.approx(0.75)

    def test_all_positive(self):
        returns = pl.DataFrame({"ASSET_01": [0.01, 0.02, 0.03, 0.01]})
        assert compute_win_rate(returns, (1.0,)) == 1.0

    def test_all_negative(self):
        returns = pl.DataFrame({"ASSET_01": [-0.01, -0.02, -0.03, -0.01]})
        assert compute_win_rate(returns, (1.0,)) == 0.0

    def test_zero_returns_not_counted_as_wins(self, zero_returns):
        assert compute_win_rate(zero_returns, (0.5, 0.5)) == 0.0

    def test_exactly_half(self):
        returns = pl.DataFrame({"ASSET_01": [0.01, -0.01, 0.02, -0.02]})
        assert compute_win_rate(returns, (1.0,)) == 0.5

    def test_negative_weights_short_position(self, basic_returns):
        """Short positions should produce a valid win rate in [0, 1]."""
        result = compute_win_rate(basic_returns, (1.2, -0.2))
        assert 0.0 <= result <= 1.0
