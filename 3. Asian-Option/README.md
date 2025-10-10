# Asian Option: Pricing Methods and Implementation

## Project Focus
Pricing Asian options, whose payoffs depend on average asset prices, using numerical methods (finite differences, Monte Carlo, control variates) and closed-form solutions for geometric averages.

## Key Components

### 1. Motivation
- Asian options reduce sensitivity to volatility, protect against price manipulation, and offer lower premiums than European options.
- Useful in commodities, FX markets, and employee compensation plans.

### 2. Option Types & Theoretical Framework
- **Arithmetic Average:** `Payoff = max((1/T ∫ S(t) dt) - K, 0)`
- **Geometric Average:** `Payoff = max(exp(1/T ∫ log S(t) dt) - K, 0)`  
  Closed-form solution available.
- Stock dynamics under risk-neutral measure: `dS = rS dt + σ S dW`
- Arithmetic average requires numerical methods; geometric has analytical formulas.

### 3. Numerical Methods
- **Finite Differences:** Forward Euler, Backward Euler, Crank-Nicolson (grid: 1000×1000).
- **Monte Carlo Simulation:** Track path averages over 5000+ simulations.
- **Control Variates:** Use terminal stock price to reduce variance (~40% improvement).

### 4. Results & Analysis
- Asian options are cheaper than European equivalents, with lower volatility sensitivity.
- Finite differences: fast, accurate; Monte Carlo: flexible for path-dependent payoffs.
- Put-call parity and geometric < arithmetic average prices confirmed.
- Execution times: Finite Differences ~0.1s; Monte Carlo 2–5s.

### 5. Key Insights
- Practical advantages: lower hedging costs, robust pricing in volatile markets.
- Computational trade-offs: finite differences for speed/accuracy; Monte Carlo with control variates for flexibility and variance reduction.

### 6. Code Implementation
- Python functions for each pricing method.
- Visualization tools for sensitivity analysis.
- Automated validation and performance comparisons.

### 7. Conclusions
- Finite differences optimal for standard contracts.
- Monte Carlo methods essential for complex path-dependent options.
- Control variates significantly improve Monte Carlo efficiency.

### 8. Future Extensions
- American-style Asian options with optimal exercise.
- Discrete sampling, multi-asset baskets, jump-diffusion models.
- GPU acceleration for Monte Carlo.
