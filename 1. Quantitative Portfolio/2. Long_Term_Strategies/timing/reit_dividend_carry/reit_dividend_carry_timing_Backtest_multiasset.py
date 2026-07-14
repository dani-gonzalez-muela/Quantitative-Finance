# -*- coding: utf-8 -*-
"""
REIT Dividend Carry — Multi-Asset Timing Backtest
=================================================
Tests the REIT dividend carry timing signal on individual ETFs in the real_assets basket.

Original signal (reit_dividend_carry_Backtest.py):
  REIT trailing dividend yield vs 24-month average.
  When yield > 24m avg → 100% exposure (above-average carry).
  When yield < 24m avg × 0.70 → 50% exposure (overpriced).
  Data: CRSP market income return (dlyincret) + FRED 10yr Treasury.
  Reference: Fama & French (1988); AQR "Value and Momentum in REITs" (2012).

Multi-asset adaptation:
  NOTE: CRSP income return data not available for ETFs. FRED also unavailable.
  Proxy: use ETF total-return rolling 12m return as carry estimate.
  (ETF prices are total-return, so rolling returns embed dividends implicitly.)

  For each real_assets ETF:
    carry_proxy = 12m trailing return (captures dividend + price appreciation)
    carry_avg   = 24m rolling average of carry_proxy
    signal = 1.0 (full) if carry_proxy > carry_avg
             0.5 (half)  if carry_proxy < carry_avg × 0.70
             0.75 (mid)  otherwise

  Each month = one "trade" with exposure-scaled return.

  Limitation: This proxy cannot separate dividend yield from capital gains.
  A proper implementation requires CRSP income return or REIT FFO data.
  See: reit_dividend_carry_Backtest.py for the CRSP-based single-instrument version.

Canonical params: yield_window=12m, avg_window=24m, low_threshold=0.70

Outputs
-------
  results/reit_dividend_carry_multiasset_per_instrument.csv
  results/reit_dividend_carry_multiasset_summary.json
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

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "REIT Dividend Carry (Multi-Asset)"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

# Canonical params
YIELD_WINDOW   = 12   # months — trailing return as carry proxy
AVG_WINDOW     = 24   # months — moving average for comparison
LOW_THRESHOLD  = 0.70  # carry < avg × low_threshold → 50% exposure
EXP_HIGH       = 1.00
EXP_MID        = 0.75
EXP_LOW        = 0.50

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

BASKETS = {
    "real_assets": ["VNQ","VNQI","AMLP","XLRE"],
}

print("=" * 75)
print("REIT DIVIDEND CARRY — Multi-Asset Timing Backtest")
print("=" * 75)
print(f"Proxy signal: {YIELD_WINDOW}m trailing return vs {AVG_WINDOW}m average")
print(f"Exposure    : >{AVG_WINDOW}m avg → {EXP_HIGH}x | <{LOW_THRESHOLD}×avg → {EXP_LOW}x | else {EXP_MID}x")
print(f"NOTE: CRSP income return unavailable; ETF total return used as carry proxy.")
print(f"Period   : {START_DATE} → {END_DATE}\n")


def load_close(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns:
            return None
        return df["close"].resample("ME").last()
    except Exception:
        return None


def generate_reit_trades(monthly, ticker, yield_window, avg_window, low_threshold):
    """
    Monthly carry-proxy signal: trailing total return as yield estimate.
    Scale monthly return by exposure derived from carry signal.
    """
    carry_proxy = monthly.pct_change(yield_window).shift(1)
    carry_avg   = carry_proxy.rolling(avg_window - yield_window + 1).mean()
    monthly_ret = monthly.pct_change()

    trades = []
    for i in range(1, len(monthly)):
        d      = monthly.index[i]
        d_prev = monthly.index[i-1]
        cp     = float(carry_proxy.get(d, np.nan))
        ca     = float(carry_avg.get(d, np.nan))
        raw_r  = float(monthly_ret.iloc[i]) if not pd.isna(monthly_ret.iloc[i]) else 0.0

        if pd.isna(cp) or pd.isna(ca) or ca == 0:
            continue

        ratio = cp / ca if ca != 0 else 1.0
        if cp > ca:
            exp = EXP_HIGH
        elif cp < ca * low_threshold:
            exp = EXP_LOW
        else:
            exp = EXP_MID

        sized_ret = raw_r * exp
        ep = float(monthly.iloc[i-1])
        xp = float(monthly.iloc[i])

        trades.append({
            "entry_time":       d_prev,
            "exit_time":        d,
            "direction":        "long",
            "instrument":       ticker,
            "entry_price":      round(ep, 4),
            "exit_price":       round(xp, 4),
            "pct_return_gross": round(sized_ret, 6),
            "raw_return":       round(raw_r, 6),
            "exposure":         exp,
            "carry_proxy":      round(cp, 6),
            "carry_avg":        round(ca, 6),
            "exit_reason":      "month_end",
            "stop_price":       np.nan,
        })
    return pd.DataFrame(trades)


def instrument_metrics(trades, ticker):
    if trades.empty or len(trades) < 12:
        return None

    tc_rt = 2 * TC_BPS_OW / 10_000
    r_arr = np.array(trades["pct_return_gross"] - tc_rt)
    ppy   = 12.0

    sharpe = float(r_arr.mean() / r_arr.std() * np.sqrt(ppy)) if r_arr.std() > 0 else 0.0

    from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns
    r_series = pd.Series(r_arr, index=trades["entry_time"].values)
    tt  = ttest_returns(r_series)

    rng = np.random.RandomState(42)
    ann = np.sqrt(ppy)
    bs  = [rng.choice(r_arr, size=len(r_arr), replace=True) for _ in range(1000)]
    bp5 = float(np.percentile([b.mean()/b.std()*ann if b.std()>0 else 0.0 for b in bs], 5))

    rng2  = np.random.RandomState(42)
    abs_r = np.abs(r_arr); cnt = 0
    for _ in range(1000):
        sh2 = abs_r * rng2.choice([-1,1], size=len(abs_r))
        if (sh2.mean()/sh2.std()*ann if sh2.std()>0 else 0.0) >= sharpe: cnt += 1
    perm_p = cnt / 1000

    # Unscaled comparison
    if "raw_return" in trades.columns:
        r_raw  = np.array(trades["raw_return"] - tc_rt)
        sh_raw = float(r_raw.mean() / r_raw.std() * np.sqrt(ppy)) if r_raw.std() > 0 else 0.0
    else:
        sh_raw = sharpe

    n_pass = int(tt["significant"]) + int(bp5 > 0) + int(perm_p < 0.05)

    return {
        "ticker":          ticker,
        "n_months":        len(trades),
        "sharpe_carry":    round(float(sharpe), 4),
        "sharpe_raw":      round(float(sh_raw), 4),
        "t_stat":          round(float(tt["t_stat"]), 4),
        "t_p":             round(float(tt["p_value"]), 4),
        "boot_p5":         round(float(bp5), 4),
        "perm_p":          round(float(perm_p), 4),
        "gates_pass":      n_pass,
        "verdict":         "PASS" if n_pass >= 2 else "FAIL",
    }


# ── Run per instrument ────────────────────────────────────────────────────────
all_tickers = BASKETS["real_assets"]

print(f"Testing {len(all_tickers)} instruments...\n")
print(f"  {'Ticker':<8}  {'Basket':<12}  {'n_mo':>5}  {'Sh(carry)':>9}  "
      f"{'Sh(raw)':>7}  {'Gates':>5}  Verdict")
print(f"  {'-'*68}")

results = []
for ticker in all_tickers:
    basket_name = "real_assets"
    monthly = load_close(ticker)
    if monthly is None:
        print(f"  {ticker:<8}  {basket_name:<12}  SKIP (no data)")
        continue

    trades = generate_reit_trades(monthly, ticker, YIELD_WINDOW, AVG_WINDOW, LOW_THRESHOLD)
    m = instrument_metrics(trades, ticker)
    if m is None:
        print(f"  {ticker:<8}  {basket_name:<12}  SKIP (<12 months)")
        continue
    m["basket"] = basket_name
    results.append(m)
    v = "***" if m["gates_pass"] == 3 else ("**" if m["gates_pass"] == 2 else "")
    print(f"  {ticker:<8}  {basket_name:<12}  {m['n_months']:>5}  "
          f"{m['sharpe_carry']:>9.3f}  {m['sharpe_raw']:>7.3f}  "
          f"[{m['gates_pass']}/3]  {m['verdict']} {v}")

# ── Save outputs ──────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)

results_df = pd.DataFrame(results)
csv_path   = os.path.join(RESULTS_DIR, "reit_dividend_carry_multiasset_per_instrument.csv")
results_df.to_csv(csv_path, index=False)

passing = results_df[results_df["gates_pass"] >= 2]["ticker"].tolist() if not results_df.empty else []
print(f"\n  Instruments passing (≥2/3 gates): {passing}")

summary = {
    "strategy":       STRATEGY_NAME,
    "period":         f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "canonical_params": {
        "yield_window":  YIELD_WINDOW,
        "avg_window":    AVG_WINDOW,
        "low_threshold": LOW_THRESHOLD,
    },
    "data_note":      "Carry proxy = ETF total-return trailing returns (CRSP income return unavailable). FRED 10yr yield also unavailable in current session.",
    "baskets_tested":      BASKETS,
    "n_instruments":       len(results),
    "passing_instruments": passing,
    "per_instrument": {r["ticker"]: {k: v for k, v in r.items() if k != "ticker"}
                       for r in results},
}
json_path = os.path.join(RESULTS_DIR, "reit_dividend_carry_multiasset_summary.json")
with open(json_path, "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(f"\n  CSV  → {json_path.replace('.json','.csv')}")
print(f"  JSON → {json_path}")
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
                    ticker_data[_t]["close"], generate_reit_dividend_carry_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "reit_dividend_carry_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
