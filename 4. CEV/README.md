# Constant Elasticity of Variance (CEV) Model: Implementation and Comparison

## Project Focus
Pricing options using the CEV model, which generalizes Black-Scholes by allowing volatility to depend on the stock price. Implements Crank-Nicolson numerical scheme and validates results against Black-Scholes.

## Key Components

### 1. Motivation
- Black-Scholes assumes constant volatility; CEV captures volatility smiles and leverage effects.
- Useful for exotic options, risk management, and asset price forecasting.

### 2. Model & CEV-CIR Connection
- **Stock dynamics:** `dS(t) = rS(t)dt + σ S(t)^δ dW(t)`
- If `X(t)` follows a CIR process, then `S(t) = X(t)^θ` solves the CEV equation, enabling CIR-based techniques.

### 3. Numerical Implementation
- **PDE:** `-∂_t u + r x ∂_x u + (σ²/2) x^(2δ) ∂²_x u = 0`
- **Scheme:** Crank-Nicolson (stable, combines forward/backward Euler)
- **Grid:** M=100, N=1000; boundary: terminal payoff, lower=0, upper=discounted linear growth.

### 4. Results
- Validated against Black-Scholes (δ=1); minor discrepancies observed.
- Finer grids/adaptive meshes improve accuracy.
- Fast computation with good stability-accuracy balance.

### 5. Key Insights
- Use CEV for pronounced volatility smiles or long-term/exotic options.
- Black-Scholes sufficient for short-term, at-the-money options.
- Numerical methods are essential; Crank-Nicolson provides efficiency.

### 6. Conclusions
- CEV implemented successfully, capturing realistic market volatility.
- CEV-CIR link provides theoretical foundation.
- Future work: adaptive schemes and exotic option pricing.
