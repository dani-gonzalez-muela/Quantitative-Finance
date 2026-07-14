# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
EM/DM Carry — Multi-Asset Implementation
=========================================
Canonical: top_pct=0.25, carry_window=9, threshold=0.05, freq=6ME
Signal   : binary regime — EM_carry > DM_carry + threshold → long EM ETFs,
           else long DM ETFs (top_pct of each group).

Note: summary JSON does not have a "universes" key (this is a binary-switch
strategy, not a per-basket grid). Uses hardcoded EM/DM universe.

Outputs: results/em_dm_carry_multiasset_daily_equity/*.csv
         results/em_dm_carry_implementations_multiasset.json
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings
import numpy as np
import pandas as pd
from _shared.implementations import build_basket_equity

warnings.filterwarnings("ignore")

STRATEGY_NAME    = "em_dm_carry"
STARTING_CAPITAL = 100_000
TC_BPS_OW        = 5
START_DATE       = "2016-01-01"
END_DATE         = "2026-04-01"
HERE         = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR  = os.path.join(HERE, "results")
EQUITY_DIR   = os.path.join(RESULTS_DIR, f"{STRATEGY_NAME}_multiasset_daily_equity")
DATA_DIR     = data_dir("daily_tickers")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "em_dm_carry_multiasset_summary.json")
os.makedirs(EQUITY_DIR, exist_ok=True)

_FREQ_MONTHS = {"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}
EM_TICKERS = ["EEM","INDA","EWZ","EWJ","EWG","EWU","EWA","EWC","EWP","EWI","EWL"]
DM_TICKERS = ["SPY","QQQ","IWM","MDY"]

print("="*70); print("EM/DM CARRY — Multi-Asset Implementation"); print("="*70)

with open(SUMMARY_PATH) as f: summary = json.load(f)
best = summary["best_params"]
CANON_TOP_PCT   = float(best["top_pct"])
CANON_CARRY_WIN = int(best["carry_window"])
CANON_THRESHOLD = float(best["threshold"])
CANON_FREQ      = best["freq"]
print(f"\nCanonical: top_pct={CANON_TOP_PCT}, carry_win={CANON_CARRY_WIN}, "
      f"threshold={CANON_THRESHOLD}, freq={CANON_FREQ}\n")

def load_prices(tickers):
    frames = {}
    for t in tickers:
        p = os.path.join(DATA_DIR, f"{t}.csv")
        if not os.path.exists(p): continue
        try:
            df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
            df.index = pd.to_datetime(df.index)
            s = df["close"].dropna()
            s = s[(s.index>=START_DATE)&(s.index<=END_DATE)]
            if len(s)>=252: frames[t] = s
        except: pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()

def compute_em_dm_signal(em_prices, dm_prices, carry_win, threshold, freq):
    """
    EM_carry = equal-weight EM basket N-month return (skip-1).
    DM_carry = equal-weight DM basket N-month return (skip-1).
    Regime = "em" (1) if EM_carry - DM_carry > threshold, else "dm" (0).
    Matches em_dm_carry_selection_Backtest_multiasset.py signal exactly.
    """
    fmon = _FREQ_MONTHS.get(freq, 1)
    wper = max(1, int(round(carry_win / fmon)))

    all_p = pd.concat([em_prices, dm_prices], axis=1).sort_index()
    monthly = all_p.resample(freq).last()

    em_cols = [c for c in em_prices.columns if c in monthly.columns]
    dm_cols = [c for c in dm_prices.columns if c in monthly.columns]
    em_m = monthly[em_cols].mean(axis=1)
    dm_m = monthly[dm_cols].mean(axis=1)

    regime = pd.Series(index=monthly.index, dtype=object)
    for i in range(len(monthly)):
        if i < wper + 1: continue
        em_ret = float(em_m.iloc[i-1] / em_m.iloc[i-1-wper] - 1)
        dm_ret = float(dm_m.iloc[i-1] / dm_m.iloc[i-1-wper] - 1)
        regime.iloc[i] = 1 if (em_ret - dm_ret) > threshold else 0

    return regime.dropna().astype(int)

def generate_regime_trades(em_prices, dm_prices, regime, top_pct, freq):
    """
    When regime=1 (EM): hold top_pct EM ETFs by trailing momentum.
    When regime=0 (DM): hold top_pct DM ETFs by trailing momentum.
    """
    all_prices = pd.concat([em_prices, dm_prices], axis=1).sort_index()
    fmon = _FREQ_MONTHS.get(freq,1)
    monthly = all_prices.resample(freq).last()

    regime_rebal = regime.reindex(monthly.index, method="ffill")
    rdates = regime_rebal.dropna().index.tolist()
    trades = []

    for i, rd in enumerate(rdates):
        r = int(regime_rebal.get(rd, 0))
        pool = em_prices.columns.tolist() if r == 1 else dm_prices.columns.tolist()
        pool = [p for p in pool if p in all_prices.columns]
        if not pool: continue

        # Rank by trailing momentum (skip-1, 12m)
        wper = max(1, int(round(12/fmon))); skip=1
        pi = i - wper - skip; ri = i - skip
        if pi >= 0 and ri >= 0:
            past_p = monthly.iloc[pi][pool]; rec_p = monthly.iloc[ri][pool]
            mom = (rec_p / past_p - 1).dropna().sort_values(ascending=False)
            top_n = max(1, round(len(mom)*top_pct))
            tops = mom.head(top_n).index.tolist()
        else:
            top_n = max(1, round(len(pool)*top_pct))
            tops = pool[:top_n]

        if not tops: continue
        ec = all_prices.index[all_prices.index>=rd]
        if len(ec)==0: continue
        ed = ec[0]
        if i+1<len(rdates):
            xc = all_prices.index[all_prices.index>=rdates[i+1]]
            if len(xc)==0: continue
            xd=xc[0]; xr="rebalance"
        else:
            xd=all_prices.index[-1]; xr="end_of_data"
        for sym in tops:
            ep = float(all_prices.loc[ed,sym]) if ed in all_prices.index else np.nan
            xp = float(all_prices.loc[xd,sym]) if xd in all_prices.index else np.nan
            if pd.isna(ep) or pd.isna(xp) or ep<=0: continue
            trades.append({"entry_time":ed,"exit_time":xd,"direction":"long","instrument":sym,
                           "entry_price":round(ep,4),"exit_price":round(xp,4),
                           "pct_return_gross":round((xp-ep)/ep,6),
                           "exit_reason":xr,"stop_price":np.nan})
    return pd.DataFrame(trades)

def compute_stats(eq):
    r = eq.pct_change().dropna()
    sharpe = float(r.mean()/r.std()*np.sqrt(252)) if r.std()>0 else 0.0
    days = (eq.index[-1]-eq.index[0]).days
    cagr = float(((eq.iloc[-1]/eq.iloc[0])**(365.25/days)-1)*100) if days>0 else 0.0
    roll = eq.cummax(); dd = (eq-roll)/roll
    return {"sharpe":round(sharpe,4),"cagr":round(cagr,2),"max_dd":round(float(dd.min()*100),2)}

em_prices = load_prices(EM_TICKERS)
dm_prices = load_prices(DM_TICKERS)
print(f"EM: {len(em_prices.columns)} tickers  DM: {len(dm_prices.columns)} tickers")

regime = compute_em_dm_signal(em_prices, dm_prices, CANON_CARRY_WIN, CANON_THRESHOLD, CANON_FREQ)
trades = generate_regime_trades(em_prices, dm_prices, regime, CANON_TOP_PCT, CANON_FREQ)
print(f"Trades: {len(trades)}")

ALLOC_VARIANTS = {"simple_85":0.85,"simple_100":1.00}
all_prices = pd.concat([em_prices, dm_prices], axis=1)
daily_prices = {s: all_prices[s] for s in all_prices.columns}
sleeve_results = {"em_dm_combined": {}}

print()
for var_name, alloc in ALLOC_VARIANTS.items():
    if trades.empty:
        print(f"  {var_name}: no trades"); continue
    res = build_basket_equity(trades, daily_prices, starting_capital=STARTING_CAPITAL, allocation=alloc, include_fees=True)
    eq = res["daily_equity"]; st = compute_stats(eq)
    eq.reset_index().rename(columns={"index":"date",0:"equity"}).to_csv(
        os.path.join(EQUITY_DIR,f"em_dm_combined_{var_name}.csv"),index=False)
    sleeve_results["em_dm_combined"][var_name] = {"metrics":{**st,"n_trades":len(trades),"allocation":alloc}}
    print(f"  {var_name:>12}  Sharpe={st['sharpe']:>6.3f}  CAGR={st['cagr']:>6.2f}%  MaxDD={st['max_dd']:>6.2f}%")

out = {"strategy":STRATEGY_NAME,"period":f"{START_DATE} → {END_DATE}","tc_bps_one_way":TC_BPS_OW,
       "canonical_params":{"top_pct":CANON_TOP_PCT,"carry_window":CANON_CARRY_WIN,
                           "threshold":CANON_THRESHOLD,"freq":CANON_FREQ},
       "em_tickers":EM_TICKERS,"dm_tickers":DM_TICKERS,
       "sleeves":{b:{v:d["metrics"] for v,d in vd.items()} for b,vd in sleeve_results.items()}}
jp = os.path.join(RESULTS_DIR, "em_dm_carry_implementations_multiasset.json")
with open(jp,"w") as f: json.dump(out, f, indent=2, default=str)
print(f"\n  JSON → {jp}\n  Equity → {EQUITY_DIR}/\n{'='*70}\nDone.\n{'='*70}")
