# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
shared.implementations — Sizing implementations for backtested signal trades.

Takes standardized signal trades (from generate_signals) and applies
different position sizing methods. Returns equity curve + sized returns.

All implementations:
- Accept the same standardized trades DataFrame (9-column CSV format)
- Use calculate_fees for realistic transaction costs
- Return a dict with equity_curve, returns, and summary stats
- Accept starting_capital parameter (default 100k) for sleeve-based architectures

Organization:
    ── Internal Helpers ──
        _compute_stats          Compute Sharpe, CAGR, MaxDD from equity curve
        _get_years              Calendar years spanned by trades

    ── Sizing Methods (Short-Term & Long-Term) ──
        simple_bet              Fixed fraction of equity per trade
        risk_based              Stop-distance sizing with leverage cap
        kelly_sizing            Walk-forward half/quarter Kelly
        vol_targeting           Strategy-return vol targeting

    ── Sizing Methods (Long-Term / Swing Only) ──
        asset_vol_targeting     Underlying asset vol targeting (per-trade)

    ── Sizing Methods (Short-Term / Intraday Only) ──
        intraday_asset_vol      Paper's exact intraday sizing (per-day)

    ── Equity Curve Builders ──
        build_daily_equity          Single-stream daily equity (intraday or multi-day)
        build_multi_sleeve_equity   Combine per-sleeve daily equity into portfolio
        build_basket_equity         Rotation strategies — single capital pool,
                                     multiple concurrent positions, MTM daily

    ── Comparison / Display ──
        compare_implementations     Print comparison table
"""

import numpy as np
import pandas as pd
from _shared.fees import calculate_fees, SLIPPAGE_PER_SHARE


# ═══════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _compute_stats(equity_curve, starting_capital, trades=None):
    """Compute standard metrics from an equity curve and trades DataFrame."""
    eq = np.array(equity_curve)
    if len(eq) < 2 or eq[-1] <= 0:
        return {"total_return": 0, "cagr": 0, "sharpe": 0, "sortino": 0,
                "max_dd": 0, "profit_factor": 0}

    total_ret = (eq[-1] / starting_capital - 1) * 100

    # ── CAGR from actual date range ──
    years = _get_years(trades) if trades is not None else None
    if years is None or years <= 0:
        years = (len(eq) - 1) / 252  # fallback
    if eq[-1] <= 0 or min(eq) <= 0:
        cagr = float('nan')
    else:
        cagr = ((eq[-1] / starting_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

    # ── Sharpe/Sortino from daily equity returns ──
    if trades is not None and "exit_time" in trades.columns and len(trades) >= 2:
        # Build daily equity: take last equity value per calendar day
        exit_dates = pd.to_datetime(trades["exit_time"], utc=True).dt.date.values
        # equity_curve[0] is starting capital, equity_curve[1:] correspond to trades
        trade_eq = eq[1:]  # one per trade

        daily_eq = pd.Series(trade_eq, index=exit_dates)
        daily_eq = daily_eq.groupby(daily_eq.index).last()  # end-of-day equity
        daily_eq = daily_eq.sort_index()

        # Prepend starting capital as first day
        first_date = daily_eq.index[0] - pd.Timedelta(days=1)
        daily_eq = pd.concat([pd.Series([starting_capital], index=[first_date]), daily_eq])

        daily_rets = daily_eq.pct_change().dropna()
        sharpe = daily_rets.mean() / daily_rets.std() * np.sqrt(252) if daily_rets.std() > 0 else 0
        downside = daily_rets[daily_rets < 0]
        sortino = daily_rets.mean() / downside.std() * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0
    else:
        # Fallback: per-trade returns with sqrt(252)
        rets = pd.Series(eq).pct_change().dropna()
        sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
        downside = rets[rets < 0]
        sortino = rets.mean() / downside.std() * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0

    # ── Max drawdown from full equity curve ──
    rm = np.maximum.accumulate(eq)
    max_dd = ((eq - rm) / rm).min() * 100

    # ── Profit factor from per-trade returns ──
    rets = pd.Series(eq).pct_change().dropna()
    wins = rets[rets > 0]
    losses = rets[rets < 0]
    pf = abs(wins.sum() / losses.sum()) if losses.sum() != 0 else np.inf

    return {
        "total_return": round(total_ret, 1),
        "cagr": round(cagr, 1),
        "sharpe": round(sharpe, 2),
        "sortino": round(sortino, 2),
        "max_dd": round(max_dd, 1),
        "profit_factor": round(pf, 2),
    }


def _get_years(trades):
    """Compute actual years spanned by the trades DataFrame."""
    if "entry_time" not in trades.columns or len(trades) < 2:
        return None
    first = pd.to_datetime(trades["entry_time"].iloc[0], utc=True)
    last = pd.to_datetime(trades["exit_time"].iloc[-1], utc=True)
    days = (last - first).days
    return days / 365.25 if days > 0 else None


# ═══════════════════════════════════════════════════════════════════════
# SIZING METHODS — SHORT-TERM & LONG-TERM (work for any strategy)
# ═══════════════════════════════════════════════════════════════════════


def simple_bet(trades, bet_size=0.85, starting_capital=100_000, include_fees=True, slippage=SLIPPAGE_PER_SHARE):
    """
    Fixed fraction of equity per trade.

    Parameters
    ----------
    trades : DataFrame — standardized signal trades
    bet_size : float — fraction of equity to deploy per trade (e.g., 0.85 = 85%)
    starting_capital : float
    include_fees : bool

    Returns
    -------
    dict with equity_curve (list), sized_returns (list), stats (dict), label (str)
    """
    equity = starting_capital
    equity_curve = [starting_capital]
    sized_returns = []
    shares_per_trade = []

    for _, t in trades.iterrows():
        if equity <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        notional = equity * bet_size
        shares = int(notional / t["entry_price"])
        if shares <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        if t["direction"] == "long":
            pnl = shares * (t["exit_price"] - t["entry_price"])
        else:
            pnl = shares * (t["entry_price"] - t["exit_price"])

        fees = calculate_fees(shares, t["entry_price"], t["exit_price"], t["direction"], slippage=slippage) if include_fees else 0.0
        net_pnl = pnl - fees
        ret = net_pnl / equity

        equity += net_pnl
        equity_curve.append(equity)
        sized_returns.append(round(ret, 6))
        shares_per_trade.append(shares)

    stats = _compute_stats(equity_curve, starting_capital, trades)
    stats["trades"] = len(trades)
    stats["win_rate"] = round((pd.Series(sized_returns) > 0).mean() * 100, 1)

    return {
        "equity_curve": equity_curve,
        "sized_returns": sized_returns,
        "shares_per_trade": shares_per_trade,
        "stats": stats,
        "label": f"Simple ({bet_size:.0%} bet)",
    }


def risk_based(trades, risk_pct=0.01, leverage=1, starting_capital=100_000, include_fees=True, slippage=SLIPPAGE_PER_SHARE):
    """
    Risk-based position sizing using stop_price.

    Sizes each trade so that max loss (if stopped out) = risk_pct of equity.
    Leverage controls the max capital cap — at 1× the cap usually overrides
    the risk formula. Higher leverage unlocks variable sizing where tight
    stops get larger positions (the actual edge of risk-based sizing).

    Parameters
    ----------
    trades : DataFrame — standardized signal trades (must have stop_price)
    risk_pct : float — fraction of equity to risk per trade (e.g., 0.01 = 1%)
    leverage : float — max leverage multiplier (1 = no leverage, 12 = 12× margin)
    starting_capital : float
    include_fees : bool

    Returns
    -------
    dict with equity_curve, sized_returns, stats, label
    """
    equity = starting_capital
    equity_curve = [starting_capital]
    sized_returns = []
    shares_per_trade = []

    for _, t in trades.iterrows():
        if equity <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        # Compute risk distance from stop
        stop = t.get("stop_price", np.nan)
        if pd.notna(stop) and stop > 0:
            risk_dist = abs(t["entry_price"] - stop)
        else:
            risk_dist = t["entry_price"] * risk_pct  # fallback

        if risk_dist <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        # Size by risk, capped by leverage
        shares_by_risk = (equity * risk_pct) / risk_dist
        shares_by_cap = (equity * leverage) / t["entry_price"]
        shares = int(min(shares_by_risk, shares_by_cap))
        if shares <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        if t["direction"] == "long":
            pnl = shares * (t["exit_price"] - t["entry_price"])
        else:
            pnl = shares * (t["entry_price"] - t["exit_price"])

        fees = calculate_fees(shares, t["entry_price"], t["exit_price"], t["direction"], slippage=slippage) if include_fees else 0.0
        net_pnl = pnl - fees
        ret = net_pnl / equity

        equity += net_pnl
        equity_curve.append(equity)
        sized_returns.append(round(ret, 6))
        shares_per_trade.append(shares)

    stats = _compute_stats(equity_curve, starting_capital, trades)
    stats["trades"] = len(trades)
    stats["win_rate"] = round((pd.Series(sized_returns) > 0).mean() * 100, 1)

    return {
        "equity_curve": equity_curve,
        "sized_returns": sized_returns,
        "shares_per_trade": shares_per_trade,
        "stats": stats,
        "label": f"Risk-based ({risk_pct:.0%} risk, {leverage}× lev)",
    }


def kelly_sizing(trades, fraction=0.5, burn_in=100, default_bet=0.02,
                 starting_capital=100_000, include_fees=True, slippage=SLIPPAGE_PER_SHARE):
    """
    Walk-forward Kelly sizing.

    Estimates Kelly fraction from past trades and applies a fraction of it
    (half Kelly, quarter Kelly, etc.).

    Parameters
    ----------
    trades : DataFrame — standardized signal trades
    fraction : float — fraction of Kelly to use (0.5 = half Kelly, 0.25 = quarter)
    burn_in : int — number of trades to estimate initial Kelly (uses default_bet during burn-in)
    default_bet : float — bet size during burn-in period
    starting_capital : float
    include_fees : bool

    Returns
    -------
    dict with equity_curve, sized_returns, stats, label
    """
    def _compute_kelly(returns):
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        if len(wins) < 5 or len(losses) < 5:
            return default_bet
        p = len(wins) / len(returns)
        b = wins.mean() / abs(losses.mean())
        k = (p * b - (1 - p)) / b
        return max(k, 0)

    equity = starting_capital
    equity_curve = [starting_capital]
    sized_returns = []

    for i, (_, t) in enumerate(trades.iterrows()):
        if equity <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            continue

        # Determine bet size
        if i < burn_in:
            bet = default_bet
        else:
            past = pd.Series(sized_returns[:i])
            k = _compute_kelly(past)
            bet = k * fraction

        # Cap bet at 100% of equity
        bet = min(bet, 1.0)

        notional = equity * bet
        shares = int(notional / t["entry_price"])
        if shares <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            continue

        if t["direction"] == "long":
            pnl = shares * (t["exit_price"] - t["entry_price"])
        else:
            pnl = shares * (t["entry_price"] - t["exit_price"])

        fees = calculate_fees(shares, t["entry_price"], t["exit_price"], t["direction"], slippage=slippage) if include_fees else 0.0
        net_pnl = pnl - fees
        ret = net_pnl / equity

        equity += net_pnl
        equity_curve.append(equity)
        sized_returns.append(round(ret, 6))

    frac_label = {1.0: "Full", 0.5: "Half", 0.25: "Quarter"}.get(fraction, f"{fraction:.0%}")
    stats = _compute_stats(equity_curve, starting_capital, trades)
    stats["trades"] = len(trades)
    stats["win_rate"] = round((pd.Series(sized_returns) > 0).mean() * 100, 1)

    return {
        "equity_curve": equity_curve,
        "sized_returns": sized_returns,
        "stats": stats,
        "label": f"{frac_label} Kelly (burn-in={burn_in})",
    }


def vol_targeting(trades, target_vol=0.10, lookback=60, max_leverage=2.0,
                  default_bet=0.20, starting_capital=100_000, include_fees=True, slippage=SLIPPAGE_PER_SHARE):
    """
    Volatility targeting — scale position so portfolio vol ≈ target_vol.

    Uses rolling realized vol of past strategy returns to determine bet size:
        bet = target_vol / (realized_vol * sqrt(252))

    Parameters
    ----------
    trades : DataFrame — standardized signal trades
    target_vol : float — target annualized volatility (e.g., 0.10 = 10%)
    lookback : int — rolling window for vol estimation
    max_leverage : float — max bet as fraction of equity (2.0 = 200% = 2× leverage)
    default_bet : float — bet size before enough history
    starting_capital : float
    include_fees : bool

    Returns
    -------
    dict with equity_curve, sized_returns, stats, label
    """
    equity = starting_capital
    equity_curve = [starting_capital]
    sized_returns = []

    for i, (_, t) in enumerate(trades.iterrows()):
        if equity <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            continue

        # Determine bet size from realized vol
        if i < lookback:
            bet = default_bet
        else:
            past = pd.Series(sized_returns[max(0, i - lookback):i])
            realized_vol = past.std() * np.sqrt(252)
            if realized_vol > 0:
                bet = target_vol / realized_vol
                bet = np.clip(bet, 0.01, max_leverage)
            else:
                bet = default_bet

        notional = equity * bet
        shares = int(notional / t["entry_price"])
        if shares <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            continue

        if t["direction"] == "long":
            pnl = shares * (t["exit_price"] - t["entry_price"])
        else:
            pnl = shares * (t["entry_price"] - t["exit_price"])

        fees = calculate_fees(shares, t["entry_price"], t["exit_price"], t["direction"], slippage=slippage) if include_fees else 0.0
        net_pnl = pnl - fees
        ret = net_pnl / equity

        equity += net_pnl
        equity_curve.append(equity)
        sized_returns.append(round(ret, 6))

    stats = _compute_stats(equity_curve, starting_capital, trades)
    stats["trades"] = len(trades)
    stats["win_rate"] = round((pd.Series(sized_returns) > 0).mean() * 100, 1)

    return {
        "equity_curve": equity_curve,
        "sized_returns": sized_returns,
        "stats": stats,
        "label": f"Vol target ({target_vol:.0%} ann, {max_leverage:.0f}× max lev)",
    }


# ═══════════════════════════════════════════════════════════════════════
# SIZING METHODS — LONG-TERM / SWING ONLY
# ═══════════════════════════════════════════════════════════════════════


def asset_vol_targeting(trades, prices, target_vol=0.02, lookback=14,
                        max_leverage=4.0, starting_capital=100_000, include_fees=True, slippage=SLIPPAGE_PER_SHARE):
    """
    Asset-vol targeting — scale position by the underlying asset's realized vol.

    This replicates the Concretum/Zarattini "Beat the Market" sizing:
        leverage = min(max_leverage, target_vol / asset_realized_vol)
        shares = equity * leverage / entry_price

    Unlike vol_targeting() which uses the strategy's own P&L vol, this uses
    the underlying asset's price vol — an exogenous signal that doesn't depend
    on past trade outcomes.

    Both target_vol and asset vol are in DAILY terms (not annualized) to match
    the paper. Paper uses target_vol=0.02 (2% daily).

    Parameters
    ----------
    trades : DataFrame — standardized signal trades (must have entry_time)
    prices : Series or DataFrame — daily close prices of the underlying asset,
             indexed by date (used to compute realized vol)
    target_vol : float — target DAILY volatility (e.g., 0.02 = 2% daily, paper default)
    lookback : int — rolling window in trading days for vol estimation (paper uses 14)
    max_leverage : float — max leverage multiplier (paper uses 4.0)
    starting_capital : float
    include_fees : bool

    Returns
    -------
    dict with equity_curve, sized_returns, stats, label
    """
    # Compute daily returns and rolling vol from asset prices (DAILY, not annualized)
    if isinstance(prices, pd.DataFrame):
        prices = prices.iloc[:, 0]  # take first column if DataFrame
    daily_ret = prices.pct_change().dropna()
    rolling_vol = daily_ret.rolling(lookback, min_periods=lookback).std()

    equity = starting_capital
    equity_curve = [starting_capital]
    sized_returns = []
    shares_per_trade = []

    for _, t in trades.iterrows():
        if equity <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        # Find the asset vol on the trade date (or most recent prior date)
        trade_date = pd.Timestamp(t["entry_time"]).normalize()
        vol_before = rolling_vol.loc[:trade_date]

        if len(vol_before) == 0 or pd.isna(vol_before.iloc[-1]):
            leverage = 1.0  # default during warmup
        else:
            asset_vol = vol_before.iloc[-1]
            if asset_vol > 0:
                leverage = min(max_leverage, target_vol / asset_vol)
            else:
                leverage = 1.0

        notional = equity * leverage
        shares = int(notional / t["entry_price"])
        if shares <= 0:
            equity_curve.append(equity)
            sized_returns.append(0.0)
            shares_per_trade.append(0)
            continue

        if t["direction"] == "long":
            pnl = shares * (t["exit_price"] - t["entry_price"])
        else:
            pnl = shares * (t["entry_price"] - t["exit_price"])

        fees = calculate_fees(shares, t["entry_price"], t["exit_price"], t["direction"], slippage=slippage) if include_fees else 0.0
        net_pnl = pnl - fees
        ret = net_pnl / equity

        equity += net_pnl
        equity_curve.append(equity)
        sized_returns.append(round(ret, 6))
        shares_per_trade.append(shares)

    stats = _compute_stats(equity_curve, starting_capital, trades)
    stats["trades"] = len(trades)
    stats["win_rate"] = round((pd.Series(sized_returns) > 0).mean() * 100, 1)

    return {
        "equity_curve": equity_curve,
        "sized_returns": sized_returns,
        "shares_per_trade": shares_per_trade,
        "stats": stats,
        "label": f"Asset vol ({target_vol:.0%}, {lookback}d, {max_leverage:.0f}× max)",
    }


# ═══════════════════════════════════════════════════════════════════════
# SIZING METHODS — SHORT-TERM / INTRADAY ONLY
# ═══════════════════════════════════════════════════════════════════════


def intraday_asset_vol(trades, prices, target_vol=0.02, lookback=14,
                       max_leverage=4.0, cost_per_share=0.0045,
                       starting_capital=100_000):
    """
    Intraday asset-vol sizing — replicates "Beat the Market" paper exactly.

    This is the paper's sizing method for intraday strategies where:
    - Leverage is computed ONCE per day from the asset's realized vol
    - All trades within a day use the SAME share count (sized at day open)
    - Equity updates at end-of-day, not per-trade
    - Fees are flat per-share (commission + slippage), not SEC/TAF

    Use this for intraday strategies. For swing/daily strategies, use
    asset_vol_targeting() instead.

    Parameters
    ----------
    trades : DataFrame — standardized signal trades (must have entry_time)
    prices : DataFrame — daily prices with columns [date, day_open, day_close]
             indexed by date, or Series of daily closes (day_open derived from
             first trade entry if not available)
    target_vol : float — target DAILY volatility (paper uses 0.02 = 2%)
    lookback : int — rolling window in trading days (paper uses 14)
    max_leverage : float — max leverage multiplier (paper uses 4.0)
    cost_per_share : float — total cost per share per side
                     (paper: 0.0035 commission + 0.001 slippage = 0.0045)
    starting_capital : float

    Returns
    -------
    dict with equity_curve, sized_returns, stats, label
    """
    # Handle both DataFrame (with day_open, day_close) and Series (close only)
    if isinstance(prices, pd.Series):
        close_prices = prices
        open_prices = None
    elif isinstance(prices, pd.DataFrame):
        if "day_close" in prices.columns:
            close_prices = prices.set_index("date")["day_close"] if "date" in prices.columns else prices["day_close"]
            open_prices = prices.set_index("date")["day_open"] if "day_open" in prices.columns else None
        else:
            close_prices = prices.iloc[:, 0]
            open_prices = None
    else:
        raise ValueError("prices must be a Series or DataFrame")

    # Compute daily vol from closes (daily, not annualized)
    # Normalize index to Timestamp for consistent .loc lookups
    close_prices.index = pd.to_datetime(close_prices.index)
    if open_prices is not None:
        open_prices.index = pd.to_datetime(open_prices.index)
    daily_ret = close_prices.pct_change().dropna()
    rolling_vol = daily_ret.rolling(lookback, min_periods=lookback).std()

    # Compute leverage per day (shifted to avoid look-ahead)
    daily_leverage = (target_vol / rolling_vol).clip(upper=max_leverage).shift(1)

    trades = trades.copy()
    trades["trade_date"] = pd.to_datetime(trades["entry_time"], utc=True).dt.tz_localize(None).dt.normalize()

    # Group trades by day
    day_groups = trades.groupby("trade_date")

    equity = starting_capital
    equity_curve = [starting_capital]
    sized_returns = []

    for day, day_trades in day_groups:
        day_trades = day_trades.sort_values("entry_time")

        # Get leverage for this day
        lev_before = daily_leverage.loc[:day]
        if len(lev_before) == 0 or pd.isna(lev_before.iloc[-1]):
            leverage = 1.0
        else:
            leverage = lev_before.iloc[-1]

        # Get day open price — from prices DataFrame if available, else first entry
        if open_prices is not None:
            op_before = open_prices.loc[:day]
            if len(op_before) > 0 and not pd.isna(op_before.iloc[-1]):
                day_open_price = op_before.iloc[-1]
            else:
                day_open_price = day_trades["entry_price"].iloc[0]
        else:
            day_open_price = day_trades["entry_price"].iloc[0]

        # Size ONCE for the whole day
        notional = equity * leverage
        shares = int(notional / day_open_price)

        if shares <= 0:
            for _ in range(len(day_trades)):
                equity_curve.append(equity)
                sized_returns.append(0.0)
            continue

        # Process all trades for this day with SAME share count, start-of-day equity
        day_pnl = 0.0
        for _, t in day_trades.iterrows():
            if t["direction"] == "long":
                pnl = shares * (t["exit_price"] - t["entry_price"])
            else:
                pnl = shares * (t["entry_price"] - t["exit_price"])

            cost = shares * cost_per_share * 2  # round trip
            net = pnl - cost
            day_pnl += net

            # Per-trade return uses start-of-day equity
            ret = net / equity
            sized_returns.append(round(ret, 6))
            equity_curve.append(equity + day_pnl)

        # Update equity at end of day
        equity += day_pnl

    stats = _compute_stats(equity_curve, starting_capital, trades)
    stats["trades"] = len(trades)
    stats["win_rate"] = round((pd.Series(sized_returns) > 0).mean() * 100, 1)

    return {
        "equity_curve": equity_curve,
        "sized_returns": sized_returns,
        "stats": stats,
        "label": f"Intraday asset vol ({target_vol:.0%}, {lookback}d, {max_leverage:.0f}× max)",
    }


# ═══════════════════════════════════════════════════════════════════════
# EQUITY CURVE BUILDERS
# ═══════════════════════════════════════════════════════════════════════


def build_daily_equity(trades, equity_curve, starting_capital, daily_prices=None):
    """
    Build a daily equity Series from trade-level equity curve.

    For intraday strategies (daily_prices=None):
        Maps equity to exit dates, forward-fills on non-trading days.

    For multi-day strategies (daily_prices provided):
        Marks open positions to market using daily close prices.
        On days between entry and exit, equity reflects unrealized P&L.

    Parameters
    ----------
    trades : DataFrame — sized trades with entry_time, exit_time, direction,
             entry_price, exit_price. For multi-day: needs 'shares' column too.
    equity_curve : list — equity after each trade (from sizing function output).
                   equity_curve[0] = starting_capital, [1:] = post-trade equity.
    starting_capital : float
    daily_prices : Series indexed by date — daily close of the instrument.
                   None for intraday strategies (forward-fill only).

    Returns
    -------
    pd.Series indexed by business day with daily equity values.
    """
    trades = trades.copy()
    # ── Normalize ALL dates to Timestamps (midnight, no timezone) ──
    # This prevents the datetime.date vs Timestamp mismatch that breaks reindex/lookup
    def _to_ts(series):
        dt = pd.to_datetime(series)
        if hasattr(dt, 'dt'):
            if dt.dt.tz is not None:
                dt = dt.dt.tz_convert(None)
            return dt.dt.normalize()
        # scalar
        if hasattr(dt, 'tz') and dt.tz is not None:
            dt = dt.tz_convert(None)
        return dt.normalize()

    trades["exit_date"] = _to_ts(trades["exit_time"])
    trades["entry_date"] = _to_ts(trades["entry_time"])

    first_date = trades["entry_date"].iloc[0]
    last_date = trades["exit_date"].iloc[-1]
    all_days = pd.bdate_range(first_date, last_date)

    if daily_prices is None:
        # ── Intraday: no open positions at end of day ──
        trade_eq = np.array(equity_curve[1:])  # one per trade
        daily_eq = pd.Series(trade_eq, index=trades["exit_date"].values)
        daily_eq = daily_eq.groupby(daily_eq.index).last()
        daily_eq = daily_eq.reindex(all_days, method="ffill")
        daily_eq = daily_eq.fillna(starting_capital)

    else:
        # ── Multi-day: mark open positions to market ──
        # Normalize daily_prices index to Timestamps (same type as all_days)
        daily_prices = daily_prices.copy()
        daily_prices.index = pd.to_datetime(daily_prices.index).normalize()
        daily_prices = daily_prices.reindex(all_days)
        daily_prices = daily_prices.ffill()

        # We need shares for mark-to-market — check if trades have them
        if "shares" not in trades.columns:
            trades["_shares"] = [
                int(equity_curve[max(0, i)] * 0.85 / trades.iloc[i]["entry_price"])
                for i in range(len(trades))
            ]
            shares_col = "_shares"
        else:
            shares_col = "shares"

        # For each calendar day, compute equity = cash + unrealized positions
        daily_values = {}
        cash = starting_capital

        trades = trades.sort_values("entry_time").reset_index(drop=True)
        open_positions = []

        for day in all_days:
            # day is a Timestamp — all comparisons are Timestamp vs Timestamp

            # Close positions that exit today or before
            still_open = []
            for pos in open_positions:
                if pos["exit_date"] <= day:
                    if pos["direction"] == "long":
                        pnl = pos["shares"] * (pos["exit_price"] - pos["entry_price"])
                    else:
                        pnl = pos["shares"] * (pos["entry_price"] - pos["exit_price"])
                    cash += pnl
                else:
                    still_open.append(pos)
            open_positions = still_open

            # Open new positions that enter today
            day_trades = trades[trades["entry_date"] == day]
            for _, t in day_trades.iterrows():
                open_positions.append({
                    "direction": t["direction"],
                    "entry_price": t["entry_price"],
                    "exit_price": t["exit_price"],
                    "exit_date": t["exit_date"],
                    "shares": t[shares_col],
                })

            # Mark-to-market
            current_price = daily_prices.get(day, np.nan)
            unrealized = 0.0
            if not pd.isna(current_price):
                for pos in open_positions:
                    if pos["direction"] == "long":
                        unrealized += pos["shares"] * (current_price - pos["entry_price"])
                    else:
                        unrealized += pos["shares"] * (pos["entry_price"] - current_price)

            daily_values[day] = cash + unrealized

        daily_eq = pd.Series(daily_values)
        daily_eq = daily_eq.reindex(all_days, method="ffill")
        daily_eq = daily_eq.fillna(starting_capital)

    daily_eq.index.name = "date"
    daily_eq.name = "equity"
    return daily_eq


def build_multi_sleeve_equity(sleeve_daily, starting_capital):
    """
    Combine multiple per-sleeve daily equity Series into one portfolio curve.

    For multi-asset strategies (e.g. Bollinger on SPY/QQQ/IWM), each instrument
    runs as an independent "sleeve" with its own capital allocation. This function
    sums the sleeve-level daily equity into a single portfolio daily equity.

    Parameters
    ----------
    sleeve_daily : dict {sleeve_name: pd.Series}
        Each Series indexed by date, values = sleeve equity in $.
        Sleeves may have different date ranges — they are unioned and
        forward-filled (missing days = sleeve unchanged).
    starting_capital : float
        Portfolio starting capital. Should equal sum of sleeve starting
        capitals within 0.01.

    Returns
    -------
    pd.Series
        Portfolio daily equity, indexed by date, values = total equity in $.
    """
    if not sleeve_daily:
        raise ValueError("sleeve_daily is empty")

    # Align all sleeves to the same date index
    all_dates = sorted(set().union(*[s.index for s in sleeve_daily.values()]))
    aligned = {}
    for name, series in sleeve_daily.items():
        s = series.copy()
        s.index = pd.to_datetime(s.index)
        # Reindex to the full union of dates and forward-fill
        aligned[name] = s.reindex(pd.to_datetime(all_dates)).ffill().bfill()

    combined = sum(aligned.values())

    # Sanity check: day 1 total should be close to starting capital
    # (differences up to a few % are normal from mark-to-market on entry day,
    #  especially with leveraged positions)
    if abs(combined.iloc[0] - starting_capital) / starting_capital > 0.05:
        import warnings
        warnings.warn(
            f"Sleeve sum on first date ({combined.iloc[0]:.2f}) does not "
            f"match starting capital ({starting_capital:.2f}). Check sleeve "
            f"allocations."
        )

    combined.index.name = "date"
    combined.name = "equity"
    return combined


# ═══════════════════════════════════════════════════════════════════════
# COMPARISON / DISPLAY
# ═══════════════════════════════════════════════════════════════════════


def build_basket_equity(trades, daily_prices, starting_capital=100_000,
                         allocation=0.85, include_fees=True,
                         slippage=SLIPPAGE_PER_SHARE):
    """
    Build a daily equity curve for a basket-rotation strategy.

    Unlike build_multi_sleeve_equity (which assumes fixed per-instrument
    capital sleeves), this treats capital as a single pool and sizes each
    position as an equal share of the deployed allocation at the moment
    of entry. Multiple positions are held concurrently (e.g. top-K
    cross-sectional rotation) and marked to market daily.

    At each day:
        equity = cash + Σ (shares_i × current_price_i) for open positions

    At each trade entry:
        notional_per_position = equity × allocation / n_concurrent_positions
        shares = int(notional_per_position / entry_price)
        cash -= shares × entry_price

    Where ``n_concurrent_positions`` is the number of trades opening on the
    same entry_date (a rebalance cohort). This matches equal-weight top-K
    rotation: on each rebalance, the fraction ``allocation`` of current
    equity is split evenly across the K new positions.

    Parameters
    ----------
    trades : DataFrame
        Standardized signal trades with at minimum: entry_time, exit_time,
        direction, instrument, entry_price, exit_price.
    daily_prices : dict {ticker: pd.Series indexed by date}
        Close prices for every instrument that appears in trades. Needed
        for mark-to-market between entry and exit.
    starting_capital : float
    allocation : float
        Total fraction of equity deployed into the basket on each rebalance.
        Can exceed 1.0 for leverage (e.g. 2.0 = 2× gross exposure).
        Per-position allocation = allocation / K where K is the cohort size.
    include_fees : bool
    slippage : float
        Per-share slippage (from shared.fees).

    Returns
    -------
    dict with keys:
        equity_curve : list
            Equity after each trade exit, in entry_time order. One value
            per trade plus the starting_capital at index 0 — same contract
            as simple_bet / risk_based for downstream compatibility.
        sized_returns : list
            Per-trade net return (net_pnl / equity_at_entry). One per trade.
        shares_per_trade : list
            Share count per trade, aligned with the trades DataFrame order.
        daily_equity : pd.Series
            Business-day indexed equity series with MTM valuation.
        stats : dict
            Standard metrics (sharpe, cagr, max_dd, ...) computed from the
            daily equity curve (not from per-trade returns).
        label : str
    """
    # ── Normalize dates to Timestamps (same pattern as build_daily_equity) ──
    def _to_ts(series):
        dt = pd.to_datetime(series)
        if hasattr(dt, 'dt'):
            if dt.dt.tz is not None:
                dt = dt.dt.tz_convert(None)
            return dt.dt.normalize()
        if hasattr(dt, 'tz') and dt.tz is not None:
            dt = dt.tz_convert(None)
        return dt.normalize()

    trades = trades.copy()
    trades["entry_date"] = _to_ts(trades["entry_time"])
    trades["exit_date"]  = _to_ts(trades["exit_time"])
    trades = trades.sort_values(["entry_date", "instrument"]).reset_index(drop=True)

    # Track original order for shares_per_trade alignment
    trades["_orig_idx"] = trades.index

    first_date = trades["entry_date"].min()
    last_date  = trades["exit_date"].max()
    all_days = pd.bdate_range(first_date, last_date)

    # Normalize daily_prices dict indexes AND reindex to all_days with ffill.
    # The ffill is critical: without it, any day missing from a price series
    # (holidays, data gaps, cross-instrument trading-day mismatches) causes
    # the MTM lookup to miss and fall back to entry_price, producing visible
    # single-day equity spikes/drops.
    prices_norm = {}
    for sym, s in daily_prices.items():
        s = s.copy()
        s.index = pd.to_datetime(s.index).normalize()
        s = s[~s.index.duplicated(keep="last")]
        s = s.reindex(all_days).ffill().bfill()
        prices_norm[sym] = s

    # Rebalance cohort sizes — number of trades entering on each date
    cohort_size = trades.groupby("entry_date").size().to_dict()

    # Pre-allocate outputs aligned to original trade order
    shares_per_trade = [0] * len(trades)
    sized_returns    = [0.0] * len(trades)
    # Per-trade equity_at_entry and net_pnl for building equity_curve
    per_trade_pnl    = [0.0] * len(trades)
    per_trade_equity_at_entry = [0.0] * len(trades)

    # Simulate day by day
    cash = starting_capital
    open_positions = []  # list of dicts with shares, entry_price, exit_price,
                         # exit_date, direction, instrument, trade_idx
    daily_values = {}

    for day in all_days:
        # ── 1. Close positions exiting today or earlier ──
        still_open = []
        for pos in open_positions:
            if pos["exit_date"] <= day:
                # Exit proceeds returned to cash, minus fees
                if pos["direction"] == "long":
                    proceeds = pos["shares"] * pos["exit_price"]
                    gross_pnl = pos["shares"] * (pos["exit_price"] - pos["entry_price"])
                else:
                    # Short: on entry cash += shares×entry_price, on exit cash -= shares×exit_price
                    proceeds = pos["shares"] * (2 * pos["entry_price"] - pos["exit_price"])
                    gross_pnl = pos["shares"] * (pos["entry_price"] - pos["exit_price"])
                fees = (calculate_fees(pos["shares"], pos["entry_price"],
                                        pos["exit_price"], pos["direction"],
                                        slippage=slippage)
                          if include_fees else 0.0)
                net_pnl = gross_pnl - fees
                cash += proceeds - fees
                # Record per-trade return / pnl for this closed position
                idx = pos["trade_idx"]
                per_trade_pnl[idx] = net_pnl
                eq_at_entry = per_trade_equity_at_entry[idx]
                sized_returns[idx] = (net_pnl / eq_at_entry) if eq_at_entry > 0 else 0.0
            else:
                still_open.append(pos)
        open_positions = still_open

        # ── 2. Compute current equity (cash + MTM of open positions) ──
        #    This is the equity_at_entry basis for new positions opening today.
        #    Note: entry cost was deducted from cash, so position value is
        #    shares × current_price (for longs). For shorts, position value
        #    is shares × (2×entry_price − current_price) since cash received
        #    on entry was + shares×entry_price.
        position_value = 0.0
        for pos in open_positions:
            series = prices_norm.get(pos["instrument"])
            if series is not None and day in series.index:
                px = series.loc[day]
            else:
                px = np.nan
            if pd.isna(px):
                px = pos["entry_price"]  # fallback if price missing
            if pos["direction"] == "long":
                position_value += pos["shares"] * px
            else:
                # Short: entry added cash, exit P&L = entry_price − current_price
                position_value += pos["shares"] * (2 * pos["entry_price"] - px)
        equity_now = cash + position_value

        # ── 3. Open new positions entering today ──
        day_trades = trades[trades["entry_date"] == day]
        if not day_trades.empty:
            k = cohort_size[day]
            per_position_notional = equity_now * allocation / k
            for _, t in day_trades.iterrows():
                shares = int(per_position_notional / t["entry_price"])
                if shares <= 0:
                    shares_per_trade[t["_orig_idx"]] = 0
                    per_trade_equity_at_entry[t["_orig_idx"]] = equity_now
                    continue
                # Long: pay cash to buy. Short: receive cash.
                cost = shares * t["entry_price"]
                if t["direction"] == "long":
                    cash -= cost
                else:
                    cash += cost
                shares_per_trade[t["_orig_idx"]] = shares
                per_trade_equity_at_entry[t["_orig_idx"]] = equity_now
                open_positions.append({
                    "shares":      shares,
                    "entry_price": t["entry_price"],
                    "exit_price":  t["exit_price"],
                    "exit_date":   t["exit_date"],
                    "direction":   t["direction"],
                    "instrument":  t["instrument"],
                    "trade_idx":   t["_orig_idx"],
                })

        # ── 4. Record daily equity (cash + position value) ──
        position_value = 0.0
        for pos in open_positions:
            series = prices_norm.get(pos["instrument"])
            if series is not None and day in series.index:
                px = series.loc[day]
            else:
                px = np.nan
            if pd.isna(px):
                px = pos["entry_price"]
            if pos["direction"] == "long":
                position_value += pos["shares"] * px
            else:
                position_value += pos["shares"] * (2 * pos["entry_price"] - px)
        daily_values[day] = cash + position_value

    # Close any remaining open positions at their exit_price (safety net)
    for pos in open_positions:
        if pos["direction"] == "long":
            proceeds = pos["shares"] * pos["exit_price"]
            gross_pnl = pos["shares"] * (pos["exit_price"] - pos["entry_price"])
        else:
            proceeds = pos["shares"] * (2 * pos["entry_price"] - pos["exit_price"])
            gross_pnl = pos["shares"] * (pos["entry_price"] - pos["exit_price"])
        fees = (calculate_fees(pos["shares"], pos["entry_price"],
                                pos["exit_price"], pos["direction"],
                                slippage=slippage)
                  if include_fees else 0.0)
        net_pnl = gross_pnl - fees
        cash += proceeds - fees
        idx = pos["trade_idx"]
        per_trade_pnl[idx] = net_pnl
        eq_at_entry = per_trade_equity_at_entry[idx]
        sized_returns[idx] = (net_pnl / eq_at_entry) if eq_at_entry > 0 else 0.0

    # ── Build equity_curve (one point per trade exit, in exit_time order) ──
    # Same contract as simple_bet: [starting_capital, eq_after_trade_1, ...]
    trades_by_exit = trades.sort_values("exit_date")
    eq = starting_capital
    equity_curve = [starting_capital]
    for _, t in trades_by_exit.iterrows():
        eq += per_trade_pnl[t["_orig_idx"]]
        equity_curve.append(eq)

    # ── Build daily equity Series ──
    daily_eq = pd.Series(daily_values).sort_index()
    daily_eq = daily_eq.reindex(all_days, method="ffill").fillna(starting_capital)
    daily_eq.index.name = "date"
    daily_eq.name = "equity"

    # ── Stats from daily equity (more accurate for concurrent-position basket) ──
    # Detect account ruin first — negative equity breaks all ratios
    blew_up = (daily_eq.iloc[-1] <= 0) or (daily_eq.min() <= 0)
    daily_returns = daily_eq.pct_change().dropna()

    if blew_up:
        total_return = max((daily_eq.iloc[-1] / starting_capital - 1) * 100, -100.0)
        sharpe       = float('nan')
        sortino      = float('nan')
        max_dd       = -100.0
        cagr         = float('nan')
    else:
        total_return = (daily_eq.iloc[-1] / starting_capital - 1) * 100
        sharpe = (daily_returns.mean() / daily_returns.std() * np.sqrt(252)
                   if daily_returns.std() > 0 else 0.0)
        peak = daily_eq.expanding().max()
        max_dd = ((daily_eq - peak) / peak).min() * 100
        years = (daily_eq.index[-1] - daily_eq.index[0]).days / 365.25
        cagr = ((daily_eq.iloc[-1] / starting_capital) ** (1 / years) - 1) * 100 if years > 0 else 0.0
        downside = daily_returns[daily_returns < 0]
        sortino = (daily_returns.mean() / downside.std() * np.sqrt(252)
                    if len(downside) > 0 and downside.std() > 0 else 0.0)

    win_rate = (pd.Series(sized_returns) > 0).mean() * 100
    pos_sum = sum(p for p in per_trade_pnl if p > 0)
    neg_sum = -sum(p for p in per_trade_pnl if p < 0)
    profit_factor = pos_sum / neg_sum if neg_sum > 0 else (np.inf if pos_sum > 0 else 0.0)

    stats = {
        "total_return":  round(total_return, 2) if not blew_up else total_return,
        "cagr":          round(cagr, 2) if not blew_up else cagr,
        "sharpe":        round(sharpe, 2) if not blew_up else sharpe,
        "sortino":       round(sortino, 2) if not blew_up else sortino,
        "max_dd":        round(max_dd, 2),
        "win_rate":      round(win_rate, 1),
        "profit_factor": round(profit_factor, 2) if np.isfinite(profit_factor) else 999.0,
        "trades":        len(trades),
        "blew_up":       blew_up,
    }

    return {
        "equity_curve":     equity_curve,
        "sized_returns":    sized_returns,
        "shares_per_trade": shares_per_trade,
        "daily_equity":     daily_eq,
        "stats":            stats,
        "label":            f"Basket ({allocation:.0%} allocation)",
    }


# ═══════════════════════════════════════════════════════════════════════
# COMPARISON / DISPLAY
# ═══════════════════════════════════════════════════════════════════════


def compare_implementations(results_list, starting_capital=100_000):
    """
    Print comparison table of multiple implementation results.

    Parameters
    ----------
    results_list : list of dicts — output from the sizing functions above
    """
    print(f"\n{'Implementation':<35} {'Return':<12} {'CAGR':<10} {'Sharpe':<10} "
          f"{'Sortino':<10} {'MaxDD':<10} {'WinRate':<10} {'PF':<10}")
    print("=" * 107)

    for r in results_list:
        s = r["stats"]
        print(f"{r['label']:<35} {s['total_return']:>8.1f}%   {s['cagr']:>6.1f}%   "
              f"{s['sharpe']:>7.2f}   {s['sortino']:>7.2f}   {s['max_dd']:>7.1f}%   "
              f"{s['win_rate']:>6.1f}%   {s['profit_factor']:>6.2f}")
