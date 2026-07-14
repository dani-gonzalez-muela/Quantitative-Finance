# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

"""
shared/basket_significance.py  (fable run 2, 2026-07-02)
=========================================================
Generic Phase-2 Bonferroni-rescue engine for LONG-TERM strategies, so the
two-tier framework lives INSIDE each strategy's own Backtest script (same
philosophy as the Daily/Intraday families) instead of an external validator.

Usage — append to a *_Backtest_multiasset_v2.py after its summary JSON is
written (the standard appendix; see tools/apply_longterm_refactor.py):

    from _shared.basket_significance import bonferroni_rescue
    bonferroni_rescue(
        summary_per_basket=summary_per_basket,       # the script's own dict
        instrument_best={...},                       # per-instrument best combo (script computes this)
        monthly_returns_fn=lambda tkr, combo: ...,   # regenerate monthly returns for (ticker, combo)
        out_path=os.path.join(RESULTS_DIR, f"{SAVE_NAME}_v2_bonferroni_results.json"),
    )

NO-RERUN NOTE: existing on-disk results remain canonical. This code only
executes on the NEXT run of a Backtest script; adding it is code organization,
not a results change.
"""
import json
import numpy as np
import pandas as pd
from scipy import stats as _st


def gates_at_alpha(monthly_returns, alpha=0.05, n_boot=5000, seed=42):
    """3-gate test on a monthly-returns series at an arbitrary alpha.
    Gate1 one-sided t-test p<alpha; Gate2 bootstrap 5th-pct Sharpe>0;
    Gate3 sign-randomization permutation p<alpha."""
    r = pd.Series(monthly_returns).dropna().values
    if len(r) < 12 or r.std() == 0:
        return {"n_months": len(r), "passes": False, "note": "insufficient history"}
    t, p2 = _st.ttest_1samp(r, 0)
    g1 = float(p2 / 2 if t > 0 else 1 - p2 / 2)
    rng = np.random.RandomState(seed)
    obs = r.mean() / r.std() * np.sqrt(12)
    boots = []
    for _ in range(n_boot):
        s = rng.choice(r, size=len(r), replace=True)
        boots.append(s.mean() / s.std() * np.sqrt(12) if s.std() > 0 else 0.0)
    g2 = float(np.percentile(boots, 5))
    cnt = 0
    for _ in range(n_boot):
        s = r * rng.choice([-1, 1], len(r))
        if (s.mean() / s.std() * np.sqrt(12) if s.std() > 0 else 0.0) >= obs:
            cnt += 1
    g3 = float(cnt / n_boot)
    return {
        "sharpe_m": round(float(obs), 4), "n_months": len(r),
        "gate1_p": round(g1, 5), "gate2_boot5": round(g2, 4), "gate3_p": round(g3, 5),
        "alpha": alpha,
        "passes": bool(g1 < alpha and g2 > 0 and g3 < alpha),
    }


def bonferroni_rescue(summary_per_basket, instrument_best, monthly_returns_fn,
                      out_path, alpha_base=0.05, verbose=True):
    """
    Tier-2 rescue: for every basket whose Tier-1 verdict is NOT significant,
    test each instrument individually — at its own best params (the script's
    universality pass already computed instrument_best) — against the 3 gates
    at Bonferroni-corrected alpha = alpha_base / N_basket.

    Parameters
    ----------
    summary_per_basket : dict  {basket: {"binomial_significant": bool,
                                          "instruments": [...], ...}}
    instrument_best    : dict  {ticker: combo_tuple}
    monthly_returns_fn : callable (ticker, combo) -> pd.Series of monthly returns
    out_path           : str   JSON output path

    Returns the rescue dict (also saved to out_path).
    """
    rescue = {"_run_info": "integrated Phase-2 Bonferroni rescue (shared/basket_significance.py); "
                           "readers must isinstance-guard non-dict keys"}
    for basket, meta in summary_per_basket.items():
        if not isinstance(meta, dict):
            continue
        if meta.get("binomial_significant"):
            continue  # Tier 1 passed — nothing to rescue
        instruments = meta.get("instruments", [])
        n = len(instruments)
        if n == 0:
            continue
        alpha = alpha_base / n
        if verbose:
            print(f"\n  [Bonferroni rescue] basket '{basket}' failed Tier 1 -> "
                  f"per-instrument tests at alpha = {alpha_base}/{n} = {alpha:.5f}")
        rescue[basket] = {}
        for tkr in instruments:
            combo = instrument_best.get(tkr)
            if combo is None:
                rescue[basket][tkr] = {"rescued": False, "note": "no best combo available"}
                continue
            try:
                mret = monthly_returns_fn(tkr, combo)
            except Exception as e:  # keep the rescue loop robust
                rescue[basket][tkr] = {"rescued": False, "note": f"returns fn failed: {e}"}
                continue
            g = gates_at_alpha(mret, alpha=alpha)
            g["params"] = list(combo) if isinstance(combo, (tuple, list)) else combo
            g["rescued"] = g.pop("passes")
            rescue[basket][tkr] = g
            if verbose:
                tag = "RESCUED" if g["rescued"] else "no"
                print(f"    {tkr:<8} Sharpe(m)={g.get('sharpe_m','n/a')}  "
                      f"t={g.get('gate1_p','-')}  perm={g.get('gate3_p','-')}  -> {tag}")
    with open(out_path, "w") as f:
        json.dump(rescue, f, indent=2, default=str)
    if verbose:
        print(f"  Bonferroni rescue saved -> {out_path}")
    return rescue
