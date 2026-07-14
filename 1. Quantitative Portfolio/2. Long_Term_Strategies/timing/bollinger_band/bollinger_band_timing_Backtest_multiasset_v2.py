# -*- coding: utf-8 -*-
"""
Bollinger Band — Multi-Asset Timing Backtest v2  (fable refactor 2026-07-02)
============================================================================
REFERENCE INTEGRATION for the long-term family: this file shows the canonical
shape every Long_Term Backtest converges to. Changes vs the previous v2:

  1. INTEGRATED Phase-2 Bonferroni rescue (was an external family-level
     script, Long_Term_Strategies/Bonferroni/) — now runs inside this script
     after Tier-1, exactly like the Daily/Intraday families. Engine:
     shared/basket_significance.py. NO RERUN REQUIRED — existing results
     stay canonical; the rescue executes on the next run only.
  2. Imports fixed for the 2026-07 reorg: `long_term._backtest_utils` ->
     `shared._backtest_utils` (moved); DATA_DIR resolves through
     shared.paths / data_manifest.json instead of the retired
     long_term/multi_asset_expansion/data path.
  3. Root discovery via .project_root marker (kills the `..`-count bug class).

Everything else (grid, gates, binomial, universality, stability) is unchanged.

Outputs
-------
  results/bollinger_band_v2_multiasset_grid.csv
  results/bollinger_band_v2_multiasset_summary.json
  results/bollinger_band_v2_universality/{basket}_best_combos.csv
  results/bollinger_band_v2_bonferroni_results.json      (NEW, Tier 2)
"""

import sys, os

# ── fable root bootstrap ─────────────────────────────────────────────────────
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d)
    assert _p != _d, ".project_root marker not found — place it at the algo_trading root"
    _d = _p
_ROOT = _d
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json, warnings, itertools
import numpy as np
import pandas as pd
from scipy.stats import binom

from _shared._backtest_utils import ttest_returns, bootstrap_sharpe, permutation_test
from _shared.paths import data_dir

warnings.filterwarnings("ignore")

# ── Constants ────────────────────────────────────────────────────────────────

STRATEGY_NAME    = "Bollinger Band v2 (Multi-Asset)"
SAVE_NAME        = "bollinger_band"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

BB_PERIODS = [10, 20, 30, 50]
BB_STDS    = [1.5, 2.0, 2.5]
HOLD_DAYS  = [0, 15, 30, 45]

BASKETS = {
    "us_equity_broad": ["SPY", "QQQ", "IWM", "MDY"],
    "us_sectors":      ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE", "XLC"],
    "us_factor":       ["IWF", "IWD", "USMV", "MTUM", "PKW", "DVY"],
}

DATA_DIR    = data_dir("daily_tickers")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
UNIV_DIR    = os.path.join(RESULTS_DIR, "bollinger_band_v2_universality")

ALL_COMBOS = list(itertools.product(BB_PERIODS, BB_STDS, HOLD_DAYS))


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_ohlc(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
        df.index = pd.to_datetime(df.index)
        df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
        if len(df) < 252 or "close" not in df.columns:
            return None
        return df
    except Exception:
        return None


# ── Signal Generation ────────────────────────────────────────────────────────

def generate_bb_trades_v2(df, ticker, bb_period, bb_std, hold_days):
    """BB mean-reversion: entry next open after close <= lower band;
    exit at upper band or hold_days (0 = band exit only). 5bps/side."""
    TC_RT = 2 * TC_BPS_OW / 10_000
    close = df["close"]
    sma   = close.rolling(bb_period).mean()
    sigma = close.rolling(bb_period).std()
    upper = sma + bb_std * sigma
    lower = sma - bb_std * sigma

    trades, in_trade = [], False
    entry_date = entry_price = entry_idx = None
    for i in range(1, len(df)):
        today = df.index[i]
        if not in_trade:
            if close.iloc[i - 1] <= lower.iloc[i - 1] and not pd.isna(lower.iloc[i - 1]):
                ep = (df["open"].iloc[i]
                      if "open" in df.columns and not pd.isna(df["open"].iloc[i])
                      else close.iloc[i])
                in_trade, entry_date, entry_price, entry_idx = True, today, float(ep), i
        else:
            days_held = i - entry_idx
            hit_upper = not pd.isna(upper.iloc[i]) and close.iloc[i] >= upper.iloc[i]
            hit_time  = (hold_days > 0) and (days_held >= hold_days)
            if hit_upper or hit_time:
                xp = float(close.iloc[i])
                gross = (xp - entry_price) / entry_price
                trades.append({"entry_time": entry_date, "exit_time": today, "direction": "long",
                               "instrument": ticker, "entry_price": round(entry_price, 4),
                               "exit_price": round(xp, 4), "pct_return_gross": round(gross, 6),
                               "pct_return_net": round(gross - TC_RT, 6),
                               "exit_reason": "upper_band" if hit_upper else "max_hold",
                               "stop_price": np.nan})
                in_trade = False
    if in_trade and entry_price is not None:
        xp = float(close.iloc[-1])
        gross = (xp - entry_price) / entry_price
        trades.append({"entry_time": entry_date, "exit_time": df.index[-1], "direction": "long",
                       "instrument": ticker, "entry_price": round(entry_price, 4),
                       "exit_price": round(xp, 4), "pct_return_gross": round(gross, 6),
                       "pct_return_net": round(gross - 2 * TC_BPS_OW / 10_000, 6),
                       "exit_reason": "end_of_data", "stop_price": np.nan})
    _COLS = ["entry_time", "exit_time", "direction", "instrument", "entry_price",
             "exit_price", "pct_return_gross", "pct_return_net", "exit_reason", "stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_COLS)


# ── Daily Equity / Monthly Returns ───────────────────────────────────────────

def build_daily_equity_from_trades(close, trades):
    TC_RT = 2 * TC_BPS_OW / 10_000
    n = len(close)
    if trades.empty:
        return pd.Series(1.0, index=close.index)
    trades = trades.copy()
    trades["entry_ts"] = pd.to_datetime(trades["entry_time"])
    trades["exit_ts"]  = pd.to_datetime(trades["exit_time"])
    trades = trades.sort_values("entry_ts").reset_index(drop=True)
    equity_arr, cap, prev_exit = np.full(n, np.nan), 1.0, -1
    for _, t in trades.iterrows():
        ep, xp = t["entry_price"], t["exit_price"]
        e_pos = min(int(close.index.searchsorted(t["entry_ts"])), n - 1)
        x_pos = max(min(int(close.index.searchsorted(t["exit_ts"])), n - 1), e_pos)
        if prev_exit + 1 < e_pos:
            equity_arr[prev_exit + 1: e_pos] = cap
        if x_pos > e_pos:
            equity_arr[e_pos: x_pos] = cap * (close.values[e_pos: x_pos] / ep)
        net = (xp - ep) / ep - TC_RT
        equity_arr[x_pos] = cap * (1 + net)
        cap *= (1 + net)
        prev_exit = x_pos
    if prev_exit + 1 < n:
        equity_arr[prev_exit + 1:] = cap
    return pd.Series(equity_arr, index=close.index)


def compute_monthly_returns(equity):
    return equity.resample("ME").last().dropna().pct_change().dropna()


def annualized_sharpe_monthly(mret):
    r = pd.Series(mret).dropna()
    return float(r.mean() / r.std() * np.sqrt(12)) if len(r) >= 6 and r.std() > 0 else 0.0


def check_significance_3gates(monthly_returns, n_boot=2000):
    r = pd.Series(monthly_returns).dropna()
    if len(r) < 6:
        return 0, {}
    t_res, bs_res, pm_res = ttest_returns(r), bootstrap_sharpe(r, n=n_boot), permutation_test(r, n=n_boot)
    n_pass = int(t_res["significant"]) + int(bs_res["significant"]) + int(pm_res["significant"])
    return n_pass, {"t_stat": t_res["t_stat"], "t_p": t_res["p_value"],
                    "boot_ci_lo": bs_res["ci_lower"], "perm_p": pm_res["p_value"]}


# ── MAIN — Tier 1 (unchanged framework) ──────────────────────────────────────

print("=" * 75)
print("BOLLINGER BAND TIMING -- Multi-Asset Backtest v2 (integrated two-tier)")
print("=" * 75)

all_tickers = list(dict.fromkeys(t for ts in BASKETS.values() for t in ts))
ticker_data = {t: load_ohlc(t) for t in all_tickers}
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(UNIV_DIR, exist_ok=True)

all_combo_rows, summary_per_basket = [], {}
instrument_best_global = {}

for basket_name, basket_tickers in BASKETS.items():
    available = [(t, ticker_data[t]) for t in basket_tickers if ticker_data.get(t) is not None]
    if not available:
        continue
    tickers_avail = [t for t, _ in available]
    instr_combo_sharpes = {t: {} for t in tickers_avail}
    combo_rows = []
    print(f"\nBASKET: {basket_name} ({len(available)} instruments) — {len(ALL_COMBOS)} combos")

    for bb_period, bb_std, hold_days in ALL_COMBOS:
        sharpes_list, pass_count = [], 0
        for ticker, df in available:
            trades = generate_bb_trades_v2(df, ticker, bb_period, bb_std, hold_days)
            eq = build_daily_equity_from_trades(df["close"], trades)
            mret = compute_monthly_returns(eq)
            if len(mret) < 6:
                instr_combo_sharpes[ticker][(bb_period, bb_std, hold_days)] = np.nan
                continue
            sh = annualized_sharpe_monthly(mret)
            instr_combo_sharpes[ticker][(bb_period, bb_std, hold_days)] = sh
            sharpes_list.append(sh)
            n_gates, _ = check_significance_3gates(mret)
            if n_gates >= 2:
                pass_count += 1
        if not sharpes_list:
            continue
        n_valid = len(sharpes_list)
        binom_p = float(binom.sf(pass_count - 1, n_valid, 0.05))
        combo_rows.append({"basket": basket_name, "bb_period": bb_period, "bb_std": bb_std,
                           "hold_days": hold_days, "n_instruments": n_valid,
                           "median_sharpe": round(float(np.median(sharpes_list)), 4),
                           "mean_sharpe": round(float(np.mean(sharpes_list)), 4),
                           "pass_count": pass_count,
                           "binomial_pvalue": round(binom_p, 6),
                           "binomial_significant": binom_p < 0.05})
    if not combo_rows:
        continue
    all_combo_rows.extend(combo_rows)
    basket_df = pd.DataFrame(combo_rows)

    instrument_best = {}
    for t in tickers_avail:
        cs = {c: s for c, s in instr_combo_sharpes[t].items() if not np.isnan(s)}
        if cs:
            instrument_best[t] = max(cs, key=cs.get)
    instrument_best_global.update(instrument_best)
    pd.DataFrame([{"ticker": t, "bb_period": c[0], "bb_std": c[1], "hold_days": c[2],
                   "best_sharpe": round(instr_combo_sharpes[t][c], 4)}
                  for t, c in instrument_best.items()]
                 ).to_csv(os.path.join(UNIV_DIR, f"{basket_name}_best_combos.csv"), index=False)

    ranked = basket_df.sort_values(by=["binomial_significant", "median_sharpe"],
                                   ascending=[False, False]).reset_index(drop=True)
    canon = ranked.iloc[0]
    verdict = "STRATEGY EXISTS" if canon["binomial_pvalue"] < 0.05 else "NO EVIDENCE OF EFFECT"
    print(f"  Tier 1: canon p={canon['bb_period']},s={canon['bb_std']},h={canon['hold_days']}  "
          f"med Sharpe {canon['median_sharpe']:.3f}  pass {int(canon['pass_count'])}/{int(canon['n_instruments'])}  -> {verdict}")
    summary_per_basket[basket_name] = {
        "instruments": tickers_avail,
        "n_instruments": int(canon["n_instruments"]),
        "pass_count_at_canon": int(canon["pass_count"]),
        "binomial_pvalue": float(canon["binomial_pvalue"]),
        "binomial_significant": bool(canon["binomial_pvalue"] < 0.05),
        "verdict": verdict,
        "canonical_params": {"bb_period": int(canon["bb_period"]),
                             "bb_std": float(canon["bb_std"]),
                             "hold_days": int(canon["hold_days"])},
        "canonical_median_sharpe": float(canon["median_sharpe"]),
    }

pd.DataFrame(all_combo_rows).to_csv(
    os.path.join(RESULTS_DIR, "bollinger_band_v2_multiasset_grid.csv"), index=False)
with open(os.path.join(RESULTS_DIR, "bollinger_band_v2_multiasset_summary.json"), "w") as f:
    json.dump({"strategy": STRATEGY_NAME, "period": f"{START_DATE} -> {END_DATE}",
               "tc_bps_one_way": TC_BPS_OW,
               "grid": {"bb_periods": BB_PERIODS, "bb_stds": BB_STDS, "hold_days": HOLD_DAYS},
               "baskets": summary_per_basket}, f, indent=2, default=str)

# ── Tier 2 — INTEGRATED Bonferroni rescue (NEW) ──────────────────────────────

from _shared.basket_significance import bonferroni_rescue

def _monthly_returns_for(ticker, combo):
    bb_period, bb_std, hold_days = combo
    df = ticker_data[ticker]
    trades = generate_bb_trades_v2(df, ticker, bb_period, bb_std, hold_days)
    eq = build_daily_equity_from_trades(df["close"], trades)
    return compute_monthly_returns(eq)

bonferroni_rescue(
    summary_per_basket=summary_per_basket,
    instrument_best=instrument_best_global,
    monthly_returns_fn=_monthly_returns_for,
    out_path=os.path.join(RESULTS_DIR, f"{SAVE_NAME}_v2_bonferroni_results.json"),
)

print("\nDone (Tier 1 + integrated Tier 2).")
