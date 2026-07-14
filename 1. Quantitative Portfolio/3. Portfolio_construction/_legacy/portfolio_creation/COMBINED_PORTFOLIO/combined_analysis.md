# Combined Portfolio A + B — Full Analysis

**Date:** 2026-06-19  
**Common window:** 2016-06-15 → 2025-07-02 (2275 trading days, ~9.0 yrs)  
**A–B correlation:** 0.2020  


---

## Part 1: Portfolio A (Short-Term, 5 Strategies)

| Strategy | Signal Type | Instrument | Sharpe | CAGR | MaxDD |
|---|---|---|---|---|---|
| ema_crossover | Intraday Trend | QQQ | 3.021 | 43.0% | -5.6% |
| ibs_mean_reversion | Mean Reversion | SPY | 1.380 | 11.5% | -7.9% |
| congress_s3 | Event-Driven Alpha | Multi | 0.863 | 7.2% | -10.5% |
| overnight | Overnight Carry | SPY | 0.759 | 3.3% | -7.2% |
| intraday_momentum | Intraday Momentum | SPY | 1.498 | 9.5% | -6.6% |

**Portfolio A combined (EW):** Sharpe 3.226 | CAGR 14.4% | MaxDD -2.8% | Sortino 6.105  


---

## Part 2: Portfolio B (Long-Term, 9 Strategies)

| Strategy | Signal Type | Sharpe | CAGR | MaxDD | Source |
|---|---|---|---|---|---|
| congress_s2 | Political Alpha — Trade Mirror | 1.276 | 10.7% | -9.6% | sleeve |
| gtaa | Global Tactical AA | 0.929 | 6.7% | -9.2% | sleeve |
| vol_overlay | Vol Regime Overlay | 0.996 | 11.3% | -17.7% | sleeve |
| quality_profitability | Quality Factor | 0.793 | 7.9% | -15.2% | sleeve |
| turn_of_month__real_assets | Calendar Seasonality | 0.828 | 6.1% | -8.5% | basket |
| bond_duration_carry | Bond Carry | 0.601 | 2.5% | -9.1% | basket |
| donchian_channel | Trend Following | 0.968 | 11.4% | -18.7% | sleeve |
| xs_momentum | Cross-Sec Momentum | 0.836 | 10.8% | -22.1% | sleeve |
| bollinger_band | Mean Reversion | 0.776 | 11.6% | -27.9% | sleeve |

**Portfolio B combined (EW):** Sharpe 1.983 | CAGR 9.2% | MaxDD -9.4% | Sortino 2.690  


---

## Part 3: Leverage & Allocation Scenarios

| Scenario | Sharpe | CAGR | MaxDD | Sortino | Notes |
|---|---|---|---|---|---|
| A 1x standalone | 3.226 | 14.4% | -2.8% | 6.105 | Baseline A |
| B 1x standalone | 1.983 | 9.2% | -9.4% | 2.690 | Baseline B |
| A1x + B1x (50/50) | 3.329 | 11.8% | -2.6% | 5.971 | Conservative |
| A2x + B1x (50/50) ⭐ | 3.503 | 16.7% | -2.9% | 6.728 | RECOMMENDED |
| A2x + B2x (50/50) | 3.221 | 21.9% | -5.5% | 5.617 | Moderate aggression |
| A4x + B1x (50/50) | 3.605 | 18.5% | -2.9% | 7.213 | High A leverage |

**Recommended allocation: A 2x + B 1x, 50/50**  
- Sharpe 3.50, CAGR 16.7%, MaxDD -2.9%  
- A runs at 2x internal leverage (proper vol-targeting, not margin)  
- B runs at 1x — Bond Carry and Congress S2 are sensitive to sizing  
- A–B correlation: 0.20 (genuine diversification)  


---

## Part 4: Correlation Heatmap (All 14 Strategies)

| | A: EMA | A: IBS | A: S3 | A: Overnight | A: IntradayMom | B: S2 | B: GTAA | B: VolOv | B: Qual | B: ToM | B: BondCarry | B: Donch | B: XSMom | B: Bollinger |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A:ema_crossover | 1.0 | -0.04 | 0.02 | 0.01 | 0.49 | -0.0 | -0.08 | -0.01 | -0.01 | -0.02 | 0.05 | -0.07 | -0.03 | 0.02 |
| A:ibs_mean_reversion | -0.04 | 1.0 | -0.03 | 0.23 | 0.02 | 0.0 | 0.41 | -0.03 | 0.01 | 0.26 | 0.1 | 0.46 | 0.0 | **0.55** |
| A:congress_s3 | 0.02 | -0.03 | 1.0 | 0.12 | 0.02 | -0.0 | 0.01 | 0.13 | -0.01 | -0.03 | 0.04 | -0.0 | -0.01 | -0.04 |
| A:overnight | 0.01 | 0.23 | 0.12 | 1.0 | 0.04 | -0.0 | 0.15 | -0.07 | -0.02 | 0.1 | -0.0 | 0.15 | -0.0 | 0.32 |
| A:intraday_momentum | 0.49 | 0.02 | 0.02 | 0.04 | 1.0 | -0.0 | -0.04 | -0.03 | 0.01 | -0.03 | 0.06 | -0.11 | 0.0 | 0.06 |
| B:congress_s2 | -0.0 | 0.0 | -0.0 | -0.0 | -0.0 | 1.0 | 0.01 | 0.02 | 0.0 | -0.0 | -0.01 | 0.01 | 0.01 | 0.01 |
| B:gtaa | -0.08 | 0.41 | 0.01 | 0.15 | -0.04 | 0.01 | 1.0 | -0.02 | 0.02 | 0.33 | 0.16 | **0.53** | 0.0 | 0.36 |
| B:vol_overlay | -0.01 | -0.03 | 0.13 | -0.07 | -0.03 | 0.02 | -0.02 | 1.0 | 0.0 | 0.01 | 0.03 | -0.0 | 0.02 | -0.09 |
| B:quality_profitability | -0.01 | 0.01 | -0.01 | -0.02 | 0.01 | 0.0 | 0.02 | 0.0 | 1.0 | -0.05 | 0.03 | 0.01 | **0.81** | 0.01 |
| B:turn_of_month__real_assets | -0.02 | 0.26 | -0.03 | 0.1 | -0.03 | -0.0 | 0.33 | 0.01 | -0.05 | 1.0 | 0.12 | 0.26 | -0.06 | 0.26 |
| B:bond_duration_carry | 0.05 | 0.1 | 0.04 | -0.0 | 0.06 | -0.01 | 0.16 | 0.03 | 0.03 | 0.12 | 1.0 | 0.11 | 0.01 | 0.06 |
| B:donchian_channel | -0.07 | 0.46 | -0.0 | 0.15 | -0.11 | 0.01 | **0.53** | -0.0 | 0.01 | 0.26 | 0.11 | 1.0 | -0.01 | 0.27 |
| B:xs_momentum | -0.03 | 0.0 | -0.01 | -0.0 | 0.0 | 0.01 | 0.0 | 0.02 | **0.81** | -0.06 | 0.01 | -0.01 | 1.0 | -0.01 |
| B:bollinger_band | 0.02 | **0.55** | -0.04 | 0.32 | 0.06 | 0.01 | 0.36 | -0.09 | 0.01 | 0.26 | 0.06 | 0.27 | -0.01 | 1.0 |