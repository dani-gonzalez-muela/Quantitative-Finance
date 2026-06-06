# -*- coding: utf-8 -*-
"""
Created on Fri Mar  1 14:39:24 2024

@author: amief
"""

import numpy as np

def crank_nicolson_european_option(T, X, r, sigma, delta, K, M, N):
    dt = T / N
    dx = X / M

    # Create grid
    x_values = np.linspace(0, X, M + 1)
    t_values = np.linspace(0, T, N + 1)

    # Initialize matrix for option prices
    u = np.zeros((M + 1, N + 1))

    # Set initial condition for European call option
    u[:, 0] = np.maximum(x_values - K, 0)

    # Crank-Nicolson update loop
    for n in range(0, N):
        for i in range(1, M):
            # Coefficients for the update formula
            alpha = 0.25 * dt * r * x_values[i]
            beta = 0.5 * dt * sigma**2 * x_values[i]**(2 * delta) / dx**2

            # Update formula
            u[i, n+1] = (
                (dt / 4) * (alpha * (u[i+1, n+1] - u[i-1, n+1] + u[i+1, n] - u[i-1, n]) + beta * (u[i+1, n+1] - 2*u[i, n+1] + u[i-1, n+1] + u[i+1, n] - 2*u[i, n] + u[i-1, n]))
                + u[i, n]
            )

    return u, x_values, t_values 

# Example usage:
T = 1.0        # Time to expiration
X = 100.0      # Maximum spatial coordinate
r = 0.05       # Risk-free interest rate
sigma = 0.2    # Volatility
delta = 1.0    # Delta parameter
K = 50.0       # Option strike price
M = 100        # Number of spatial steps
N = 1000       # Number of time steps

option_prices, x_values, t_values = crank_nicolson_european_option(T, X, r, sigma, delta, K, M, N)

# Plot the option price at different time steps
import matplotlib.pyplot as plt

for i in range(0, N+1, N//5):
    plt.plot(x_values, option_prices[:, i], label=f'Time: {t_values[i]:.2f}')

plt.xlabel('Stock Price (x)')
plt.ylabel('Option Price (u)')
plt.legend()
plt.title('European Call Option Pricing using Crank-Nicolson Method')
plt.show()
