# Stochastic Modelling and Numerical Methods in Finance: SABR and Heston
---
## Project Focus
The thesis centers on option pricing in financial mathematics, specifically studying two stochastic volatility models (**SABR** and **Heston**) and applying advanced numerical techniques to price vanilla options efficiently and accurately. The project was carried out jointly between **Pompeu Fabra University** and **CaixaBank**, combining academic research with practical financial applications.
---

## Key Components

### 1. Background and Motivation
- The **Black–Scholes model**, while fundamental, assumes constant volatility, which does not match observed market behaviors.  
- **Stochastic volatility models** allow volatility to vary randomly, better capturing market dynamics but are computationally complex.

### 2. Models Studied
- **SABR Model:** Captures the volatility smile, relatively simpler with fewer parameters and easier calibration; widely used in interest rate derivatives.  
- **Heston Model:** Includes mean reversion in volatility, has an explicit option pricing formula but more challenging calibration due to extra parameters.

### 3. Numerical Methods
- **Monte Carlo simulations** are essential for pricing since closed-form solutions are often unavailable.  
- **Variance reduction techniques** (Control Variates, Antithetic Variates, Conditional Monte Carlo, and combinations thereof) significantly improve the precision and computational speed of option price estimators.

### 4. Results – Variance Reduction
- Applied variance reduction methods to **SABR** and **Heston** models, showing dramatic improvements in estimator precision and reduced computational cost.  
- The combination of **Control Variate + Antithetic + Conditional Monte Carlo** yielded up to **460× improvement in SABR** and **30× in Heston** compared to naïve Monte Carlo.

### 5. Implied Volatility Surfaces
- Simulated surfaces reflect market-observed volatility smiles and skews, unlike the constant volatility assumption of Black–Scholes.  
- **SABR** surfaces matched well with **Hagan approximations**; **Heston** surfaces demonstrated complex shapes consistent with empirical phenomena.

### 6. Model Calibration
- Calibrated **SABR parameters** using real market data, minimizing the error between observed and model-implied volatilities per maturity.  
- Achieved calibration results very close to industry benchmarks, producing accurate implied volatility surfaces.

### 7. Conclusions and Future Directions
- Combining advanced variance reduction techniques is key to practical and efficient stochastic volatility model pricing.  
- Stochastic volatility models better reflect market realities and offer practical tools for traders and risk managers.  
- Future work could focus on improving computational efficiency, applying to local volatility or exotic options, and extending calibration methods.
