# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: low_volatility — Multi-Asset Timing Backtest
#
# Reason:
#   Low volatility factor (BAB proxy) is a stock-level ranking strategy.
#   Signal requires individual stock historical volatility from CRSP daily returns.
#   Selecting the lowest-vol ETFs from a basket (e.g. USMV from us_factor) is
#   a 1-instrument degenerate case — the cross-sectional spread is trivial.
#
# Multi-asset analog:
#   Basket: us_factor = ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"]
#   Could rank ETFs by trailing 12m realized vol → hold the lowest 2.
#   However, this is equivalent to an inverse-vol momentum strategy, already
#   partially captured by usmv_bias in quality_profitability.
#
# Next steps:
#   1. Implement ETF-level realized-vol ranking as a separate strategy.
#   2. Or download stock-level CRSP data for proper low-vol factor.
#
# Status: SKIPPED — individual stock volatility data not available; ETF-level
#   ranking produces degenerate results (always USMV)
# Assigned basket: us_factor


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
                    ticker_data[_t]["close"], generate_low_volatility_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "low_volatility_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
