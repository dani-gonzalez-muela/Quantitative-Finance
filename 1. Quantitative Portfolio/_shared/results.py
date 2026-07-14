"""
shared.results — Save and load trade results.

Simple CSV persistence so you don't have to re-run backtests.
"""

import os
import pandas as pd


def save_trades(trades_df, strategy_name, output_dir="results"):
    """
    Save trades DataFrame to CSV.

    Parameters
    ----------
    trades_df     : pd.DataFrame — standardized trades DataFrame.
    strategy_name : str          — used in the filename (e.g. "ema_crossover").
    output_dir    : str          — directory to save into.

    Returns
    -------
    str — path to the saved file.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{strategy_name}_trades.csv"
    path = os.path.join(output_dir, filename)
    trades_df.to_csv(path, index=False)
    print(f"Saved {len(trades_df)} trades → {path}")
    return path


def load_trades(strategy_name, output_dir="results"):
    """
    Load trades DataFrame from CSV.

    Parameters
    ----------
    strategy_name : str — must match the name used in save_trades.
    output_dir    : str — directory to look in.

    Returns
    -------
    pd.DataFrame
    """
    filename = f"{strategy_name}_trades.csv"
    path = os.path.join(output_dir, filename)
    df = pd.read_csv(path)

    # Robustly parse datetime columns — handles timezone-aware strings
    for col in ["entry_time", "exit_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
            # Strip timezone so downstream .dt accessors work cleanly
            df[col] = df[col].dt.tz_localize(None)

    print(f"Loaded {len(df)} trades ← {path}")
    return df
