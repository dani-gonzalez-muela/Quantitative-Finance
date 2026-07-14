# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: pead_earnings_drift — Multi-Asset Timing Backtest
#
# Reason:
#   Post-Earnings Announcement Drift (PEAD) is a stock-level strategy.
#   Signal requires earnings surprise scores (EPS actual vs consensus or prior quarter)
#   for individual stocks, then ranks stocks by SUE (standardized unexpected earnings).
#
#   ETF-level earnings are aggregated across hundreds of holdings. An ETF's quarterly
#   return cannot be linked to a single earnings announcement date.
#
# Required data: Compustat quarterly (epspxq, rdq announcement date) + CRSP daily.
#   Available: 03_na_security_daily.parquet (partial), 17_ccm_master.parquet (CCM bridge).
#   Missing: clean per-announcement daily return windows, point-in-time S&P 500 membership.
#
# Status: SKIPPED — individual stock earnings announcement infrastructure not yet built
# Assigned basket: us_equity_broad (needs individual stock data)


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
                    ticker_data[_t]["close"], generate_pead_earnings_drift_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "pead_earnings_drift_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
