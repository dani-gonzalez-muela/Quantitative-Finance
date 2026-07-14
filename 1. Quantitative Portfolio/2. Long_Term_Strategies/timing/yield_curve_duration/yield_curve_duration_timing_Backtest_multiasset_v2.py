# -*- coding: utf-8 -*-
"""
Yield Curve Duration — Multi-Asset Timing Backtest v2
======================================================
Grid: STEEP_THRESH x FLAT_THRESH = 4x3 = 12 combos
Signal: T10Y2Y > steep_thresh -> hold long-dur ETFs (TLT,IEF,LQD,HYG,TIP)
        T10Y2Y < flat_thresh  -> hold short-dur ETFs (SHY,BIL)
        Otherwise: flat (no trade)

Outputs
-------
  results/yield_curve_duration_v2_multiasset_grid.csv
  results/yield_curve_duration_v2_multiasset_summary.json
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

import json, warnings, itertools
import numpy as np
import pandas as pd
from scipy.stats import binom
from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test
warnings.filterwarnings("ignore")

STRATEGY_NAME = "Yield Curve Duration v2 (Multi-Asset)"
START_DATE    = "2016-01-01"
END_DATE      = "2026-04-01"
TC_BPS_OW     = 5

STEEP_THRESHOLDS = [0.25, 0.50, 0.75, 1.0]   # T10Y2Y > this -> long regime
FLAT_THRESHOLDS  = [0.0, -0.25, -0.50]         # T10Y2Y < this -> short regime

BASKET = ["TLT", "IEF", "SHY", "TIP", "BIL", "LQD", "HYG"]
REGIME_MAP = {"TLT": "long", "IEF": "long", "LQD": "long", "HYG": "long",
              "TIP": "long", "SHY": "short", "BIL": "short"}

DATA_DIR    = data_dir("daily_tickers")
SYNTH_CSV   = os.path.join(_ROOT, "data", "wrds", "fred_rates_synthetic.csv")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
ALL_COMBOS  = list(itertools.product(STEEP_THRESHOLDS, FLAT_THRESHOLDS))


def load_monthly_close(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        return df["close"].resample("ME").last() if len(df) >= 200 and "close" in df.columns else None
    except: return None


def load_daily_close(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        return df["close"] if len(df) >= 200 and "close" in df.columns else None
    except: return None


print("=" * 70)
print("YIELD CURVE DURATION -- Multi-Asset Backtest v2")
print("=" * 70)
print(f"Grid: {len(STEEP_THRESHOLDS)} steep x {len(FLAT_THRESHOLDS)} flat = {len(ALL_COMBOS)} combos")

# Load synthetic FRED data
if not os.path.exists(SYNTH_CSV):
    raise FileNotFoundError(f"Run data/build_synthetic_fred.py first: {SYNTH_CSV}")
fr = pd.read_csv(SYNTH_CSV, parse_dates=["date"]).set_index("date").sort_index()
fr = fr[(fr.index >= START_DATE) & (fr.index <= END_DATE)]
fr_m = fr.resample("ME").last()
spread_lag = fr_m["t10y2y"].shift(1)
print(f"T10Y2Y range: {fr_m['t10y2y'].min():.2f}% -> {fr_m['t10y2y'].max():.2f}%\n")

# Load data
print("Loading ETF data...")
monthly_data = {}; daily_data = {}
for t in BASKET:
    monthly_data[t] = load_monthly_close(t)
    daily_data[t]   = load_daily_close(t)
    status = f"{len(monthly_data[t])} monthly" if monthly_data[t] is not None else "NO DATA"
    print(f"  {t:<8} {status}")
tickers_avail = [t for t in BASKET if monthly_data.get(t) is not None and daily_data.get(t) is not None]


def classify_regime(spread, steep_thresh, flat_thresh):
    if pd.isna(spread): return "unknown"
    if spread > steep_thresh: return "long"
    if spread < flat_thresh:  return "short"
    return "flat"


def generate_yc_trades(ticker, etf_monthly, steep_thresh, flat_thresh):
    TC_RT      = 2 * TC_BPS_OW / 10_000
    fav_regime = REGIME_MAP.get(ticker, "long")
    etf_ret    = etf_monthly.pct_change().dropna()
    trades     = []
    for dt in etf_ret.index:
        sp  = spread_lag.get(dt, np.nan)
        reg = classify_regime(sp, steep_thresh, flat_thresh)
        if reg != fav_regime: continue
        idx = etf_monthly.index.get_loc(dt)
        ep  = float(etf_monthly.iloc[idx - 1]) if idx > 0 else float(etf_monthly.iloc[0])
        xp  = float(etf_monthly.loc[dt])
        pr  = float(etf_ret.loc[dt])
        trades.append({"entry_time": etf_monthly.index[max(idx-1,0)],
                        "exit_time": dt, "direction": "long", "instrument": ticker,
                        "entry_price": round(ep,4), "exit_price": round(xp,4),
                        "pct_return_gross": round(pr,6), "pct_return_net": round(pr-TC_RT,6),
                        "exit_reason": "month_end", "stop_price": np.nan})
    _C = ["entry_time","exit_time","direction","instrument","entry_price","exit_price",
          "pct_return_gross","pct_return_net","exit_reason","stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_C)


def build_daily_equity_from_monthly_trades(daily_close, trades):
    TC_RT = 2 * TC_BPS_OW / 10_000
    n = len(daily_close)
    if trades.empty: return pd.Series(1.0, index=daily_close.index)
    t2 = trades.copy()
    t2["entry_ts"] = pd.to_datetime(t2["entry_time"])
    t2["exit_ts"]  = pd.to_datetime(t2["exit_time"])
    t2 = t2.sort_values("entry_ts").reset_index(drop=True)
    arr = np.full(n, np.nan); cap = 1.0; prev = -1
    for _, t in t2.iterrows():
        ep = t["entry_price"]; xp = t["exit_price"]
        ei_ = min(int(daily_close.index.searchsorted(t["entry_ts"])), n - 1)
        xi_ = min(int(daily_close.index.searchsorted(t["exit_ts"])),  n - 1)
        if xi_ < ei_: xi_ = ei_
        if prev + 1 < ei_: arr[prev + 1: ei_] = cap
        if xi_ > ei_: arr[ei_: xi_] = cap * (daily_close.values[ei_: xi_] / ep)
        net_ret = (xp - ep) / ep - TC_RT
        arr[xi_] = cap * (1 + net_ret); cap *= (1 + net_ret); prev = xi_
    if prev + 1 < n: arr[prev + 1:] = cap
    return pd.Series(arr, index=daily_close.index)


def compute_monthly_returns(equity):
    return equity.resample("ME").last().dropna().pct_change().dropna()


def annualized_sharpe_monthly(mret):
    r = pd.Series(mret).dropna()
    if len(r) < 6 or r.std() == 0: return 0.0
    return float(r.mean() / r.std() * np.sqrt(12))


def check_significance_3gates(monthly_returns, n_boot=2000):
    r = pd.Series(monthly_returns).dropna()
    if len(r) < 6: return 0, {}
    t_res  = ttest_returns(r)
    bs_res = bootstrap_sharpe(r, n=n_boot)
    pm_res = permutation_test(r, n=n_boot)
    n_pass = int(t_res["significant"]) + int(bs_res["significant"]) + int(pm_res["significant"])
    return n_pass, {}


os.makedirs(RESULTS_DIR, exist_ok=True)
all_combo_rows = []; summary_per_basket = {}
N = len(tickers_avail)
instr_combo_sharpes = {t: {} for t in tickers_avail}
combo_rows = []

print(f"\n  Running {len(ALL_COMBOS)} combos x {N} instruments ({len(ALL_COMBOS)*N} backtests)...")
print(f"  {'#':>3}  {'steep':>6}  {'flat':>6}  {'med_sh':>7}  {'pass':>5}  {'binom_p':>8}  sig")
print(f"  {'-'*50}")

for cidx, (steep, flat_t) in enumerate(ALL_COMBOS):
    sharpes = []; pass_count = 0
    for ticker in tickers_avail:
        trades = generate_yc_trades(ticker, monthly_data[ticker], steep, flat_t)
        if trades.empty or len(trades) < 6:
            instr_combo_sharpes[ticker][(steep, flat_t)] = np.nan; continue
        eq = build_daily_equity_from_monthly_trades(daily_data[ticker], trades)
        mret = compute_monthly_returns(eq)
        if len(mret) < 6:
            instr_combo_sharpes[ticker][(steep, flat_t)] = np.nan; continue
        sharpe = annualized_sharpe_monthly(mret)
        instr_combo_sharpes[ticker][(steep, flat_t)] = sharpe; sharpes.append(sharpe)
        ng, _ = check_significance_3gates(mret)
        if ng >= 2: pass_count += 1
    if not sharpes: continue
    n_valid = len(sharpes); med_sh = float(np.median(sharpes))
    bp = float(binom.sf(pass_count - 1, n_valid, 0.05)); bs_ = bp < 0.05
    row = {"basket": "bonds_us", "steep_thresh": steep, "flat_thresh": flat_t,
           "n_instruments": n_valid, "median_sharpe": round(med_sh, 4),
           "mean_sharpe": round(float(np.mean(sharpes)), 4), "pass_count": pass_count,
           "binomial_pvalue": round(bp, 6), "binomial_significant": bs_}
    combo_rows.append(row); all_combo_rows.append(row)
    print(f"  {cidx+1:>3}  {steep:>6.2f}  {flat_t:>6.2f}  {med_sh:>7.3f}  "
          f"{pass_count:>2}/{n_valid}  {bp:>8.4f}  {'SIG' if bs_ else ''}")

if combo_rows:
    ranked = pd.DataFrame(combo_rows).sort_values(by=["binomial_significant","median_sharpe"],
                                                   ascending=[False,False]).reset_index(drop=True)
    cr = ranked.iloc[0]
    canon = {"steep_thresh": float(cr["steep_thresh"]), "flat_thresh": float(cr["flat_thresh"])}
    binom_p = float(cr["binomial_pvalue"]); verdict = "STRATEGY EXISTS" if binom_p < 0.05 else "NO EVIDENCE"
    print(f"\n  BINOMIAL TEST: N={int(cr['n_instruments'])}, pass={int(cr['pass_count'])}, "
          f"p={binom_p:.6f}  -> {verdict}")
    print(f"  CANONICAL: steep_thresh={canon['steep_thresh']}, flat_thresh={canon['flat_thresh']} | "
          f"medSharpe={cr['median_sharpe']:.3f}")
    summary_per_basket["bonds_us"] = {
        "instruments": tickers_avail, "n_instruments": int(cr["n_instruments"]),
        "pass_count_at_canon": int(cr["pass_count"]), "binomial_pvalue": round(binom_p, 6),
        "binomial_significant": bool(binom_p < 0.05), "verdict": verdict,
        "canonical_params": canon, "canonical_median_sharpe": float(cr["median_sharpe"]),
    }

pd.DataFrame(all_combo_rows).to_csv(os.path.join(RESULTS_DIR, "yield_curve_duration_v2_multiasset_grid.csv"), index=False)
with open(os.path.join(RESULTS_DIR, "yield_curve_duration_v2_multiasset_summary.json"), "w") as f:
    json.dump({"strategy": STRATEGY_NAME, "period": f"{START_DATE}->{END_DATE}",
               "grid": {"steep_thresholds": STEEP_THRESHOLDS, "flat_thresholds": FLAT_THRESHOLDS,
                        "n_combos": len(ALL_COMBOS)},
               "baskets": summary_per_basket}, f, indent=2, default=str)

print(f"\n{'='*70}\nFINAL RESULTS")
for bn, bd in summary_per_basket.items():
    cp = bd["canonical_params"]
    print(f"  {bn}: {bd['verdict']} | steep={cp['steep_thresh']}, flat={cp['flat_thresh']} | "
          f"medSharpe={bd['canonical_median_sharpe']:.3f} | p={bd['binomial_pvalue']:.4f}")
print(f"\n{'='*70}\nDone.\n{'='*70}")


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
                    ticker_data[_t]["close"], generate_ycd_trades_v2(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "yield_curve_duration_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
