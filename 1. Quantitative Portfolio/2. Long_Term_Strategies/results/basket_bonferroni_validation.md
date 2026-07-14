# Long-Term Basket+Bonferroni Validation (fable Phase C, 2026-07-02)

## timing family (19 strategies)

Composite EW monthly: Sharpe 0.846, gates t-p=0.0 boot5=0.621 perm-p=0.0 -> **PASS**

Per-strategy gates (informational, alpha=0.05):
- bab_long_short: Sharpe 0.343, t-p=0.0311, boot5=0.037, perm-p=0.0247 -> pass
- bollinger_band: Sharpe 1.083, t-p=0.0006, boot5=0.474, perm-p=0.001 -> pass
- bond_duration_carry: Sharpe 0.111, t-p=0.3675, boot5=-0.411, perm-p=0.371 -> WEAK
- credit_carry: Sharpe 0.582, t-p=0.0411, boot5=0.062, perm-p=0.0423 -> pass
- donchian_channel: Sharpe 0.945, t-p=0.0022, boot5=0.425, perm-p=0.0027 -> pass
- insider_buying: Sharpe 0.722, t-p=0.0, boot5=0.431, perm-p=0.0 -> pass
- low_volatility: Sharpe 0.725, t-p=0.0, boot5=0.495, perm-p=0.0 -> pass
- overnight_premium: Sharpe 0.695, t-p=0.0002, boot5=0.366, perm-p=0.0 -> pass
- pead_earnings_drift: Sharpe 0.753, t-p=0.0, boot5=0.458, perm-p=0.0 -> pass
- qmj_long_short: Sharpe 0.495, t-p=0.0016, boot5=0.237, perm-p=0.001 -> pass
- reit_dividend_carry: Sharpe 0.61, t-p=0.0041, boot5=0.204, perm-p=0.0037 -> pass
- sentiment_timing: Sharpe 0.671, t-p=0.0209, boot5=0.151, perm-p=0.019 -> pass
- short_interest_contrarian: Sharpe 0.685, t-p=0.0016, boot5=0.28, perm-p=0.0013 -> pass
- turn_of_month: Sharpe 0.91, t-p=0.0031, boot5=0.38, perm-p=0.0013 -> pass
- us_cross_sectional_momentum: Sharpe 0.966, t-p=0.0, boot5=0.687, perm-p=0.0 -> pass
- us_earnings_momentum: Sharpe 1.039, t-p=0.0, boot5=0.754, perm-p=0.0 -> pass
- us_return_seasonality: Sharpe 0.635, t-p=0.0003, boot5=0.331, perm-p=0.0003 -> pass
- us_shareholder_yield: Sharpe 0.819, t-p=0.0, boot5=0.529, perm-p=0.0 -> pass
- yield_curve_duration: Sharpe 0.154, t-p=0.3207, boot5=-0.359, perm-p=0.3463 -> WEAK

Weak members carried by the family basket: bond_duration_carry, yield_curve_duration

## selection family (10 strategies)

Composite EW monthly: Sharpe 0.79, gates t-p=0.0 boot5=0.578 perm-p=0.0 -> **PASS**

Per-strategy gates (informational, alpha=0.05):
- bond_trend: Sharpe 0.187, t-p=0.176, boot5=-0.15, perm-p=0.175 -> WEAK
- commodity_carry: Sharpe 0.544, t-p=0.0046, boot5=0.209, perm-p=0.0037 -> pass
- commodity_trend: Sharpe 0.381, t-p=0.0327, boot5=0.028, perm-p=0.0337 -> pass
- country_cape_rotation: Sharpe 0.47, t-p=0.0052, boot5=0.163, perm-p=0.0053 -> pass
- cross_asset_carry: Sharpe 0.181, t-p=0.2904, boot5=-0.341, perm-p=0.2937 -> WEAK
- em_dm_carry: Sharpe 0.845, t-p=0.0, boot5=0.489, perm-p=0.0 -> pass
- gtaa: Sharpe 0.831, t-p=0.0086, boot5=0.247, perm-p=0.0067 -> pass
- industry_trend: Sharpe 0.727, t-p=0.0145, boot5=0.17, perm-p=0.016 -> pass
- quality_profitability: Sharpe 0.895, t-p=0.0, boot5=0.683, perm-p=0.0 -> pass
- sector_momentum: Sharpe 0.896, t-p=0.0067, boot5=0.281, perm-p=0.007 -> pass

Weak members carried by the family basket: bond_trend, cross_asset_carry
