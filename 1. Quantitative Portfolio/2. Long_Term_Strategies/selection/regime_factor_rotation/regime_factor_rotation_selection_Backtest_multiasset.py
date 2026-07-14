# -*- coding: utf-8 -*-
"""
Regime Factor Rotation — Multi-Asset Selection Backtest
=========================================================
Signal: PCA + Gaussian Mixture Model (GMM) on the macro panel
        (monthly_panel_transformed.csv + quarterly_panel_transformed.csv)
        detects 2 or 3 economic regimes.  For each regime, average historical
        Fama-French factor returns determine a per-regime factor score.
        Available factor ETFs are ranked by their factor-loading × regime score
        and the top_pct fraction are held until the next rebalance.

Basket
------
  us_factor_quality: IWF, IWD, QUAL, USMV, MTUM, PKW, DVY, IWM

Factor → ETF mapping (loading-based)
-------------------------------------
  SMB  → IWM  (small-cap)
  HML  → IWD  (value) and DVY (dividend / value tilt, half-weight)
  -HML → IWF  (growth, inverse value)
  RMW  → QUAL (quality) and USMV (defensive, half-weight)
  Mom  → MTUM (momentum)
  CMA  → PKW  (buyback / conservative investment)

Grid
----
  TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
  REBAL_FREQS = ['ME', '2ME', 'QE', '6ME', '12ME']
  N_REGIMES   = [2, 3]
  = 60 combos × 2 regime configs × 1 universe = 60 runs

Data (all local)
----------------
  data/monthly_panel_transformed.csv
  data/quarterly_panel_transformed.csv
  data/ff_factors_monthly.csv
  long_term/multi_asset_expansion/data/tickers/{ticker}.csv

Outputs
-------
  results/regime_factor_rotation_multiasset_grid.csv
  results/regime_factor_rotation_multiasset_summary.json
"""

import sys, os

import sys, os
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d)
    assert _p != _d, ".project_root marker not found - place it at the algo_trading root"
    _d = _p
_ROOT = _d
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
from itertools import product

warnings.filterwarnings("ignore")

# ── optional sklearn (PCA + GMM) ─────────────────────────────────────────────
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.mixture import GaussianMixture
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("WARNING: sklearn not found — falling back to k-means-style regime detection")

# ── constants ──────────────────────────────────────────────────────────────────
STRATEGY_NAME    = "Regime Factor Rotation (Multi-Asset)"
SAVE_NAME        = "regime_factor_rotation_multiasset"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
MACRO_START      = "1984-01-01"
GMM_PCA_COMPS    = 10
GMM_COV_TYPE     = "full"
GMM_REFIT_EVERY  = 24          # months between GMM refits

# -- fable data-manifest bootstrap (Phase E consolidation) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
if _bd not in _sys.path:
    _sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
DATA_DIR    = data_dir('daily_tickers')
LOCAL_DATA  = os.path.join(_FILE_DIR, "data")
OUTPUT_BASE = _FILE_DIR
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
N_REGIMES   = [2, 3]
_FREQ_MONTHS = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

# Factor ETFs and their loadings on each FF factor
# Format: {ticker: {factor: weight}}  (weights sum doesn't need to be 1 — used for scoring)
ETF_FACTOR_LOADS = {
    "IWM":  {"SMB":  1.0, "HML":  0.0, "RMW": 0.0, "CMA": 0.0, "Mom": 0.0},
    "IWD":  {"SMB":  0.0, "HML":  1.0, "RMW": 0.0, "CMA": 0.0, "Mom": 0.0},
    "QUAL": {"SMB":  0.0, "HML":  0.0, "RMW": 1.0, "CMA": 0.0, "Mom": 0.0},
    "USMV": {"SMB":  0.0, "HML":  0.0, "RMW": 0.5, "CMA": 0.5, "Mom": 0.0},
    "MTUM": {"SMB":  0.0, "HML":  0.0, "RMW": 0.0, "CMA": 0.0, "Mom": 1.0},
    "PKW":  {"SMB":  0.0, "HML":  0.0, "RMW": 0.0, "CMA": 1.0, "Mom": 0.0},
    "DVY":  {"SMB":  0.0, "HML":  0.5, "RMW": 0.5, "CMA": 0.0, "Mom": 0.0},
    "IWF":  {"SMB":  0.0, "HML": -1.0, "RMW": 0.0, "CMA": 0.0, "Mom": 0.0},
}
ALL_FACTOR_ETFS = list(ETF_FACTOR_LOADS.keys())
FF_FACTORS = ["SMB", "HML", "RMW", "CMA", "Mom"]

UNIVERSE_SPECS = {
    "us_factor_quality": ALL_FACTOR_ETFS,
}

print("=" * 75)
print("REGIME FACTOR ROTATION — Multi-Asset Backtest")
print("=" * 75)
print(f"Period   : {START_DATE} → {END_DATE}")
print(f"ETFs     : {ALL_FACTOR_ETFS}\n")

# ── Load macro panel ──────────────────────────────────────────────────────────
print("Loading macro panel...")
monthly_macro  = pd.read_csv(
    os.path.join(LOCAL_DATA, "monthly_panel_transformed.csv"),
    index_col=0, parse_dates=True)
quarterly_macro = pd.read_csv(
    os.path.join(LOCAL_DATA, "quarterly_panel_transformed.csv"),
    index_col=0, parse_dates=True)

quarterly_ffill = quarterly_macro.resample("MS").ffill()
macro_panel = pd.concat([monthly_macro, quarterly_ffill], axis=1).ffill().bfill().fillna(0)
macro_panel = macro_panel.dropna(axis=1, how="all")
macro_panel = macro_panel[macro_panel.index >= MACRO_START]
print(f"  macro panel: {macro_panel.shape}, "
      f"{macro_panel.index.min().date()} → {macro_panel.index.max().date()}")

# ── Load Fama-French factor returns ──────────────────────────────────────────
print("Loading FF factor returns...")
ff = pd.read_csv(
    os.path.join(LOCAL_DATA, "ff_factors_monthly.csv"),
    index_col=0, parse_dates=True)
ff.index = pd.to_datetime(ff.index)
# Align to month-start
ff.index = ff.index.to_period("M").to_timestamp()  # normalize to month-start
factor_returns = ff[FF_FACTORS].copy()
print(f"  FF factors: {factor_returns.shape}, "
      f"{factor_returns.index.min().date()} → {factor_returns.index.max().date()}")

# Common index
common_start = max(macro_panel.index.min(), factor_returns.index.min())
common_end   = min(macro_panel.index.max(),  factor_returns.index.max())
common_idx   = macro_panel[common_start:common_end].index.intersection(
               factor_returns[common_start:common_end].index)
macro_aligned   = macro_panel.loc[common_idx]
factors_aligned = factor_returns.loc[common_idx]
print(f"  aligned: macro {macro_aligned.shape}, factors {factors_aligned.shape}\n")

# ── Load ETF prices ───────────────────────────────────────────────────────────
print("Loading factor ETF prices...")
ETF_PRICES = {}
for ticker in ALL_FACTOR_ETFS:
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        print(f"  {ticker}: NOT FOUND — skipping")
        continue
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        s = df["close"].dropna()
        s = s[(s.index >= START_DATE) & (s.index <= END_DATE)]
        if len(s) >= 252:
            ETF_PRICES[ticker] = s
            print(f"  {ticker}: {len(s)} days, {s.index[0].date()} → {s.index[-1].date()}")
        else:
            print(f"  {ticker}: only {len(s)} days — skipping")
    except Exception as e:
        print(f"  {ticker}: ERROR {e}")

AVAILABLE = list(ETF_PRICES.keys())
print(f"\nAvailable ETFs: {AVAILABLE}")

def load_universe_prices(tickers):
    avail = [t for t in tickers if t in ETF_PRICES]
    if not avail:
        return pd.DataFrame()
    df = pd.DataFrame({t: ETF_PRICES[t] for t in avail})
    return df.sort_index()

UNIVERSES = {}
for uni_name, tickers in UNIVERSE_SPECS.items():
    wide = load_universe_prices(tickers)
    avail = list(wide.columns)
    print(f"\n  {uni_name}: {len(avail)}/{len(tickers)} tickers  [{', '.join(avail)}]")
    if len(avail) >= 3:
        UNIVERSES[uni_name] = wide
    else:
        print(f"  *** {uni_name} excluded — only {len(avail)} tickers ***")

if not UNIVERSES:
    print("ERROR: No valid universes. Exiting.")
    sys.exit(1)

# ── GMM Regime Detection ──────────────────────────────────────────────────────

def fit_gmm_walk_forward(macro_df, n_regimes, n_pca=GMM_PCA_COMPS,
                          cov_type=GMM_COV_TYPE, refit_every=GMM_REFIT_EVERY):
    """
    Walk-forward PCA + GMM regime labelling on the macro panel.
    Returns pd.Series of regime labels indexed by month-start date.
    Uses 50% of history for initial training, then refits every `refit_every` months.
    """
    n = len(macro_df)
    init_n = max(int(n * 0.50), 24)   # at least 2 years
    labels = pd.Series(np.nan, index=macro_df.index)

    scaler = StandardScaler()
    pca    = PCA(n_components=min(n_pca, macro_df.shape[1]))

    last_fit_idx = -1
    gmm = None
    scaler_fitted = None
    pca_fitted = None

    for i in range(init_n, n):
        needs_refit = (last_fit_idx < 0) or ((i - last_fit_idx) >= refit_every)
        if needs_refit:
            train_X = macro_df.iloc[:i].values
            # re-scale on full training window
            scaler_fitted = StandardScaler().fit(train_X)
            X_s = scaler_fitted.transform(train_X)
            n_comps = min(n_pca, X_s.shape[1], X_s.shape[0] - 1)
            pca_fitted = PCA(n_components=n_comps).fit(X_s)
            X_pca = pca_fitted.transform(X_s)
            try:
                gmm = GaussianMixture(
                    n_components=n_regimes, covariance_type=cov_type,
                    random_state=42, n_init=5, max_iter=500
                ).fit(X_pca)
            except Exception:
                gmm = None
            last_fit_idx = i

        if gmm is None:
            continue
        row = macro_df.iloc[i:i+1].values
        row_s = scaler_fitted.transform(row)
        row_pca = pca_fitted.transform(row_s)
        labels.iloc[i] = int(gmm.predict(row_pca)[0])

    return labels.dropna().astype(int)


def compute_regime_factor_scores(regime_labels, factor_rets_df):
    """
    For each date in regime_labels, compute a score for every FF factor
    = mean historical factor return in that regime (expanding window).
    Returns DataFrame: index=dates, columns=FF_FACTORS.
    """
    scores = pd.DataFrame(index=regime_labels.index, columns=FF_FACTORS, dtype=float)
    all_dates = regime_labels.index

    for i, date in enumerate(all_dates):
        regime = regime_labels.iloc[i]
        # Use all history up to but not including current date
        past_labels  = regime_labels.iloc[:i]
        past_factors = factor_rets_df.reindex(past_labels.index).dropna()
        past_labels  = past_labels.reindex(past_factors.index)

        mask = past_labels == regime
        if mask.sum() < 3:
            # Not enough history in this regime — use equal scores
            scores.loc[date] = pd.Series(1.0 / len(FF_FACTORS), index=FF_FACTORS)
            continue

        regime_avg = past_factors[mask].mean()
        # Rank-based: convert to weights ∈ [0,1]
        rnk = regime_avg.rank(ascending=True)
        w   = rnk / rnk.sum()
        w   = np.maximum(w.values, 0.05)
        w   = w / w.sum()
        scores.loc[date] = w

    return scores


def score_etfs(factor_scores_df, factor_loads, tickers):
    """
    For each date, ETF score = sum of (factor_loading[ticker][factor] * factor_score[factor]).
    Returns DataFrame: index=dates, columns=tickers.
    """
    loads_df = pd.DataFrame(factor_loads).T.reindex(tickers).fillna(0)  # shape: (n_etf, n_factor)
    factor_scores_aligned = factor_scores_df.reindex(columns=FF_FACTORS).fillna(0)  # (n_dates, n_factor)
    etf_scores = factor_scores_aligned.values @ loads_df.values.T   # (n_dates, n_etf)
    return pd.DataFrame(etf_scores, index=factor_scores_df.index, columns=tickers)


# ── Backtest engine ───────────────────────────────────────────────────────────

def generate_trades(prices_wide, etf_score_df, top_n, rebalance_freq):
    """
    Rebalance at each `rebalance_freq` date.
    At each rebalance, pick top_n ETFs by current regime score.
    """
    rebal_prices = prices_wide.resample(rebalance_freq).last()
    # Resample scores to same frequency (use last available score in period)
    rebal_scores = etf_score_df.resample(rebalance_freq).last()
    # Align
    common = rebal_prices.index.intersection(rebal_scores.index)
    rebal_prices = rebal_prices.loc[common]
    rebal_scores = rebal_scores.loc[common]

    tickers_avail = list(prices_wide.columns)
    trades = []
    rdates = rebal_prices.index.tolist()

    for i, rd in enumerate(rdates):
        scores_row = rebal_scores.loc[rd].reindex(tickers_avail).dropna()
        if len(scores_row) < 1:
            continue
        n_sel = min(top_n, len(scores_row))
        tops  = scores_row.nlargest(n_sel).index.tolist()
        if not tops:
            continue
        # Entry: first trading day >= rd
        entry_cands = prices_wide.index[prices_wide.index >= rd]
        if len(entry_cands) == 0:
            continue
        entry_date = entry_cands[0]
        # Exit: first trading day >= next rebal date
        if i + 1 < len(rdates):
            exit_cands = prices_wide.index[prices_wide.index >= rdates[i+1]]
            if len(exit_cands) == 0:
                continue
            exit_date   = exit_cands[0]
            exit_reason = "rebalance"
        else:
            exit_date   = prices_wide.index[-1]
            exit_reason = "end_of_data"
        for sym in tops:
            if sym not in prices_wide.columns:
                continue
            ep = prices_wide.loc[entry_date, sym]
            xp = prices_wide.loc[exit_date,  sym]
            if pd.isna(ep) or pd.isna(xp) or ep <= 0:
                continue
            trades.append({
                "entry_time":      entry_date,
                "exit_time":       exit_date,
                "direction":       "long",
                "instrument":      sym,
                "entry_price":     round(float(ep), 4),
                "exit_price":      round(float(xp), 4),
                "pct_return_gross": round(float((xp - ep) / ep), 6),
                "exit_reason":     exit_reason,
                "stop_price":      np.nan,
            })
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time", "instrument"]).reset_index(drop=True)


def basket_metrics(trades):
    if trades.empty or len(trades) < 3:
        return {"sharpe": 0.0}
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
    cohort.columns = ["entry_time", "gross"]
    cohort["net"] = cohort["gross"] - tc_rt
    r    = cohort["net"]
    gaps = cohort["entry_time"].diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    sh   = r.mean() / r.std() * np.sqrt(ppy) if r.std() > 0 else 0.0
    return {"sharpe": round(float(sh), 4)}


def get_period_returns(trades):
    if trades.empty or len(trades) < 3:
        return None, None
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
    cohort.columns = ["entry_time", "gross"]
    cohort["net"] = cohort["gross"] - tc_rt
    r    = cohort.set_index("entry_time")["net"]
    gaps = cohort["entry_time"].diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    return r, ppy


# ── Pre-compute GMM regimes for each n_regimes value ─────────────────────────
if not HAS_SKLEARN:
    print("\nERROR: sklearn required for GMM regime detection.")
    sys.exit(1)

# Restrict macro to period with FF overlap
macro_for_gmm = macro_aligned.copy()
factor_for_gmm = factors_aligned.copy()

regime_cache = {}
print("\n" + "=" * 75)
print("PRE-COMPUTING GMM REGIMES")
print("=" * 75)
for n_reg in N_REGIMES:
    print(f"  Fitting walk-forward GMM (n_regimes={n_reg})...", end="", flush=True)
    labels = fit_gmm_walk_forward(macro_for_gmm, n_regimes=n_reg)
    # Only keep dates in the trading window
    labels_trade = labels[labels.index >= pd.Timestamp(START_DATE)]
    regime_cache[n_reg] = labels
    print(f" done. {len(labels_trade)} labelled months in trade window. "
          f"Distribution: {dict(labels_trade.value_counts().sort_index())}")

# Pre-compute factor scores and ETF scores per n_regimes
score_cache = {}
print("\nPre-computing regime factor scores...")
for n_reg in N_REGIMES:
    labels = regime_cache[n_reg]
    factor_scores = compute_regime_factor_scores(labels, factor_for_gmm)
    # Filter to trade window
    factor_scores_trade = factor_scores[factor_scores.index >= pd.Timestamp(START_DATE)]
    # Score all ETFs in the basket
    uni_tickers = list(UNIVERSES.get("us_factor_quality", pd.DataFrame()).columns)
    loads_subset = {t: ETF_FACTOR_LOADS[t] for t in uni_tickers if t in ETF_FACTOR_LOADS}
    etf_scores = score_etfs(factor_scores_trade, loads_subset, list(loads_subset.keys()))
    score_cache[n_reg] = etf_scores
    print(f"  n_regimes={n_reg}: scores computed for {len(etf_scores.columns)} ETFs "
          f"over {len(etf_scores)} months")

# ── Grid search ───────────────────────────────────────────────────────────────
all_combos = list(product(TOP_PCTS, REBAL_FREQS, N_REGIMES))
uni_names  = list(UNIVERSES.keys())

print(f"\n{'='*75}")
print(f"GRID SEARCH — {len(all_combos)} combos × {len(UNIVERSES)} universe(s)")
print(f"{'='*75}\n")

results_raw = []
for idx, (top_pct, freq, n_reg) in enumerate(all_combos, 1):
    row = {"top_pct": top_pct, "freq": freq, "n_regimes": n_reg}
    sharpes = []
    for uni_name, prices in UNIVERSES.items():
        n_tickers = len(prices.columns)
        top_n     = max(1, round(n_tickers * top_pct))
        etf_scores = score_cache.get(n_reg, pd.DataFrame())
        if etf_scores.empty:
            row[uni_name] = None
            continue
        try:
            trades = generate_trades(prices, etf_scores, top_n, freq)
            if trades.empty or len(trades) < max(top_n, 3):
                row[uni_name] = None
                continue
            s = basket_metrics(trades)["sharpe"]
            row[uni_name] = s
            if s is not None:
                sharpes.append(s)
        except Exception as e:
            print(f"  ERROR {uni_name} top_pct={top_pct} {freq} n_reg={n_reg}: {e}")
            row[uni_name] = None
    row["median_sharpe"] = round(float(np.median(sharpes)), 4) if sharpes else None
    row["min_sharpe"]    = round(float(np.min(sharpes)),    4) if sharpes else None
    row["n_positive"]    = int(sum(s > 0 for s in sharpes))
    results_raw.append(row)

grid_df = pd.DataFrame(results_raw)
n_prim  = len(list(UNIVERSES.values())[0].columns)
grid_df["top_n"] = grid_df["top_pct"].apply(lambda p: max(1, round(n_prim * p)))

# Stability (neighbour-average / self)
lookup = {(r["top_pct"], r["freq"], r["n_regimes"]): r["median_sharpe"]
          for _, r in grid_df.iterrows()}
stab_scores = []
for _, row in grid_df.iterrows():
    nbrs = []
    for di in [-1, 1]:
        ni = TOP_PCTS.index(row["top_pct"]) + di
        if 0 <= ni < len(TOP_PCTS):
            nbrs.append((TOP_PCTS[ni], row["freq"], row["n_regimes"]))
    for dj in [-1, 1]:
        nj = REBAL_FREQS.index(row["freq"]) + dj
        if 0 <= nj < len(REBAL_FREQS):
            nbrs.append((row["top_pct"], REBAL_FREQS[nj], row["n_regimes"]))
    nbr_s = [lookup.get(k) for k in nbrs if lookup.get(k) is not None]
    if nbr_s and row["median_sharpe"] and row["median_sharpe"] != 0:
        stab_scores.append(round(float(np.mean(nbr_s)) / row["median_sharpe"], 4))
    else:
        stab_scores.append(None)
grid_df["stability"] = stab_scores
grid_df_sorted = grid_df.sort_values("median_sharpe", ascending=False).reset_index(drop=True)
grid_df_sorted.index += 1

print(f"\n{'='*75}\nTOP-20 PARAMETER COMBINATIONS\n{'='*75}")
for rank, row in grid_df_sorted.head(20).iterrows():
    uni_vals = "  ".join(
        f"{row[u]:>8.3f}" if row[u] is not None else f"{'n/a':>8}" for u in uni_names
    )
    stab_str = f"{row['stability']:>7.3f}" if row["stability"] is not None else "    n/a"
    print(f"{rank:>4}  top_pct={row['top_pct']:.2f}  n_reg={int(row['n_regimes'])}  "
          f"{row['freq']:>5}  med={row['median_sharpe']:>6.3f}  stab={stab_str}  [{uni_vals}]")

# ── Save grid ──────────────────────────────────────────────────────────────────
col_order = (["top_pct", "top_n", "freq", "n_regimes",
               "median_sharpe", "min_sharpe", "n_positive", "stability"]
             + uni_names)
grid_df[[c for c in col_order if c in grid_df.columns]].sort_values(
    "median_sharpe", ascending=False
).to_csv(os.path.join(RESULTS_DIR, f"{SAVE_NAME}_grid.csv"), index=False)
print(f"\n  Grid CSV saved → {RESULTS_DIR}/{SAVE_NAME}_grid.csv")

# ── Significance tests (top-3 combos) ─────────────────────────────────────────
from _shared._backtest_utils import ttest_returns

_top3 = grid_df_sorted.head(3)

print("\n" + "=" * 75 + "\nSIGNIFICANCE TESTS (3-gate)\n" + "=" * 75)

PASSING = {}   # {(top_pct, freq, n_regimes): {uni_name: sharpe}}
GATE_RESULTS = {}

for _, _r in _top3.iterrows():
    _tp   = float(_r["top_pct"])
    _freq = _r["freq"]
    _nreg = int(_r["n_regimes"])
    print(f"\n  -- top_pct={_tp:.2f}  n_reg={_nreg}  {_freq} "
          f"(med_sharpe={_r['median_sharpe']}) --")
    print("  {:<20}  {:>7}  {:>7}  {:>7}  {:>8}  {:>7}  Score".format(
          "Universe", "Sharpe", "t-stat", "t-p", "boot5%", "perm-p"))
    print("  " + "-" * 67)

    combo_pass = {}
    for _uni, _prices in UNIVERSES.items():
        n_t     = len(_prices.columns)
        top_n   = max(1, round(n_t * _tp))
        escores = score_cache.get(_nreg, pd.DataFrame())
        if escores.empty:
            print(f"  {_uni:<20}  SCORES UNAVAILABLE")
            continue
        try:
            trades = generate_trades(_prices, escores, top_n, _freq)
        except Exception as e:
            print(f"  {_uni:<20}  ERROR: {e}")
            continue
        _r_s, _ppy = get_period_returns(trades)
        if _r_s is None or len(_r_s) < 5:
            print(f"  {_uni:<20}  INSUFFICIENT DATA ({len(_r_s) if _r_s is not None else 0} periods)")
            continue
        _ann = np.sqrt(_ppy)
        _ra  = np.array(_r_s)
        _sh  = _ra.mean() / _ra.std() * _ann if _ra.std() > 0 else 0.0

        # Gate 1: t-test
        _tt  = ttest_returns(_r_s)
        # Gate 2: bootstrap Sharpe (5th pct > 0)
        _rng = np.random.RandomState(42)
        _bs  = [_rng.choice(_ra, size=len(_ra), replace=True) for _ in range(1000)]
        _bp5 = float(np.percentile(
            [b.mean() / b.std() * _ann if b.std() > 0 else 0.0 for b in _bs], 5))
        # Gate 3: sign-permutation p-value
        _abs  = np.abs(_ra)
        _rng2 = np.random.RandomState(42)
        _cnt  = 0
        for _ in range(1000):
            _sh2 = _abs * _rng2.choice([-1, 1], size=len(_abs))
            if (_sh2.mean() / _sh2.std() * _ann if _sh2.std() > 0 else 0.0) >= _sh:
                _cnt += 1
        _pp  = _cnt / 1000
        _np_ = int(_tt["significant"]) + int(_bp5 > 0) + int(_pp < 0.05)
        print("  {:<20}  {:>7.3f}  {:>7.3f}  {:>7.4f}  {:>+8.3f}  {:>7.4f}  [{}/3]{}".format(
              _uni, _sh, _tt["t_stat"], _tt["p_value"], _bp5, _pp, _np_,
              "  ***" if _np_ == 3 else ("  **" if _np_ == 2 else "")))

        if _np_ >= 3:
            combo_pass[_uni] = round(_sh, 4)

        GATE_RESULTS.setdefault((_tp, _freq, _nreg), {})[_uni] = {
            "sharpe": round(float(_sh), 4),
            "t_stat": _tt["t_stat"], "t_p": _tt["p_value"],
            "boot5_sharpe": round(_bp5, 4), "perm_p": round(_pp, 4),
            "gates_passed": _np_,
        }

    if combo_pass:
        PASSING[(_tp, _freq, _nreg)] = combo_pass

print("\n" + "=" * 75)
if PASSING:
    print("PASSING BASKETS (all 3 gates):")
    for (tp, fr, nr), unis in PASSING.items():
        print(f"  top_pct={tp}  n_reg={nr}  freq={fr}  →  {unis}")
else:
    print("No basket passed all 3 significance gates.")
print("=" * 75)

# ── Summary JSON ───────────────────────────────────────────────────────────────
best = grid_df_sorted.iloc[0]
per_universe = {}
for u in uni_names:
    per_universe[u] = {
        "n_tickers": len(UNIVERSES[u].columns),
        "tickers":   list(UNIVERSES[u].columns),
        "best_sharpe": round(float(best[u]), 4) if best[u] is not None else None,
    }

summary = {
    "strategy":      STRATEGY_NAME,
    "period":        f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "universes":     per_universe,
    "etf_factor_loads": ETF_FACTOR_LOADS,
    "grid_search": {
        "top_pcts":    TOP_PCTS,
        "rebal_freqs": REBAL_FREQS,
        "n_regimes":   N_REGIMES,
        "total_runs":  len(all_combos),
    },
    "best_params": {
        "top_pct":     float(best["top_pct"]),
        "top_n":       int(best["top_n"]),
        "freq":        best["freq"],
        "n_regimes":   int(best["n_regimes"]),
        "median_sharpe": float(best["median_sharpe"]) if best["median_sharpe"] is not None else None,
        "min_sharpe":  float(best["min_sharpe"]) if best["min_sharpe"] is not None else None,
        "per_universe_sharpe": {
            u: (round(float(best[u]), 4) if best[u] is not None else None) for u in uni_names
        },
    },
    "significance": {
        str(k): v for k, v in GATE_RESULTS.items()
    },
    "passing_baskets": {
        str(k): v for k, v in PASSING.items()
    },
    "download_report": {
        "available_etfs":       AVAILABLE,
        "missing_etfs_vlue":    "VLUE — not in local store; network blocked in sandbox",
        "missing_etfs_cowz":    "COWZ — not in local store; network blocked in sandbox",
        "size_proxy":           "IWM used as small-cap/SMB proxy",
        "note":                 "QUAL already present; IWF, IWD, USMV, MTUM, PKW, DVY, IWM all present"
    },
}

summary_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_summary.json")
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  Summary JSON → {summary_path}")
print("\nDone.")


# ── Tier 2: INTEGRATED Bonferroni rescue (fable refactor 2026-07-02) ─────────
# Runs after Tier 1 on the NEXT execution of this script; on-disk results
# remain canonical until then. Engine: shared/basket_significance.py.
# Requires: summary_per_basket dict + per-instrument best combos + a
# (ticker, combo) -> monthly returns callable. Wire the lambda below to this
# script's own signal/equity functions if the auto-detected name is wrong.
try:
    from _shared.basket_significance import bonferroni_rescue
    if "summary_per_basket" in dir() and "instrument_best" in dir():
        bonferroni_rescue(
            summary_per_basket=summary_per_basket,
            instrument_best=instrument_best,
            monthly_returns_fn=lambda _t, _c: compute_monthly_returns(
                build_daily_equity_from_trades(
                    ticker_data[_t]["close"], generate_regime_factor_rotation_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "regime_factor_rotation_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
