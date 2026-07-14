"""
shared.metrics — Standardized performance metrics.

All strategies produce a trades DataFrame with at least these columns:
    entry_time, exit_time, position, entry_price, exit_price,
    exit_reason, risk, shares, gross_pnl, fees, net_pnl,
    equity_before, equity

The functions here consume that standard format.
"""

import numpy as np
import pandas as pd


# ── Required columns ──
REQUIRED_COLUMNS = [
    "entry_time", "exit_time", "position", "entry_price", "exit_price",
    "exit_reason", "risk", "shares", "gross_pnl", "fees", "net_pnl",
    "equity_before", "equity",
]


def validate_trades(trades_df):
    """Check that trades_df has the required columns."""
    missing = [c for c in REQUIRED_COLUMNS if c not in trades_df.columns]
    if missing:
        raise ValueError(f"Trades DataFrame missing required columns: {missing}")


def evaluate_strategy(trades_df, name="Strategy", starting_capital=None):
    """
    Compute performance metrics from a standardized trades DataFrame.

    Parameters
    ----------
    trades_df        : pd.DataFrame — must contain REQUIRED_COLUMNS.
    name             : str          — label for this strategy.
    starting_capital : float or None — inferred from equity_before if not given.

    Returns
    -------
    dict with all metrics. Suitable for pd.DataFrame([result1, result2, ...]).
    """
    validate_trades(trades_df)

    if trades_df.empty:
        return {"Strategy": name, "Trades": 0}

    df = trades_df.copy().sort_values("entry_time").reset_index(drop=True)

    if starting_capital is None:
        starting_capital = df["equity_before"].iloc[0]

    final_equity = df["equity"].iloc[-1]
    total_return = (final_equity / starting_capital) - 1
    days = (df["exit_time"].iloc[-1] - df["entry_time"].iloc[0]).days
    annualized = (1 + total_return) ** (252 / max(days, 1)) - 1

    # ── Drawdown ──
    running_max = df["equity"].expanding().max()
    drawdown_series = (df["equity"] - running_max) / running_max
    max_dd = drawdown_series.min()

    # ── Risk-adjusted returns ──
    returns = df["net_pnl"] / df["equity_before"]

    sharpe = 0
    if returns.std() > 0:
        sharpe = returns.mean() / returns.std() * np.sqrt(252)

    downside = returns[returns < 0]
    sortino = 0
    if len(downside) > 0 and downside.std() > 0:
        sortino = returns.mean() / downside.std() * np.sqrt(252)

    # ── Win/loss ──
    winners = df[df["net_pnl"] > 0]
    losers = df[df["net_pnl"] <= 0]
    win_rate = len(winners) / len(df) if len(df) > 0 else 0

    avg_win = winners["net_pnl"].mean() if len(winners) > 0 else 0
    avg_loss = losers["net_pnl"].mean() if len(losers) > 0 else 0
    profit_factor = abs(winners["net_pnl"].sum() / losers["net_pnl"].sum()) if losers["net_pnl"].sum() != 0 else float("inf")

    # ── Long vs Short ──
    long_trades = df[df["position"] == "long"]
    short_trades = df[df["position"] == "short"]

    long_pnl = long_trades["net_pnl"].sum() if len(long_trades) > 0 else 0
    short_pnl = short_trades["net_pnl"].sum() if len(short_trades) > 0 else 0
    long_wr = (long_trades["net_pnl"] > 0).mean() if len(long_trades) > 0 else 0
    short_wr = (short_trades["net_pnl"] > 0).mean() if len(short_trades) > 0 else 0

    # ── Yearly returns ──
    df["year"] = df["exit_time"].dt.year
    yearly = {}
    for year in sorted(df["year"].unique()):
        yr = df[df["year"] == year]
        yr_return = (yr["equity"].iloc[-1] / yr["equity_before"].iloc[0]) - 1
        yearly[int(year)] = round(yr_return * 100, 2)

    return {
        "Strategy":       name,
        "Total Return":   round(total_return * 100, 2),
        "Annualized":     round(annualized * 100, 2),
        "Max Drawdown":   round(max_dd * 100, 2),
        "Sharpe":         round(sharpe, 2),
        "Sortino":        round(sortino, 2),
        "Profit Factor":  round(profit_factor, 2),
        "Trades":         len(df),
        "Win Rate":       round(win_rate * 100, 2),
        "Avg Win":        round(avg_win, 2),
        "Avg Loss":       round(avg_loss, 2),
        "Long Trades":    len(long_trades),
        "Long PnL":       round(long_pnl, 2),
        "Long WR":        round(long_wr * 100, 2),
        "Short Trades":   len(short_trades),
        "Short PnL":      round(short_pnl, 2),
        "Short WR":       round(short_wr * 100, 2),
        "Total Fees":     round(df["fees"].sum(), 2),
        "Final Equity":   round(final_equity, 2),
        "Yearly Returns": yearly,
    }


def print_metrics(metrics):
    """Pretty-print a metrics dict from evaluate_strategy."""
    for k, v in metrics.items():
        if k == "Yearly Returns":
            print(f"\n{k}:")
            for year, ret in v.items():
                print(f"  {year}: {ret}%")
        elif isinstance(v, float):
            if "Return" in k or "Drawdown" in k or "WR" in k or "Win Rate" in k:
                print(f"  {k:<20} {v:>10.2f}%")
            elif "Equity" in k or "PnL" in k or "Win" in k or "Loss" in k or "Fees" in k:
                print(f"  {k:<20} ${v:>12,.2f}")
            else:
                print(f"  {k:<20} {v:>10.2f}")
        else:
            print(f"  {k:<20} {v}")


def compare_strategies(metrics_list):
    """
    Create a comparison DataFrame from multiple evaluate_strategy results.

    Parameters
    ----------
    metrics_list : list[dict] — output of evaluate_strategy for each strategy.

    Returns
    -------
    pd.DataFrame with one row per strategy.
    """
    rows = []
    for m in metrics_list:
        row = {k: v for k, v in m.items() if k != "Yearly Returns"}
        rows.append(row)
    return pd.DataFrame(rows).set_index("Strategy")
