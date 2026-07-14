"""
Immutable data structures for the portfolio risk analysis pipeline.

All dataclasses are frozen — data cannot be modified after creation.
New instances are created at each pipeline stage:

    PortfolioConfig → DataValidationResult → WeightValidationResult → RiskMetrics
"""

from __future__ import annotations

from dataclasses import dataclass
import polars as pl


# ── Input ────────────────────────────────────────────────────

@dataclass(frozen=True)
class PortfolioConfig:
    """
    User-defined portfolio configuration, created from CLI arguments.

    Attributes:
        asset_names: Names of assets in the portfolio.
        weights: Allocation per asset, must sum to 1.0. Negative values
                 represent short positions (e.g., (1.2, -0.2) is 120% long
                 asset A, 20% short asset B).
        risk_free_rate: Annualized risk-free rate for Sharpe/Sortino (default 0.0).
    """
    asset_names: tuple[str, ...]
    weights: tuple[float, ...]
    risk_free_rate: float = 0.0


# ── Pipeline Data Container ─────────────────────────────────

@dataclass(frozen=True)
class ReturnsData:
    """
    Validated and cleaned returns data, created after CSV validation.

    Acts as a type-level marker that the data has passed all checks
    (no NaNs, correct columns, numeric values) and is safe for computation.

    Attributes:
        data: Polars DataFrame of daily returns (immutable by default).
        asset_names: Column names matching the assets in the DataFrame.
        n_days: Number of trading days (rows).
        n_assets: Number of assets (columns).
    """
    data: pl.DataFrame
    asset_names: tuple[str, ...]
    n_days: int
    n_assets: int


# ── Validation Result Types ──────────────────────────────────
# Instead of raising exceptions (side effects), validators return explicit
# result objects. Keeps validation functions pure and testable.

@dataclass(frozen=True)
class DataValidationResult:
    """
    Result of data validation, returned by validate_data().

    Attributes:
        is_valid: True if data passed validation (possibly with warnings).
        data: Validated ReturnsData if successful, None on failure.
        message: What happened — errors, dropped assets, or filled NaNs.
        warnings: Structured warning messages for downstream consumers.
    """
    is_valid: bool
    data: ReturnsData | None
    message: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeightValidationResult:
    """
    Result of weight validation, returned by validate_weights().

    If assets were dropped during data validation, corresponding weights
    are removed and remaining weights renormalized to sum to 1.0.

    Attributes:
        is_valid: True if weights are valid (possibly after renormalization).
        config: Validated PortfolioConfig if successful, None on failure.
        message: What happened — errors or renormalization details.
        warnings: Structured warning messages for downstream consumers.
    """
    is_valid: bool
    config: PortfolioConfig | None
    message: str
    warnings: tuple[str, ...] = ()


# ── Output ───────────────────────────────────────────────────

@dataclass(frozen=True)
class RiskMetrics:
    """
    Computed risk metrics for the portfolio. Final pipeline output.

    All values annualized assuming 252 trading days/year.
    """
    portfolio_variance: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    asset_volatilities: tuple[float, ...]
    correlation_matrix: tuple[tuple[float, ...], ...]

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict. Pure transformation."""
        return {
            "portfolio_variance": self.portfolio_variance,
            "annualized_return": self.annualized_return,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            # tuple → list at the output boundary for JSON compatibility
            "asset_volatilities": list(self.asset_volatilities),
            "correlation_matrix": [list(row) for row in self.correlation_matrix],
        }


@dataclass(frozen=True)
class PipelineResult:
    """
    Final output of the pipeline. Either a success with metrics or an error.

    Replaces raw dicts with a typed, immutable container — consistent with
    the FP approach used throughout the rest of the pipeline.

    Attributes:
        status: "success" or "error".
        message: Error description (only meaningful when status == "error").
        config: Portfolio configuration used (None on error).
        metrics: Computed risk metrics (None on error).
        warnings: Collected warnings from validation steps.
    """
    status: str
    message: str = ""
    config: PortfolioConfig | None = None
    metrics: RiskMetrics | None = None
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict for CLI output."""
        if self.status == "error":
            return {"status": "error", "message": self.message}

        return {
            "status": "success",
            "config": {
                "asset_names": list(self.config.asset_names),
                "weights": list(self.config.weights),
                "risk_free_rate": self.config.risk_free_rate,
            },
            "metrics": self.metrics.to_dict(),
            "warnings": " ".join(self.warnings) if self.warnings else None,
        }
