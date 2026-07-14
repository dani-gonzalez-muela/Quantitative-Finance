# -*- coding: utf-8 -*-
"""
EM/DM Carry — Multi-Asset Selection Backtest
============================================
Adapts em_dm_carry_selection_backtest.py to ETF universes.
Original signal: when EM 12m trailing return > DM 12m by >1%: long EM basket;
                 else long DM basket.
Original data: WRDS CRSP world country returns.

Multiasset ETF adaptation:
  EM proxy : EEM, INDA, EWZ (em_country ETFs)
  DM proxy : SPY, QQQ, IWM, MDY (us_equity_broad ETFs)
  Signal: EM_carry > DM_carry + threshold → go long EM ETFs; else DM ETFs.
  Carry = N-month trailing return (equal-weight of EM or DM basket).
  Sweep threshold and carry window.

Universes (treated jointly — signal selects BETWEEN groups)
--------
  em_dm  — us_equity_broad + em_country combined basket

Grid
----
  TOP_PCTS      = [0.25, 0.50, 1.00]   (fraction of EM or DM basket to hold)
  REBAL_FREQS   = ['ME', '2ME', 'QE', '6ME', '12ME']
  CARRY_WINDOWS = [3, 6, 9, 12]   (months — lookback for carry comparison)
  THRESHOLDS    = [0.0, 0.01, 0.02, 0.05]  (minimum EM - DM carry spread to flip to EM)
  = 60 × 4 = 240 total runs

Outputs
-------
  results/em_dm_carry_multiasset_grid.csv
  results/em_dm_carry_multiasset_summary.json
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

STRATEGY_NAME    = "EM/DM Carry (Multi-Asset, ETF proxy)"
SAVE_NAME        = "em_dm_carry_multiasset"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5

DATA_DIR    = data_dir("daily_tickers")
OUTPUT_BASE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OUTPUT_BASE, "results")

EM_TICKERS = ["EEM","INDA","EWZ","EWJ","EWG","EWU","EWA","EWC","EWP","EWI","EWL"]  # em_country
DM_TICKERS = ["SPY","QQQ","IWM","MDY"]                                               # us_equity_broad

TOP_PCTS      = [0.25, 0.50, 1.00]
REBAL_FREQS   = ["ME", "2ME", "QE", "6ME", "12ME"]
CARRY_WINDOWS = [3, 6, 9, 12]
THRESHOLDS    = [0.0, 0.01, 0.02, 0.05]
_FREQ_MONTHS  = {"ME": 1, "2ME": 2, "QE": 3, "6ME": 6, "12ME": 12}

print("=" * 75)
print("EM/DM CARRY — Multi-Asset Backtest (ETF proxy)")
print("=" * 75)
print(f"Period     : {START_DATE} → {END_DATE}")
print(f"EM tickers : {EM_TICKERS}")
print(f"DM tickers : {DM_TICKERS}")
print()


def load_prices(tickers):
    frames = {}
    for ticker in tickers:
        path = os.path.join(DATA_DIR, f"{ticker}.csv")
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
            df.index = pd.to_datetime(df.index)
            if "close" not in df.columns:
                continue
            s = df["close"].dropna()
            s = s[(s.index >= START_DATE) & (s.index <= END_DATE)]
            if len(s) >= 252:
                frames[ticker] = s
        except Exception:
            pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()


em_prices = load_prices(EM_TICKERS)
dm_prices = load_prices(DM_TICKERS)

print(f"EM available: {list(em_prices.columns)}")
print(f"DM available: {list(dm_prices.columns)}")

if em_prices.empty or dm_prices.empty:
    print("ERROR: insufficient price data — cannot run EM/DM carry")
    import sys; sys.exit(1)

# Combined price DataFrame for trade generation
all_prices = pd.concat([em_prices, dm_prices], axis=1).ffill().dropna(how="all")
all_prices = all_prices[(all_prices.index >= START_DATE) & (all_prices.index <= END_DATE)]

em_tickers_avail = [t for t in EM_TICKERS if t in all_prices.columns]
dm_tickers_avail = [t for t in DM_TICKERS if t in all_prices.columns]
print(f"\nUsing EM={em_tickers_avail}, DM={dm_tickers_avail}\n")


def compute_em_dm_signal(carry_window, rebalance_freq, threshold, top_pct):
    """
    For each rebalance date:
      EM_carry = equal-weight EM basket N-month return
      DM_carry = equal-weight DM basket N-month return
      If EM_carry - DM_carry > threshold → long top_pct EM ETFs by individual momentum
      Else → long top_pct DM ETFs by individual momentum
    Returns signal_df: index=rebal_dates, cols=all tickers, values=score (0=skip).
    """
    monthly = all_prices.resample(rebalance_freq).last()
    months_per_period = _FREQ_MONTHS.get(rebalance_freq, 1)
    window_periods = max(1, int(round(carry_window / months_per_period)))

    em_m = monthly[em_tickers_avail].mean(axis=1)  # equal-weight EM
    dm_m = monthly[dm_tickers_avail].mean(axis=1)  # equal-weight DM

    signal_df = pd.DataFrame(0.0, index=monthly.index, columns=all_prices.columns)

    n_em_top = max(1, round(len(em_tickers_avail) * top_pct))
    n_dm_top = max(1, round(len(dm_tickers_avail) * top_pct))

    for i in range(len(monthly)):
        if i < window_periods + 1:
            continue
        em_ret = float(em_m.iloc[i-1] / em_m.iloc[i-1-window_periods] - 1)
        dm_ret = float(dm_m.iloc[i-1] / dm_m.iloc[i-1-window_periods] - 1)
        spread = em_ret - dm_ret

        if spread > threshold:
            # Long EM — rank individual EM ETFs by momentum
            sub = monthly[em_tickers_avail]
            mom = sub.iloc[i-1] / sub.iloc[i-1-window_periods] - 1
            top_t = mom.nlargest(n_em_top).index.tolist() if n_em_top < len(mom) else mom.index.tolist()
            for sym in top_t:
                signal_df.iloc[i][sym] = float(mom[sym]) + 1e-9  # positive score
        else:
            # Long DM
            sub = monthly[dm_tickers_avail]
            mom = sub.iloc[i-1] / sub.iloc[i-1-window_periods] - 1
            top_t = mom.nlargest(n_dm_top).index.tolist() if n_dm_top < len(mom) else mom.index.tolist()
            for sym in top_t:
                signal_df.iloc[i][sym] = float(mom[sym]) + 1e-9

    return signal_df


def generate_trades(signal_df, rebalance_freq):
    rebal_dates = signal_df.index.tolist()
    trades = []
    for i, rd in enumerate(rebal_dates):
        top_t = signal_df.loc[rd][signal_df.loc[rd] > 0].index.tolist()
        if not top_t:
            continue
        entry_cands = all_prices.index[all_prices.index >= rd]
        if len(entry_cands) == 0:
            continue
        entry_date = entry_cands[0]
        if i + 1 < len(rebal_dates):
            exit_cands = all_prices.index[all_prices.index >= rebal_dates[i+1]]
            if len(exit_cands) == 0:
                continue
            exit_date = exit_cands[0]; exit_reason = "rebalance"
        else:
            exit_date = all_prices.index[-1]; exit_reason = "end_of_data"
        for sym in top_t:
            if sym not in all_prices.columns:
                continue
            ep = all_prices.loc[entry_date, sym]; xp = all_prices.loc[exit_date, sym]
            if pd.isna(ep) or pd.isna(xp):
                continue
            trades.append({"entry_time": entry_date, "exit_time": exit_date, "direction": "long",
                           "instrument": sym, "entry_price": round(float(ep), 4),
                           "exit_price": round(float(xp), 4),
                           "pct_return_gross": round(float((xp-ep)/ep), 6),
                           "exit_reason": exit_reason, "stop_price": np.nan})
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time","instrument"]).reset_index(drop=True)


def basket_sharpe(trades):
    if trades.empty:
        return None
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
    cohort["net"] = cohort["pct_return_gross"] - tc_rt
    r = cohort["net"]
    if len(r) < 5:
        return None
    gaps = cohort["entry_time"].diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    return round(float(r.mean() / r.std() * np.sqrt(ppy)) if r.std() > 0 else 0.0, 4)


def run_single(top_pct, freq, carry_win, thresh):
    try:
        sig    = compute_em_dm_signal(carry_win, freq, thresh, top_pct)
        trades = generate_trades(sig, freq)
        if trades is None or trades.empty or len(trades) < 4:
            return None
        return basket_sharpe(trades)
    except Exception:
        return None


all_combos = list(product(TOP_PCTS, REBAL_FREQS, CARRY_WINDOWS, THRESHOLDS))
print(f"\n{'='*75}")
print(f"GRID SEARCH — {len(all_combos)} combos (1 universe)")
print(f"{'='*75}\n")

results_raw = []
for idx, (top_pct, freq, carry_win, thresh) in enumerate(all_combos, 1):
    row = {"top_pct": top_pct, "freq": freq, "carry_window": carry_win,
           "threshold": thresh}
    s = run_single(top_pct, freq, carry_win, thresh)
    row["em_dm"] = s
    row["median_sharpe"] = s if s is not None else None
    row["min_sharpe"]    = s if s is not None else None
    row["n_positive"]    = int(s is not None and s > 0)
    results_raw.append(row)
    if idx % 60 == 0: print(f"  {idx}/{len(all_combos)} done...")
print(f"  {len(all_combos)}/{len(all_combos)} done.\n")

grid_df = pd.DataFrame(results_raw)
grid_df_sorted = grid_df.sort_values("median_sharpe", ascending=False).reset_index(drop=True)
grid_df_sorted.index += 1

print(f"{'='*75}\nTOP-20 PARAMETER COMBINATIONS\n{'='*75}")
for rank, row in grid_df_sorted.head(20).iterrows():
    print(f"{rank:>4}  top_pct={row['top_pct']:.2f}  carry_win={int(row['carry_window'])}  "
          f"thresh={row['threshold']:.2f}  {row['freq']:>5}  med={row['median_sharpe']:>6.3f}")

os.makedirs(RESULTS_DIR, exist_ok=True)
best = grid_df_sorted.iloc[0]
col_order = ["top_pct","freq","carry_window","threshold","median_sharpe","min_sharpe","n_positive","em_dm"]
grid_df[[c for c in col_order if c in grid_df.columns]].sort_values(
    "median_sharpe", ascending=False).to_csv(os.path.join(RESULTS_DIR, "em_dm_carry_multiasset_grid.csv"), index=False)

summary = {
    "strategy": STRATEGY_NAME, "period": f"{START_DATE} → {END_DATE}",
    "tc_bps_one_way": TC_BPS_OW,
    "em_tickers": em_tickers_avail, "dm_tickers": dm_tickers_avail,
    "signal_note": "ETF proxy for EM vs DM carry. True carry needs WRDS country returns.",
    "grid_search": {"top_pcts": TOP_PCTS, "rebal_freqs": REBAL_FREQS,
                    "carry_windows": CARRY_WINDOWS, "thresholds": THRESHOLDS,
                    "total_runs": len(all_combos)},
    "best_params": {
        "top_pct": float(best["top_pct"]), "carry_window": int(best["carry_window"]),
        "threshold": float(best["threshold"]), "freq": best["freq"],
        "median_sharpe": float(best["median_sharpe"]) if best["median_sharpe"] is not None else None,
        "n_positive": int(best["n_positive"]),
    },
}
with open(os.path.join(RESULTS_DIR, "em_dm_carry_multiasset_summary.json"), "w") as f:
    json.dump(summary, f, indent=2, default=str)
print(f"\n  grid CSV + summary JSON → {RESULTS_DIR}")

# ── Significance tests ────────────────────────────────────────────────────────
from _shared.paths import data_dir
from _shared._backtest_utils import ttest_returns

def get_period_returns(top_pct, freq, carry_win, thresh):
    try:
        sig    = compute_em_dm_signal(carry_win, freq, thresh, top_pct)
        trades = generate_trades(sig, freq)
        if trades is None or trades.empty or len(trades) < 4:
            return None, None
        cohort = trades.groupby("entry_time")["pct_return_gross"].mean().reset_index()
        cohort["net"] = cohort["pct_return_gross"] - 2*TC_BPS_OW/10_000
        r = cohort.set_index("entry_time")["net"]
        gaps = cohort["entry_time"].diff().dropna().dt.days
        ppy  = 365/gaps.median() if len(gaps)>0 else 12
        return r, ppy
    except Exception:
        return None, None

_top3 = grid_df_sorted.head(3)
print("\n"+"="*75+"\nSIGNIFICANCE TESTS\n"+"="*75)
for _, _rr in _top3.iterrows():
    _tp = float(_rr["top_pct"]); _freq = _rr["freq"]
    _cw = int(_rr["carry_window"]); _th = float(_rr["threshold"])
    print(f"\n  -- top_pct={_tp:.2f}  carry_win={_cw}  thresh={_th:.2f}  {_freq} --")
    _r_s, _ppy = get_period_returns(_tp, _freq, _cw, _th)
    if _r_s is None or len(_r_s) < 5:
        print("  INSUFFICIENT DATA"); continue
    _ann = np.sqrt(_ppy); _ra = np.array(_r_s)
    _sh  = _ra.mean()/_ra.std()*_ann if _ra.std()>0 else 0.0
    _tt  = ttest_returns(_r_s)
    _rng = np.random.RandomState(42)
    _bs  = [_rng.choice(_ra, size=len(_ra), replace=True) for _ in range(1000)]
    _bp5 = float(np.percentile([b.mean()/b.std()*_ann if b.std()>0 else 0.0 for b in _bs], 5))
    _abs = np.abs(_ra); _rng2 = np.random.RandomState(42); _cnt = 0
    for _ in range(1000):
        _sh2 = _abs*_rng2.choice([-1,1],size=len(_abs))
        if (_sh2.mean()/_sh2.std()*_ann if _sh2.std()>0 else 0.0) >= _sh: _cnt+=1
    _pp = _cnt/1000
    _np_ = int(_tt["significant"]) + int(_bp5>0) + int(_pp<0.05)
    print(f"  Sharpe={_sh:.3f}  t={_tt['t_stat']:.3f}  p={_tt['p_value']:.4f}  "
          f"boot5%={_bp5:+.3f}  perm-p={_pp:.4f}  [{_np_}/3]{'  ***' if _np_==3 else ('  **' if _np_==2 else '')}")

print("\n"+"="*75+"\nSignificance tests complete.\n"+"="*75)
