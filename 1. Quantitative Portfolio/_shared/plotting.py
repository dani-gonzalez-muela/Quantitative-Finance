"""
shared.plotting — Standardized plotting utilities.

All functions expect a trades DataFrame with the standard columns
(see shared.metrics.REQUIRED_COLUMNS).
"""

import matplotlib.pyplot as plt
import numpy as np


def plot_equity_curve(trades_df, label="Strategy", starting_capital=None,
                      log_scale=True, figsize=(14, 6)):
    """
    Plot equity curve from a standardized trades DataFrame.

    Parameters
    ----------
    trades_df        : pd.DataFrame — must have 'exit_time' and 'equity'.
    label            : str          — legend label.
    starting_capital : float        — horizontal reference line.
    log_scale        : bool         — use log y-axis.
    figsize          : tuple        — figure size.
    """
    df = trades_df.sort_values("exit_time")
    if starting_capital is None:
        starting_capital = df["equity_before"].iloc[0]

    fig, ax = plt.subplots(figsize=figsize)
    final = df["equity"].iloc[-1]
    ax.plot(df["exit_time"].values, df["equity"].values,
            linewidth=2, alpha=0.9, label=f"{label} (${final:,.0f})")
    ax.axhline(y=starting_capital, linestyle="--", alpha=0.5,
               color="gray", label="Starting Capital")

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Equity ($)", fontsize=12)
    ax.set_title(f"Equity Curve — {label}", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    if log_scale:
        ax.set_yscale("log")
    plt.tight_layout()
    plt.show()


def plot_equity_comparison(trades_list, labels, starting_capital,
                           title="Strategy Comparison", log_scale=True,
                           figsize=(14, 7)):
    """
    Plot multiple equity curves on the same axes.

    Parameters
    ----------
    trades_list      : list[pd.DataFrame] — each a standardized trades DataFrame.
    labels           : list[str]          — one label per DataFrame.
    starting_capital : float              — horizontal reference line.
    title            : str                — plot title.
    """
    fig, ax = plt.subplots(figsize=figsize)

    for df, label in zip(trades_list, labels):
        df = df.sort_values("exit_time")
        final = df["equity"].iloc[-1]
        ax.plot(df["exit_time"].values, df["equity"].values,
                linewidth=2, alpha=0.9, label=f"{label} (${final:,.0f})")

    ax.axhline(y=starting_capital, linestyle="--", alpha=0.5,
               color="gray", label="Starting Capital")

    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Equity ($)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    if log_scale:
        ax.set_yscale("log")
    plt.tight_layout()
    plt.show()


def plot_trade_returns(trades_df, title="Per-Trade Returns", figsize=(14, 4)):
    """
    Bar chart of per-trade net P&L.

    Parameters
    ----------
    trades_df : pd.DataFrame — must have 'net_pnl'.
    title     : str          — plot title.
    """
    df = trades_df.sort_values("entry_time")
    colors = ["green" if x > 0 else "red" for x in df["net_pnl"]]

    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(range(len(df)), df["net_pnl"].values, color=colors, alpha=0.7, width=1.0)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_xlabel("Trade Number")
    ax.set_ylabel("Net P&L ($)")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.show()


def plot_yearly_returns(metrics, title="Yearly Returns"):
    """
    Bar chart of yearly returns from an evaluate_strategy result.

    Parameters
    ----------
    metrics : dict — output of evaluate_strategy (must have 'Yearly Returns').
    title   : str  — plot title.
    """
    yearly = metrics.get("Yearly Returns", {})
    if not yearly:
        print("No yearly returns data.")
        return

    years = sorted(yearly.keys())
    returns = [yearly[y] for y in years]
    colors = ["green" if r > 0 else "red" for r in returns]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar([str(y) for y in years], returns, color=colors, alpha=0.7)
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_xlabel("Year")
    ax.set_ylabel("Return (%)")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    for i, (y, r) in enumerate(zip(years, returns)):
        ax.text(i, r + (0.5 if r >= 0 else -1.5), f"{r:.1f}%",
                ha="center", fontsize=9)

    plt.tight_layout()
    plt.show()
