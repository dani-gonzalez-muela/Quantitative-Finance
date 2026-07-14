# Basket+Bonferroni for Long-Term Strategies — Design Decision & Results

**Fable run 2026-07-02.** The plan flagged this as a discussion point; the user chose **execute** at kickoff. This doc records what was built, why it was shaped this way, and what was deliberately not done.

## What was executed

`long_term/basket_bonferroni_validation.py` — a two-tier basket+Bonferroni framework where the **strategies are the instruments**, grouped into family baskets (`timing`, 19 members; `selection`, 10 members), tested on **monthly returns**:

- **Tier 1** — EW composite of each family through the standard 3 gates (one-sided t-test p<0.05, bootstrap 5th-pct Sharpe>0, sign-permutation p<0.05).
- **Tier 2** — if a family fails, per-strategy Bonferroni rescue at α = 0.05/N.

## Why strategies-as-instruments rather than per-instrument testing inside each strategy

The plan's own analysis (§Phase C) explains the problem: long-term strategies rebalance monthly, so a per-instrument Bonferroni test inside e.g. `country_cape_rotation` (α = 0.05/14 on ~120 monthly observations) needs an instrument-level monthly Sharpe ≳ 1.1 to pass — practically nothing would survive, and the exercise would either falsely gut valid strategies or force an impractically long lookback. The short-term framework works because 5-min data provides millions of observations; monthly data does not.

Testing at the strategy-within-family level keeps the framework's two-tier logic (composite gate + Bonferroni-corrected member rescue) at the aggregation level where monthly data has adequate power (~29 members × ~120 months), and directly answers the portfolio-relevant question: *which long-term strategies are included on weak evidence?*

## Results (2026-07-02)

| Family | N | Composite monthly Sharpe | Gates | Verdict |
|---|---|---|---|---|
| timing | 19 | 0.85 | t-p=0.000 ✓ boot5>0 ✓ perm ✓ | **PASS** |
| selection | 10 | 0.79 | all ✓ | **PASS** |

Both families pass, so no Bonferroni tier was triggered. Informational per-strategy gates at α=0.05 flag **4 weak members carried by their family baskets**:

- `timing/bond_duration_carry` (Sharpe 0.11, perm-p 0.37)
- `timing/yield_curve_duration` (Sharpe 0.15, perm-p 0.35)
- `selection/bond_trend` (Sharpe 0.19, perm-p 0.18)
- `selection/cross_asset_carry` (Sharpe 0.18, perm-p 0.29)

**Cross-check:** the first two are exactly the strategies `todo/_strategy_notes_and_extensions.md` already flags for re-benchmarking against IEF at quarterly rebalancing — this framework independently confirms that suspicion. Recommendation: run that re-benchmark before deciding whether to demote them; all four are bond/carry strategies whose 2016–2026 sample coincides with a historically hostile rates regime, so weak absolute Sharpe ≠ broken signal.

## Not done (deliberately)

- Per-instrument Bonferroni inside individual selection strategies (underpowered, see above).
- No strategy was removed from any portfolio — this is a measurement layer; allocation changes are the user's call.
- The existing `STRATEGY_REPORT.md` monthly 3-gate framework remains valid; this layer complements it with the family-composite + weak-member view.
