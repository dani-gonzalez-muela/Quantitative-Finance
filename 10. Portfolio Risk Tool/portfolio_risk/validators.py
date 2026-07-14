"""
Pure validation functions for data and weight inputs.

Instead of raising exceptions (side effects), these return explicit result
objects that the caller can inspect. Keeps all validation logic pure and testable.

Pipeline order:
    1. validate_data()   — checks and cleans the raw DataFrame
    2. validate_weights() — checks weights against surviving assets, renormalizes if needed
"""

from __future__ import annotations

import polars as pl

from portfolio_risk.models import (
    DataValidationResult,
    PortfolioConfig,
    ReturnsData,
    WeightValidationResult,
)


NAN_THRESHOLD: float = 0.05      # assets above 5% NaN are dropped
MIN_ROWS: int = 2                # std(ddof=1) needs at least 2 data points
WEIGHT_SUM_TOLERANCE: float = 1e-6  # 1/3 + 1/3 + 1/3 ≈ 0.9999999999999999


# ── Data Validation ──────────────────────────────────────────

def validate_data(raw_df: pl.DataFrame) -> DataValidationResult:
    """
    Validate and clean a raw DataFrame of asset returns.

    Steps:
        1. Reject empty DataFrames or those with < 2 rows
        2. Separate numeric columns from non-numeric/null columns
        3. Drop assets with >5% NaN (unreliable data)
        4. Fill remaining NaNs with 0.0 (assumes no price movement)
        5. Wrap in ReturnsData container

    NaN fill rationale: 0.0 return is correct for market closures and
    conservative for data gaps (slightly understates volatility).

    Args:
        raw_df: Raw Polars DataFrame, typically from pl.read_csv().

    Returns:
        DataValidationResult with is_valid, cleaned data (or None), and message.
    """
    if raw_df.width == 0 or raw_df.height == 0:
        return DataValidationResult(
            is_valid=False, data=None,
            message="DataFrame is empty (no rows or no columns).",
        )

    if raw_df.height < MIN_ROWS:
        return DataValidationResult(
            is_valid=False, data=None,
            message=f"Need at least {MIN_ROWS} rows to compute statistics, got {raw_df.height}.",
        )

    messages = []
    warnings = []
    non_date_columns = tuple(col for col in raw_df.columns if col.lower() != "date")

    numeric_columns = tuple(
        col for col in non_date_columns
        if raw_df[col].dtype.is_numeric()
    )

    # Polars types all-null columns as Null dtype — they won't pass is_numeric()
    null_columns = tuple(
        col for col in non_date_columns
        if raw_df[col].dtype == pl.Null
    )

    if len(null_columns) > 0:
        msg = f"Dropped assets with no valid data (100% NaN): {', '.join(null_columns)}."
        messages.append(msg)
        warnings.append(msg)

    if len(numeric_columns) == 0:
        msg = f"No valid asset columns. {messages[0]}" if null_columns else "No numeric asset columns found in DataFrame."
        return DataValidationResult(is_valid=False, data=None, message=msg)

    # .select() returns a new DataFrame — original untouched
    numeric_df = raw_df.select(numeric_columns)

    # NaN fraction per column
    nan_fractions = {
        col: numeric_df[col].null_count() / numeric_df.height
        for col in numeric_columns
    }

    assets_to_drop = tuple(col for col, frac in nan_fractions.items() if frac > NAN_THRESHOLD)
    assets_to_keep = tuple(col for col in numeric_columns if col not in assets_to_drop)

    if len(assets_to_drop) > 0:
        drop_details = ", ".join(f"{col} ({nan_fractions[col]:.1%} NaN)" for col in assets_to_drop)
        msg = f"Dropped assets exceeding {NAN_THRESHOLD:.0%} NaN threshold: {drop_details}."
        messages.append(msg)
        warnings.append(msg)

    if len(assets_to_keep) == 0:
        return DataValidationResult(
            is_valid=False, data=None,
            message="All assets exceed NaN threshold — no valid data remaining.",
        )

    clean_df = numeric_df.select(assets_to_keep)

    # Fill surviving NaNs with 0.0
    remaining_nans = clean_df.null_count().sum_horizontal().item()
    if remaining_nans > 0:
        clean_df = clean_df.fill_null(0.0)
        msg = f"Filled {remaining_nans} NaN values with 0.0 (assumed no price movement)."
        messages.append(msg)
        warnings.append(msg)

    if len(messages) == 0:
        messages.append("Data validation passed with no issues.")

    returns_data = ReturnsData(
        data=clean_df,
        asset_names=assets_to_keep,
        n_days=clean_df.height,
        n_assets=clean_df.width,
    )

    return DataValidationResult(is_valid=True, data=returns_data, message=" ".join(messages), warnings=tuple(warnings))


# ── Weight Validation ────────────────────────────────────────

def validate_weights(
    weights: tuple[float, ...],
    original_assets: tuple[str, ...],
    surviving_assets: tuple[str, ...],
    risk_free_rate: float = 0.0,
) -> WeightValidationResult:
    """
    Validate portfolio weights against the surviving asset list.

    If assets were dropped during data validation, corresponding weights
    are removed and remaining weights renormalized to preserve the user's
    intended relative allocation.

    Example:
        Original: A=0.4, B=0.2, C=0.4 → B dropped → A=0.5, C=0.5

    Args:
        weights: User-provided weights (one per original asset).
        original_assets: All asset names the user provided weights for.
        surviving_assets: Assets that passed data validation.
        risk_free_rate: Annualized risk-free rate.

    Returns:
        WeightValidationResult with is_valid, config (or None), and message.
    """
    if len(weights) != len(original_assets):
        return WeightValidationResult(
            is_valid=False, config=None,
            message=(
                f"Number of weights ({len(weights)}) does not match "
                f"number of assets ({len(original_assets)})."
            ),
        )

    asset_weight_map = dict(zip(original_assets, weights))
    surviving_weights = tuple(
        asset_weight_map[asset] for asset in surviving_assets
        if asset in asset_weight_map
    )

    messages = []
    warnings = []
    needs_renormalization = len(surviving_assets) < len(original_assets)

    if needs_renormalization:
        weight_sum = sum(surviving_weights)

        if weight_sum == 0.0:
            return WeightValidationResult(
                is_valid=False, config=None,
                message="Surviving asset weights sum to 0.0 — cannot renormalize.",
            )

        renormalized_weights = tuple(w / weight_sum for w in surviving_weights)

        dropped = set(original_assets) - set(surviving_assets)
        msg = (
            f"Assets dropped during validation: {', '.join(sorted(dropped))}. "
            f"Weights renormalized from {weight_sum:.4f} to 1.0. "
            f"Adjusted weights: {', '.join(f'{w:.4f}' for w in renormalized_weights)}."
        )
        messages.append(msg)
        warnings.append(msg)

        final_weights = renormalized_weights
    else:
        final_weights = surviving_weights

    weight_sum = sum(final_weights)
    if abs(weight_sum - 1.0) > WEIGHT_SUM_TOLERANCE:
        return WeightValidationResult(
            is_valid=False, config=None,
            message=(
                f"Weights must sum to 1.0, but got {weight_sum:.6f}. "
                f"Difference: {abs(weight_sum - 1.0):.6f}."
            ),
        )

    if len(messages) == 0:
        messages.append("Weight validation passed.")

    config = PortfolioConfig(
        asset_names=surviving_assets,
        weights=final_weights,
        risk_free_rate=risk_free_rate,
    )

    return WeightValidationResult(is_valid=True, config=config, message=" ".join(messages), warnings=tuple(warnings))
