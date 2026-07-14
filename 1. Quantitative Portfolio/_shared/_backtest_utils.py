"""
Shared backtest utilities for the 8 new long-term portfolio strategies.
Self-contained — no Alpaca dependency.
"""

import numpy as np
import pandas as pd
import json, os
from scipy import stats


# ──────────────────────────────────────────────
#  SIGNIFICANCE TESTS
# ──────────────────────────────────────────────

# ── Consolidated (fable 2026-07-02): single source of truth is
# shared/significance.py (*_series variants). These delegators keep the
# existing public API for the ~50 consumers of this module. ──
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
if _bd not in _sys.path:
    _sys.path.insert(0, _bd)
from _shared.significance import (
    ttest_returns_series as ttest_returns,
    bootstrap_sharpe_series as bootstrap_sharpe,
    permutation_test_series as permutation_test,
)


def significance_report(monthly_returns, label="Strategy"):
    r = pd.Series(monthly_returns).dropna()
    if len(r) < 5:
        return {"sharpe": 0.0, "verdict": "INSUFFICIENT DATA", "tests_passed": "0/3"}
    t = ttest_returns(r)
    b = bootstrap_sharpe(r)
    p = permutation_test(r)
    passes = sum([t["significant"], b["significant"], p["significant"]])
    verdict = (
        "SIGNIFICANT (strong)" if passes == 3 else
        "SIGNIFICANT (moderate)" if passes == 2 else
        "WEAK (only 1/3 tests pass)" if passes == 1 else
        "NOT SIGNIFICANT"
    )
    annual_sharpe = r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else 0
    return {
        "sharpe": round(float(annual_sharpe), 4),
        "verdict": verdict,
        "tests_passed": f"{passes}/3",
    }


# ──────────────────────────────────────────────
#  PORTFOLIO METRICS
# ──────────────────────────────────────────────

def portfolio_metrics(daily_equity: pd.Series, starting_capital=100_000):
    eq = daily_equity.dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / starting_capital) ** (1 / years) - 1 if years > 0 else 0
    daily_ret = eq.pct_change().dropna()
    sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(252) if daily_ret.std() > 0 else 0
    peak = eq.expanding().max()
    max_dd = ((eq - peak) / peak).min()
    total_ret = eq.iloc[-1] / starting_capital - 1
    return {
        "cagr": round(float(cagr * 100), 2),
        "total_return": round(float(total_ret * 100), 2),
        "sharpe_daily": round(float(sharpe), 4),
        "max_dd": round(float(max_dd * 100), 2),
        "years": round(years, 2),
    }


def build_monthly_returns(daily_equity: pd.Series) -> pd.Series:
    monthly = daily_equity.resample("ME").last()
    return monthly.pct_change().dropna()


# ──────────────────────────────────────────────
#  BUILD DAILY EQUITY FROM MONTHLY WEIGHTS
# ──────────────────────────────────────────────

def build_equity_from_weights(daily_prices: pd.DataFrame,
                               monthly_weights: pd.DataFrame,
                               starting_capital=100_000):
    """
    daily_prices   : daily close prices, columns=tickers, index=dates
    monthly_weights: end-of-month weights (0-1), columns=tickers, index=dates
                     forward-filled through the month

    Returns daily_equity Series.
    """
    # Forward-fill weights: weights set at end of month apply from start of next month
    # Shift weights by 1 trading day to avoid look-ahead
    weights_daily = monthly_weights.reindex(daily_prices.index).ffill().shift(1).fillna(0)

    daily_ret = daily_prices.pct_change().fillna(0)
    port_ret = (daily_ret * weights_daily).sum(axis=1)
    equity = starting_capital * (1 + port_ret).cumprod()
    return equity


# ──────────────────────────────────────────────
#  BUILD TRADES from monthly signal changes
# ──────────────────────────────────────────────

def build_trades(daily_prices: pd.DataFrame,
                 monthly_weights: pd.DataFrame,
                 daily_equity: pd.Series,
                 starting_capital=100_000,
                 tc_bps=1):
    """
    Build a standardized trades DataFrame from monthly weight changes.
    Each row = one holding period for one instrument.
    tc_bps: transaction cost in basis points (1 bp = 0.0001)
    """
    tickers = daily_prices.columns.tolist()
    rebal_dates = monthly_weights.index.tolist()

    trades = []
    open_positions = {}  # sym -> {entry_date, entry_price}
    running_equity = starting_capital

    for i, rd in enumerate(rebal_dates):
        # Find the trading date closest to rd (or next available)
        valid = daily_prices.index[daily_prices.index >= rd]
        if len(valid) == 0:
            continue
        actual_rd = valid[0]

        new_w = monthly_weights.loc[rd]

        # Close positions leaving the portfolio
        for sym in list(open_positions.keys()):
            if new_w.get(sym, 0) < 1e-6:
                h = open_positions.pop(sym)
                ep = daily_prices.loc[actual_rd, sym] if sym in daily_prices.columns else h["entry_price"]
                pct_gross = (ep - h["entry_price"]) / h["entry_price"]
                pct_net = pct_gross - tc_bps * 2 / 10000
                shares = max(1, int(running_equity * 0.1 / h["entry_price"]))  # approx
                gross_pnl = shares * h["entry_price"] * pct_gross
                net_pnl = shares * h["entry_price"] * pct_net
                fees = gross_pnl - net_pnl
                eq_before = running_equity
                running_equity += net_pnl
                trades.append({
                    "entry_time": h["entry_date"], "exit_time": actual_rd,
                    "position": "long", "instrument": sym,
                    "entry_price": round(float(h["entry_price"]), 4),
                    "exit_price": round(float(ep), 4),
                    "exit_reason": "rebalance",
                    "risk": round(float(h["entry_price"] * 0.05), 4),
                    "shares": shares,
                    "gross_pnl": round(float(gross_pnl), 2),
                    "fees": round(float(fees), 2),
                    "net_pnl": round(float(net_pnl), 2),
                    "equity_before": round(float(eq_before), 2),
                    "equity": round(float(running_equity), 2),
                })

        # Open new positions
        for sym in tickers:
            w = new_w.get(sym, 0)
            if w > 1e-6 and sym not in open_positions:
                price = daily_prices.loc[actual_rd, sym] if sym in daily_prices.columns else None
                if price is not None and not np.isnan(price):
                    open_positions[sym] = {"entry_date": actual_rd, "entry_price": float(price)}

    # Close remaining at last date
    last_date = daily_prices.index[-1]
    for sym, h in open_positions.items():
        ep = daily_prices.loc[last_date, sym] if sym in daily_prices.columns else h["entry_price"]
        pct_gross = (ep - h["entry_price"]) / h["entry_price"]
        pct_net = pct_gross - tc_bps * 2 / 10000
        shares = max(1, int(running_equity * 0.1 / h["entry_price"]))
        gross_pnl = shares * h["entry_price"] * pct_gross
        net_pnl = shares * h["entry_price"] * pct_net
        fees = gross_pnl - net_pnl
        eq_before = running_equity
        running_equity += net_pnl
        trades.append({
            "entry_time": h["entry_date"], "exit_time": last_date,
            "position": "long", "instrument": sym,
            "entry_price": round(float(h["entry_price"]), 4),
            "exit_price": round(float(ep), 4),
            "exit_reason": "end_of_data",
            "risk": round(float(h["entry_price"] * 0.05), 4),
            "shares": shares,
            "gross_pnl": round(float(gross_pnl), 2),
            "fees": round(float(fees), 2),
            "net_pnl": round(float(net_pnl), 2),
            "equity_before": round(float(eq_before), 2),
            "equity": round(float(running_equity), 2),
        })

    df = pd.DataFrame(trades)
    if not df.empty:
        df["entry_time"] = pd.to_datetime(df["entry_time"])
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        df = df.sort_values("exit_time").reset_index(drop=True)
    return df


# ──────────────────────────────────────────────
#  SAVE RESULTS
# ──────────────────────────────────────────────

def save_results(strategy_name, save_name, instruments, params,
                 trades_df, daily_equity,
                 monthly_ret_gross, monthly_ret_net,
                 start_date, end_date, output_base):

    results_dir = os.path.join(output_base, "results")
    equity_dir  = os.path.join(results_dir, f"{save_name}_daily_equity")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(equity_dir, exist_ok=True)

    # Trades
    tp = os.path.join(results_dir, f"{save_name}_trades.csv")
    trades_df.to_csv(tp, index=False)
    print(f"  trades  → {tp}")

    # Daily equity
    eq_df = daily_equity.reset_index()
    eq_df.columns = ["date", "equity"]
    ep = os.path.join(equity_dir, f"{save_name}_daily_equity.csv")
    eq_df.to_csv(ep, index=False)
    print(f"  equity  → {ep}")

    # Significance
    sig_g = significance_report(monthly_ret_gross, f"{strategy_name} gross")
    sig_n = significance_report(monthly_ret_net,   f"{strategy_name} net")

    mets = portfolio_metrics(daily_equity)

    summary = {
        "strategy": strategy_name,
        "instruments": list(instruments),
        "portfolio": "long_term",
        "period": f"{start_date} -> {end_date}",
        "params": params,
        "trades": len(trades_df),
        "stats": mets,
        "significance": {
            "gross": {"sharpe": sig_g["sharpe"], "verdict": sig_g["verdict"],
                      "tests_passed": sig_g["tests_passed"]},
            "net":   {"sharpe": sig_n["sharpe"], "verdict": sig_n["verdict"],
                      "tests_passed": sig_n["tests_passed"]},
        },
    }

    sp = os.path.join(results_dir, f"{save_name}_summary.json")
    with open(sp, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  summary → {sp}")

    return summary
