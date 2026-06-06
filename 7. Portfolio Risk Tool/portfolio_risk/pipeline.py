"""
Pipeline composition: chains all steps from CSV loading to metric output.

Architecture: "functional core, imperative shell"
    - load_csv() is the ONLY impure function (file I/O)
    - Everything after loading is pure function composition

Flow: load_csv → validate_data → validate_weights → compute_all_metrics → PipelineResult

run_pipeline() returns a typed PipelineResult (frozen dataclass) with either
computed metrics or an error message. No exceptions — explicit error handling throughout.
"""

from __future__ import annotations

import polars as pl

from portfolio_risk.models import (
    DataValidationResult,
    PipelineResult,
    PortfolioConfig,
    ReturnsData,
    RiskMetrics,
    WeightValidationResult,
)
from portfolio_risk.validators import validate_data, validate_weights
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


# ── Impure Shell: File I/O ───────────────────────────────────

def load_csv(file_path: str) -> pl.DataFrame | None:
    """
    Load a CSV file into a Polars DataFrame.

    The ONLY impure function in the pipeline — everything else is pure.

    Args:
        file_path: Path to the CSV file.

    Returns:
        Polars DataFrame if successful, None if file cannot be read.
    """
    try:
        return pl.read_csv(file_path)
    except Exception:
        return None


def detect_assets(df: pl.DataFrame) -> tuple[str, ...]:
    """
    Auto-detect asset columns from a DataFrame.

    Identifies numeric columns, excludes 'date'. Returns names in column order.

    Args:
        df: Raw Polars DataFrame loaded from CSV.

    Returns:
        Tuple of asset column names.
    """
    return tuple(
        col for col in df.columns
        if col.lower() != "date" and df[col].dtype.is_numeric()
    )


# ── Pure Core: Metric Computation ────────────────────────────

def compute_all_metrics(
    returns_data: ReturnsData,
    config: PortfolioConfig,
) -> RiskMetrics:
    """
    Compute all risk metrics for the portfolio.

    The daily portfolio return series is computed once and shared across
    all downstream metrics that need it.

    Args:
        returns_data: Validated and cleaned returns data.
        config: Validated portfolio configuration with weights.

    Returns:
        Frozen RiskMetrics dataclass.
    """
    returns_df = returns_data.data
    weights = config.weights

    # Compute once, pass to all consumers
    portfolio_returns = compute_daily_portfolio_returns(returns_df, weights)

    return RiskMetrics(
        portfolio_variance=compute_portfolio_variance(returns_df, weights),
        annualized_return=compute_annualized_return(returns_df, weights, portfolio_returns),
        sharpe_ratio=compute_sharpe_ratio(returns_df, weights, config.risk_free_rate, portfolio_returns),
        sortino_ratio=compute_sortino_ratio(returns_df, weights, config.risk_free_rate, portfolio_returns),
        max_drawdown=compute_max_drawdown(returns_df, weights, portfolio_returns),
        win_rate=compute_win_rate(returns_df, weights, portfolio_returns),
        asset_volatilities=compute_asset_volatilities(returns_df),
        correlation_matrix=compute_correlation_matrix(returns_df),
    )


# ── Pipeline Composition ────────────────────────────────────

def run_pipeline(
    file_path: str,
    weights: tuple[float, ...],
    asset_names: tuple[str, ...],
    risk_free_rate: float = 0.0,
    raw_df: pl.DataFrame | None = None,
) -> PipelineResult:
    """
    Run the full portfolio risk analysis pipeline.

    Each step checks the previous result before proceeding. If any step
    fails, returns an error PipelineResult immediately (no exceptions).

    Args:
        file_path: Path to CSV file with daily returns.
        weights: Portfolio weights (one per asset).
        asset_names: Asset names corresponding to the weights.
        risk_free_rate: Annualized risk-free rate (default 0.0).
        raw_df: Pre-loaded DataFrame (optional, avoids double file read from CLI).

    Returns:
        PipelineResult (frozen dataclass) with status, metrics, config, and warnings.
    """
    if raw_df is None:
        raw_df = load_csv(file_path)
    if raw_df is None:
        return PipelineResult(
            status="error",
            message=f"Could not read CSV file: {file_path}",
        )

    # Check that requested assets exist in the CSV
    csv_columns = tuple(raw_df.columns)
    missing_assets = tuple(a for a in asset_names if a not in csv_columns)
    if len(missing_assets) > 0:
        return PipelineResult(
            status="error",
            message=(
                f"Assets not found in CSV: {', '.join(missing_assets)}. "
                f"Available columns: {', '.join(csv_columns)}."
            ),
        )

    data_result: DataValidationResult = validate_data(raw_df)
    if not data_result.is_valid:
        return PipelineResult(
            status="error",
            message=f"Data validation failed: {data_result.message}",
        )

    weight_result: WeightValidationResult = validate_weights(
        weights=weights,
        original_assets=asset_names,
        surviving_assets=data_result.data.asset_names,
        risk_free_rate=risk_free_rate,
    )
    if not weight_result.is_valid:
        return PipelineResult(
            status="error",
            message=f"Weight validation failed: {weight_result.message}",
        )

    metrics: RiskMetrics = compute_all_metrics(data_result.data, weight_result.config)

    # Collect warnings from validation steps (structured, no string matching)
    all_warnings = data_result.warnings + weight_result.warnings

    return PipelineResult(
        status="success",
        config=weight_result.config,
        metrics=metrics,
        warnings=all_warnings,
    )
