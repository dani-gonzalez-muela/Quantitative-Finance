# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: congress_trade_for_trade — Multi-Asset Timing Backtest
#
# Reason:
#   Congressional trading signal requires SEC-filed congressional transaction data
#   (typically from Capitol Trades API, Quiver Quant, or direct EDGAR Form 4 parsing).
#   The original v1 backtest uses a Jupyter notebook (Backtest.ipynb), suggesting
#   interactive / API-dependent data access.
#
#   No congressional trading dataset is available in the local data store
#   (data/wrds/, data/*.parquet). Web API access is blocked in the sandbox.
#
# Multi-asset adaptation (theoretical):
#   Basket: us_sectors or us_equity_broad
#   Aggregate congressional buy/sell trades by sector ETF; hold sectors with net buying.
#   Data: capitoltrades.com API or efts.sec.gov/EFTS API for Form 4 filings.
#
# Next steps:
#   1. Use Quiver Quant API (quiverquant.com/data/congresstrading) to pull historic data.
#   2. Map individual stock tickers to sector ETFs (via GICS sector classification).
#   3. Aggregate monthly net buy signal per sector; test vs 3-gate significance.
#
# Status: SKIPPED — congressional trading data not available
# Assigned basket: us_sectors


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
                    ticker_data[_t]["close"], generate_congress_trade_for_trade_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "congress_trade_for_trade_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
