# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# -*- coding: utf-8 -*-
"""
Bond Trend — Multi-Asset Selection Backtest v2
===============================================
Full grid per basket. Canonical params = highest median Sharpe across all baskets.
Binomial test: P(Binom(N_baskets, 0.05) >= k_passing_baskets). n_boot=500.
Outputs: results/bond_trend_v2_multiasset_summary.json
"""
import sys, os
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT     = os.path.normpath(os.path.join(_FILE_DIR, "..", "..", ".."))
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)

import json, warnings, itertools
import numpy as np
import pandas as pd
from scipy.stats import binom
warnings.filterwarnings("ignore")

STRATEGY_NAME = "Bond Trend v2 (Multi-Asset)"
SAVE_NAME     = "bond_trend"
START_DATE    = "2016-01-01"
END_DATE      = "2026-04-01"
TC_BPS_OW     = 5
N_BOOT        = 500

DATA_DIR    = data_dir("daily_tickers")
HERE        = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")

UNIVERSE_SPECS = {
    "bonds_us":   ["TLT","IEF","SHY","TIP","BIL","LQD","HYG"],
    "bonds_intl": ["EMB","BNDX"],
}
MIN_TICKERS = 2

TOP_PCTS    = [0.10, 0.15, 0.25, 0.33, 0.50, 1.00]
REBAL_FREQS = ["ME", "2ME", "QE", "6ME", "12ME"]
MOM_WINDOWS = [3, 6, 9, 12]
_FREQ_MONTHS = {"ME":1,"2ME":2,"QE":3,"6ME":6,"12ME":12}
ALL_COMBOS  = list(itertools.product(TOP_PCTS, REBAL_FREQS, MOM_WINDOWS))

print("="*75)
print(f"{STRATEGY_NAME} — Backtest v2")
print("="*75)
print(f"Grid : {len(ALL_COMBOS)} combos × {len(UNIVERSE_SPECS)} baskets")
print(f"Period: {START_DATE} → {END_DATE}\n")


def load_prices(tickers):
    frames = {}
    for t in tickers:
        p = os.path.join(DATA_DIR, f"{t}.csv")
        if not os.path.exists(p): continue
        try:
            df = pd.read_csv(p, parse_dates=["date"], index_col="date").sort_index()
            df.index = pd.to_datetime(df.index)
            s = df["close"].dropna()
            s = s[(s.index >= START_DATE) & (s.index <= END_DATE)]
            if len(s) >= 252: frames[t] = s
        except: pass
    return pd.DataFrame(frames).sort_index() if frames else pd.DataFrame()

UNIVERSES = {}
print("Loading universes:")
for uni_name, tickers in UNIVERSE_SPECS.items():
    wide = load_prices(tickers)
    if len(wide.columns) >= MIN_TICKERS:
        UNIVERSES[uni_name] = wide
        print(f"  {uni_name}: {len(wide.columns)} tickers")
    else:
        print(f"  {uni_name}: SKIP ({len(wide.columns)} tickers < {MIN_TICKERS})")


def compute_momentum(prices, mom_win, freq):
    monthly = prices.resample(freq).last()
    fmon    = _FREQ_MONTHS.get(freq, 1)
    wper    = max(1, int(round(mom_win / fmon)))
    sig     = pd.DataFrame(index=monthly.index, columns=monthly.columns, dtype=float)
    for i in range(len(monthly)):
        pi = i - wper - 1; ri = i - 1
        if pi < 0 or ri < 0: continue
        sig.iloc[i] = monthly.iloc[ri] / monthly.iloc[pi] - 1
    return sig


def generate_trades(prices, sig, top_n, freq):
    rdates = sig.dropna(how="all").index.tolist(); trades = []
    for i, rd in enumerate(rdates):
        scores = sig.loc[rd].dropna()
        tops   = scores.nlargest(top_n).index.tolist() if top_n < len(scores) else scores.index.tolist()
        if not tops: continue
        ec = prices.index[prices.index >= rd]
        if len(ec) == 0: continue
        ed = ec[0]
        if i + 1 < len(rdates):
            xc = prices.index[prices.index >= rdates[i+1]]
            if len(xc) == 0: continue
            xd = xc[0]; xr = "rebalance"
        else:
            xd = prices.index[-1]; xr = "end_of_data"
        for sym in tops:
            if sym not in prices.columns: continue
            ep = prices.loc[ed, sym]; xp = prices.loc[xd, sym]
            if pd.isna(ep) or pd.isna(xp): continue
            trades.append({"entry_time":ed,"exit_time":xd,"direction":"long","instrument":sym,
                           "entry_price":round(float(ep),4),"exit_price":round(float(xp),4),
                           "pct_return_gross":round(float((xp-ep)/ep),6),"exit_reason":xr,"stop_price":np.nan})
    if not trades: return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["exit_time"]  = pd.to_datetime(df["exit_time"])
    return df.sort_values(["exit_time","instrument"]).reset_index(drop=True)


def run_trades(prices, combo):
    top_pct, freq, mom_win = combo
    top_n = max(1, round(len(prices.columns) * top_pct))
    try:
        sig = compute_momentum(prices, mom_win, freq)
        return generate_trades(prices, sig, top_n, freq)
    except: return pd.DataFrame()


def basket_sharpe(trades):
    if trades is None or trades.empty: return None
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean()
    r      = cohort - tc_rt
    if len(r) < 5 or r.std() == 0: return None
    gaps = pd.to_datetime(cohort.index).to_series().diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    return round(float(r.mean() / r.std() * np.sqrt(ppy)), 4)


def basket_significance_3gates(trades, n_boot=N_BOOT):
    if trades is None or trades.empty: return 0, 0.0, {}
    tc_rt  = 2 * TC_BPS_OW / 10_000
    cohort = trades.groupby("entry_time")["pct_return_gross"].mean()
    r      = (cohort - tc_rt).values
    if len(r) < 5 or r.std() == 0: return 0, 0.0, {}
    gaps = pd.to_datetime(cohort.index).to_series().diff().dropna().dt.days
    ppy  = 365 / gaps.median() if len(gaps) > 0 else 12
    ann  = np.sqrt(ppy)
    sharpe = float(r.mean() / r.std() * ann)
    from scipy.stats import ttest_1samp
    t_stat, t_p_two = ttest_1samp(r, 0)
    t_p   = float(t_p_two / 2) if t_stat > 0 else 1.0
    gate1 = t_p < 0.05
    rng = np.random.RandomState(42)
    bs  = [rng.choice(r, size=len(r), replace=True) for _ in range(n_boot)]
    bp5 = float(np.percentile([b.mean()/b.std()*ann if b.std()>0 else 0.0 for b in bs], 5))
    gate2 = bp5 > 0
    rng2  = np.random.RandomState(42); abs_r = np.abs(r); cnt = 0
    for _ in range(n_boot):
        sh2 = abs_r * rng2.choice([-1,1], size=len(abs_r))
        if (sh2.mean()/sh2.std()*ann if sh2.std()>0 else 0.0) >= sharpe: cnt += 1
    perm_p = cnt / n_boot; gate3 = perm_p < 0.05
    n_pass = int(gate1) + int(gate2) + int(gate3)
    return n_pass, round(sharpe, 4), {"t_p":round(t_p,4),"boot_p5":round(bp5,4),"perm_p":round(perm_p,4)}


def combo_to_params(combo):
    top_pct, freq, mom_win = combo
    return {"top_pct": float(top_pct), "freq": freq, "mom_window": int(mom_win)}


# ── Phase 1: fast grid search ─────────────────────────────────────────────────
print(f"\nPhase 1: Grid search ({len(ALL_COMBOS)} combos × {len(UNIVERSES)} baskets)...")
grid_sh = {}  # (uni, ci) -> sharpe
for uni, prices in UNIVERSES.items():
    for ci, combo in enumerate(ALL_COMBOS):
        grid_sh[(uni, ci)] = basket_sharpe(run_trades(prices, combo))

uni_names = list(UNIVERSES.keys()); N_baskets = len(uni_names)
combo_meds = []
for ci in range(len(ALL_COMBOS)):
    vals = [grid_sh.get((u, ci)) for u in uni_names]
    vals = [v for v in vals if v is not None]
    combo_meds.append(float(np.median(vals)) if vals else float("nan"))

valid = [(i, m) for i, m in enumerate(combo_meds) if not np.isnan(m)]
canon_idx   = max(valid, key=lambda x: x[1])[0]
canon_combo = ALL_COMBOS[canon_idx]
print(f"  Canonical combo: {combo_to_params(canon_combo)}  med_sharpe={combo_meds[canon_idx]:.4f}")

# ── Phase 2: full significance on canonical combo ─────────────────────────────
print(f"\nPhase 2: Full significance (n_boot={N_BOOT}) on canonical combo...")
canon_pass = 0; canon_sh = []; canon_details = {}
for uni, prices in UNIVERSES.items():
    tr = run_trades(prices, canon_combo)
    n_pass, sh, det = basket_significance_3gates(tr)
    canon_sh.append(sh); canon_details[uni] = {**det, "sharpe": sh, "gates": n_pass}
    if n_pass >= 2: canon_pass += 1
    print(f"  [{'PASS' if n_pass>=2 else 'FAIL'}] {uni:<20} sharpe={sh:.3f}  gates={n_pass}/3")

binom_p  = float(binom.sf(canon_pass - 1, N_baskets, 0.05))
verdict  = "STRATEGY EXISTS" if binom_p < 0.05 else "NO EVIDENCE OF EFFECT"
med_sh   = float(np.median([s for s in canon_sh if s != 0.0])) if canon_sh else 0.0
params   = combo_to_params(canon_combo)

print(f"\n  Binomial: N={N_baskets}, k={canon_pass}, p={binom_p:.6f} → {verdict}")

# Top-10 grid
print(f"\n  Top-10 combos:")
ranked = sorted(enumerate(combo_meds), key=lambda x: x[1] if not np.isnan(x[1]) else -99, reverse=True)
for rank, (ci, med) in enumerate(ranked[:10], 1):
    p = combo_to_params(ALL_COMBOS[ci])
    sh_strs = " ".join(f"{grid_sh.get((u,ci),float('nan')):>6.3f}" for u in uni_names)
    print(f"  {rank:>2}  med={med:>6.3f}  [{sh_strs}]  top_pct={p['top_pct']}  mom={p['mom_window']}  {p['freq']}")

# ── Save JSON ─────────────────────────────────────────────────────────────────
os.makedirs(RESULTS_DIR, exist_ok=True)
summary_baskets = {}
for uni, prices in UNIVERSES.items():
    summary_baskets[uni] = {
        "instruments": list(prices.columns), "n_instruments": len(prices.columns),
        "canonical_params": params, "canonical_median_sharpe": round(med_sh, 4),
        "canonical_basket_sharpe": round(canon_details[uni]["sharpe"], 4),
        "pass_count_at_canon": canon_pass, "n_baskets_tested": N_baskets,
        "binomial_pvalue": round(binom_p, 6), "binomial_significant": bool(binom_p < 0.05),
        "verdict": verdict, "basket_details": canon_details,
    }
out = {"strategy": STRATEGY_NAME, "period": f"{START_DATE} → {END_DATE}",
       "tc_bps_one_way": TC_BPS_OW, "n_boot": N_BOOT, "n_combos": len(ALL_COMBOS),
       "canonical_params": params, "canonical_median_sharpe": round(med_sh, 4),
       "binomial_pvalue": round(binom_p, 6), "binomial_significant": bool(binom_p < 0.05),
       "verdict": verdict, "baskets": summary_baskets}
json_path = os.path.join(RESULTS_DIR, f"{SAVE_NAME}_v2_multiasset_summary.json")
with open(json_path, "w") as f: json.dump(out, f, indent=2, default=str)
print(f"\n  JSON → {json_path}\n{'='*75}\nDone.\n{'='*75}")


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
                    ticker_data[_t]["close"], generate_bond_trend_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "bond_trend_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
