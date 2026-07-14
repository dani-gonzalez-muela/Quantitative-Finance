"""
vix_etn_dual_Backtest_multiasset_v2.py
======================================
Script conversion of vix_etn_dual_Backtest.ipynb (fable run 2026-07-02).

Paper: Zarattini, Mele & Aziz (2025), "The Volatility Edge: A Dual Approach
for VIX ETNs Trading" (SFI N.25-91).

Strategy family (paper Table 2), canonical = eVRP+BoC+Sizing:
  Passive          always 20% VIXSHORT
  eVRP             20% VIXSHORT when eVRP > 0
  eVRP+BoC         adds VIX term-structure (contango/backwardation) switch
  eVRP+BoC+Sizing  dynamic weight = VIX/100 (canonical)

Signals: eVRP = VIX - eRV30 (10d realized SPY vol, annualized, x100);
Contango = VIX < VIX3M. Proxies: VIXSHORT = 2x SVXY - 80bps/yr;
VIXLONG = VXX - 50bps/yr.

NOTE ON SCOPE: this is a scalar-exposure strategy on a fixed ETN pair -- per
todo/refactor_discussion_points.md section 2.1 the basket+Bonferroni framework
does NOT apply. Validation = 3-gate significance on the canonical variant
(as in the notebook: 3/3 SIGNIFICANT strong).

DATA: SPY/SVXY/VXX daily closes. Loading order:
  1. cached CSV written by a previous run (results/_price_cache.csv)
  2. Alpaca API (requires network + keys; blocked in the fable sandbox)
If neither is available the script exits with a clear message. VIX/VIX3M come
from the shared 'vix' data store (VIXCLS.csv, VIX3M_History.csv).

v2 changelog: notebook->script conversion; shared.paths for all locations
(ROOT bug class); no logic changes vs the notebook (engine copied verbatim,
including its trade-attribution fix). Existing results/ artifacts were
produced by the notebook run 2016-01-19 -> 2026-03-31 and remain canonical
until this script can be re-run with price data.
"""
import os, sys, json
import numpy as np
import pandas as pd

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, '.project_root')):
    _p = os.path.dirname(_d)
    assert _p != _d, '.project_root marker not found'
    _d = _p
sys.path.insert(0, _d)

from _shared.paths import data_file, data_dir
from _shared.significance import full_significance_report, print_significance_report

HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)
PRICE_CACHE = os.path.join(RESULTS_DIR, '_price_cache.csv')

SYMBOLS     = ["SPY", "SVXY", "VIXY"]     # VIXY renamed -> VXX downstream
START_DATE  = "2009-10-01"
END_DATE    = "2026-04-01"
STARTING_CAPITAL    = 100_000
STRATEGY_NAME       = "VIX ETN Dual"
SAVE_NAME           = "vix_etn_dual"
REALIZED_VOL_WINDOW = 10
REBALANCE_THRESHOLD = 0.02
ANNUAL_FEE_SHORT    = 0.0080
ANNUAL_FEE_LONG     = 0.0050
CANONICAL_STRATEGY  = "eVRP+BoC+Sizing"

VIX_CSV   = data_file('vix', 'VIXCLS.csv')
VIX3M_CSV = data_file('cboe_vix3m', 'VIX3M_History.csv')   # VIX3M lives in the cboe store, not vix

# ── Price loading ────────────────────────────────────────────────────────────

def _load_from_daily_tickers():
    """Return {SPY,SVXY,VXX: df[date,<px>]} from the daily_tickers store, or None if
    incomplete. VIXY is the strategy's long-vol leg (renamed to 'vxx' downstream).
    Populate this store with download_vix_etns.py / GET_VIX_ETN_DATA.bat."""
    tdir = data_dir('daily_tickers')
    want = {"SPY": "spy", "SVXY": "svxy", "VIXY": "vxx"}
    frames = {}
    for tkr, col in want.items():
        path = os.path.join(tdir, f"{tkr}.csv")
        if not os.path.exists(path):
            return None
        d = pd.read_csv(path, parse_dates=["date"])
        d = d[["date", "close"]].rename(columns={"close": col}).dropna().sort_values("date").reset_index(drop=True)
        frames["VXX" if tkr == "VIXY" else tkr] = d
    return frames

def load_prices():
    if os.path.exists(PRICE_CACHE):
        print(f"Loading prices from cache: {PRICE_CACHE}")
        px = pd.read_csv(PRICE_CACHE, parse_dates=['date'])
        return {sym: px[['date', sym.lower()]].dropna().reset_index(drop=True)
                       .rename(columns={sym.lower(): sym.lower()})
                for sym in ["SPY", "SVXY", "VXX"]}
    local = _load_from_daily_tickers()
    if local is not None:
        print("Loading prices from daily_tickers store (SPY/SVXY/VIXY)")
        return local
    try:
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
        from _shared.loaders_data import fetch_historical_data
        data_dict = fetch_historical_data(SYMBOLS, TimeFrame(1, TimeFrameUnit.Day), START_DATE, END_DATE)
    except Exception as e:
        raise SystemExit(
            f"PRICE DATA UNAVAILABLE: no cache at {PRICE_CACHE}, no daily_tickers CSVs, and Alpaca failed ({e}).\n"
            "Run download_vix_etns.py (GET_VIX_ETN_DATA.bat), or drop a CSV with columns date,spy,svxy,vxx at the cache path.")
    frames = {}
    for sym in SYMBOLS:
        d = data_dict[sym].copy()
        if d.index.tz is None:
            d.index = d.index.tz_localize("UTC").tz_convert("US/Eastern")
        else:
            d.index = d.index.tz_convert("US/Eastern")
        d = d.reset_index()
        d["date"] = pd.to_datetime(d["timestamp"].dt.date)
        d = d.groupby("date").last().reset_index()
        out_name = "vxx" if sym == "VIXY" else sym.lower()
        frames["VXX" if sym == "VIXY" else sym] = (
            d[["date", "close"]].rename(columns={"close": out_name}).sort_values("date").reset_index(drop=True))
    merged = frames["SPY"]
    for sym in ["SVXY", "VXX"]:
        merged = merged.merge(frames[sym], on="date", how="outer")
    merged.sort_values("date").to_csv(PRICE_CACHE, index=False)
    print(f"Cached prices -> {PRICE_CACHE}")
    return frames

def load_vix_series():
    vix_raw = pd.read_csv(VIX_CSV)
    vix_raw.columns = vix_raw.columns.str.strip()
    vix_raw = vix_raw.rename(columns={"observation_date": "date", "VIXCLS": "vix"})
    vix_raw["date"] = pd.to_datetime(vix_raw["date"])
    vix_raw["vix"] = pd.to_numeric(vix_raw["vix"], errors="coerce")
    vix_raw = vix_raw.dropna(subset=["vix"]).reset_index(drop=True)
    v3 = pd.read_csv(VIX3M_CSV)
    v3.columns = v3.columns.str.strip()
    v3 = v3.rename(columns={"DATE": "date", "CLOSE": "vix3m"})
    v3["date"] = pd.to_datetime(v3["date"], format="mixed")
    v3["vix3m"] = pd.to_numeric(v3["vix3m"], errors="coerce")
    return vix_raw, v3[["date", "vix3m"]].dropna().reset_index(drop=True)

# ── Strategies (paper Table 2) ───────────────────────────────────────────────

def strategy_passive(row):
    return "vixshort", 0.20

def strategy_evrp(row):
    if row["eVRP"] > 0:
        return "vixshort", 0.20
    return "cash", 0.0

def strategy_evrp_boc(row):
    if row["eVRP"] > 0 and row["contango"]:
        return "vixshort", 0.20
    elif row["eVRP"] <= 0 and row["contango"]:
        return "vixshort", 0.10
    elif row["eVRP"] <= 0 and row["backwardation"]:
        return "vixlong",  0.20
    return "cash", 0.0

def strategy_evrp_boc_sizing(row):
    vix_pct = row["vix"] / 100.0
    if row["eVRP"] > 0 and row["contango"]:
        return "vixshort", vix_pct
    elif row["eVRP"] <= 0 and row["contango"]:
        return "vixshort", 0.5 * vix_pct
    elif row["eVRP"] <= 0 and row["backwardation"]:
        return "vixlong",  vix_pct
    return "cash", 0.0

STRATEGIES = {
    "Passive":          strategy_passive,
    "eVRP":             strategy_evrp,
    "eVRP+BoC":         strategy_evrp_boc,
    "eVRP+BoC+Sizing":  strategy_evrp_boc_sizing,
}

# ── Engine (copied verbatim from the notebook, incl. trade-attribution fix) ──

def run_backtest(df, strategy_fn, starting_capital=STARTING_CAPITAL,
                 rebal_threshold=REBALANCE_THRESHOLD):
    n = len(df)
    equity = np.zeros(n)
    equity[0] = starting_capital
    current_instrument = "cash"
    current_weight = 0.0
    open_trade = None
    trades = []
    daily_log = []

    def get_price(i, instrument):
        if instrument == "vixshort":
            return df["vixshort"].iloc[i]
        elif instrument == "vixlong":
            return df["vixlong"].iloc[i]
        return np.nan

    row0 = df.iloc[0]
    target_instrument, target_weight = strategy_fn(row0)
    current_instrument, current_weight = target_instrument, target_weight
    if target_weight > 0 and target_instrument != "cash":
        open_trade = {"entry_time": row0["date"], "instrument": target_instrument,
                      "entry_price": get_price(0, target_instrument), "entry_weight": target_weight}
    daily_log.append({"date": row0["date"], "equity": equity[0], "instrument": current_instrument,
                      "weight": current_weight, "vix": row0["vix"], "eVRP": row0["eVRP"]})

    for i in range(1, n):
        row = df.iloc[i]
        if current_instrument == "vixshort" and current_weight > 0:
            instrument_ret = row["vixshort_ret"]
        elif current_instrument == "vixlong" and current_weight > 0:
            instrument_ret = row["vixlong_ret"]
        else:
            instrument_ret = 0.0
        if not np.isnan(instrument_ret):
            port_ret = current_weight * instrument_ret
            equity[i] = equity[i-1] * (1 + port_ret)
            if current_weight > 0 and (1 + port_ret) != 0:
                current_weight = current_weight * (1 + instrument_ret) / (1 + port_ret)
        else:
            equity[i] = equity[i-1]

        target_instrument, target_weight = strategy_fn(row)
        needs_rebalance = (target_instrument != current_instrument
                           or abs(current_weight - target_weight) > rebal_threshold)
        if needs_rebalance:
            if open_trade is not None:
                closed_instrument = open_trade["instrument"]
                exit_price = get_price(i, closed_instrument)
                entry_price = open_trade["entry_price"]
                if not np.isnan(entry_price) and not np.isnan(exit_price) and entry_price > 0:
                    trades.append({
                        "entry_time": open_trade["entry_time"], "exit_time": row["date"],
                        "direction": "long", "instrument": closed_instrument,
                        "entry_price": round(float(entry_price), 4),
                        "exit_price": round(float(exit_price), 4),
                        "pct_return_gross": round(float((exit_price-entry_price)/entry_price), 6),
                        "exit_reason": "rebalance", "stop_price": np.nan,
                        "entry_weight": round(float(open_trade["entry_weight"]), 4)})
                open_trade = None
            if target_weight > 0 and target_instrument != "cash":
                open_trade = {"entry_time": row["date"], "instrument": target_instrument,
                              "entry_price": get_price(i, target_instrument), "entry_weight": target_weight}
            current_instrument, current_weight = target_instrument, target_weight
        daily_log.append({"date": row["date"], "equity": equity[i], "instrument": current_instrument,
                          "weight": current_weight, "vix": row["vix"], "eVRP": row["eVRP"]})

    if open_trade is not None:
        last_row = df.iloc[-1]
        closed_instrument = open_trade["instrument"]
        exit_price = get_price(n-1, closed_instrument)
        entry_price = open_trade["entry_price"]
        if not np.isnan(entry_price) and not np.isnan(exit_price) and entry_price > 0:
            trades.append({
                "entry_time": open_trade["entry_time"], "exit_time": last_row["date"],
                "direction": "long", "instrument": closed_instrument,
                "entry_price": round(float(entry_price), 4), "exit_price": round(float(exit_price), 4),
                "pct_return_gross": round(float((exit_price-entry_price)/entry_price), 6),
                "exit_reason": "end_of_data", "stop_price": np.nan,
                "entry_weight": round(float(open_trade["entry_weight"]), 4)})
    return {"equity": equity, "daily": pd.DataFrame(daily_log), "trades": pd.DataFrame(trades)}

def stats_from_equity(eq_series, starting_capital=STARTING_CAPITAL):
    eq = np.asarray(eq_series)
    rets = np.diff(eq) / eq[:-1]
    rets = rets[~np.isnan(rets)]
    tot = (eq[-1] / starting_capital - 1) * 100
    years = len(eq) / 252
    cagr = ((eq[-1] / starting_capital) ** (1/years) - 1) * 100 if years > 0 else 0
    vol = np.std(rets) * np.sqrt(252) if len(rets) > 1 else 0
    sharpe = ((cagr/100) / vol) if vol > 0 else 0
    run_max = np.maximum.accumulate(eq)
    max_dd = ((eq - run_max) / run_max).min() * 100
    return {"total_return": round(tot, 1), "cagr": round(cagr, 2),
            "sharpe": round(sharpe, 2), "max_dd": round(max_dd, 1)}

def main():
    frames = load_prices()
    vix_raw, vix3m_raw = load_vix_series()

    df = frames["SPY"].copy()
    for sym in ["SVXY", "VXX"]:
        df = df.merge(frames[sym], on="date", how="inner")
    df = df.merge(vix_raw[["date", "vix"]], on="date", how="inner")
    df = df.merge(vix3m_raw, on="date", how="inner")
    df = df.sort_values("date").reset_index(drop=True)

    df["svxy_ret"]     = df["svxy"].pct_change()
    df["vixshort_ret"] = 2 * df["svxy_ret"] - (ANNUAL_FEE_SHORT / 252)
    df["vxx_ret"]      = df["vxx"].pct_change()
    df["vixlong_ret"]  = df["vxx_ret"] - (ANNUAL_FEE_LONG / 252)
    df["vixshort"]     = 100 * (1 + df["vixshort_ret"].fillna(0)).cumprod()
    df["vixlong"]      = 100 * (1 + df["vixlong_ret"].fillna(0)).cumprod()

    df["spy_ret"] = df["spy"].pct_change()
    df["eRV30"]   = df["spy_ret"].rolling(REALIZED_VOL_WINDOW).std() * np.sqrt(252) * 100
    df["eVRP"]    = df["vix"] - df["eRV30"]
    df["contango"]      = df["vix"] < df["vix3m"]
    df["backwardation"] = df["vix"] > df["vix3m"]
    df = df.dropna(subset=["eRV30"]).reset_index(drop=True)
    print(f"Signal coverage: {len(df):,} days")

    results = {}
    for name, fn in STRATEGIES.items():
        res = run_backtest(df, fn)
        stats = stats_from_equity(res["equity"])
        eq_series = pd.Series(res["equity"], index=pd.DatetimeIndex(res["daily"]["date"]))
        results[name] = {"backtest": res, "equity_series": eq_series, "stats": stats,
                         "n_trades": len(res["trades"])}
        print(f"{name:<22} trades={len(res['trades']):>4}  Sharpe={stats['sharpe']}  CAGR={stats['cagr']}%  MaxDD={stats['max_dd']}%")

    spy_eq = STARTING_CAPITAL * (1 + df["spy_ret"].fillna(0)).cumprod()
    spy_eq.index = pd.DatetimeIndex(df["date"])
    s_spy = stats_from_equity(spy_eq.values)

    canon = results[CANONICAL_STRATEGY]
    canon_rets = canon["equity_series"].pct_change().dropna()
    sig_df = pd.DataFrame({"net_pnl": canon_rets.values, "equity_before": 1.0,
                           "position": "long", "direction": "long"})
    report = full_significance_report(sig_df, strategy_name=CANONICAL_STRATEGY)
    print_significance_report(report)

    strategy_order = list(STRATEGIES.keys())
    std_cols = ["entry_time", "exit_time", "direction", "instrument",
                "entry_price", "exit_price", "pct_return_gross", "exit_reason", "stop_price"]
    canon_trades = canon["backtest"]["trades"]
    canon_trades[std_cols].to_csv(os.path.join(RESULTS_DIR, f"{SAVE_NAME}_trades.csv"), index=False)
    canon_trades[std_cols + ["entry_weight"]].to_csv(
        os.path.join(RESULTS_DIR, f"{SAVE_NAME}_trades_extended.csv"), index=False)
    for name in strategy_order:
        safe = name.replace("+", "_").replace(" ", "_").lower()
        results[name]["equity_series"].to_csv(os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity_{safe}.csv"))
    spy_eq.to_csv(os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily_equity_spybench.csv"))
    canon["backtest"]["daily"].to_csv(os.path.join(RESULTS_DIR, f"{SAVE_NAME}_daily.csv"), index=False)

    summary = {
        "strategy": STRATEGY_NAME,
        "paper": "Zarattini, Mele & Aziz (2025) SFI Research Paper N.25-91",
        "instruments": SYMBOLS, "portfolio": "Daily",
        "period": f"{df['date'].iloc[0].date()} -> {df['date'].iloc[-1].date()}",
        "params": {"realized_vol_window": REALIZED_VOL_WINDOW, "rebalance_threshold": REBALANCE_THRESHOLD,
                   "annual_fee_short": ANNUAL_FEE_SHORT, "annual_fee_long": ANNUAL_FEE_LONG},
        "canonical_strategy": CANONICAL_STRATEGY,
        "variants": {name: {"stats": results[name]["stats"], "n_trades": results[name]["n_trades"]}
                     for name in strategy_order},
        "spy_benchmark": s_spy,
        "significance_canonical": {"sharpe": report["bootstrap"]["observed_sharpe"],
                                   "verdict": report["verdict"], "tests_passed": report["tests_passed"]},
    }
    with open(os.path.join(RESULTS_DIR, f"{SAVE_NAME}_summary.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Saved -> {RESULTS_DIR}")

if __name__ == '__main__':
    main()
