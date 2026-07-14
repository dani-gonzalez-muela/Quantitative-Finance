# Per-Strategy Top 10 Instruments by Sharpe Ratio

*Period: 2016-01-04 to 2025-07-03 | Universe: 43 ETFs available of 68 | TC: 5 bps one-way*

*Note: overnight_premium excluded — daily TC (5 bps × 2 × 252d = ~25%/yr) makes it non-meaningful at this frequency.*


## Bond Duration Carry

*Real yield signal (DFII10) is highly effective for HYG and EMB (Sharpe ~0.79). TIPS benefit most logically given real yield construction.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| HYG | bonds_us | 5.006 | 0.7949 | 0.9299 | -10.083 |
| EMB | bonds_intl | 5.789 | 0.7869 | 0.9819 | -14.481 |
| LQD | bonds_us | 4.667 | 0.6895 | 0.8251 | -12.891 |
| TIP | bonds_us | 2.746 | 0.5706 | 0.7484 | -9.436 |
| IEF | bonds_us | 2.082 | 0.376 | 0.5071 | -13.123 |
| TLT | bonds_us | 2.038 | 0.2221 | 0.293 | -28.501 |

## Bond Trend

*SHY dominates (Sharpe 1.42) due to near-zero vol. TLT is the weakest — rising rates 2016-2023 hurt. Works for short/medium duration, fails for long.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| SHY | bonds_us | 1.564 | 1.4219 | 1.6956 | -1.369 |
| LQD | bonds_us | 3.287 | 0.4781 | 0.4539 | -21.764 |
| TIP | bonds_us | 2.057 | 0.4639 | 0.4988 | -11.208 |
| HYG | bonds_us | 1.693 | 0.2953 | 0.2667 | -22.026 |
| IEF | bonds_us | 1.051 | 0.2949 | 0.2619 | -8.335 |
| EMB | bonds_intl | 1.854 | 0.2788 | 0.2089 | -26.544 |
| TLT | bonds_us | -0.711 | -0.0309 | -0.0255 | -32.416 |

## Commodity Trend

*GLD is the standout (Sharpe 0.54). Other commodities show weaker signals. Trend momentum is less reliable in contango-heavy futures-based ETFs.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| GLD | commodities | 5.918 | 0.5403 | 0.5866 | -32.144 |
| PDBC | commodities | 2.448 | 0.2517 | 0.2245 | -30.231 |
| GDX | commodities | 1.685 | 0.1986 | 0.2382 | -53.836 |
| USO | commodities | 1.76 | 0.1899 | 0.178 | -39.933 |
| SLV | commodities | 1.249 | 0.1666 | 0.1569 | -46.647 |

## Country Cape Rotation

*Limited country coverage (only 3 ETFs available) constrains this strategy. Both value and momentum variants show similar, modest Sharpe.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| country_cape_value_top2 | multi_asset | 6.982 | 0.4492 | 0.5272 | -40.599 |
| country_cape_momentum_top2 | multi_asset | 6.618 | 0.4395 | 0.5027 | -48.173 |

## Cross Asset Carry

*Sharpe-proxy ranking produces solid risk-adjusted returns. Quality-of-carry matters more than raw momentum for cross-asset portfolios.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| cross_asset_carry_top10 | multi_asset | 7.724 | 0.6067 | 0.6936 | -25.922 |

## Cross Asset Momentum

*Top-20% selection outperforms top-10% and top-30% — concentration matters. Works well as an allocation filter across the full universe.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| cross_asset_mom_top10 | multi_asset | 14.084 | 0.7807 | 0.9541 | -27.432 |
| cross_asset_mom_top20 | multi_asset | 11.187 | 0.7328 | 0.8828 | -24.533 |
| cross_asset_mom_top30 | multi_asset | 9.208 | 0.6582 | 0.7712 | -25.416 |

## Donchian Channel

*Most transferable strategy in the set — positive Sharpe on 38/43 instruments. Best on XLK, SPY, QQQ, SHY. Trend-following works across asset classes.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| XLK | us_sectors | 13.677 | 0.9242 | 1.0069 | -19.334 |
| SPY | us_equity_broad | 9.631 | 0.9204 | 0.9284 | -15.209 |
| SHY | bonds_us | 1.067 | 0.8756 | 0.9977 | -2.164 |
| IWF | us_factor | 10.987 | 0.8684 | 0.8916 | -23.171 |
| QQQ | us_equity_broad | 11.952 | 0.868 | 0.9204 | -24.138 |
| PKW | us_factor | 9.744 | 0.8363 | 0.8639 | -17.822 |
| USMV | us_factor | 6.734 | 0.8031 | 0.809 | -14.872 |
| AMLP | real_assets | 12.614 | 0.7427 | 0.8373 | -36.29 |
| MTUM | us_factor | 8.571 | 0.728 | 0.734 | -24.475 |
| IWD | us_factor | 5.599 | 0.602 | 0.5883 | -16.783 |

## Em Dm Carry

*EEM vs SPY variant outperforms EEM vs EFA. EM/DM carry signal is meaningful but concentration risk is high; basket version is more stable.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| em_dm_carry_EEM_SPY | multi_asset | 11.572 | 0.703 | 0.882 | -32.941 |
| em_dm_carry_EEM_EFA | multi_asset | 7.488 | 0.4883 | 0.6152 | -36.772 |
| em_dm_carry_baskets | multi_asset | 4.372 | 0.4367 | 0.524 | -27.441 |

## Gtaa

*Works robustly as a top-down filter; us_sectors and full-universe variants show best risk-adjusted returns. Limited country ETF coverage hurts intl variants.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| gtaa_us_sectors | multi_asset | 10.762 | 0.6639 | 0.7455 | -28.839 |
| gtaa_full_universe | multi_asset | 8.905 | 0.6494 | 0.7512 | -22.607 |
| gtaa_bonds | multi_asset | 3.147 | 0.5665 | 0.6478 | -12.465 |
| gtaa_commodities | multi_asset | 10.105 | 0.5477 | 0.6779 | -35.625 |
| gtaa_real_assets | multi_asset | 6.899 | 0.4975 | 0.5842 | -24.437 |
| gtaa_em_countries | multi_asset | 5.392 | 0.4338 | 0.5218 | -40.635 |

## Ibs Mean Reversion

*Generalizes best to low-vol equity ETFs (IWF, USMV, XLC) and GLD. Struggles on bond ETFs and commodities with contango.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| IWF | us_factor | 8.661 | 0.7973 | 0.6466 | -19.319 |
| XLC | us_sectors | 7.933 | 0.6845 | 0.5893 | -26.392 |
| USMV | us_factor | 4.869 | 0.65 | 0.5555 | -12.367 |
| XLI | us_sectors | 5.744 | 0.5741 | 0.4559 | -21.862 |
| GLD | commodities | 4.353 | 0.5684 | 0.5056 | -12.447 |
| XLK | us_sectors | 6.862 | 0.5193 | 0.3782 | -24.789 |
| VNQ | real_assets | 5.224 | 0.5165 | 0.4182 | -18.461 |
| XLB | us_sectors | 4.962 | 0.4869 | 0.419 | -28.857 |
| INDA | em_country | 5.752 | 0.4809 | 0.3761 | -35.47 |
| IWM | us_equity_broad | 5.686 | 0.4756 | 0.3614 | -34.578 |

## Industry Trend

*US sectors and all-equity universe show best results. Cross-sectional momentum is robust in equity but hindered by limited intl country coverage.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| industry_trend_us_sectors | multi_asset | 12.135 | 0.7264 | 0.855 | -30.149 |
| industry_trend_all_equity | multi_asset | 11.762 | 0.7005 | 0.8182 | -32.085 |
| industry_trend_em | multi_asset | 6.485 | 0.4374 | 0.5055 | -44.012 |

## Low Volatility

*All-equity universe version (Sharpe 0.76) beats full-68 version (0.69). Low-vol factor is real and transferable within equities.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| low_vol_all_equity | multi_asset | 10.604 | 0.7573 | 0.8566 | -34.502 |
| low_vol_all_68 | multi_asset | 4.124 | 0.6872 | 0.8157 | -16.179 |

## Quality Timing

*Strong across all equity ETFs — largely because 2016-2025 period had quality in favor. QQQ and XLK standout with quality regime timing.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| XLK | us_sectors | 20.505 | 0.9018 | 1.1454 | -33.568 |
| QQQ | us_equity_broad | 17.941 | 0.8622 | 1.0858 | -35.008 |
| IWF | us_factor | 16.246 | 0.8347 | 1.0243 | -32.72 |
| SPY | us_equity_broad | 13.168 | 0.7958 | 0.9512 | -33.776 |
| USMV | us_factor | 9.912 | 0.736 | 0.8613 | -33.081 |
| MTUM | us_factor | 13.221 | 0.7216 | 0.8946 | -34.086 |
| XLI | us_sectors | 12.271 | 0.697 | 0.8654 | -42.315 |
| PKW | us_factor | 11.514 | 0.6582 | 0.8097 | -40.9 |
| XLY | us_sectors | 11.27 | 0.6071 | 0.7667 | -39.671 |
| IWD | us_factor | 9.219 | 0.6019 | 0.7149 | -38.514 |

## Reit Dividend Carry

*Weak overall — price-based yield proxy is noisy. AMLP shows the best result. Better results would require actual income return data.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| AMLP | real_assets | 5.351 | 0.4313 | 0.4425 | -24.388 |
| VNQI | real_assets | 1.38 | 0.2208 | 0.2028 | -23.174 |
| XLU | us_sectors | 1.996 | 0.2068 | 0.1897 | -36.025 |
| XLRE | us_sectors | -0.342 | 0.0515 | 0.0438 | -38.79 |
| VNQ | real_assets | -0.728 | 0.016 | 0.0125 | -42.439 |

## Sentiment Timing

*VIX-based sizing adds real value for US equity. XLK, QQQ, and IWF show Sharpe near 1.0. Effect fades for intl equity (less VIX sensitivity).*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| XLK | us_sectors | 17.836 | 0.9984 | 1.1511 | -25.658 |
| USMV | us_factor | 9.42 | 0.9828 | 1.1055 | -15.016 |
| IWF | us_factor | 14.44 | 0.9648 | 1.0855 | -23.356 |
| QQQ | us_equity_broad | 15.519 | 0.9499 | 1.0912 | -22.789 |
| SPY | us_equity_broad | 11.124 | 0.8941 | 0.9941 | -19.316 |
| MTUM | us_factor | 12.341 | 0.834 | 0.9567 | -24.269 |
| XLU | us_sectors | 9.286 | 0.734 | 0.8906 | -21.885 |
| XLI | us_sectors | 9.202 | 0.7007 | 0.8286 | -24.102 |
| XLY | us_sectors | 10.024 | 0.681 | 0.8165 | -26.016 |
| IWD | us_factor | 6.991 | 0.6393 | 0.7295 | -18.309 |

## Turn Of Month

*Calendar effect confirmed across equity and real assets. AMLP and XLC show strongest effect. Effect weaker for international ETFs.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| AMLP | real_assets | 9.707 | 0.8352 | 0.7056 | -11.894 |
| XLC | us_sectors | 9.24 | 0.825 | 0.6354 | -10.984 |
| INDA | em_country | 6.046 | 0.661 | 0.4524 | -25.441 |
| XLRE | us_sectors | 5.752 | 0.6328 | 0.4528 | -16.737 |
| XLV | us_sectors | 4.844 | 0.6268 | 0.4878 | -12.983 |
| VNQ | real_assets | 5.373 | 0.5993 | 0.4257 | -18.131 |
| USMV | us_factor | 3.413 | 0.5189 | 0.3708 | -13.335 |
| QQQ | us_equity_broad | 4.778 | 0.4838 | 0.3393 | -17.392 |
| VNQI | real_assets | 3.307 | 0.481 | 0.3676 | -14.401 |
| XLB | us_sectors | 4.262 | 0.4718 | 0.3747 | -18.806 |

## Vix Mean Reversion

*Consistent moderate performance across all US equity sub-categories. QQQ and XLK stand out; financials and utilities lag.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| XLK | us_sectors | 11.264 | 0.6535 | 0.4703 | -26.615 |
| QQQ | us_equity_broad | 9.057 | 0.5801 | 0.4136 | -23.67 |
| MTUM | us_factor | 8.059 | 0.559 | 0.3891 | -32.907 |
| IWF | us_factor | 8.257 | 0.5526 | 0.3892 | -27.82 |
| IWM | us_equity_broad | 8.157 | 0.5372 | 0.3744 | -38.242 |
| MDY | us_equity_broad | 7.108 | 0.4884 | 0.336 | -40.149 |
| SPY | us_equity_broad | 6.252 | 0.4864 | 0.3309 | -31.703 |
| XLI | us_sectors | 6.605 | 0.4789 | 0.3269 | -39.834 |
| XLB | us_sectors | 6.6 | 0.4702 | 0.3347 | -33.295 |
| XLC | us_sectors | 6.599 | 0.437 | 0.3393 | -33.049 |

## Vol Overlay

*Most consistently strong strategy — positive on 40/43 instruments. Tech (XLK, QQQ, IWF) delivers Sharpe>1.0. A universal overlay that adds value everywhere.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| IWF | us_factor | 11.47 | 1.0185 | 1.2778 | -14.659 |
| XLK | us_sectors | 11.592 | 1.0127 | 1.2842 | -12.471 |
| QQQ | us_equity_broad | 11.148 | 0.9829 | 1.2446 | -15.161 |
| SHY | bonds_us | 2.256 | 0.9608 | 1.3768 | -8.446 |
| USMV | us_factor | 9.982 | 0.9198 | 1.1423 | -15.056 |
| SPY | us_equity_broad | 9.732 | 0.8693 | 1.0503 | -15.71 |
| MTUM | us_factor | 9.505 | 0.8647 | 1.1113 | -18.071 |
| GLD | commodities | 9.168 | 0.8537 | 1.2329 | -18.149 |
| HYG | bonds_us | 6.359 | 0.7705 | 1.0162 | -16.944 |
| XLY | us_sectors | 8.296 | 0.7627 | 1.0103 | -16.704 |

## Yield Curve Duration

*T10Y2Y signal adds value for SHY (0.74) and HYG (0.46). TLT barely benefits — curve shape matters less when duration is extreme.*


| Instrument | Category | CAGR% | Sharpe | Sortino | MaxDD% |
|---|---|---|---|---|---|
| SHY | bonds_us | 0.784 | 0.7416 | 0.8733 | -4.681 |
| HYG | bonds_us | 3.245 | 0.4549 | 0.4519 | -22.026 |
| LQD | bonds_us | 2.065 | 0.3094 | 0.3157 | -21.764 |
| IEF | bonds_us | 0.843 | 0.189 | 0.2446 | -19.536 |
| TLT | bonds_us | 0.137 | 0.0736 | 0.094 | -39.492 |