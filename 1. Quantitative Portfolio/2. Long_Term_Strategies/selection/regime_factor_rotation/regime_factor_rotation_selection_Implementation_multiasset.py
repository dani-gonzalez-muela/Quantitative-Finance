# -*- coding: utf-8 -*-
"""
Regime Factor Rotation — Multi-Asset Implementation
=====================================================
Canonical params (best from multiasset grid search):
  top_pct   = 0.50   (4 of 8 ETFs held)
  n_regimes = 3
  freq      = 6ME (semi-annual rebalance)
  Sharpe    = 1.307  [3/3 significance gates]

Basket : us_factor_quality
  ETFs : IWF, IWD, QUAL, USMV, MTUM, PKW, DVY, IWM
  Capital allocation: 85% via build_basket_equity()

Sleeve architecture: 1 sleeve (us_factor_quality), 85% of capital.

Outputs
-------
  results/regime_factor_rotation_multiasset_daily_equity/us_factor_quality_simple_85.csv
  results/regime_factor_rotation_multiasset_daily_equity/combined_simple_85.csv
  results/regime_factor_rotation_implementations_multiasset.json
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
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
from _shared.implementations import build_basket_equity

warnings.filterwarnings("ignore")

# ── constants ──────────────────────────────────────────────────────────────────
STRATEGY_NAME    = "regime_factor_rotation"
STARTING_CAPITAL = 100_000
ALLOCATION       = 0.85
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
MACRO_START      = "1984-01-01"
GMM_PCA_COMPS    = 10
GMM_COV_TYPE     = "full"
GMM_REFIT_EVERY  = 24

# Canonical params from grid search
CANON_TOP_PCT  = 0.50
CANON_N_REG    = 3
CANON_FREQ     = "6ME"

HERE        = _FILE_DIR
RESULTS_DIR = os.path.join(HERE, "results")
EQUITY_DIR  = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR    = data_dir("daily_tickers")
LOCAL_DATA  = os.path.join(HERE, "data")
os.makedirs(EQUITY_DIR, exist_ok=True)

# Factor ETF basket & loadings
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
BASKET_TICKERS = list(ETF_FACTOR_LOADS.keys())
FF_FACTORS     = ["SMB", "HML", "RMW", "CMA", "Mom"]

PASSING_BASKETS = ["us_factor_quality"]

print("=" * 70)
print("REGIME FACTOR ROTATION — Multi-Asset Implementation")
print("=" * 70)
print(f"\nCanonical: top_pct={CANON_TOP_PCT}, n_regimes={CANON_N_REG}, freq={CANON_FREQ}")
print(f"Allocation: {ALLOCATION:.0%} of capital\n")

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_prices(tickers):
    frames = {}
    for t in tickers:
        p = os.path.join(DATA_DIR, f"{t}.csv")
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
            df.index = pd.to_datetime(df.index)
            s = df["close"].dropna()
            s = s[(s.index >= START_DATE) & (s.index <= END_DATE)]
            if len(s) >= 252:
                frames[t] = s
        except Exception:
            pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()


def fit_gmm_walk_forward(macro_df, n_regimes, n_pca=GMM_PCA_COMPS,
                          cov_type=GMM_COV_TYPE, refit_every=GMM_REFIT_EVERY):
    n = len(macro_df)
    init_n   = max(int(n * 0.50), 24)
    labels   = pd.Series(np.nan, index=macro_df.index)
    last_idx = -1
    gmm = scaler_f = pca_f = None

    for i in range(init_n, n):
        needs_refit = (last_idx < 0) or ((i - last_idx) >= refit_every)
        if needs_refit:
            X = macro_df.iloc[:i].values
            scaler_f = StandardScaler().fit(X)
            Xs = scaler_f.transform(X)
            nc = min(n_pca, Xs.shape[1], Xs.shape[0] - 1)
            pca_f = PCA(n_components=nc).fit(Xs)
            Xp = pca_f.transform(Xs)
            try:
                gmm = GaussianMixture(
                    n_components=n_regimes, covariance_type=cov_type,
                    random_state=42, n_init=5, max_iter=500
                ).fit(Xp)
            except Exception:
                gmm = None
            last_idx = i
        if gmm is None:
            continue
        row = macro_df.iloc[i:i+1].values
        row_s = scaler_f.transform(row)
        row_p = pca_f.transform(row_s)
        labels.iloc[i] = int(gmm.predict(row_p)[0])

    return labels.dropna().astype(int)


def compute_regime_factor_scores(regime_labels, factor_rets_df):
    scores = pd.DataFrame(index=regime_labels.index, columns=FF_FACTORS, dtype=float)
    for i, date in enumerate(regime_labels.index):
        regime      = regime_labels.iloc[i]
        past_labels = regime_labels.iloc[:i]
        past_fac    = factor_rets_df.reindex(past_labels.index).dropna()
        past_labels = past_labels.reindex(past_fac.index)
        mask = past_labels == regime
        if mask.sum() < 3:
            scores.loc[date] = 1.0 / len(FF_FACTORS)
            continue
        regime_avg = past_fac[mask].mean()
        rnk = regime_avg.rank(ascending=True)
        w   = rnk / rnk.sum()
        w   = np.maximum(w.values, 0.05)
        w   = w / w.sum()
        scores.loc[date] = w
    return scores


def score_etfs(factor_scores_df, loads, tickers):
    loads_df = pd.DataFrame(loads).T.reindex(tickers).fillna(0)
    fsc_al   = factor_scores_df.reindex(columns=FF_FACTORS).fillna(0)
    mat      = fsc_al.values @ loads_df.values.T
    return pd.DataFrame(mat, index=factor_scores_df.index, columns=tickers)


def generate_trades(prices_wide, etf_score_df, top_n, freq):
    rebal_p = prices_wide.resample(freq).last()
    rebal_s = etf_score_df.resample(freq).last()
    common  = rebal_p.index.intersection(rebal_s.index)
    rebal_p = rebal_p.loc[common]
    rebal_s = rebal_s.loc[common]
    tickers = list(prices_wide.columns)
    trades  = []
    rdates  = rebal_p.index.tolist()
    for i, rd in enumerate(rdates):
        scores_row = rebal_s.loc[rd].reindex(tickers).dropna()
        if len(scores_row) < 1:
            continue
        n_sel = min(top_n, len(scores_row))
        tops  = scores_row.nlargest(n_sel).index.tolist()
        entry_cands = prices_wide.index[prices_wide.index >= rd]
        if not len(entry_cands):
            continue
        entry_date = entry_cands[0]
        if i + 1 < len(rdates):
            exit_cands = prices_wide.index[prices_wide.index >= rdates[i+1]]
            if not len(exit_cands):
                continue
            exit_date, exit_reason = exit_cands[0], "rebalance"
        else:
            exit_date, exit_reason = prices_wide.index[-1], "end_of_data"
        for sym in tops:
            if sym not in prices_wide.columns:
                continue
            ep = prices_wide.loc[entry_date, sym]
            xp = prices_wide.loc[exit_date,  sym]
            if pd.isna(ep) or pd.isna(xp) or ep <= 0:
                continue
            trades.append({
                "entry_time": entry_date, "exit_time": exit_date,
                "direction": "long", "instrument": sym,
                "entry_price": round(float(ep), 4),
                "exit_price":  round(float(xp), 4),
                "pct_return_gross": round(float((xp - ep) / ep), 6),
                "exit_reason": exit_reason, "stop_price": np.nan,
            })
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time", "instrument"]).reset_index(drop=True)


# ── Load data ──────────────────────────────────────────────────────────────────
print("Loading macro panel and FF factors...")
monthly_macro   = pd.read_csv(
    os.path.join(LOCAL_DATA, "monthly_panel_transformed.csv"),
    index_col=0, parse_dates=True)
quarterly_macro = pd.read_csv(
    os.path.join(LOCAL_DATA, "quarterly_panel_transformed.csv"),
    index_col=0, parse_dates=True)
quarterly_ffill = quarterly_macro.resample("MS").ffill()
macro_panel     = pd.concat([monthly_macro, quarterly_ffill], axis=1).ffill().bfill().fillna(0)
macro_panel     = macro_panel.dropna(axis=1, how="all")
macro_panel     = macro_panel[macro_panel.index >= MACRO_START]

ff = pd.read_csv(
    os.path.join(LOCAL_DATA, "ff_factors_monthly.csv"),
    index_col=0, parse_dates=True)
ff.index = pd.to_datetime(ff.index)
ff.index = ff.index.to_period("M").to_timestamp()
factor_returns  = ff[FF_FACTORS].copy()

common_start = max(macro_panel.index.min(), factor_returns.index.min())
common_end   = min(macro_panel.index.max(),  factor_returns.index.max())
common_idx   = macro_panel[common_start:common_end].index.intersection(
               factor_returns[common_start:common_end].index)
macro_aligned   = macro_panel.loc[common_idx]
factors_aligned = factor_returns.loc[common_idx]

print(f"  macro: {macro_aligned.shape}, factors: {factors_aligned.shape}")

# ── Compute regimes & ETF scores ───────────────────────────────────────────────
print(f"\nFitting walk-forward GMM (n_regimes={CANON_N_REG})...", end="", flush=True)
labels = fit_gmm_walk_forward(macro_aligned, n_regimes=CANON_N_REG)
labels_trade = labels[labels.index >= pd.Timestamp(START_DATE)]
print(f" done. {len(labels_trade)} months in trade window.  "
      f"Dist: {dict(labels_trade.value_counts().sort_index())}")

print("Computing regime factor scores...", end="", flush=True)
factor_scores = compute_regime_factor_scores(labels, factors_aligned)
factor_scores_trade = factor_scores[factor_scores.index >= pd.Timestamp(START_DATE)]
print(" done.")

print("Scoring factor ETFs...", end="", flush=True)
etf_scores = score_etfs(factor_scores_trade, ETF_FACTOR_LOADS, BASKET_TICKERS)
print(" done.\n")

# ── Build implementation for each passing basket ───────────────────────────────
prices_wide = load_prices(BASKET_TICKERS)
avail       = list(prices_wide.columns)
if not avail:
    print("ERROR: No ETF prices loaded.")
    sys.exit(1)
n_top = max(1, round(len(avail) * CANON_TOP_PCT))

print(f"Basket : us_factor_quality  ({len(avail)} ETFs → top {n_top} held per period)")
print(f"ETFs   : {avail}\n")

# Build trades
trades = generate_trades(prices_wide, etf_scores, n_top, CANON_FREQ)
if trades.empty:
    print("ERROR: No trades generated.")
    sys.exit(1)

print(f"Trades generated: {len(trades)}")
print(f"  By instrument: {dict(trades['instrument'].value_counts().sort_index())}")
print(f"  Avg hold: {(trades['exit_time'] - trades['entry_time']).dt.days.mean():.0f} days")

# Build daily price dict for mark-to-market
daily_prices_dict = {
    sym: prices_wide[sym].dropna()
    for sym in avail if sym in prices_wide.columns
}

# Build basket equity at 85% allocation
basket_result = build_basket_equity(
    trades, daily_prices_dict,
    starting_capital=STARTING_CAPITAL,
    allocation=ALLOCATION,
)
daily_eq_85 = basket_result["daily_equity"]

# Compute metrics
def metrics(eq):
    r = eq.pct_change().dropna()
    years  = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr   = (eq.iloc[-1] / eq.iloc[0]) ** (1 / max(years, 0.1)) - 1
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0
    roll_max = eq.expanding().max()
    maxdd  = ((eq - roll_max) / roll_max).min()
    return {"cagr": round(float(cagr * 100), 2),
            "sharpe": round(float(sharpe), 3),
            "maxdd": round(float(maxdd * 100), 2),
            "start": str(eq.index[0].date()),
            "end":   str(eq.index[-1].date()),
            "n_days": len(r)}

m85 = metrics(daily_eq_85)
print(f"\n  [85% alloc]  Sharpe={m85['sharpe']:.3f}  CAGR={m85['cagr']:.1f}%  MaxDD={m85['maxdd']:.1f}%")

# Also save 100% allocation equity
daily_eq_100 = basket_result.get("daily_equity_100", None)
if daily_eq_100 is None:
    # Recompute with 100% alloc
    br100 = build_basket_equity(
        trades, daily_prices_dict,
        starting_capital=STARTING_CAPITAL,
        allocation=1.00,
    )
    daily_eq_100 = br100["daily_equity"]
m100 = metrics(daily_eq_100)
print(f"  [100% alloc] Sharpe={m100['sharpe']:.3f}  CAGR={m100['cagr']:.1f}%  MaxDD={m100['maxdd']:.1f}%")

# Save equity CSVs
eq85_path  = os.path.join(EQUITY_DIR, "us_factor_quality_simple_85.csv")
eq100_path = os.path.join(EQUITY_DIR, "us_factor_quality_simple_100.csv")
comb85_path  = os.path.join(EQUITY_DIR, "combined_simple_85.csv")
comb100_path = os.path.join(EQUITY_DIR, "combined_simple_100.csv")

daily_eq_85.to_csv(eq85_path,   header=["equity"])
daily_eq_100.to_csv(eq100_path, header=["equity"])
daily_eq_85.to_csv(comb85_path,   header=["equity"])   # single sleeve = combined
daily_eq_100.to_csv(comb100_path, header=["equity"])

print(f"\n  Equity CSVs → {EQUITY_DIR}/")
for f in [eq85_path, eq100_path, comb85_path, comb100_path]:
    print(f"    {os.path.basename(f)}")

# ── Implementation JSON ────────────────────────────────────────────────────────
impl = {
    "strategy":        STRATEGY_NAME,
    "period":          f"{START_DATE} → {END_DATE}",
    "canonical_params": {
        "top_pct":    CANON_TOP_PCT,
        "n_regimes":  CANON_N_REG,
        "freq":       CANON_FREQ,
        "top_n":      n_top,
    },
    "allocation":      ALLOCATION,
    "tc_bps_one_way":  TC_BPS_OW,
    "sleeves": {
        "us_factor_quality": {
            "tickers":        avail,
            "n_top_held":     n_top,
            "etf_factor_loads": ETF_FACTOR_LOADS,
            "metrics_85pct":  m85,
            "metrics_100pct": m100,
            "equity_file_85":  os.path.basename(eq85_path),
            "equity_file_100": os.path.basename(eq100_path),
        }
    },
    "significance_gates_passed": 3,
    "notes": (
        "VLUE and COWZ unavailable (network blocked in sandbox). "
        "IWM used as SMB/size proxy; IWD as HML/value; QUAL as RMW/quality; "
        "MTUM as Mom; PKW as CMA/conservative-investment proxy. "
        "USMV (low-vol) gets half RMW + half CMA loading. "
        "DVY (dividend) gets half HML + half RMW loading."
    ),
}
impl_path = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_implementations_multiasset.json")
with open(impl_path, "w") as f:
    json.dump(impl, f, indent=2, default=str)

print(f"\n  Implementations JSON → {impl_path}")
print("\nDone.")
