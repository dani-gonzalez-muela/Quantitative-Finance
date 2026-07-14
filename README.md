# Quantitative Finance Projects

## Overview
This repository contains quantitative finance projects covering option pricing, stochastic modeling, factor analysis, and company valuation. Projects combine theory and practical Python implementations to explore market dynamics, pricing strategies, and investment analysis. Techniques include stochastic volatility modeling, Monte Carlo simulations, finite difference methods, and empirical factor analysis.

## Projects

### 1. Stochastic Volatility Modelling: SABR and Heston
**Focus:** Option pricing using stochastic volatility models (SABR and Heston) with advanced numerical methods.  
**Key Components:**
- **Variance Reduction:** Combined Control Variate + Antithetic + Conditional Monte Carlo led to up to **460× improvement in SABR** and **30× in Heston** simulations.
- **Implied Volatility Surfaces:** Captured market-observed volatility smiles and skews.
- **Calibration:** SABR parameters calibrated on real market data, closely matching industry benchmarks.

### 2. Factor Momentum and Momentum Factor: European Market
**Focus:** Empirical study of momentum at the factor level, extending U.S.-focused findings to European equities.  
**Key Components:**
- Constructed the **FMOM (Factor Momentum)** factor.
- Tested autocorrelations and factor-level momentum profitability.
- Results: Factor momentum present in Europe, though weaker than in U.S. markets; FMOM contributes to explaining stock-level momentum returns.

### 3. Asian Option Pricing
**Focus:** Pricing arithmetic and geometric average Asian options using numerical and closed-form methods.  
**Key Components:**
- **Methods:** Finite Differences (Forward, Backward Euler, Crank-Nicolson), Monte Carlo, Control Variates.
- **Numerical Results:** Monte Carlo variance reduced by ~40%; Finite Differences execution ~0.1s, Monte Carlo 2–5s.
- **Validation:** Put-call parity satisfied; geometric < arithmetic average prices confirmed.

### 4. Constant Elasticity of Variance (CEV) Model
**Focus:** Option pricing under CEV dynamics to capture volatility smiles.  
**Key Components:**
- **CEV Dynamics:** `dS(t) = r S(t) dt + σ S(t)^δ dW(t)`
- **Numerical Scheme:** Crank-Nicolson on 100×1000 grid.
- **Results:** Good agreement with Black-Scholes for δ=1; stable and accurate solutions; fine grids improve precision.

### 5. Company Valuations
**Focus:** Python-based implementations for company valuation, including DCF and multiples.  
**Key Components:**
- Calculated intrinsic values and compared with market prices.
- Scenario analysis for investment insights.
