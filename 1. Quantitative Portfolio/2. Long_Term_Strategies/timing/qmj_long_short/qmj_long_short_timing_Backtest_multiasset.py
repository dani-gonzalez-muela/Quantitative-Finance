# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: qmj_long_short — Multi-Asset Timing Backtest
#
# Reason:
#   Quality Minus Junk (QMJ) is a stock-level long/short strategy.
#   True QMJ requires individual stock profitability scores (ROE, margins,
#   earnings stability, etc.) from Compustat. The multiasset expansion would
#   need stock-level data to form long (high quality) vs short (junk) portfolios.
#
#   Note: The v1 backtest uses FF5 RMW factor as a direct QMJ proxy, which
#   does not translate to ETF selection — there is no ETF with pure quality exposure
#   in the 68-ticker data except partially USMV/MTUM.
#
#   A quality_profitability_selection_Backtest_multiasset.py already exists
#   covering the ETF-level adaptation of this signal (us_equity_broad basket).
#
# Next steps:
#   1. Build individual-stock quality scoring from Compustat fundamentals.
#   2. Use 17_ccm_master.parquet (available) for quality metrics.
#   3. Form L/S portfolio, test on CRSP daily returns.
#
# Status: SKIPPED — CRSP/Compustat individual stock infrastructure not yet built
# Assigned basket: us_factor (see quality_profitability_selection_Backtest_multiasset.py for ETF analog)


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
                    ticker_data[_t]["close"], generate_qmj_long_short_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "qmj_long_short_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
