# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""Turn-of-Month — Multi-Asset Implementation v2"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
from _shared.implementations import simple_bet, build_daily_equity
warnings.filterwarnings("ignore")

STRATEGY_NAME    = "turn_of_month_v2"
STARTING_CAPITAL = 100_000
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
TC_BPS_OW        = 5
TC_RT            = 2 * TC_BPS_OW / 10_000
ALLOCATION       = 0.85

HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = data_dir("daily_tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "turn_of_month_v2_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

print("=" * 70); print("TURN-OF-MONTH -- Multi-Asset Implementation v2"); print("=" * 70)
with open(SUMMARY_PATH) as f: summary = json.load(f)
basket_configs = summary["baskets"]
passing_baskets = {n: c for n, c in basket_configs.items() if c.get("binomial_significant", False)}
print(f"  Baskets tested: {len(basket_configs)}, passing: {len(passing_baskets)}")
for n, c in basket_configs.items():
    cp = c["canonical_params"]
    print(f"  {'PASS' if c.get('binomial_significant') else 'FAIL'} {n}: nb={cp['n_before']},na={cp['n_after']} | medSh={c['canonical_median_sharpe']:.3f}")
if not passing_baskets: print("No passing baskets."); sys.exit(0)

def load_close(ticker):
    path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(path): return None
    df = pd.read_csv(path, parse_dates=["date"], index_col="date").sort_index()
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]
    if len(df) < 252 or "close" not in df.columns: return None
    return df["close"]

def build_tom_trades(close_s, n_before, n_after):
    """Build a trades DataFrame for TOM strategy."""
    dates = close_s.index
    months = dates.to_period("M")
    unique_months = months.unique()
    mask = np.zeros(len(dates), dtype=bool)
    for m in unique_months:
        m_pos = np.where(months == m)[0]
        for p in m_pos[-n_before:]: mask[p] = True
        for p in m_pos[:n_after]:   mask[p] = True

    # Build trades from the mask
    cv = close_s.values; n = len(cv)
    trades = []; in_t = False; ei = None
    for i in range(n):
        if mask[i] and not in_t:
            in_t = True; ei = i
        elif not mask[i] and in_t:
            xi = i - 1
            ep = cv[ei]; xp = cv[xi]; pr = (xp - ep) / ep
            trades.append({"entry_time": dates[ei], "exit_time": dates[xi],
                            "direction": "long", "instrument": close_s.name or "unk",
                            "entry_price": round(float(ep), 4), "exit_price": round(float(xp), 4),
                            "pct_return_gross": round(pr, 6), "pct_return_net": round(pr - TC_RT, 6),
                            "exit_reason": "tom_end", "stop_price": 0.0})
            in_t = False
    if in_t:
        xi = n - 1; ep = cv[ei]; xp = cv[xi]; pr = (xp - ep) / ep
        trades.append({"entry_time": dates[ei], "exit_time": dates[xi],
                        "direction": "long", "instrument": close_s.name or "unk",
                        "entry_price": round(float(ep), 4), "exit_price": round(float(xp), 4),
                        "pct_return_gross": round(pr, 6), "pct_return_net": round(pr - TC_RT, 6),
                        "exit_reason": "end_of_data", "stop_price": 0.0})
    _C = ["entry_time","exit_time","direction","instrument","entry_price","exit_price","pct_return_gross","pct_return_net","exit_reason","stop_price"]
    return pd.DataFrame(trades) if trades else pd.DataFrame(columns=_C)

def compute_stats(eq):
    r = eq.pct_change().dropna()
    sh = float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
    d = (eq.index[-1] - eq.index[0]).days
    cagr = float(((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / d) - 1) * 100) if d > 0 else 0.0
    dd = float(((eq - eq.cummax()) / eq.cummax()).min() * 100)
    return {"sharpe": round(sh, 4), "cagr_pct": round(cagr, 2), "max_dd_pct": round(dd, 2)}

N_passing = len(passing_baskets); sleeve_cap = STARTING_CAPITAL / N_passing
basket_results = {}; sleeve_equity_dict = {}
print(f"\n  Sleeve capital: ${sleeve_cap:,.0f} per basket\n")

for basket_name, cfg in passing_baskets.items():
    cp = cfg["canonical_params"]; nb = int(cp["n_before"]); na = int(cp["n_after"])
    instruments = cfg["instruments"]
    print(f"  {'='*55}\n  BASKET: {basket_name}  |  n_before={nb}, n_after={na}")
    inst_data = {}
    for ticker in instruments:
        cs = load_close(ticker)
        if cs is None: print(f"    {ticker}: no data"); continue
        cs.name = ticker
        t = build_tom_trades(cs, nb, na)
        print(f"    {ticker}: {len(t)} trades"); inst_data[ticker] = (t, cs)
    n_inst = len(inst_data)
    if n_inst == 0: continue
    inst_capital = sleeve_cap / n_inst
    print(f"  Per-instrument capital: ${inst_capital:,.0f}")
    inst_curves = {}
    for ticker, (trades_inst, close_s) in inst_data.items():
        if trades_inst.empty:
            flat = pd.Series(inst_capital, index=pd.bdate_range(START_DATE, END_DATE)); flat.index.name = "date"
            inst_curves[ticker] = flat; continue
        sizing = simple_bet(trades_inst, bet_size=ALLOCATION, starting_capital=inst_capital, include_fees=True)
        inst_curves[ticker] = build_daily_equity(trades_inst, sizing["equity_curve"], inst_capital, daily_prices=close_s)
    all_dates = pd.to_datetime(sorted(set().union(*[eq.index for eq in inst_curves.values()])))
    aligned = {t: eq.reindex(all_dates).ffill().bfill() for t, eq in inst_curves.items()}
    daily_eq = sum(aligned.values()); daily_eq.index.name = "date"; daily_eq.name = "equity"
    stats = compute_stats(daily_eq)
    daily_eq.reset_index().to_csv(os.path.join(EQUITY_DIR, f"{basket_name}_equity.csv"), index=False)
    print(f"  Sharpe={stats['sharpe']:.3f}  CAGR={stats['cagr_pct']:.2f}%  MaxDD={stats['max_dd_pct']:.2f}%")
    sleeve_equity_dict[basket_name] = daily_eq
    basket_results[basket_name] = {"canonical_params": cp, "n_instruments": n_inst, "stats": stats}

print(f"\n{'='*70}\nCOMBINED PORTFOLIO\n{'='*70}")
if sleeve_equity_dict:
    all_dates = pd.to_datetime(sorted(set().union(*[s.index for s in sleeve_equity_dict.values()])))
    combined = sum(eq.reindex(all_dates).ffill().bfill() for eq in sleeve_equity_dict.values())
    combined.index.name = "date"; combined.name = "equity"
    cs = compute_stats(combined)
    print(f"  Sharpe={cs['sharpe']:.4f}  CAGR={cs['cagr_pct']:.2f}%  MaxDD={cs['max_dd_pct']:.2f}%")
    combined.reset_index().to_csv(os.path.join(EQUITY_DIR, "combined_equity.csv"), index=False)
    impl_json = {"strategy": STRATEGY_NAME, "n_passing_baskets": N_passing,
                 "baskets": basket_results, "combined_stats": cs}
    with open(os.path.join(RESULTS_DIR, "turn_of_month_v2_implementations_multiasset.json"), "w") as f:
        json.dump(impl_json, f, indent=2, default=str)
print(f"\n{'='*70}\nDone.\n{'='*70}")
