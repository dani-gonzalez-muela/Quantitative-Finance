# Intraday Portfolio (fixed additive)

portfolio = mean(EMA,IMOM,ORB,VWAP) + overnight (non-overlapping sessions)

**Sharpe(d) 4.032 | CAGR 50.82% | MaxDD -8.34%**

Components = each strategy's v2 best-by-Sharpe combined_equity_final.csv.

Correlations (daily):

|                   |   ema_crossover |   intraday_momentum |   orb |   vwap_trend |
|:------------------|----------------:|--------------------:|------:|-------------:|
| ema_crossover     |            1    |                0.48 |  0.22 |         0.14 |
| intraday_momentum |            0.48 |                1    |  0.27 |         0.17 |
| orb               |            0.22 |                0.27 |  1    |         0.14 |
| vwap_trend        |            0.14 |                0.17 |  0.14 |         1    |
