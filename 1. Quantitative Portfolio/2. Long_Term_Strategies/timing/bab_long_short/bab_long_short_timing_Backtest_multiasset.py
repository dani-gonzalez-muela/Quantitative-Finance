# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: bab_long_short — Multi-Asset Timing Backtest
#
# Reason:
#   Betting Against Beta (BAB) is a stock-level long/short strategy.
#   Signal requires individual stock betas (from CRSP daily + CCM bridge),
#   which cannot be replicated with 68 ETF tickers.
#   ETF-level betas are aggregated and stable — no cross-sectional spread
#   of low-beta vs high-beta instruments exists within a basket.
#
# Multi-asset adaptation (theoretical):
#   Basket: us_factor = ["IWF","IWD","IWM","USMV","MTUM","PKW","DVY"]
#   USMV (min-vol) would be the "low-beta" proxy; MTUM or IWF the "high-beta".
#   This collapses to a 2-instrument carry trade, not a proper BAB implementation.
#
# Next steps:
#   1. Build individual-stock beta infrastructure using CRSP daily data.
#   2. Use 03_na_security_daily.parquet with 17_ccm_master.parquet.
#   3. Rank stocks by beta monthly; long bottom quintile, short top quintile.
#
# Status: SKIPPED — CRSP individual stock data infrastructure not yet built
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
                    ticker_data[_t]["close"], generate_bab_long_short_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "bab_long_short_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
