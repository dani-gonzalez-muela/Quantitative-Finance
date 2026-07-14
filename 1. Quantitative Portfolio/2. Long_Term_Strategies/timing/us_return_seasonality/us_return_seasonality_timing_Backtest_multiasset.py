# __ROOTBOOT__ ensure project root on sys.path (auto-added; safe to keep)
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while _r != _os.path.dirname(_r) and not _os.path.exists(_os.path.join(_r, '.project_root')):
    _r = _os.path.dirname(_r)
if _os.path.exists(_os.path.join(_r, '.project_root')) and _r not in _sys.path:
    _sys.path.insert(0, _r)

# SKIPPED: us_return_seasonality — Multi-Asset Timing Backtest
#
# Reason:
#   While the calendar seasonality signal (same-month 5yr trailing avg) could
#   technically be applied to any ETF, the ETF history in the 68-ticker dataset
#   begins 2016-2017. With only ~9 years of data and 12 months × 9 years = ~9
#   observations per calendar slot, the seasonal estimates are extremely noisy.
#
#   A robust seasonality test requires at least 20+ years of monthly history
#   to estimate per-month averages with significance. The ETF window is insufficient.
#   The v1 backtest uses FF market returns (1963-present) for this reason.
#
# Next steps:
#   1. Extend ETF history using Alpaca API (blocked in sandbox) or synthetic proxies.
#   2. Alternatively test on CRSP decile portfolio returns (longer history available).
#
# Status: SKIPPED — insufficient ETF history (need 20+ years; have ~9)
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
                    ticker_data[_t]["close"], generate_us_return_seasonality_trades  # TODO: verify fn name(ticker_data[_t], _t, *_c))),
            out_path=os.path.join(RESULTS_DIR, "us_return_seasonality_v2_bonferroni_results.json"),
        )
    else:
        print("[bonferroni] summary_per_basket/instrument_best not found in this "
              "script's namespace - wire manually (see bollinger_band reference).")
except Exception as _e:
    print(f"[bonferroni] integration inactive: {_e}")
