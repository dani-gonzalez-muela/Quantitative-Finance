# Congress Momentum (QUIVER_OPEN)

**Portfolio:** Daily | **Status:** ✅ Active (scripted) | **Canonical file:** `congress_momentum_Implementation_v2.py`

---

## 1. Strategy

Event strategy on US Congressional **Purchase** disclosures (QuiverQuant). Filters for stocks already moving before publication (Annualized_Traded_To_File > 1.5) with fast Quiver publication (≤3 days from SEC filing). Buys at **open** on the Quiver upload day, sells at **close** same day.

⚠️ Live execution requires intraday Quiver API polling — disclosures uploaded after market close are not executable same-day.

## 2. Standardization decisions (fable run 2026-07-02)

- **Backtest/Implementation split** executed: `congress_momentum_Backtest_v2.py` (signal + significance + trades CSV) and `congress_momentum_Implementation_v2.py` (sizing sweep + selection).
- **Basket testing does not apply** (plan Phase B item 4 / refactor_discussion_points §2.1): single-signal event strategy on a rotating cross-section, not a fixed instrument basket. Validation = 3-gate significance on per-trade returns.
- **Quiver data stays private** (not merged into shared price stores): distinct external source/licensing. Registered in the data manifest as store `congress_quiver` → `Congress Things/_ARCHIVE/final_data_MEGA.pkl` (589MB, not duplicated). The notebook's hardcoded absolute Windows path was removed (ROOT-bug class).
- **Sizing variants** = bet-fraction sweep (5%/10%/20% of capital per trade) — per-share vol targeting doesn't apply to same-day events. Best-by-Sharpe auto-selected.
- Performance: the notebook's per-trade price lookup (re-sorted each ticker frame per trade, "takes a few minutes") was vectorized with searchsorted — full run now ~30s.

## 3. Results (v2 script run, 2026-07-02, 2016 → 2026)

Universe: 56,167 disclosures → 31,957 after delay filter → **3,481 trades** after momentum filter. Mean +0.198%/trade. Significance: **3/3 gates, SIGNIFICANT (strong)**.

| Variant (fraction/trade) | Sharpe | CAGR | MaxDD |
|---|---|---|---|
| conservative (5%) | 0.87 | 3.6% | −5.4% |
| base (10%, notebook setting) | 0.87 | 7.4% | −10.5% |
| **aggressive (20%)** ⭐ selected | **0.89** | 15.1% | −20.0% |

10/10 positive years at the 10% base setting. **Sharpe convention note (2026-07-02):** returns are computed on a business-day grid. The notebook (and this script's first version) padded weekends as zero-return calendar days while annualizing by √252, deflating Sharpe ~15% (0.74 instead of 0.87) — that's why the notebook's Sharpe never matched the old implementations.json (0.88) despite identical CAGR/MaxDD. Fixed; base_10pct now reproduces the old value. Sharpe is nearly fraction-invariant (as expected for sequential fractional sizing) — the 20% variant is selected on marginal Sharpe, but the fraction choice is effectively a risk-appetite dial; the 10% base remains the documented notebook-confirmed setting.

Diff vs notebook header ("$100K → $155,545"): the script covers a longer period (through mid-2026) and reproduces the notebook's pipeline; the notebook's header quoted V2_02 §8 numbers from an earlier data cut.

## 4. Files

| File | Description |
|---|---|
| `congress_momentum_Backtest_v2.py` | Signal + significance + trades (loads Quiver pickle via manifest; auto-uses /tmp staging copy if present) |
| `congress_momentum_Implementation_v2.py` | Bet-fraction sweep + best-by-Sharpe selection |
| `results/congress_momentum_quiver_open_trades.csv` | 3,481 canonical 9-col trades (now with real entry/exit prices) |
| `results/congress_momentum_quiver_open_daily_equity.csv` | Base-setting daily equity |
| `results/equity/combined_equity_{conservative_5pct,base_10pct,aggressive_20pct,final}.csv` | Sizing variants + selected |
| `results/congress_momentum_quiver_open_{summary,implementations}.json` | Stats, significance, `selected_variant` |
| `congress_momentum_Backtest.ipynb` | Original notebook (historical) |
