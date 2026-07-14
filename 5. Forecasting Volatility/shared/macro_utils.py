"""
macro_utils.py — Shared utilities for the Macro Strategy project.

Consolidated from:
  - AR_Development.ipynb (picos, rolling stats, percentiles)
  - MACROS_DATA.ipynb / Commodities_Processing.ipynb (process_df, alphas, outliers)
  - SUPERFILES_1.ipynb (constituent processing)
  - SP500_DATA.ipynb (return features)

Key fixes vs. originals:
  - No weekend/holiday interpolation (business days only)
  - Deduplicated functions (were copy-pasted across 4+ notebooks)
  - Publication lag support for macro data
  - Proper frequency inference (median diff, not just first two rows)
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from scipy.stats import percentileofscore, skew


# =============================================================================
# 1. DATA CLEANING
# =============================================================================

def reset_index(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
    """Set date column as DatetimeIndex named 'date'."""
    df = df.rename(columns={date_column: 'date'})
    df.index = pd.to_datetime(df['date'])
    df = df.drop(columns='date')
    df.index.name = 'date'
    return df


def infer_frequency(df: pd.DataFrame) -> str:
    """
    Infer frequency from a DatetimeIndex DataFrame using median gap.
    
    Fixed vs. original: uses median of first 10 diffs instead of just
    the first two rows, which was fragile.
    """
    diffs = df.index.to_series().diff().dropna().head(10)
    median_days = diffs.dt.days.median()
    
    if median_days <= 5:
        return 'daily'
    elif median_days <= 35:
        return 'monthly'
    elif median_days <= 100:
        return 'quarterly'
    else:
        return 'yearly'


def fill_na_ts(df: pd.DataFrame, method: str = 'ffill') -> pd.DataFrame:
    """
    Fill NaN values in a time series. 
    
    Uses forward-fill by default (causal — no future leakage).
    Original used backward-fill which leaks future data.
    """
    if method == 'ffill':
        return df.ffill()
    elif method == 'bfill':
        return df.bfill()
    elif method == 'interpolate':
        return df.interpolate(method='linear')
    else:
        raise ValueError(f"Unknown method: {method}")


def trim_nan_edges(df: pd.DataFrame) -> pd.DataFrame:
    """Trim to the range between first and last fully non-NaN rows."""
    df_clean = df.dropna()
    if df_clean.empty:
        return df
    return df.loc[df_clean.index[0]:df_clean.index[-1]]


# =============================================================================
# 2. ALPHA / CHANGE FEATURES
# =============================================================================

def get_alpha(df: pd.DataFrame, column: str, window: int) -> pd.Series:
    """
    Percent change from `window` periods ago: (current - past) / past.
    
    Returns as a decimal (0.05 = 5%), not multiplied by 100.
    Fixed vs. original: handles zero/near-zero denominators gracefully.
    """
    current = df[column]
    past = df[column].shift(window)
    alpha = (current - past) / past.replace(0, np.nan)
    return alpha.round(4)


def add_alpha_columns(df: pd.DataFrame, column: str, freq: str) -> pd.DataFrame:
    """
    Add standard alpha columns based on frequency.
    
    Daily:     1d, 5d (week), 21d (month), 63d (quarter), 252d (year)
    Monthly:   1m, 3m, 12m
    Quarterly: 1q, 4q
    """
    df = df.copy()
    prefix = column
    
    if freq == 'daily':
        for window, suffix in [(1, '_d1'), (5, '_w1'), (21, '_m1'), (63, '_q1'), (252, '_y1')]:
            df[f'{prefix}{suffix}'] = get_alpha(df, column, window)
    elif freq == 'monthly':
        for window, suffix in [(1, '_m1'), (3, '_q1'), (12, '_y1')]:
            df[f'{prefix}{suffix}'] = get_alpha(df, column, window)
    elif freq == 'quarterly':
        for window, suffix in [(1, '_q1'), (4, '_y1')]:
            df[f'{prefix}{suffix}'] = get_alpha(df, column, window)
    elif freq == 'yearly':
        df[f'{prefix}_y1'] = get_alpha(df, column, 1)
    
    return df


# =============================================================================
# 3. OUTLIER DETECTION
# =============================================================================

def is_outlier_iqr(value: float, data: np.ndarray) -> bool:
    """Check if value is an outlier using IQR method."""
    q1 = np.percentile(data, 25)
    q3 = np.percentile(data, 75)
    iqr = q3 - q1
    return value < (q1 - 1.5 * iqr) or value > (q3 + 1.5 * iqr)


def add_historical_outlier_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    For each row, flag whether the value is an outlier relative to all
    PRIOR data (expanding window). Causal — no future leakage.
    
    Note: O(n²) — fine for monthly/quarterly, slow for large daily datasets.
    For daily data with 8000+ rows, consider using a rolling window instead.
    """
    df = df.copy()
    values = df[column].values
    flags = []
    
    for i in range(len(values)):
        if i < 20:  # need minimum sample
            flags.append(False)
        else:
            flags.append(is_outlier_iqr(values[i], values[:i+1]))
    
    df[f'{column}_outlier'] = flags
    return df


def add_historical_percentile_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    For each row, compute the percentile of the current value relative
    to all prior data (expanding window).
    """
    df = df.copy()
    values = df[column].values
    pcts = []
    
    for i in range(len(values)):
        if i < 2:
            pcts.append(np.nan)
        else:
            pcts.append(percentileofscore(values[:i], values[i]) / 100)
    
    df[f'{column}_pctile'] = pcts
    return df


# =============================================================================
# 4. MACRO / COMMODITY DATA PROCESSING
# =============================================================================

def process_macro_series(
    df: pd.DataFrame,
    name: str,
    date_column: str,
    value_column: str,
    publication_lag_days: int = 0,
    add_outliers: bool = False,
    verbose: bool = False
) -> Tuple[pd.DataFrame, str]:
    """
    Full processing pipeline for a single macro/commodity time series.
    
    Steps:
      1. Reset index to DatetimeIndex
      2. Infer frequency
      3. Forward-fill NaNs (causal)
      4. Apply publication lag (shift dates forward)
      5. Rename value column
      6. Add alpha columns
      7. Optionally add outlier flags
    
    Args:
        df: Raw DataFrame with date and value columns.
        name: Name for this series (used as column prefix).
        date_column: Name of the date column.
        value_column: Name of the value column.
        publication_lag_days: Days to shift forward (for macro release delays).
        add_outliers: Whether to compute historical outlier flags (slow for daily).
        verbose: Print info.
    
    Returns:
        (processed_df, frequency_string)
    """
    if df.shape[1] > 2:
        # Keep only date + value columns
        df = df[[date_column, value_column]]
    
    # Reset index
    df = reset_index(df, date_column)
    
    # Infer frequency
    freq = infer_frequency(df)
    
    # Rename value column
    col_name = f'{name}'
    df = df.rename(columns={value_column: col_name})
    
    # Forward-fill NaNs (causal, no future leakage)
    df = df.ffill()
    
    # Apply publication lag
    if publication_lag_days > 0:
        df.index = df.index + pd.Timedelta(days=publication_lag_days)
    
    # Add alphas
    df = add_alpha_columns(df, col_name, freq)
    
    # Add outlier flags (optional, slow for daily)
    if add_outliers:
        df = add_historical_outlier_column(df, col_name)
    
    if verbose:
        print(f"  {name}: {freq}, {df.index[0].date()} → {df.index[-1].date()}, {len(df)} rows")
    
    return df, freq


def process_macro_folder(
    directory: str,
    publication_lags: Optional[dict] = None,
    files_to_drop: Optional[List[str]] = None,
    add_outliers: bool = False,
    verbose: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Process all CSV files in a macro data folder, sorting by frequency.
    
    Returns four DataFrames: (daily, monthly, quarterly, yearly).
    """
    import os
    import fnmatch
    
    if publication_lags is None:
        publication_lags = {}
    if files_to_drop is None:
        files_to_drop = []
    
    matching_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if fnmatch.fnmatch(file, '*.csv') and file not in files_to_drop:
                matching_files.append(file)
    
    dfs = {'daily': pd.DataFrame(), 'monthly': pd.DataFrame(),
           'quarterly': pd.DataFrame(), 'yearly': pd.DataFrame()}
    refs = {}
    
    for file in sorted(matching_files):
        file_name = file.split('.')[0]
        raw = pd.read_csv(os.path.join(directory, file))
        lag = publication_lags.get(file_name, 0)
        
        try:
            processed, freq = process_macro_series(
                raw, file_name, raw.columns[0], raw.columns[1],
                publication_lag_days=lag, add_outliers=add_outliers, verbose=verbose
            )
            dfs[freq] = dfs[freq].join(processed, how='outer')
            refs[file_name] = {
                'start': processed.index[0], 'end': processed.index[-1], 'freq': freq
            }
        except Exception as e:
            print(f"  ERROR processing {file_name}: {e}")
    
    if verbose:
        print(f"\nProcessed {len(refs)} series.")
    
    return dfs['daily'], dfs['monthly'], dfs['quarterly'], dfs['yearly']


# =============================================================================
# 5. S&P 500 INDEX FEATURES (from SP500_DATA / AR_Development)
# =============================================================================

def add_return_features(df: pd.DataFrame, price_col: str = 'spindx',
                        return_col: str = 'sprtrn') -> pd.DataFrame:
    """
    Add rolling return statistics at standard windows.
    Windows: 5d, 20d, 60d, 126d, 252d.
    """
    df = df.copy()
    returns = df[return_col]
    
    for w in [5, 20, 60, 126, 252]:
        df[f'ma_return_{w}'] = returns.rolling(w).mean()
        df[f'momentum_{w}'] = returns.shift(1).rolling(w).mean()
        df[f'realized_vol_{w}'] = returns.rolling(w).std()
        rolling_mean = returns.rolling(w).mean()
        df[f'return_trend_{w}'] = rolling_mean - rolling_mean.shift(w)
    
    return df


# --- Picos detection (from AR_Development) ---

def get_picos(df: pd.DataFrame, column: str) -> pd.DatetimeIndex:
    """Detect all local peaks/troughs (sign changes in first derivative)."""
    delta = df[column] - df[column].shift(1)
    sign = np.sign(delta)
    sign_shift = sign.shift(-1)
    return df[sign != sign_shift].index


def get_main_picos(df: pd.DataFrame, column: str,
                   threshold: float = 0.04) -> pd.DataFrame:
    """
    Detect significant peaks/troughs where the move exceeds `threshold`.
    Returns DataFrame with columns: [column, 'type', 'alpha'].
    """
    picos = get_picos(df, column)
    df_picos = df.loc[picos][[column]].copy()
    
    # Compute move since previous pico
    alpha = (df_picos[column] - df_picos[column].shift(1)) / df_picos[column].shift(1)
    df_picos['alpha'] = alpha.round(4)
    df_picos['type'] = np.where(df_picos['alpha'] > 0, 'peak', 'trough')
    
    # Keep only significant moves
    df_picos = df_picos[df_picos['alpha'].abs() >= threshold]
    
    return df_picos


def add_pico_features(df: pd.DataFrame, column: str,
                      threshold: float = 0.04) -> pd.DataFrame:
    """
    Add pico-derived features: distance to last peak/trough, magnitude
    of last significant move, count of recent significant moves.
    """
    df = df.copy()
    main_picos = get_main_picos(df, column, threshold)
    
    peaks = main_picos[main_picos['type'] == 'peak'].index
    troughs = main_picos[main_picos['type'] == 'trough'].index
    
    # For each row, find days since last peak and last trough
    days_since_peak = []
    days_since_trough = []
    last_peak_alpha = []
    last_trough_alpha = []
    
    for date in df.index:
        # Last peak
        prior_peaks = peaks[peaks < date]
        if len(prior_peaks) > 0:
            last_p = prior_peaks[-1]
            days_since_peak.append((date - last_p).days)
            last_peak_alpha.append(main_picos.loc[last_p, 'alpha'])
        else:
            days_since_peak.append(np.nan)
            last_peak_alpha.append(np.nan)
        
        # Last trough
        prior_troughs = troughs[troughs < date]
        if len(prior_troughs) > 0:
            last_t = prior_troughs[-1]
            days_since_trough.append((date - last_t).days)
            last_trough_alpha.append(main_picos.loc[last_t, 'alpha'])
        else:
            days_since_trough.append(np.nan)
            last_trough_alpha.append(np.nan)
    
    df['days_since_peak'] = days_since_peak
    df['days_since_trough'] = days_since_trough
    df['last_peak_alpha'] = last_peak_alpha
    df['last_trough_alpha'] = last_trough_alpha
    
    return df


# --- Rolling stats (from AR_Development) ---

def add_rolling_stats(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Add rolling max, min, percentile, drawdown at standard windows."""
    df = df.copy()
    
    for w in [60, 126, 252]:
        rolling = df[column].rolling(w)
        df[f'rolling_max_{w}'] = rolling.max()
        df[f'rolling_min_{w}'] = rolling.min()
        df[f'pct_from_max_{w}'] = (df[column] - df[f'rolling_max_{w}']) / df[f'rolling_max_{w}']
        df[f'pct_from_min_{w}'] = (df[column] - df[f'rolling_min_{w}']) / df[f'rolling_min_{w}']
    
    return df


# =============================================================================
# 6. S&P 500 CONSTITUENT FEATURES (from SUPERFILES_1 / SUPERFIELS_DATA)
# =============================================================================

def compute_daily_constituent_stats(stocks: pd.DataFrame,
                                     date_col: str = 'DlyCalDt') -> pd.DataFrame:
    """
    Compute daily cross-sectional statistics across S&P 500 constituents.
    
    Input: stock-level DataFrame with columns including DlyVol, DlyRetx, DlyCap, ShrOut.
    Output: one row per day with aggregate statistics.
    """
    result = []
    
    for date, group in stocks.groupby(date_col):
        group = group.dropna(subset=['DlyVol', 'DlyRetx'])
        if group.empty:
            continue
        
        total_volume = group['DlyVol'].sum()
        avg_volume = total_volume / len(group)
        
        # Volume concentration
        vol_share = group['DlyVol'] / total_volume
        herfindahl_vol = (vol_share ** 2).sum()
        volume_skewness = group['DlyVol'].skew()
        
        # Cap-based splits
        group_sorted = group.sort_values('DlyCap', ascending=False)
        top_n = max(int(len(group) * 0.10), 1)
        top_10_vol_share = group_sorted.head(top_n)['DlyVol'].sum() / total_volume
        
        # Turnover
        avg_turnover = np.nan
        if 'ShrOut' in group.columns:
            turnover = group['DlyVol'] / group['ShrOut'].replace(0, np.nan)
            avg_turnover = turnover.mean()
        
        # Return stats
        avg_ret = group['DlyRetx'].mean()
        ret_abs = group['DlyRetx'].abs()
        ret_share = ret_abs / ret_abs.sum()
        herfindahl_ret = (ret_share ** 2).sum()
        return_skewness = group['DlyRetx'].skew()
        
        result.append({
            'date': date,
            'avg_volume': avg_volume,
            'top_10_vol_share': top_10_vol_share,
            'herfindahl_vol': herfindahl_vol,
            'volume_skewness': volume_skewness,
            'avg_turnover': avg_turnover,
            'avg_ret': avg_ret,
            'herfindahl_ret': herfindahl_ret,
            'return_skewness': return_skewness,
        })
    
    df_stats = pd.DataFrame(result).sort_values('date').reset_index(drop=True)
    df_stats['date'] = pd.to_datetime(df_stats['date'])
    df_stats = df_stats.set_index('date')
    
    # Add rolling features
    for w in [5, 20, 60, 126, 252]:
        for col in ['avg_volume', 'herfindahl_vol', 'avg_ret', 'herfindahl_ret', 'avg_turnover']:
            df_stats[f'{col}_ma{w}'] = df_stats[col].rolling(w).mean()
    
    return df_stats


# =============================================================================
# 7. MERGING
# =============================================================================

def merge_frequencies_to_daily(
    daily_df: pd.DataFrame,
    monthly_df: Optional[pd.DataFrame] = None,
    quarterly_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Upsample monthly/quarterly data to daily using forward-fill (causal),
    then join to the daily DataFrame.
    
    Only fills on dates that exist in daily_df (business days only —
    no weekend interpolation).
    """
    daily_index = daily_df.index
    merged = daily_df.copy()
    
    if monthly_df is not None and not monthly_df.empty:
        monthly_up = monthly_df.reindex(daily_index, method='ffill')
        merged = merged.join(monthly_up, how='left', rsuffix='_monthly')
    
    if quarterly_df is not None and not quarterly_df.empty:
        quarterly_up = quarterly_df.reindex(daily_index, method='ffill')
        merged = merged.join(quarterly_up, how='left', rsuffix='_quarterly')
    
    return merged


# =============================================================================
# 8. TARGET CREATION
# =============================================================================

def add_forward_return_target(df: pd.DataFrame, price_col: str = 'spindx',
                               horizon: int = 60) -> pd.DataFrame:
    """
    Add forward return columns for a given horizon.
    
    Creates:
      - target_return_{horizon}d: continuous forward return
      - target_up_{horizon}d: binary (1 if positive, 0 otherwise)
    """
    df = df.copy()
    future = df[price_col].shift(-horizon)
    df[f'target_return_{horizon}d'] = (future - df[price_col]) / df[price_col]
    df[f'target_up_{horizon}d'] = (df[f'target_return_{horizon}d'] > 0).astype(float)
    # NaN out the tail where we don't have future data
    df.loc[df[f'target_return_{horizon}d'].isna(), f'target_up_{horizon}d'] = np.nan
    return df


# =============================================================================
# 9. PLOTTING HELPERS
# =============================================================================

def plot_picos(df: pd.DataFrame, column: str, picos: pd.DatetimeIndex = None):
    """Plot time series with peak/trough markers."""
    import matplotlib.pyplot as plt
    
    if picos is None:
        picos = get_picos(df, column)
    
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df.index, df[column], label=column)
    ax.scatter(picos, df.loc[picos, column], color='red', s=20, zorder=5, label='Picos')
    ax.set_title(f'{column} with detected peaks/troughs')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
