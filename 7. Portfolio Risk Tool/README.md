# Portfolio Risk Analysis Tool

A command-line tool that computes risk metrics for a portfolio of assets, built with **functional programming principles** and **test-driven development**.

## Quick Start

```bash
pip install polars numpy pytest pytest-cov hypothesis

# Run with CLI args
python -m portfolio_risk --csv sample_returns.csv --weights 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1

# Run with a config file
python -m portfolio_risk --config portfolio.json

# JSON output instead of summary
python -m portfolio_risk --csv sample_returns.csv --weights 0.5 0.5 --json

# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=portfolio_risk --cov-report=term-missing
```

## Metrics

All metrics annualized assuming 252 trading days/year.

- **Portfolio Variance**: `wᵀΣw × 252` — weighted covariance matrix approach
- **Annualized Return**: `mean(daily portfolio returns) × 252`
- **Sharpe Ratio**: `(return - risk_free) / volatility` — returns 0.0 when vol is zero
- **Sortino Ratio**: Like Sharpe, but only penalizes downside volatility — returns 0.0 when fewer than 2 negative returns (std undefined for n=1)
- **Max Drawdown**: Largest peak-to-trough decline, computed via `functools.reduce`
- **Win Rate**: Fraction of days with positive returns (zero returns are not counted as wins)
- **Per-Asset Volatilities**: `std(daily, ddof=1) × √252`
- **Correlation Matrix**: Pairwise Pearson correlation between all assets

## Architecture

```
portfolio_risk/
├── models.py        # Frozen dataclasses (PortfolioConfig, ReturnsData, RiskMetrics, validation results)
├── metrics.py       # Pure metric functions (variance, Sharpe, Sortino, drawdown, etc.)
├── validators.py    # Pure validation → returns result objects instead of raising exceptions
├── pipeline.py      # Composition: load → validate → compute → output
├── cli.py           # Imperative shell: argparse, JSON/summary output
└── __main__.py      # Entry point for python -m portfolio_risk

tests/
├── test_metrics.py      # 43 unit tests — hand-calculated expected values, edge cases
├── test_validators.py   # 18 unit tests — data quality, weight normalization, edge cases
├── test_pipeline.py     # 13 integration tests — detect_assets + end-to-end pipeline
├── test_cli.py          #  8 E2E tests — argument parsing, output format, config mode
└── test_properties.py   # 16 unit tests — Hypothesis property-based testing (~2000 random inputs)
```

**98 tests, 94% coverage.**

## Functional Programming Design

### Immutability

All data structures use `@dataclass(frozen=True)` with `tuple` fields instead of `list`. Polars DataFrames are immutable by default — every `.select()`, `.filter()`, or `.fill_null()` returns a new DataFrame. The original is never modified.

### Pure Functions

Every function in `metrics.py` and `validators.py` takes typed inputs and returns typed outputs with no side effects. No file I/O, no printing, no mutation. The only impure function in the entire pipeline is `load_csv()`, which reads from disk.

### Composability

Two levels of composition:

1. **Pipeline level**: `load_csv → validate_data → validate_weights → compute_all_metrics` — each stage consumes the previous stage's output.
2. **Metric level**: The daily portfolio return series is computed once by `compute_daily_portfolio_returns` and passed to Sharpe, Sortino, drawdown, and win rate. `compute_sharpe_ratio` composes `compute_annualized_return` and `compute_portfolio_variance` rather than reimplementing their logic.

### FP Error Handling

Validators return explicit result objects (`DataValidationResult`, `WeightValidationResult`) instead of raising exceptions. This keeps validation functions pure — the caller decides what to do with errors. Error paths are testable just like happy paths.

```python
result = validate_data(raw_df)
if not result.is_valid:
    return {"status": "error", "message": result.message}
# result.data is a validated ReturnsData container
```

### Functional Core, Imperative Shell

All I/O (file reading, CLI parsing, printing) lives at the edges in `cli.py` and `load_csv()`. The core logic in `validators.py`, `metrics.py`, and `models.py` never touches the filesystem. This means the entire computation layer is trivially testable without mocking.

### No Loops in Core Logic

`compute_max_drawdown` uses `functools.reduce` to carry `(cumulative, peak, max_drawdown)` state through the return sequence. Column operations use Polars expressions and comprehensions.

### Why Polars Over Pandas

Polars DataFrames are immutable by default — every operation returns a new DataFrame rather than modifying in place. If the project's core principle is immutability, the data layer should enforce it too, not just the function signatures.

## Testing Strategy

Tests follow the **testing pyramid**: many fast unit tests at the base, integration tests in the middle, and a few E2E tests at the top.

### Unit Tests (test_metrics.py, test_validators.py, test_properties.py)

Hand-calculated expected values using simple data that can be verified on paper. Covers edge cases like:
- Zero returns, single asset portfolios
- Negative weights (short positions) across all portfolio-level metrics
- Total portfolio loss (-100% return)
- Floating point tolerance (1/3 + 1/3 + 1/3 ≈ 0.9999999999999999)
- Sortino with exactly 1 negative return (std undefined for n=1)
- All-NaN assets, assets exceeding NaN threshold

Hypothesis property-based tests generate ~2000 random portfolios and verify mathematical invariants:
- Variance is always non-negative
- Drawdown is always in [-1, 0]
- Correlations are always in [-1, 1], symmetric, with diagonal of 1s
- Win rate is always in [0, 1]
- Renormalized weights always sum to 1.0
- Sharpe and Sortino are always finite

During development, Hypothesis discovered that all-zero returns produce NaN correlations via `np.corrcoef` — an edge case that wouldn't surface from hand-written tests.

### Integration Tests (test_pipeline.py)

End-to-end flow from CSV to output dict, plus unit tests for `detect_assets` and `load_csv`. Verifies that all pieces compose correctly together and that error paths (bad file, bad weights, missing assets) return structured error responses.

### E2E Tests (test_cli.py)

Invoke `main()` with real arguments and verify full system behavior: argument parsing, JSON output format, human-readable summary, config file mode, and error messages for common mistakes (wrong weight count includes the asset names and count in the error message).

### Why No Mocking?

The architecture makes mocking unnecessary. Since all core logic is pure functions with no external dependencies, tests call functions directly with test data. The only impure function (`load_csv`) is tested with real temp files via pytest's `tmp_path` fixture — no need to mock file I/O.

## Data Validation

- **Assets with >5% missing data**: Dropped entirely with a warning
- **Remaining NaNs**: Filled with 0.0 (assumes no price movement — correct for market closures, conservative for data gaps)
- **Weight renormalization**: If assets are dropped, corresponding weights are removed and remaining weights renormalized to preserve relative allocation
- **Non-numeric columns**: Silently excluded
- **Friendly errors**: Wrong weight count tells you exactly how many assets were detected and their names

## Sample Data

`sample_returns.csv` contains 504 trading days (~2 years) of daily returns for 10 fictional assets with varying volatilities (8%–35%), correlated returns, and 15 intentional NaN values. Generated by `generate_sample_data.py` for reproducibility.
