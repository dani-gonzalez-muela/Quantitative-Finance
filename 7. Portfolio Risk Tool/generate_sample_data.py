"""
Generate sample CSV with fictional daily returns for 10 assets over 2 years.

This script produces realistic-looking return distributions:
- Varying annualized volatilities (8% to 35%) across assets
- Slight positive mean returns (mimicking risk premia)
- Correlated returns (not independent noise)
- A few intentional NaN values for testing missing data handling
"""

import numpy as np
import pandas as pd

SEED = 42
N_DAYS = 504  # ~2 years of trading days
N_ASSETS = 10
ASSET_NAMES = [f"ASSET_{i:02d}" for i in range(1, N_ASSETS + 1)]

# Reproducible
rng = np.random.default_rng(SEED)

# Annualized volatilities ranging from bond-like (8%) to crypto-like (35%)
annual_vols = np.array([0.08, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.35])
daily_vols = annual_vols / np.sqrt(252)

# Annualized mean returns (slight positive bias, higher vol -> higher mean)
annual_means = np.array([0.03, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.14])
daily_means = annual_means / 252

# Generate a random correlation matrix to make returns realistic
# Method: generate random matrix, multiply by transpose, normalize
random_matrix = rng.standard_normal((N_ASSETS, N_ASSETS))
cov_raw = random_matrix @ random_matrix.T
std_diag = np.sqrt(np.diag(cov_raw))
corr_matrix = cov_raw / np.outer(std_diag, std_diag)

# Build covariance matrix from correlations and daily vols
cov_matrix = np.outer(daily_vols, daily_vols) * corr_matrix

# Generate correlated returns
returns = rng.multivariate_normal(daily_means, cov_matrix, size=N_DAYS)

# Create date index (business days)
dates = pd.bdate_range(start="2023-01-02", periods=N_DAYS)

df = pd.DataFrame(returns, index=dates, columns=ASSET_NAMES)
df.index.name = "date"

# Round to 6 decimal places (realistic precision)
df = df.round(6)

# Scatter a few NaN values for testing (about 0.3% of data)
n_nans = 15
nan_rows = rng.integers(0, N_DAYS, size=n_nans)
nan_cols = rng.integers(0, N_ASSETS, size=n_nans)
for r, c in zip(nan_rows, nan_cols):
    df.iloc[r, c] = np.nan

# Save
output_path = "sample_returns.csv"
df.to_csv(output_path)
print(f"Generated {output_path}: {df.shape[0]} days x {df.shape[1]} assets")
print(f"NaN count: {df.isna().sum().sum()}")
print(f"\nFirst 5 rows:")
print(df.head())
print(f"\nSummary statistics (annualized):")
print(f"Mean returns: {(df.mean() * 252).round(4).to_dict()}")
print(f"Volatilities: {(df.std() * np.sqrt(252)).round(4).to_dict()}")
