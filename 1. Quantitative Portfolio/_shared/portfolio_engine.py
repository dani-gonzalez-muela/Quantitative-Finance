"""
shared.portfolio_engine — Multi-strategy portfolio simulator.

Simulates running multiple strategies from a single capital pool.
All trades from all strategies are merged chronologically and executed
against the shared pool with position sizing rules.

Design:
- Single pool of capital (equity tracks total account value)
- Rolling 1-month Sharpe determines priority for simultaneous trades
- Global MAX_TRADE_PERCENT caps per-trade capital usage (based on CURRENT equity)
- Idle capital earns risk-free rate
- Tracks pool utilization per strategy
- Position sizing: fixed MAX_TRADE_PERCENT of current equity (no risk-based sizing —
  strategies arrive pre-sized from implementation layer)
"""

import numpy as np
import pandas as pd
from collections import defaultdict


def compute_rolling_sharpe(trades_df, window_days=21):
    """
    Compute rolling Sharpe for each strategy based on recent trades.
    """
    strategies = trades_df["strategy"].unique()
    rolling_sharpes = {}

    for strat in strategies:
        strat_trades = trades_df[trades_df["strategy"] == strat].copy()
        strat_trades["trade_date"] = pd.to_datetime(strat_trades["exit_time"]).dt.date
        daily_pnl = strat_trades.groupby("trade_date")["pct_return"].sum()

        rolling_mean = daily_pnl.rolling(window_days, min_periods=5).mean()
        rolling_std  = daily_pnl.rolling(window_days, min_periods=5).std()
        rolling_s    = (rolling_mean / rolling_std * np.sqrt(252)).fillna(0)

        rolling_sharpes[strat] = rolling_s

    return rolling_sharpes


def prepare_trades(strategy_trades_dict):
    """
    Merge all strategy trades into one DataFrame with pct_return and strategy label.
    pct_return is computed from entry/exit prices and direction.
    """
    all_trades = []

    for name, trades in strategy_trades_dict.items():
        t = trades.copy()
        t["strategy"] = name

        t["pct_return"] = (t["exit_price"] - t["entry_price"]) / t["entry_price"]
        t.loc[t["direction"] == "short", "pct_return"] *= -1

        all_trades.append(t)

    merged = pd.concat(all_trades, ignore_index=True)
    merged["entry_time"] = pd.to_datetime(merged["entry_time"])
    merged["exit_time"]  = pd.to_datetime(merged["exit_time"])
    merged = merged.sort_values("entry_time").reset_index(drop=True)

    return merged


def simulate_portfolio(strategy_trades_dict,
                       starting_capital=100_000,
                       max_trade_percent=0.30,
                       risk_free_rate=0.04,
                       sharpe_window_days=21):
    """
    Simulate a multi-strategy portfolio from a single capital pool.

    Position sizing: fixed MAX_TRADE_PERCENT of current equity per trade.
    Strategies are assumed to arrive pre-sized from the implementation layer —
    no risk-based re-sizing is applied.

    Key: all sizing is based on CURRENT EQUITY, not starting capital.
    As the account grows, trades get larger. As it shrinks, they get smaller.
    """
    all_trades = prepare_trades(strategy_trades_dict)

    if all_trades.empty:
        return {"equity_curve": pd.DataFrame(), "trades": pd.DataFrame(),
                "utilization": {}, "summary": {}}

    rolling_sharpes = compute_rolling_sharpe(all_trades, sharpe_window_days)
    daily_rf = risk_free_rate / 252

    # State
    equity        = starting_capital
    deployed      = {}
    active_trades = {}

    # Output
    executed_trades = []
    daily_records   = []
    utilization     = defaultdict(lambda: {"trades_taken": 0, "trades_skipped": 0,
                                           "capital_deployed_total": 0.0,
                                           "minutes_deployed": 0})

    # Build event list
    events = []
    for idx, trade in all_trades.iterrows():
        events.append({"time": trade["entry_time"], "type": "entry", "trade_idx": idx})
        events.append({"time": trade["exit_time"],  "type": "exit",  "trade_idx": idx})

    # Sort: by time, exits before entries at same timestamp
    events.sort(key=lambda e: (e["time"], 0 if e["type"] == "exit" else 1))

    current_date = None

    for event in events:
        event_date = event["time"].date() if hasattr(event["time"], "date") else event["time"]

        # New day — record equity, apply risk-free on idle capital
        if current_date is not None and event_date != current_date:
            days_passed = (pd.Timestamp(event_date) - pd.Timestamp(current_date)).days
            if days_passed > 0:
                free_capital = equity - sum(deployed.values())
                if free_capital > 0:
                    equity += free_capital * daily_rf * days_passed
            daily_records.append({"date": current_date, "equity": round(equity, 2)})

        current_date = event_date
        trade_idx    = event["trade_idx"]
        trade        = all_trades.iloc[trade_idx]

        if event["type"] == "exit":
            if trade_idx in active_trades:
                cap_deployed = deployed[trade_idx]
                pct_ret      = trade["pct_return"]
                pnl          = cap_deployed * pct_ret

                equity += pnl

                executed_trades.append({
                    "strategy":         trade["strategy"],
                    "entry_time":       trade["entry_time"],
                    "exit_time":        trade["exit_time"],
                    "entry_price":      trade["entry_price"],
                    "exit_price":       trade["exit_price"],
                    "direction":        trade["direction"],
                    "pct_return":       round(pct_ret * 100, 4),
                    "capital_deployed": round(cap_deployed, 2),
                    "pnl":              round(pnl, 2),
                    "equity_after":     round(equity, 2),
                })

                strat = trade["strategy"]
                utilization[strat]["capital_deployed_total"] += cap_deployed
                duration = (trade["exit_time"] - trade["entry_time"]).total_seconds() / 60
                utilization[strat]["minutes_deployed"] += duration

                del deployed[trade_idx]
                del active_trades[trade_idx]

        elif event["type"] == "entry":
            free_capital = equity - sum(deployed.values())

            if free_capital <= 0:
                utilization[trade["strategy"]]["trades_skipped"] += 1
                continue

            # Size as fixed fraction of current equity, capped by free capital
            capital_to_deploy = min(equity * max_trade_percent, free_capital)

            if capital_to_deploy <= 0:
                utilization[trade["strategy"]]["trades_skipped"] += 1
                continue

            deployed[trade_idx]      = capital_to_deploy
            active_trades[trade_idx] = trade
            utilization[trade["strategy"]]["trades_taken"] += 1

    # Record final day
    if current_date is not None:
        daily_records.append({"date": current_date, "equity": round(equity, 2)})

    # Build outputs
    equity_df = pd.DataFrame(daily_records)
    if not equity_df.empty:
        equity_df["date"] = pd.to_datetime(equity_df["date"])
        equity_df = equity_df.drop_duplicates(subset=["date"], keep="last")
        equity_df = equity_df.sort_values("date").reset_index(drop=True)

    trades_df = pd.DataFrame(executed_trades)

    # Utilization summary
    util_summary = {}
    for strat, stats in utilization.items():
        taken   = stats["trades_taken"]
        skipped = stats["trades_skipped"]
        total   = taken + skipped
        util_summary[strat] = {
            "trades_taken":   taken,
            "trades_skipped": skipped,
            "fill_rate":      round(taken / total * 100, 1) if total > 0 else 0,
            "avg_capital":    round(stats["capital_deployed_total"] / taken, 2) if taken > 0 else 0,
            "total_minutes":  round(stats["minutes_deployed"], 0),
        }

    # Portfolio summary
    summary = {}
    if not equity_df.empty:
        final        = equity_df["equity"].iloc[-1]
        total_return = (final / starting_capital) - 1
        days         = len(equity_df)
        annualized   = (1 + total_return) ** (252 / max(days, 1)) - 1

        daily_returns = equity_df["equity"].pct_change().dropna()
        sharpe  = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0

        downside = daily_returns[daily_returns < 0]
        sortino  = daily_returns.mean() / downside.std() * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0

        cum_max = equity_df["equity"].expanding().max()
        max_dd  = ((equity_df["equity"] - cum_max) / cum_max).min()

        summary = {
            "Starting Capital": starting_capital,
            "Final Equity":     round(final, 2),
            "Total Return":     round(total_return * 100, 2),
            "Annualized":       round(annualized * 100, 2),
            "Max Drawdown":     round(max_dd * 100, 2),
            "Sharpe":           round(sharpe, 2),
            "Sortino":          round(sortino, 2),
            "Total Trades":     len(trades_df),
            "Total Days":       days,
        }

    return {
        "equity_curve": equity_df,
        "trades":       trades_df,
        "utilization":  util_summary,
        "summary":      summary,
    }


def print_portfolio_summary(result):
    """Pretty-print portfolio simulation results."""
    print("=" * 60)
    print("PORTFOLIO SUMMARY")
    print("=" * 60)

    for k, v in result["summary"].items():
        if isinstance(v, float):
            if "Return" in k or "Drawdown" in k:
                print(f"  {k:<22} {v:>10.2f}%")
            elif "Equity" in k or "Capital" in k:
                print(f"  {k:<22} ${v:>12,.2f}")
            else:
                print(f"  {k:<22} {v:>10.2f}")
        else:
            print(f"  {k:<22} {v}")

    print(f"\n{'=' * 60}")
    print("STRATEGY UTILIZATION")
    print(f"{'=' * 60}")
    print(f"  {'Strategy':<20} {'Taken':>7} {'Skipped':>8} {'Fill%':>7} {'Avg Cap':>12}")
    print(f"  {'-' * 56}")

    for strat, stats in result["utilization"].items():
        print(f"  {strat:<20} {stats['trades_taken']:>7} {stats['trades_skipped']:>8} "
              f"{stats['fill_rate']:>6.1f}% ${stats['avg_capital']:>10,.0f}")
