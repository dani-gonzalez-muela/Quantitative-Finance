# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Bond Duration Carry - Multi-Asset Implementation
Passing instrument (2/3 gates): HYG
Signal: DFII10 > 0 (positive real yield) -> hold HYG.
Sleeves: simple_85 (85% allocation), simple_100 (100% allocation).
"""
import sys, os, json, warnings
import numpy as np, pandas as pd

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

from _shared.implementations import build_basket_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME    = "bond_duration_carry"
STARTING_CAPITAL = 100_000
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
RESULTS_DIR      = os.path.join(_FILE_DIR, "results")
EQUITY_DIR       = os.path.join(RESULTS_DIR, "%s_multiasset_daily_equity" % STRATEGY_NAME)
DATA_DIR         = data_dir("daily_tickers")
SYNTH_CSV        = os.path.join(_ROOT, "data", "wrds", "fred_rates_synthetic.csv")
SUMMARY_PATH     = os.path.join(RESULTS_DIR, "bond_duration_carry_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("=" * 70)
print("BOND DURATION CARRY -- Multi-Asset Implementation")
print("=" * 70)

with open(SUMMARY_PATH) as f:
    summary = json.load(f)

PASSING = summary["passing_instruments"]   # ['HYG']
print("\nPassing instruments: %s" % PASSING)
print("Signal: DFII10 lagged 1m; hold ETF when regime in ['long','mid'] (DFII10 > 0%)\n")

# ---------- Load synthetic FRED signal ---------------------------------------
fr = pd.read_csv(SYNTH_CSV, parse_dates=["date"]).set_index("date").sort_index()
fr = fr[(fr.index >= START_DATE) & (fr.index <= END_DATE)]
fr_m           = fr.resample("ME").last()
real_yield_lag = fr_m["dfii10"].shift(1)
slope_lag      = fr_m["t10y2y"].shift(1)

def carry_regime(dt):
    ry = real_yield_lag.get(dt, float("nan"))
    sl = slope_lag.get(dt, 0.3)
    if pd.isna(ry):             return "unknown"
    if ry > 1.0 and sl > 0.5:  return "long"
    if ry > 0.0:                return "mid"
    if ry < -0.5:               return "short"
    return "mid"

HOLD_REGIMES = {"long", "mid"}

# ---------- ETF loaders ------------------------------------------------------
def load_monthly(t):
    p = os.path.join(DATA_DIR, "%s.csv" % t)
    if not os.path.exists(p): return None
    df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
    return df["close"].resample("ME").last() if len(df) >= 200 else None

def load_daily(t):
    p = os.path.join(DATA_DIR, "%s.csv" % t)
    if not os.path.exists(p): return None
    df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
    return df["close"] if len(df) >= 200 else None

# ---------- Trade generator --------------------------------------------------
def gen_trades(etf_monthly, ticker):
    etf_ret = etf_monthly.pct_change()
    trades  = []
    for i in range(1, len(etf_monthly)):
        d  = etf_monthly.index[i]
        dp = etf_monthly.index[i - 1]
        if carry_regime(d) not in HOLD_REGIMES:
            continue
        rr = float(etf_ret.iloc[i]) if not pd.isna(etf_ret.iloc[i]) else 0.0
        ep = float(etf_monthly.iloc[i - 1])
        xp = float(etf_monthly.iloc[i])
        trades.append({
            "entry_time":       dp,
            "exit_time":        d,
            "direction":        "long",
            "instrument":       ticker,
            "entry_price":      round(ep, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(rr, 6),
            "exit_reason":      "month_end",
            "stop_price":       float("nan"),
        })
    return pd.DataFrame(trades)

# ---------- Metrics helper ---------------------------------------------------
def stats(eq):
    r    = eq.pct_change().dropna()
    sh   = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    days = (eq.index[-1] - eq.index[0]).days
    cagr = float(((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / days) - 1) * 100) if days > 0 else 0.0
    dd   = float(((eq - eq.cummax()) / eq.cummax()).min() * 100)
    return {"sharpe": round(sh, 4), "cagr": round(cagr, 2), "max_dd": round(dd, 2)}

# ---------- Run sleeves ------------------------------------------------------
ALLOC = {"simple_85": 0.85, "simple_100": 1.00}
sleeve_results   = {}
combined_equities = {}

print("  %-8s  %5s  %7s  %7s  %7s" % ("Ticker", "Trades", "Sharpe", "CAGR%", "MaxDD%"))
print("  " + "-" * 45)

for ticker in PASSING:
    etf_m = load_monthly(ticker)
    if etf_m is None:
        print("  %s: no monthly data" % ticker)
        continue
    trades = gen_trades(etf_m, ticker)
    if trades.empty:
        print("  %s: no trades generated" % ticker)
        continue
    daily_c = load_daily(ticker)
    if daily_c is None:
        print("  %s: no daily data" % ticker)
        continue

    dp = {ticker: daily_c}
    sleeve_results[ticker] = {}

    for vn, al in ALLOC.items():
        res = build_basket_equity(trades, dp,
                                  starting_capital=STARTING_CAPITAL,
                                  allocation=al, include_fees=True)
        eq  = res["daily_equity"]
        st  = stats(eq)
        eq.reset_index().rename(columns={"index": "date", 0: "equity"}).to_csv(
            os.path.join(EQUITY_DIR, "%s_%s.csv" % (ticker, vn)), index=False)
        sleeve_results[ticker][vn] = {"metrics": {**st, "n_trades": len(trades), "allocation": al}}
        combined_equities.setdefault(vn, []).append(eq)

    s = sleeve_results[ticker]["simple_85"]["metrics"]
    print("  %-8s  %5d  %7.3f  %7.2f  %7.2f" % (
        ticker, len(trades), s["sharpe"], s["cagr"], s["max_dd"]))

# ---------- Combined portfolio -----------------------------------------------
print("\n  Combined portfolio:")
combined_results = {}
for vn, eq_list in combined_equities.items():
    n   = len(eq_list)
    psc = STARTING_CAPITAL / n
    idx = eq_list[0].index
    for e in eq_list[1:]:
        idx = idx.union(e.index)
    nm  = pd.DataFrame({
        "s%d" % i: e.reindex(idx).ffill() / e.reindex(idx).ffill().dropna().iloc[0] * psc
        for i, e in enumerate(eq_list)
    })
    ceq = nm.sum(axis=1)
    ceq.reset_index().rename(columns={"index": "date", 0: "equity"}).to_csv(
        os.path.join(EQUITY_DIR, "combined_%s.csv" % vn), index=False)
    st = stats(ceq)
    combined_results[vn] = {"n_sleeves": n, "instruments": PASSING, **st}
    print("  %-14s  n=%d  Sharpe=%6.3f  CAGR=%6.2f%%  MaxDD=%6.2f%%" % (
        vn, n, st["sharpe"], st["cagr"], st["max_dd"]))

# ---------- Save summary JSON ------------------------------------------------
out = {
    "strategy":          STRATEGY_NAME,
    "period":            "%s -> %s" % (START_DATE, END_DATE),
    "tc_bps_one_way":    TC_BPS_OW,
    "signal":            "DFII10 lagged 1m; hold HYG when DFII10 > 0% (regime: long or mid)",
    "passing_instruments": PASSING,
    "sleeves":           {t: {v: d["metrics"] for v, d in vd.items()}
                          for t, vd in sleeve_results.items()},
    "combined":          combined_results,
}
jp = os.path.join(RESULTS_DIR, "bond_duration_carry_implementations_multiasset.json")
with open(jp, "w") as f:
    json.dump(out, f, indent=2, default=str)

print("\n  JSON ->", jp)
print("=" * 70 + "\nDone.\n" + "=" * 70)
