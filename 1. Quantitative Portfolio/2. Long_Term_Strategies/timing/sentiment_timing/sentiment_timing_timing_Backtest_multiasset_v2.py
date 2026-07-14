# -*- coding: utf-8 -*-
"""
Sentiment Timing (VIX) — Multi-Asset Timing Backtest v2
========================================================
Grid: VIX_LOWS x VIX_HIGHS = 4x4 = 16 combos (invalid pairs filtered)
Signal: VIX-regime monthly sizing:
  VIX < vix_low  -> 0.5x (reduce exposure in complacency)
  VIX > vix_high -> 1.5x (increase exposure in fear)
  Otherwise      -> 1.0x (neutral)
Baskets: us_equity_broad, us_sectors

Outputs
-------
  results/sentiment_timing_v2_multiasset_grid.csv
  results/sentiment_timing_v2_multiasset_summary.json
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
import duckdb
from scipy.stats import binom
from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test
warnings.filterwarnings("ignore")

STRATEGY_NAME = "Sentiment Timing v2 (Multi-Asset)"
START_DATE    = "2016-01-01"
END_DATE      = "2026-04-01"
TC_BPS_OW     = 5

VIX_LOWS  = [12, 15, 18, 20]
VIX_HIGHS = [22, 25, 28, 32]

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "MDY"],
    "us_sectors":      ["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"],
}

DATA_DIR    = data_dir("daily_tickers")
VIX_PARQUET = os.path.join(_ROOT, "data", "wrds", "15_cboe_vix.parquet")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
# Filter: only combos where vix_low < vix_high
ALL_COMBOS  = [(vl, vh) for vl, vh in itertools.product(VIX_LOWS, VIX_HIGHS) if vl < vh]


def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        return df if len(df) >= 252 and "close" in df.columns else None
    except: return None


print("=" * 75)
print("SENTIMENT TIMING (VIX) -- Multi-Asset Backtest v2")
print("=" * 75)
print(f"Grid: {len(VIX_LOWS)} vix_low x {len(VIX_HIGHS)} vix_high = {len(ALL_COMBOS)} valid combos")

# Load VIX
print("\nLoading VIX...")
con = duckdb.connect()
try:
    vix = con.execute(f"SELECT date, vix_close FROM read_parquet('{VIX_PARQUET}') ORDER BY date").fetchdf()
    vix["date"] = pd.to_datetime(vix["date"]); vix = vix.set_index("date")
except:
    df_ = con.execute(f"SELECT * FROM read_parquet('{VIX_PARQUET}') LIMIT 3").fetchdf()
    dc  = [c for c in df_.columns if "date" in c.lower()][0]
    vc  = [c for c in df_.columns if "vix" in c.lower() or "close" in c.lower()][-1]
    vix = con.execute(f"SELECT {dc},{vc} FROM read_parquet('{VIX_PARQUET}') ORDER BY {dc}").fetchdf()
    vix["date"] = pd.to_datetime(vix[dc]); vix = vix.rename(columns={vc:"vix_close"}).set_index("date")
vix_daily   = vix["vix_close"][(vix.index >= START_DATE) & (vix.index <= END_DATE)]
vix_monthly = vix_daily.resample("ME").mean()
print(f"  VIX: {len(vix_daily)} daily obs, range {vix_daily.min():.1f}-{vix_daily.max():.1f}")

print("\nLoading price data...")
all_tickers = list(dict.fromkeys(t for ts in BASKETS.values() for t in ts))
ticker_data = {}
for t in all_tickers:
    df = load_ohlc(t); ticker_data[t] = df
    print(f"  {t:<8} {f'{len(df)} rows' if df is not None else 'NO DATA'}")


def generate_vix_trades(df, ticker, vix_low, vix_high):
    """Monthly VIX-sized returns. Always invested; exposure varies by VIX regime."""
    TC_RT  = 2 * TC_BPS_OW / 10_000
    monthly = df["close"].resample("ME").last()
    monthly_ret = monthly.pct_change().dropna()
    trades = []
    for i in range(1, len(monthly)):
        d = monthly.index[i]; dp = monthly.index[i - 1]
        vm = vix_monthly.get(d, np.nan)
        if pd.isna(vm): continue
        exp = 0.5 if float(vm) < vix_low else (1.5 if float(vm) > vix_high else 1.0)
        rr  = float(monthly_ret.iloc[i - 1]) if i - 1 < len(monthly_ret) else 0.0
        # re-index monthly_ret to match d
        rr = float(monthly_ret.loc[d]) if d in monthly_ret.index else 0.0
        ep = float(monthly.iloc[i - 1]); xp = float(monthly.iloc[i])
        sized_ret = rr * exp
        trades.append({"entry_time": dp, "exit_time": d, "direction": "long",
                        "instrument": ticker, "entry_price": round(ep, 4),
                        "exit_price": round(ep * (1 + sized_ret), 4),
                        "pct_return_gross": round(sized_ret, 6),
                        "pct_return_net": round(sized_ret - TC_RT, 6),
                        "exit_reason": "month_end", "stop_price": np.nan})
    _C = ["entry_time","exit_time","direction","instrument","entry_price","exit_price",
          "pct_return_gross","pct_return_net","exit_reason","stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_C)


def build_daily_equity_from_monthly_trades(daily_close, trades):
    """Build daily equity from monthly-frequency trades using daily MTM on actual prices."""
    TC_RT = 2 * TC_BPS_OW / 10_000
    n = len(daily_close)
    if trades.empty: return pd.Series(1.0, index=daily_close.index)
    # For VIX-sized monthly trades, we apply sized return at month-end
    # Between month-ends: use actual daily price changes × (size factor implicit in gross return)
    t2 = trades.copy()
    t2["entry_ts"] = pd.to_datetime(t2["entry_time"])
    t2["exit_ts"]  = pd.to_datetime(t2["exit_time"])
    t2 = t2.sort_values("entry_ts").reset_index(drop=True)
    arr = np.full(n, np.nan); cap = 1.0; prev = -1
    for _, t in t2.iterrows():
        gross_ret = t["pct_return_gross"]
        ei_ = min(int(daily_close.index.searchsorted(t["entry_ts"])), n - 1)
        xi_ = min(int(daily_close.index.searchsorted(t["exit_ts"])),  n - 1)
        if xi_ < ei_: xi_ = ei_
        if prev + 1 < ei_: arr[prev + 1: ei_] = cap
        # For monthly periods: linearly interpolate between entry and exit
        if xi_ > ei_:
            frac = np.linspace(0, gross_ret, xi_ - ei_ + 1)
            arr[ei_: xi_ + 1] = cap * (1 + frac)
        else:
            arr[xi_] = cap * (1 + gross_ret - TC_RT)
        if xi_ > ei_: cap *= (1 + gross_ret - TC_RT)
        prev = xi_
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
all_combo_rows = {}; summary_per_basket = {}

for basket_name, basket_tickers in BASKETS.items():
    print(f"\n{'='*75}\nBASKET: {basket_name}  ({len(basket_tickers)} instruments)\n{'='*75}")
    available = [(t, ticker_data[t]) for t in basket_tickers if ticker_data.get(t) is not None]
    if not available: continue
    N = len(available); tickers_avail = [t for t, _ in available]
    instr_combo_sharpes = {t: {} for t in tickers_avail}
    combo_rows = []

    print(f"\n  Running {len(ALL_COMBOS)} combos x {N} instruments ({len(ALL_COMBOS)*N} backtests)...")
    print(f"  {'#':>3}  {'vix_lo':>6}  {'vix_hi':>6}  {'med_sh':>7}  {'pass':>5}  {'binom_p':>8}  sig")
    print(f"  {'-'*55}")

    for cidx, (vl, vh) in enumerate(ALL_COMBOS):
        sharpes = []; pass_count = 0
        for ticker, df in available:
            trades = generate_vix_trades(df, ticker, vl, vh)
            eq = build_daily_equity_from_monthly_trades(df["close"], trades)
            mret = compute_monthly_returns(eq)
            if len(mret) < 6:
                instr_combo_sharpes[ticker][(vl, vh)] = np.nan; continue
            sharpe = annualized_sharpe_monthly(mret)
            instr_combo_sharpes[ticker][(vl, vh)] = sharpe; sharpes.append(sharpe)
            ng, _ = check_significance_3gates(mret)
            if ng >= 2: pass_count += 1
        if not sharpes: continue
        n_valid = len(sharpes); med_sh = float(np.median(sharpes))
        bp = float(binom.sf(pass_count - 1, n_valid, 0.05)); bs_ = bp < 0.05
        row = {"basket": basket_name, "vix_low": vl, "vix_high": vh,
               "n_instruments": n_valid, "median_sharpe": round(med_sh, 4),
               "mean_sharpe": round(float(np.mean(sharpes)), 4), "pass_count": pass_count,
               "binomial_pvalue": round(bp, 6), "binomial_significant": bs_}
        combo_rows.append(row); all_combo_rows.setdefault(basket_name, []).append(row)
        if cidx % 4 == 0 or bs_:
            print(f"  {cidx+1:>3}  {vl:>6}  {vh:>6}  {med_sh:>7.3f}  "
                  f"{pass_count:>2}/{n_valid}  {bp:>8.4f}  {'SIG' if bs_ else ''}")

    if not combo_rows: continue
    ranked = pd.DataFrame(combo_rows).sort_values(by=["binomial_significant","median_sharpe"],
                                                   ascending=[False,False]).reset_index(drop=True)
    cr = ranked.iloc[0]
    canon = {"vix_low": int(cr["vix_low"]), "vix_high": int(cr["vix_high"])}
    binom_p = float(cr["binomial_pvalue"]); verdict = "STRATEGY EXISTS" if binom_p < 0.05 else "NO EVIDENCE"
    print(f"\n  BINOMIAL TEST: N={int(cr['n_instruments'])}, pass={int(cr['pass_count'])}, "
          f"p={binom_p:.6f}  -> {verdict}")
    print(f"  CANONICAL: vix_low={canon['vix_low']}, vix_high={canon['vix_high']} | medSharpe={cr['median_sharpe']:.3f}")
    summary_per_basket[basket_name] = {
        "instruments": tickers_avail, "n_instruments": int(cr["n_instruments"]),
        "pass_count_at_canon": int(cr["pass_count"]), "binomial_pvalue": round(binom_p, 6),
        "binomial_significant": bool(binom_p < 0.05), "verdict": verdict,
        "canonical_params": canon, "canonical_median_sharpe": float(cr["median_sharpe"]),
    }

grid_rows = [r for rows in all_combo_rows.values() for r in rows]
pd.DataFrame(grid_rows).to_csv(os.path.join(RESULTS_DIR, "sentiment_timing_v2_multiasset_grid.csv"), index=False)
with open(os.path.join(RESULTS_DIR, "sentiment_timing_v2_multiasset_summary.json"), "w") as f:
    json.dump({"strategy": STRATEGY_NAME, "period": f"{START_DATE}->{END_DATE}",
               "grid": {"vix_lows": VIX_LOWS, "vix_highs": VIX_HIGHS, "n_combos": len(ALL_COMBOS)},
               "baskets": summary_per_basket}, f, indent=2, default=str)

print(f"\n{'='*75}\nFINAL RESULTS")
for bn, bd in summary_per_basket.items():
    cp = bd["canonical_params"]
    print(f"  {bn}: {bd['verdict']} | vix_low={cp['vix_low']}, vix_high={cp['vix_high']} | "
          f"medSharpe={bd['canonical_median_sharpe']:.3f} | p={bd['binomial_pvalue']:.4f}")
print(f"\n{'='*75}\nDone.\n{'='*75}")


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
                    ticker_data[_t]["close"], generate_sentiment_trades_v2(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "sentiment_timing_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
