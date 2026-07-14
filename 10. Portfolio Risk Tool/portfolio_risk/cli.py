"""
Command-line interface for the portfolio risk analysis tool.

Imperative shell — thinnest possible wrapper around the pure pipeline.
Handles argument parsing, config loading, and output formatting.
No business logic lives here.

Usage:
    python -m portfolio_risk --csv sample_returns.csv --weights 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1
    python -m portfolio_risk --config portfolio.json
"""

from __future__ import annotations

import argparse
import json
import sys

from portfolio_risk.pipeline import load_csv, detect_assets, run_pipeline


def load_config(config_path: str) -> dict | None:
    """Load a JSON config file. Returns None on failure (no exceptions leak)."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def build_parser() -> argparse.ArgumentParser:
    """
    Build the argument parser.

    Two modes: --config file.json, or --csv + --weights + optional --risk-free-rate.
    Separated into its own function for testability.
    """
    parser = argparse.ArgumentParser(
        prog="portfolio_risk",
        description=(
            "Analyze a portfolio of assets for basic risk metrics. "
            "Reads a CSV of daily returns, validates the data, and computes "
            "portfolio variance, Sharpe ratio, max drawdown, and more."
        ),
        epilog=(
            "Examples:\n"
            "  python -m portfolio_risk --csv sample_returns.csv "
            "--weights 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1 0.1\n\n"
            "  python -m portfolio_risk --config portfolio.json\n\n"
            "The tool auto-detects asset columns from the CSV. "
            "Weights are assigned to assets in column order."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--config", help="Path to JSON config file (alternative to --csv and --weights)")
    parser.add_argument("--csv", help="Path to CSV file with daily returns")
    parser.add_argument("--weights", nargs="+", type=float, help="Portfolio weights (must sum to 1.0)")
    parser.add_argument("--risk-free-rate", type=float, default=0.0, help="Annualized risk-free rate (default: 0.0)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON instead of summary")

    return parser


def _print_error_and_exit(message: str) -> None:
    """Print a JSON error message and exit with code 1."""
    print(json.dumps({"status": "error", "message": message}, indent=2))
    sys.exit(1)


def _print_summary(result: dict) -> None:
    """
    Print a human-readable summary of the pipeline result.

    Correlation matrix compressed to top 3 positive/negative pairs —
    nobody reads a 10×10 matrix in a terminal.
    """
    if result["status"] == "error":
        print(f"Error: {result['message']}")
        return

    metrics = result["metrics"]
    config = result["config"]
    asset_names = config["asset_names"]
    volatility = metrics["portfolio_variance"] ** 0.5

    print()
    print("Portfolio Risk Analysis")
    print("=" * 45)
    print(f"  Annualized Return:    {metrics['annualized_return']:>8.2%}")
    print(f"  Portfolio Volatility: {volatility:>8.2%}")
    print(f"  Sharpe Ratio:         {metrics['sharpe_ratio']:>8.4f}")
    print(f"  Sortino Ratio:        {metrics['sortino_ratio']:>8.4f}")
    print(f"  Max Drawdown:         {metrics['max_drawdown']:>8.2%}")
    print(f"  Win Rate:             {metrics['win_rate']:>8.2%}")
    print(f"  Risk-Free Rate:       {config['risk_free_rate']:>8.2%}")
    print()

    print("Asset Volatilities")
    print("-" * 45)
    for name, vol in zip(asset_names, metrics["asset_volatilities"]):
        print(f"  {name:<12} {vol:>8.2%}")
    print()

    # Extract upper triangle, sort by correlation value
    corr = metrics["correlation_matrix"]
    n = len(asset_names)
    pairs = [
        (asset_names[i], asset_names[j], corr[i][j])
        for i in range(n) for j in range(i + 1, n)
    ]
    pairs.sort(key=lambda x: x[2], reverse=True)
    top_n = min(3, len(pairs))

    if pairs:
        print("Top Positive Correlations")
        print("-" * 45)
        for a, b, c in pairs[:top_n]:
            print(f"  {a} / {b:<12} {c:>+.4f}")
        print()

        print("Top Negative Correlations")
        print("-" * 45)
        for a, b, c in pairs[-top_n:]:
            print(f"  {a} / {b:<12} {c:>+.4f}")
        print()

    if result.get("warnings"):
        print("Warnings")
        print("-" * 45)
        print(f"  {result['warnings']}")
        print()


def main() -> None:
    """Main entry point. Parse args → load CSV → detect assets → run pipeline → print."""
    parser = build_parser()
    args = parser.parse_args()
    use_json = args.json

    # Resolve config from JSON file or CLI args
    if args.config:
        config = load_config(args.config)
        if config is None:
            _print_error_and_exit(f"Could not read or parse config file: {args.config}")

        csv_path = config.get("csv")
        weights_list = config.get("weights")
        risk_free_rate = config.get("risk_free_rate", 0.0)

        if csv_path is None or weights_list is None:
            _print_error_and_exit(
                "Config file must contain 'csv' and 'weights' keys. "
                "Example: {\"csv\": \"data.csv\", \"weights\": [0.5, 0.5]}"
            )
        weights = tuple(weights_list)
    elif args.csv and args.weights:
        csv_path = args.csv
        weights = tuple(args.weights)
        risk_free_rate = args.risk_free_rate
    else:
        _print_error_and_exit(
            "Provide either --config <file.json> or both --csv and --weights. "
            "Run with --help for usage."
        )
        return

    # Load CSV and detect assets
    raw_df = load_csv(csv_path)
    if raw_df is None:
        _print_error_and_exit(f"Could not read CSV file: {csv_path}")

    detected_assets = detect_assets(raw_df)
    if len(detected_assets) == 0:
        _print_error_and_exit("No numeric asset columns found in CSV.")

    if len(weights) != len(detected_assets):
        asset_list = ", ".join(detected_assets)
        _print_error_and_exit(
            f"Found {len(detected_assets)} assets in CSV "
            f"({asset_list}) but received {len(weights)} weights. "
            f"Please provide exactly {len(detected_assets)} weights."
        )

    # Pass pre-loaded DataFrame to avoid double file read
    result = run_pipeline(
        file_path=csv_path,
        weights=weights,
        asset_names=detected_assets,
        risk_free_rate=risk_free_rate,
        raw_df=raw_df,
    )

    result_dict = result.to_dict()

    if use_json:
        print(json.dumps(result_dict, indent=2))
    else:
        _print_summary(result_dict)

    if result_dict["status"] == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
