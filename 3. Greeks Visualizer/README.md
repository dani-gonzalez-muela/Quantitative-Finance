# Options Greeks Visualizer

An interactive tool for exploring how options behave — how sensitive they are to price moves, time, and volatility — built on the Black-Scholes model.

## What it does

Move the sliders (spot price, strike, implied volatility, interest rate, time to expiry) and watch all five Greeks update instantly across four views:

- **Greeks vs Spot** — how delta, gamma, theta, vega, and rho change as the underlying moves
- **Greeks vs Time** — how they evolve as the option approaches expiry
- **Multi-T Overlay** — all expiries on the same chart, making the gamma spike near expiry visible
- **Payoff & P&L** — the classic hockey-stick payoff alongside fair value curves at different points in time

## What it shows

The core idea is that after delta-hedging, an option's P&L is driven entirely by the difference between implied and realized volatility — not by the direction of the market. The charts make this concrete: gamma and theta are mirror images of each other, and the only way to have one is to pay for the other.

## Assumptions

Greeks are computed under Black-Scholes, which assumes the stock follows geometric Brownian motion with constant volatility. Real markets have vol smiles, jumps, and stochastic volatility — so treat this as a clean theoretical baseline, not a production pricing tool.

## Built with

Vanilla HTML, CSS, and JavaScript. No frameworks. Chart.js for the charts.
