# _shared/ — the single shared package

Imported everywhere as `from _shared... import ...` (project root on `sys.path`
via the `.project_root` walk — the guarded `# __ROOTBOOT__` block present in all
live scripts/notebooks; never hardcode `../..`).

| Module | Role |
|---|---|
| `paths.py` | Project-root discovery + `data_dir()/data_file()` resolver over the STORE-REGISTRY table in `0. Data/README.md` |
| `fees.py` | SEC + FINRA TAF + slippage fee model (`SLIPPAGE_PER_SHARE` default $0.01; the intraday Implementations pass their own `SLIPPAGE`, canonical $0.005 since 2026-07-10) |
| `implementations.py` | Sizing variants (simple_bet, intraday_asset_vol, vol_targeting, risk_based, …) + daily-equity builders |
| `basket_significance.py` / `significance.py` | 3-gate test (t-test, bootstrap Sharpe, sign-permutation) + Bonferroni rescue |
| `metrics.py`, `benchmark.py`, `plotting.py`, `results.py` | Stats, benchmarks, plots, results IO |
| `portfolio_engine.py` | Portfolio math used by `3. Portfolio_construction` |
| `basket_implementations.py`, `daily_impl_utils.py`, `_backtest_utils.py` | Basket/daily helpers |
| `fix_imports.py` | One-off migration tool (shared.* -> _shared.*), dry-run by default |
