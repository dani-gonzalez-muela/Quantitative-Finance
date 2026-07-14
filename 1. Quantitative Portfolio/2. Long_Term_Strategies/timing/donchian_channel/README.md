# Donchian Channel

**Portfolio:** Daily (sub-monthly holds) | **Status:** ✅ Active | **Canonical:** `*_v2_multiasset_daily_equity/`

## 1. Strategy

Breakout trend timing: long on a 20-day channel breakout, minimum 30-day hold, −8% stop. Long only, 5bps/side.

## 2. Validation

Multi-asset across us_equity_broad / us_sectors / us_factor (21 instruments): **19/21 pass** at canonical params (channel=20, min_hold=30, stop=−8%). v1 (SPY/QQQ/IWM, 2006–2026): 3/3 gates, Sharpe 0.92.

## 3. Results

Monthly Sharpe ≈ 0.94 (Daily-portfolio measurement). v1 variants: simple 85% Sharpe 0.92/CAGR 9.5%; asset-vol 10% Sharpe 0.93/CAGR 11.1%.

## 4. Portfolio role

Daily-portfolio candidate. Rejected at step 7 of the 2026-06-28 Daily greedy (−0.16 Sharpe, ρ=0.69 with Bollinger); not selected 2026-07-02 either. Kept validated as a Bollinger substitute if band mean-reversion decays.

## 5. Files

| File | Description |
|---|---|
| `results/donchian_channel_v2_multiasset_daily_equity/combined_equity.csv` | Canonical equity (portfolio input) |
| `results/donchian_channel_{multiasset_,}summary.json` | Gates + stats |
| `results/donchian_channel_implementations*.json` | Sizing variants |
