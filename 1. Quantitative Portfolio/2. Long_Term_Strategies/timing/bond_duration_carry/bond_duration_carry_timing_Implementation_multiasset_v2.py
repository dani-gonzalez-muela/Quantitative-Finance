# -*- coding: utf-8 -*-
"""Bond Duration Carry — Multi-Asset Implementation v2
No baskets passed the binomial significance test → no implementation.
"""
import sys, os, json
_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
HERE = _FILE_DIR
RESULTS_DIR = os.path.join(HERE, "results")
SUMMARY_PATH = os.path.join(RESULTS_DIR, "bond_duration_carry_v2_multiasset_summary.json")

print("=" * 70); print("BOND DURATION CARRY -- Multi-Asset Implementation v2"); print("=" * 70)
with open(SUMMARY_PATH) as f: summary = json.load(f)
basket_configs = summary["baskets"]
passing_baskets = {n: c for n, c in basket_configs.items() if c.get("binomial_significant", False)}
print(f"  Baskets tested: {len(basket_configs)}, passing: {len(passing_baskets)}")
for n, c in basket_configs.items():
    cp = c["canonical_params"]
    print(f"  {'PASS' if c.get('binomial_significant') else 'FAIL'} {n}: ry_long={cp['ry_long']},ry_short={cp['ry_short']},slope={cp['slope_thresh']} | medSh={c['canonical_median_sharpe']:.3f} | {c['verdict']}")
print("\n  No passing baskets — strategy not implemented.")
impl_json = {"strategy": "bond_duration_carry_v2", "n_passing_baskets": 0, "baskets": {}, "combined_stats": {}}
with open(os.path.join(RESULTS_DIR, "bond_duration_carry_v2_implementations_multiasset.json"), "w") as f:
    json.dump(impl_json, f, indent=2)
print("  Results written (empty).")
