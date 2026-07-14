# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: insider_buying — Multi-Asset Timing Backtest
#
# Reason:
#   True insider buying signal requires EDGAR Form 4 data (SEC filing feed)
#   or OpenInsider API. Both are blocked in the sandbox.
#   The v1 backtest uses a VIX-spike proxy (insiders tend to buy after
#   sharp market drops), but that approach is already covered in detail by
#   sentiment_timing_timing_Backtest_multiasset.py, which implements the
#   VIX-regime sizing signal across us_equity_broad + us_sectors with
#   significance tests.
#
# Multi-asset adaptation (theoretical):
#   Basket: us_sectors or us_equity_broad
#   Aggregate Form 4 insider buys by sector; hold sectors with net insider buying.
#   Data: EDGAR efts.sec.gov or openinsider.com API.
#
# Next steps:
#   1. Set up EDGAR Form 4 downloader or subscribe to OpenInsider API.
#   2. Map insider ticker symbols to sector ETF GICS codes.
#   3. Aggregate monthly net-buy ratio per sector; run 3-gate test.
#
# Note: The VIX-proxy variant is implemented in:
#   sentiment_timing/sentiment_timing_timing_Backtest_multiasset.py
#
# Status: SKIPPED — EDGAR Form 4 / OpenInsider data not available
# Assigned basket: us_equity_broad + us_sectors


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
                    ticker_data[_t]["close"], generate_insider_buying_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "insider_buying_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
