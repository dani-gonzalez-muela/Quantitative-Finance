# Research Framework — Long-Term Algorithmic Strategies

**Last updated**: 2026-06-23 (v2: per-basket param selection, 1/N sleeves for Type 1)  
**Universe**: 68 ETFs across 8 baskets, 2016–2026  
**Transaction cost**: 5 bps one-way  
**Significance**: 3-gate test on monthly returns

---

## What We Are Trying to Do

The goal of this project is to build a portfolio of systematic trading strategies — rules-based approaches to investing that can be expressed as code and applied consistently over time without discretionary judgment.

Each strategy is built around a **signal**: a piece of information that predicts whether an asset's return over the next period will be positive or negative, or which assets in a group will outperform others. The signal might be a technical indicator (price crossing a moving average), a calendar pattern (returns tend to be higher at the turn of the month), a relative valuation measure (buy the cheapest country by earnings yield), or a momentum score (buy whatever went up most in the last 6 months).

The job of the research process is to answer three questions for each signal:

1. **Does it work?** Is the signal's predictive power statistically real, or is it random noise that happened to look good over this sample period?
2. **Does it generalise?** Does it work on one lucky asset, or does the same signal work across many structurally different assets and markets?
3. **Is it practically investable?** After realistic transaction costs and position sizing, does enough alpha survive to be worth implementing?

We answer these questions through a structured three-step pipeline — Backtest, Multi-Asset Expansion, Implementation — with statistical guardrails at every step to prevent us from fooling ourselves.

---

## 1. The Two Types of Strategy

Before describing the pipeline, it helps to understand that we have two fundamentally different types of signal, and they require slightly different research processes.

### Type 1 — Timing Strategies

A timing strategy operates on one instrument at a time and answers the question: **should I be holding this asset right now, or not?**

The signal is binary (or at least generates a yes/no entry/exit decision). When the signal fires, you buy. When it turns off, you sell. You might be holding SPY for three weeks, flat for a week, then holding it again. The strategy does not compare SPY to any other asset — it just tells you when SPY is attractive versus when it is not.

Examples of timing signals:
- **Bollinger Band**: the asset is "cheap" when price falls to the lower band (mean reversion) and "expensive" at the upper band
- **Turn-of-Month**: stocks consistently have higher returns during the last two and first three trading days of each calendar month (a calendar anomaly)
- **Yield Curve Duration**: hold short-duration bonds when the yield curve is flat or inverted; hold long-duration bonds when it is steep

### Type 2 — Selection Strategies

A selection strategy operates on a basket of instruments simultaneously and answers the question: **which of these assets should I be holding right now?**

Instead of a binary yes/no, the signal produces a ranking score for every asset in the basket. You sort all assets by score, pick the top fraction (say the top third), hold them with equal weight, and rebalance periodically. You are always invested — you are just choosing which subset of the basket to hold.

Examples of selection signals:
- **Sector Momentum**: rank the 11 US sector ETFs by their trailing 3-month return; hold the top 4. The idea is that recent winners in one sector (e.g. technology) tend to continue outperforming for a few months.
- **Commodity Carry**: rank commodities by their carry (the spread between spot and futures price, a proxy for whether the market is in backwardation or contango); hold the top ones.
- **Country CAPE Rotation**: rank country ETFs by their earnings valuation (cheapest countries tend to outperform expensive ones over a multi-year horizon); hold the cheapest few.

---

## 2. The Asset Universe

We test strategies on a universe of 68 Exchange-Traded Funds (ETFs) organised into 8 thematic baskets. ETFs are used because they are liquid, cheap to trade, have long price histories, and each one provides transparent exposure to a well-defined asset class or market segment.

The baskets are:

**US Equity (Broad)** — SPY (S&P 500), QQQ (Nasdaq), IWM (Russell 2000 small caps), MDY (S&P 400 mid caps). The main large US equity indices. Used primarily as timing strategy targets.

**US Sectors** — The 11 SPDR sector ETFs: XLK (Technology), XLF (Financials), XLE (Energy), XLV (Healthcare), XLI (Industrials), XLP (Consumer Staples), XLY (Consumer Discretionary), XLU (Utilities), XLB (Materials), XLRE (Real Estate), XLC (Communication). These break the S&P 500 into its constituent industry groups, which is the natural universe for sector rotation/momentum strategies.

**US Factor ETFs** — IWF (Growth), IWD (Value), IWM (Size), USMV (Minimum Volatility), MTUM (Momentum), PKW (Buyback), DVY (Dividend Yield). Factor ETFs each represent a systematic tilt toward a specific academic risk premium. Used for factor rotation strategies.

**US Factor + Quality** — Same as above plus QUAL (Quality). Used specifically for regime-based factor rotation.

**Real Assets** — VNQ (US REITs), VNQI (International REITs), AMLP (Energy Pipelines/MLPs), XLRE (Real Estate sector). Hard assets with income characteristics.

**US Bonds** — TLT (20+ year Treasuries), IEF (7-10 year Treasuries), SHY (1-3 year Treasuries), TIP (TIPS/inflation-linked), BIL (T-Bills/cash), LQD (Investment Grade Corporate), HYG (High Yield Corporate). The US fixed income spectrum from cash to long-duration to credit.

**International Bonds** — EMB (Emerging Market bonds in USD), BNDX (International bonds hedged). Small basket for carry and trend strategies.

**Commodities** — GLD (Gold), SLV (Silver), DBC (Commodity index), USO (Oil), UNG (Natural Gas), GDX (Gold miners), PDBC (Diversified commodity). Used for commodity trend and carry strategies.

**EM Country ETFs** — EEM (broad EM), INDA (India), EWZ (Brazil), EWJ (Japan), EWG (Germany), EWU (UK), EWA (Australia), EWC (Canada), EWP (Spain), EWI (Italy), EWL (Switzerland). Country-level equity exposure used for cross-country momentum and valuation rotation.

All price data covers the period **2016 to 2026** at daily granularity and is stored locally as CSV files. The 2016 start date reflects when most of these ETFs have reliable, clean data. All strategies are backtested in-sample over this period.

---

## 3. The Three-Step Pipeline

Every strategy goes through three steps before we consider it validated. The three steps are not just different analyses — they represent three different tests of whether the signal is real. Passing step 1 is necessary but far from sufficient.

```
Step 1: Backtest
        ↓
Step 2: Multi-Asset Expansion
        ↓
Step 3: Implementation
```

---

### Step 1 — Backtest

**The question being answered**: Does this signal have predictive power? And if so, what are the best parameter settings?

**What data goes in**: Daily price data for one asset (Type 1) or one basket of assets (Type 2). The full 2016–2026 history.

**What comes out**: A set of "canonical" parameters (the best settings for the signal), a statistical verdict (STRONG / MODERATE / WEAK / NOT SIGNIFICANT), and performance metrics (Sharpe ratio, annualised return, maximum drawdown).

#### The grid search

Most signals have free parameters — numbers that you have to set. The Bollinger Band strategy needs three: how many days to look back when computing the moving average, how many standard deviations wide to set the bands, and the maximum number of days to hold a position after entry. A sector momentum strategy needs: how many months to look back when computing momentum scores, what fraction of the basket to hold (top 3? top 5? all 11?), and how often to rebalance.

There is no single correct value for any of these. Different values produce different results. If you just try a few values by hand and pick the one that looked best, you are almost certainly overfitting — you have found a combination that happened to work in this specific historical period but has no reason to work going forward.

The grid search solves this by being exhaustive and transparent. We define a grid of candidate values for every parameter (for example: lookback = 3, 6, 9, or 12 months; top fraction = 10%, 25%, 33%, 50%, or 100%; rebalance = monthly, quarterly, or every 6 months). We then run the full strategy for every single combination — if there are 4 × 5 × 3 = 60 combinations, we run 60 complete backtests. Every combination produces a Sharpe ratio and a significance verdict. The full grid is saved to a CSV so it can be inspected.

#### The rebalancing baseline (Type 2 only)

For selection strategies, we always include `top_pct = 1.0` in the grid. This means: hold all assets in the basket with equal weight and rebalance on schedule. This is not buy-and-hold — it is periodic rebalancing with no selection. A rebalancing-only strategy actually generates a small return through mechanical mean reversion (you are automatically selling assets that went up more than average and buying those that went up less, which tends to be slightly positive over time).

The significance of this baseline is: a selection strategy that cannot outperform `top_pct=1.0` has no selection skill. All its returns could be explained by the rebalancing effect alone. We are specifically looking for strategies where the selection signal adds value on top of that baseline.

#### What happens day by day in the backtest

**For a Type 1 strategy** (e.g. Bollinger Band on SPY):
Each day the code computes the moving average of SPY's price over the past N days and the bands at ±K standard deviations around it. When SPY's price falls to the lower band, that is the entry signal: we record a buy at today's closing price. We then hold the position, marking it to market each day, until either the price reaches the upper band (the exit signal) or the maximum hold period has elapsed. Each trade is recorded with its entry date, exit date, entry price, and exit price. After processing the full 10-year history this way, we have a complete list of trades and from that a daily equity curve.

**For a Type 2 strategy** (e.g. Sector Momentum):
On each rebalance date (say the last trading day of each month), the code computes the trailing 6-month return for each of the 11 sector ETFs. It ranks them from highest to lowest. If `top_n = 3`, it selects the top 3. It then assigns an equal weight of 1/3 to each of those 3 ETFs and holds those weights until the next rebalance date. Between rebalance dates the portfolio drifts as prices move — the weights change slightly day to day because different ETFs move by different amounts. On the next rebalance date the ranking is recomputed, the new top 3 is selected, and if the composition changed, the old holdings are sold and new ones bought (incurring transaction costs). This process produces a daily equity curve for the full 10-year period.

#### Statistical significance tests

Once we have the monthly return series from the backtest, we run the 3-gate significance battery (described in detail in Section 4). A signal must pass at least 2 of the 3 gates to be considered worth pursuing further. Passing 3/3 is labelled STRONG.

#### Stability scoring

Before we pick the best parameters, we compute a stability score for every grid combination. The idea is that a good parameter set should not only have a high Sharpe ratio — it should be surrounded by nearby parameter sets that also have high Sharpe ratios. If the best-looking combo has Sharpe 0.9 but its immediate neighbours (slightly longer lookback, slightly different top_pct, slightly different rebalance frequency) all have Sharpe 0.3–0.4, that 0.9 is almost certainly a lucky fluke — a narrow spike in parameter space that will not repeat out of sample.

The stability score is computed as: (average Sharpe of all ±1 neighbours) ÷ (this combo's Sharpe). A score near 1.0 means all neighbours are almost as good — you are on a stable plateau. A score well below 1.0 means this combo is an isolated peak — suspicious and deprioritised.

#### Picking canonical parameters

After the grid runs, the researcher reviews the table of combinations sorted by Sharpe, filtered to those passing ≥2/3 significance gates, with stability scores shown. The canonical parameters are then **chosen by hand** — not picked by automated argmax. The researcher looks at: is the Sharpe materially better than the top_pct=1.0 baseline? Is the stability score reasonable? Does the performance make economic sense (e.g., is a 1-day rebalance frequency winning only because of look-ahead or data artefacts)?

These canonical parameters are then **locked permanently**. They do not change in step 2 or step 3.

**Files saved after Step 1:**
- `results/{strategy}_signal.csv` — daily signal values or portfolio weights
- `results/{strategy}_trades.csv` — one row per trade or rebalance event
- `results/{strategy}_summary.json` — canonical params, Sharpe, CAGR, max drawdown, significance verdict

---

### Step 2 — Multi-Asset Expansion

**The question being answered**: Does this signal generalise, or did it only work on the specific asset/basket we happened to use in Step 1?

**What changed in v2**: Parameters are selected **per basket** in this step, not frozen globally from Step 1. Step 1 established that the signal concept works on one instrument or basket — a proof of concept. Step 2 is where the actual basket-level parameter selection happens. Different baskets are allowed (and expected) to have different canonical parameters, because a momentum signal that works best at a 6-month lookback in US sectors might work best at a 9-month lookback in EM country ETFs.

#### Why this step matters

The fundamental danger in quantitative research is finding a pattern that is specific to one dataset rather than a general market phenomenon. If sector momentum works beautifully on US sector ETFs, that's promising, but it could be because the 2016–2026 period happened to be particularly favourable for sector rotation in the US. Maybe technology just dominated for most of the decade, and any strategy that overweighted tech would have looked smart.

The way to test this is to run the signal on structurally different markets — European country ETFs, factor ETFs, commodity ETFs, bond ETFs. If the momentum signal works in US sectors AND in EM country ETFs AND in factor ETFs, it is much harder to explain as luck. The underlying phenomenon — recent winners tend to continue outperforming over a medium-term horizon — appears to be a real, persistent market effect that shows up across asset classes and geographies.

#### For Type 1 — Per-basket grid search

For each basket of instruments, we run a full grid search across **all instruments in that basket simultaneously**. For every parameter combination in the grid, we apply the signal to each instrument independently and collect that instrument's Sharpe ratio. We then compute the **median Sharpe across all instruments in the basket** for that combination. The combination with the highest median Sharpe becomes the basket's canonical parameters.

Using the median (rather than the mean) makes the selection robust to outlier instruments — one asset with an anomalously lucky run under a particular parameter setting does not inflate the aggregate score. Because each basket optimises independently, different baskets can (and typically do) end up with different canonical parameters.

The result for each basket is: a set of canonical parameters, and a list of **passing instruments** — those where the timing signal with those parameters shows statistically significant positive returns. The pass rate is itself informative: 19/21 is strong evidence of a genuine broad effect; 4/15 suggests the effect is real but selective; 0/15 means we do not proceed with that basket.

#### For Type 2 — Per-basket grid search

For each eligible basket, we run a full grid search on that basket independently. For every parameter combination, we run the selection strategy on the basket and record its Sharpe ratio and significance verdict. The combination with the highest Sharpe (subject to significance and stability filters) becomes that basket's canonical parameters.

As with Type 1, different baskets optimise independently. `us_sectors` might find its best momentum lookback at 3 months while `em_country` finds 9 months. Both are valid — the optimisation is over the basket as a unit. If the signal works on `us_sectors`, `us_factor`, AND `em_country` — each with its own canonical parameters — that is much stronger evidence than it working only on the original basket from Step 1.

#### Confirming the strategy effect is real — Binomial test

After selecting basket-level canonical parameters and identifying the passing instruments, we run a **binomial test** to guard against the multiple testing problem.

The issue: with N instruments and 48 parameter combinations in the grid, you would expect roughly 5% to pass significance gates at p<0.05 by pure chance — about 27 false positives if testing 11 sectors × 48 combos. Simply counting how many instruments pass is not sufficient.

The binomial test corrects for this. Under H₀ (no strategy edge), each instrument passes significance gates by chance with probability p₀ = 0.05. If k instruments actually passed out of N tested, we compute:

**P(Binomial(N, 0.05) ≥ k)**

If this p-value < 0.05, we conclude **STRATEGY EXISTS** for that basket — the pass rate is too high to be explained by chance alone. If the p-value ≥ 0.05, the pass rate is consistent with random noise and we do not proceed with that basket. This is the final gate before a basket is cleared for implementation.

**Files saved after Step 2:**
- `results/{strategy}_multiasset_grid.csv` — per-basket, per-combo: Sharpe, gates passed, stability
- `results/{strategy}_multiasset_summary.json` — list of passing baskets/instruments with gate-level detail

---

### Step 3 — Implementation

**The question being answered**: After realistic transaction costs and position sizing, how much does this strategy actually return, and what would an investment in it look like?

This step converts the validated signal into a realistic daily equity curve — the same kind of chart you would see in a fund's performance report. It shows day-by-day what would have happened to $100,000 invested in this strategy.

#### What a sleeve is

Each passing basket (from a Type 2 strategy) or each passing instrument (from a Type 1 strategy) becomes its own **sleeve** — an independently managed sub-portfolio. A sleeve runs the strategy with $100,000 of starting capital, applies transaction costs every time it trades, and produces a daily equity time series showing how that $100,000 evolved.

The reason sleeves are kept independent is transparency and modularity. Each sleeve can be evaluated on its own merits. The combined portfolio can be assembled later by deciding how much capital to allocate to each sleeve.

#### How position sizing works

For **Type 1 (Timing)**, each instrument in the basket gets its own independent **1/N sleeve** of the basket's capital, where N is the number of instruments in the basket. Each instrument's sleeve runs its own equity curve in isolation: fully invested in that instrument when the signal fires, flat in cash otherwise. The N daily equity curves are summed to produce the basket equity curve.

This structure is correct for timing strategies because entries are staggered — each instrument triggers independently on its own day based on its own signal. Pooling all instruments into a shared capital pool would make the effective cohort size nearly always 1 (only one instrument happens to enter on any given day), producing an ~85% allocation per trade regardless of how many concurrent trades are open, which overleverages the portfolio and can drive equity negative.

For **Type 2 (Selection)**, multiple instruments enter together on the same periodic rebalance date, so shared-pool sizing is meaningful. The code allocates `allocation / top_n` of capital to each position. With 85% allocation and 3 holdings, each position gets 28.3% of the portfolio. Transaction costs are applied to every position that changes at each rebalance event — both the ones being sold and the new ones being bought.

The core function for Type 2 is `build_basket_equity()`. The tricky edge case it handles is: what happens when one position is entered at the start of the month and another exits mid-month, so for a few days you have 2 open positions instead of 3? The function tracks all open positions on each day, computes their current market value, sums them up, and adds the uninvested cash. This mark-to-market calculation happens every single day for the full 10-year period. Note: `build_basket_equity()` is **not** appropriate for Type 1 timing strategies — use the 1/N independent sleeve approach described above.

#### Capital allocation variants

For each sleeve we compute two variants to see which is better:
- **simple_85**: deploy 85% of capital into positions, keep 15% in cash
- **simple_100**: deploy 100% into positions

We also compute a **vol-targeted** variant that dynamically scales position sizes up or down to target a specific annualised volatility (10%). In theory this gives a smoother, more consistent risk profile. In practice, for strategies that rebalance monthly or less frequently, this variant consistently underperforms because the 6-month trailing volatility estimate is too noisy — by the time the volatility calculation has registered that a period was turbulent, the turbulence is often already over.

#### Combining sleeves

Once each sleeve is computed independently, they are combined into a single strategy-level equity curve. The combination rule is: **equal capital weight, 1/N per sleeve**. If 3 baskets passed for Industry Trend (us_sectors, us_factor, em_country), each sleeve gets 1/3 of the total capital.

The combined result typically shows better risk-adjusted returns than any individual sleeve because the sleeves are not perfectly correlated. US sectors and EM country ETFs respond differently to the same market event — US sectors are sensitive to domestic earnings and Fed policy, EM country ETFs are sensitive to the dollar, commodity prices, and local growth. Holding both reduces the overall volatility of the combined portfolio without proportionally reducing the returns.

**Files saved after Step 3:**
- `results/{strategy}_daily_equity/{sleeve_name}_{variant}.csv` — daily equity curve per sleeve and variant
- `results/{strategy}_implementations.json` — Sharpe, CAGR, MaxDD for every sleeve and variant

---

## 4. Statistical Significance Tests (The 3-Gate Battery)

Every strategy, at both the Backtest and Multi-Asset Expansion stages, must pass a 3-gate statistical significance battery before we call it validated. All three tests are run on the **monthly return series** from the strategy's equity curve. Requiring monthly returns (rather than daily) means we are testing the strategy's ability to generate sustained outperformance over multi-week horizons, not noise that averages away.

The reason for running three different tests instead of one is that each test makes different assumptions, and they cover different failure modes.

### Gate 1 — One-Sided t-test

This is the classical statistical test for whether the mean of a series is greater than zero. It asks: given the mean monthly return and the variability of those returns, what is the probability of observing results this good if the true mean were actually zero?

The test is one-sided — we only care whether returns are significantly positive, not significantly negative. Pass condition: p-value < 0.05 (less than 5% probability that results this good would appear by chance if there were no edge).

**Assumption**: monthly returns are approximately normally distributed (bell-curve shaped). Financial returns are not perfectly normal — they have fat tails and occasional large outliers — which is why this test alone is not sufficient.

### Gate 2 — Bootstrap Sharpe (5th Percentile)

This test asks: if we drew a different 10-year sample of returns from the same distribution, would the Sharpe ratio still be positive? It uses no distributional assumptions — it resamples from the actual observed returns.

The procedure: randomly draw N returns from the observed N-month series (with replacement — so the same month can appear more than once in the resampled series). Compute the Sharpe ratio of this resampled series. Repeat 10,000 times. Look at the 5th percentile of the 10,000 bootstrap Sharpe ratios.

Pass condition: the 5th percentile > 0. This means: even in the worst 5% of alternative historical paths, the Sharpe ratio would still have been positive. If the strategy's performance is fragile — heavily dependent on a few very good months in a specific year — the bootstrap distribution will spread wide and the 5th percentile will be negative or near zero.

### Gate 3 — Sign Permutation Test

This test asks: could the positive Sharpe ratio arise purely from the pattern of which months had positive vs negative returns, without any predictive signal at all?

The procedure: take the absolute values of all monthly returns (removing the sign). Randomly assign positive or negative signs to each one, 10,000 times. Compute the Sharpe ratio of each randomly-signed series. Measure what fraction of the 10,000 random series achieved a Sharpe ratio as high as the actual observed one.

Pass condition: p-value < 0.05. This means fewer than 5% of random sign assignments produce a Sharpe as high as what we observed, which suggests the actual pattern of positive/negative months is non-random.

**Why this is a strong test**: if the strategy's positive Sharpe comes from a handful of unusually large positive months that happened to be correctly predicted by the signal, the permutation test will detect this. If the strategy correctly and consistently distinguishes good months from bad months, the permutation test will confirm it.

### Verdict Labels

| Gates passed | Label | What it means |
|---|---|---|
| 3/3 | **STRONG** | All three independent tests confirm genuine edge. High confidence. |
| 2/3 | **MODERATE** | Likely a real effect but some fragility. Worth implementing with reduced conviction. |
| 1/3 | **WEAK** | Borderline at best. Do not implement. |
| 0/3 | **NOT SIGNIFICANT** | No evidence of edge. Discard. |

---

## 5. Shared Code Infrastructure

Rather than each strategy implementing these mechanics from scratch, we have a set of shared utilities used across all strategies.

**`long_term/_backtest_utils.py`** contains: the three significance test functions, a function to compute portfolio metrics (Sharpe, CAGR, max drawdown) from a daily equity curve, a function to convert a daily weight series into a daily equity curve (used by all Type 2 strategies), and a function to convert a signal into a list of trades (used by Type 1 strategies).

**`shared/implementations.py`** contains: the `build_basket_equity()` function for converting a trade list into a realistic daily equity curve with simultaneous position handling, plus simpler per-trade sizing functions for sequential (non-overlapping) positions.

**`data/data.py`** is the Alpaca API data fetcher — used for initial data download. Price data is stored locally as CSVs so backtests do not depend on live API access.

**`data/wrds_data.py`** is the loader for WRDS/CRSP/Compustat academic data stored locally as Parquet files. Used by the stock-level strategies. Also contains a yield curve loader.

---

## 6. Current Strategy Results

### Type 1 — Timing Strategies

| Strategy | Signal | Assets tested | Pass rate | Combined Sharpe | Status |
|---|---|---|---|---|---|
| **Bollinger Band** | Mean reversion: buy lower band, sell upper band | 21 equity ETFs | 19/21 | 0.671 | ✅ STRONG |
| **Donchian Channel** | Breakout: buy N-day high, exit on M-day low | 21 equity ETFs | 19/21 | 1.034 | ✅ STRONG |
| **Turn-of-Month** | Calendar: long last 2 + first 3 days of month | 15 equity ETFs | 4/15 | 0.800 | ✅ MODERATE |
| **Credit Carry** | Bond: hold bond with highest 12m return vs T-bill | 6 bond ETFs | 1/6 | 4.7* | ✅ MODERATE |
| **Yield Curve Duration** | Rates: short-duration when curve flat/inverted | 7 bond ETFs | 2/7 (SHY, BIL) | — | ✅ STRONG |
| **Bond Duration Carry** | Rates: long HY credit when real yield positive | 7 bond ETFs | 1/7 (HYG) | — | ✅ MODERATE |
| **Sentiment Timing** | VIX: scale equity exposure by VIX level | 15 equity ETFs | 2/15 | 0.469 | ⚠️ WEAK |
| **Overnight Premium** | Hold close-to-open return window | 15 equity ETFs | 0/15 | — | ❌ FAILED |
| **REIT Dividend Carry** | Dividend yield proxy for REIT carry | 4 REIT ETFs | 0/4 | — | ❌ FAILED |
| **Congress Trade** | Replicate congressional stock trades | 1 (SPY proxy) | — | — | ⏸️ DATA MISSING |
| **Insider Buying** | Follow insider purchase filings | Stocks | — | — | ⏸️ DATA MISSING |
| **BAB** | Long low-beta, short high-beta | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **QMJ** | Long quality stocks, short junk | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **Low Volatility** | Long lowest-vol decile | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **PEAD** | Drift after positive earnings surprise | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **Short Interest Contrarian** | Long high-short-interest stocks | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **US Cross-Sectional Momentum** | Long top 12-1m momentum decile | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **US Earnings Momentum** | Long stocks with rising EPS estimates | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **US Return Seasonality** | Long stocks with strong same-month historical return | CRSP stocks | — | — | ⏸️ NEEDS CRSP |
| **US Shareholder Yield** | Long high buyback + dividend yield | CRSP stocks | — | — | ⏸️ NEEDS CRSP |

*Credit carry Sharpe is high (4.7) but the CAGR is only 0.9% — the strategy is essentially "stay in T-bills vs long bonds," generating near-risk-free returns with very low volatility.

### Type 2 — Selection Strategies

| Strategy | Signal | Basket(s) | Sleeves | Combined Sharpe | CAGR | MaxDD | Status |
|---|---|---|---|---|---|---|---|
| **Cross-Asset Carry** | Sharpe-like carry score, 2ME rebal | 13-ETF mixed | 1 | 0.975 | 11.2% | −17.4% | ✅ STRONG |
| **Country CAPE Rotation** | Cheapest countries by trailing return (CAPE proxy) | EM country | 1 | 0.859 | 17.7% | −34.5% | ✅ STRONG |
| **Quality Profitability** | RMW-gated 18m momentum (quality filter) | US equity broad | 1 | 0.824 | 13.2% | −26.4% | ✅ STRONG |
| **EM/DM Carry** | EM vs DM 9m return spread; binary regime | EM + DM | 1 | 0.801 | 14.7% | −30.5% | ✅ STRONG |
| **GTAA** | SMA-300 momentum filter, 4 baskets | Sectors, bonds, commodities, real assets | 4 | 0.810 | 9.7% | −20.8% | ✅ STRONG |
| **Regime Factor Rotation** | GMM 3-regime on factor returns | US factor quality | 1 | 0.779 | 10.8% | −30.3% | ✅ STRONG |
| **Sector Momentum** | 3m trailing momentum, 6ME rebal | US sectors, US factor | 2 | 0.777 | 11.7% | −26.9% | ✅ STRONG |
| **Bond Trend** | 3m momentum in bond ETFs, 2ME rebal | Bonds US, bonds intl | 2 | 0.703 | 3.4% | −12.1% | ✅ STRONG |
| **Quantitative Momentum** | Top-decile 12-1m momentum in S&P 500 stocks | S&P 500 (CRSP) | 1 | 0.610 | 12.7% | −50.1% | ✅ STRONG |
| **Industry Trend** | 12m momentum, top 33%, 6ME rebal | Sectors, factor, EM country | 3 | 0.596 | 8.3% | −30.5% | ✅ STRONG |
| **Commodity Carry** | Backwardation/contango carry signal | Commodities | 1 | 0.554 | 9.7% | −32.3% | ✅ MODERATE |
| **Commodity Trend** | Momentum on commodities + real assets | Commodities, real assets | 2 | 0.447 | 6.5% | −30.9% | ⚠️ MIXED |
| **Regime Factor Rotation** | Macro regime + factor ETF selection | US factor quality | 1 | 0.779 | 10.8% | −30.3% | ✅ STRONG |

---

## 7. Why Certain Strategies Failed or Are Incomplete

**Overnight Premium** — The original academic finding (Cooper et al., 2008) was that stocks earn most of their returns overnight (close to open) rather than during the day. This edge has been almost entirely arbitraged away by high-frequency traders and index arbitrageurs since around 2010. Our test on 15 ETFs over 2016–2026 confirms: 0/15 pass significance. We did not proceed.

**REIT Dividend Carry** — The carry signal requires knowing dividend yield, which for ETFs is not cleanly extractable from price data alone (total return indices smooth it differently than price-only). The proxy used was too noisy to generate a reliable signal.

**Sentiment Timing** — The VIX-based sizing strategy (overweight equities when VIX is low, underweight when VIX is high — or the reverse, as a contrarian signal) only passed on QQQ and XLK. More importantly, in 2022 the VIX spiked at the same time as large losses — meaning a strategy that bought on high VIX would have been overweight equities precisely when they were falling the hardest. The strategy was considered too inconsistent to use broadly.

**9 CRSP-Dependent Strategies** — BAB, QMJ, Low Volatility, PEAD, Short Interest, and the four academic factor strategies require individual stock data (returns, book values, earnings, short interest, beta) at the stock level. Our CRSP/Compustat data is on disk but the stock-level backtest infrastructure — the code to loop over thousands of stocks, construct decile portfolios, and run the signal — has not yet been built. These strategies are marked as stubs.

**Commodity Trend** — The commodities basket (GLD, SLV, DBC, USO, UNG, GDX, PDBC) shows very weak momentum Sharpe (0.21). Raw commodities are highly mean-reverting at the 3–12 month frequencies where equity momentum works well. The trend signal on the `real_assets` basket (REITs + MLPs) is stronger (0.67) and we keep that sleeve. For the commodities basket itself, the carry signal (Sharpe 0.55) works better than the trend signal, so we use carry there instead.

---

## 8. Parameter Selection Safeguards

We take five explicit steps to prevent data-mining and overfitting:

**Express selection size as a fraction**: Instead of picking `top_n = 3`, we set `top_pct = 0.33` (hold the top third). This means the parameter means the same thing whether the basket has 5 or 15 instruments, and results generalise across basket sizes.

**Always include the rebalancing baseline**: `top_pct = 1.0` (hold everything) is always in the grid. A selection strategy that cannot beat equal-weight rebalancing has no signal — only the rebalancing premium.

**Compute stability scores**: Prefer parameter combos that sit on stable plateaus over isolated peaks. A Sharpe of 0.85 with stability 0.95 is more trustworthy than a Sharpe of 0.95 with stability 0.35.

**Use median cross-instrument Sharpe for parameter selection**: In Step 2, parameter combinations are ranked by their **median Sharpe across all instruments in the basket** — not the mean and not the single best instrument. This makes selection robust to outlier assets and avoids the bias of picking parameters tuned to one instrument's luck. For Type 2 strategies the basket runs as a unit, so the Sharpe is computed over the basket equity curve directly and no within-basket median is needed.

**Manual canonical parameter selection**: The final parameter choice is made by the researcher, not by automated argmax. The researcher reviews the grid, stability scores, economic plausibility, and significance before locking in parameters.

---

## 9. Remaining Work

### Must do (blocking real allocation)

**CRSP stock-level infrastructure**: The CRSP daily security data is on disk (`data/wrds/03_na_security_daily.parquet`). What does not exist yet is a stock-level backtest runner that can loop over thousands of securities, rank them by any signal, form decile portfolios, and apply the same 3-gate tests. Building this would unlock 9 strategies (BAB, QMJ, Low Vol, PEAD, Short Interest, Cross-Sectional Momentum, Earnings Momentum, Seasonality, Shareholder Yield).

**Real FRED rates**: The yield curve strategies currently use synthetic rates derived from ETF prices (accurate to ~0.1–0.3%). Real FRED data (DGS10, DGS2) is downloadable from fred.stlouisfed.org — the sandbox environment cannot reach it, but a manual download would replace the synthetic rates with the actual series.

**Shiller CAPE per country**: `country_cape_rotation` currently uses inverse trailing return as a proxy for CAPE — which works as a contrarian signal but is not a true valuation measure. Real CAPE data by country (from StarCapital or Research Affiliates) would give this strategy a fundamentally grounded signal.

**Portfolio-level construction**: All the individual strategies have been validated in isolation. The next major step is combining them into a portfolio — deciding how much capital to allocate to each strategy sleeve, ensuring non-overlapping risks, and computing the combined equity curve. A `greedy_optimizer.py` script already exists in `multi_asset_expansion/` and can be used as the starting point.

### Should do (improvements)

**Extend history before 2016**: Most ETFs have data back to 2003–2010. Extending the backtest history would dramatically improve statistical power for seasonal strategies and reduce the "single regime" risk (everything in our sample happened during post-GFC QE → normalisation → rate hike cycle).

**VIX-lagged sentiment**: Instead of sizing up on high VIX in the same period, test a 1-month lag (high VIX in month t → overweight in month t+1). This avoids the 2022 problem where VIX and losses peaked simultaneously.

**Intraday data for overnight premium**: The test with daily open/close prices may understate the true overnight return. Intraday data (e.g., first and last tick of the day) would give a cleaner signal and might show a residual edge that daily data misses.

### Cleanup

**Consolidate significance functions**: Two copies exist (`shared/significance.py` and `long_term/_backtest_utils.py`). Should be one.

**Archive legacy files**: The original `multi_asset_expansion/` per-strategy scripts predate the new `timing/` and `selection/` folder structure. They can be archived once the new multiasset scripts in each strategy folder are confirmed working.

**Clear pycache**: `__pycache__` and `.ipynb_checkpoints` directories scattered throughout. Safe to delete entirely.

---

## 10. Multi-Asset Expansion TODO

These strategies are blocked from Step 2 expansion for specific, known reasons. Each entry states what is missing, why the ETF workaround is insufficient or degenerate, and what would unblock the work.

### Needs Alternative Data

**congress_trade_for_trade** — The strategy replicates individual congressional stock trades as disclosed in STOCK Act filings. No ETF price series encodes this information; the signal is inherently stock-level. The natural ETF expansion would aggregate net congressional buy/sell activity by GICS sector and use it as a timing or rotation signal on the 11 SPDR sector ETFs — if Congress is net-buying Energy and net-selling Financials, rotate accordingly. This is theoretically valid and would fit cleanly into the `us_sectors` basket. The blocker is data: congressional trade disclosures at the individual-filing level require the Quiver Quant congressional trading API (or a scrape of house.gov disclosures), which we do not currently have. Once that feed is available, building the sector-aggregated signal is straightforward.

**insider_buying** — The strategy follows net insider purchases from SEC Form 4 filings, which are stock-level disclosures. As with congress trades, the ETF expansion would aggregate net insider buying by sector and generate a rotation signal on `us_sectors`. The blocker is EDGAR Form 4 data at the individual-trade level; a sector-level aggregate version is obtainable from several data vendors. One consideration: the VIX-sensitivity version of this strategy (scaling equity exposure when insider buying spikes during high-VIX drawdowns) overlaps substantially with `sentiment_timing`, which already covers that mechanism using freely available VIX data. The insider-buying version is only worth prioritising with the real filing data — the VIX proxy alone adds nothing that `sentiment_timing` does not already capture.

### Needs CRSP Stock Infrastructure

The six strategies below require individual stock data that our ETF universe cannot proxy. The conceptual problem is not missing data files — CRSP daily security data (`data/wrds/03_na_security_daily.parquet`) and the CCM bridge to Compustat are on disk. What does not exist is the **stock-level backtest runner**: code that loops over thousands of CRSP securities, computes per-stock signals, sorts into decile portfolios, and passes the resulting return series through the 3-gate battery. Building that infrastructure once unblocks all six strategies simultaneously.

**bab_long_short** — Betting Against Beta requires a daily beta estimate for every stock, computed against the market return, using the CRSP daily return file. An ETF version (rank factor ETFs by their beta to SPY) is degenerate: in a basket of seven factor ETFs the ranking is nearly deterministic and changes rarely. The strategy only makes sense at the stock level.

**pead_earnings_drift** — Post-earnings announcement drift requires knowing each stock's EPS announcement date and the magnitude of the EPS surprise. That comes from Compustat quarterly earnings linked via the CCM bridge. There is no ETF-level equivalent; an ETF's price already reflects the average of hundreds of earnings events, smoothing out precisely the individual announcement effect the strategy exploits.

**qmj_long_short** — Quality Minus Junk ranks stocks by composite profitability (return on equity, gross profit, earnings stability). At the stock level this is a distinct signal from our existing `quality_profitability` ETF strategy, which uses RMW factor exposure as a regime gate rather than direct stock-level accounting metrics. At the ETF level, however, the two strategies collapse into the same thing — both end up selecting QUAL and USMV — so an ETF expansion of QMJ adds no new information. Stock-level Compustat data (quarterly ROE, gross margins) is the unblocking requirement.

**reit_dividend_carry** — This strategy's carry signal is the income return component of REIT total return, available in CRSP as the `dlyincret` field (daily income return). ETF-level REIT dividends can be partially reconstructed from distribution history, but the resulting series is too noisy for a carry signal — as confirmed by the Step 1 failure of the ETF-based version. The CRSP income return field at the individual REIT stock level is the correct input.

**us_earnings_momentum** — This strategy ranks stocks by standardised unexpected earnings (SUE scores) — the difference between reported EPS and analyst consensus, scaled by forecast dispersion. SUE is a Compustat-level construct computed per stock per quarter. ETF prices already aggregate across hundreds of earnings events and cannot replicate this signal. Unblocked by Compustat quarterly EPS data via the CCM bridge, plus the stock-level backtest runner.

**short_interest_contrarian** — This strategy goes long stocks with anomalously high short interest, betting on short squeezes. Short interest data is in Compustat's supplemental short interest tables (bi-monthly settlement dates). There is no ETF-level equivalent; ETF short interest reflects fund-level borrowing demand, not the stock-level short squeeze dynamics the strategy targets. Unblocked by Compustat short interest tables and the stock-level runner.

### Insufficient ETF History

**us_return_seasonality** — This strategy buys stocks in months where their own historical same-month return was strong (e.g., gold mining stocks tend to outperform in January). The signal requires estimating a reliable per-asset mean return for each of the 12 calendar months. With monthly data, that is roughly N/12 observations per calendar slot. Our ETF data starts in 2016 (~10 years, ~10 observations per slot), which is far too few: the standard error on a 10-observation mean is large enough to make the ranking across assets essentially noise. The academic literature establishes this strategy requires at least 20 years of monthly history to achieve stable calendar-slot estimates. Most of our ETFs do not have clean data before 2016. The unblocking options are: extend the price history for ETFs with earlier inception dates (many sector and factor ETFs have data back to 2000–2006), or implement the strategy at the stock level using CRSP, where 40+ years of monthly data are available.

### Portfolio A — Multi-Asset Expansion (Not Yet Done)

The seven Portfolio A strategies (ema_crossover, ibs_mean_reversion, intraday_momentum, vix_mean_reversion, orb, overnight, vwap_trend) have never been systematically expanded to multi-asset baskets. Each currently runs on a single fixed instrument (e.g. ema_crossover → QQQ only). The same v2 multi-asset framework used for Portfolio B strategies — per-basket grid search, binomial test to confirm strategy existence, and 1/N sleeves for timing strategies — should eventually be applied here.

Two strategies cannot be expanded under this framework: congress_s3_quiver relies on Quiver Quant congressional trade filing data and is inherently instrument-specific; vix_etn_dual is built around the VIX ETN universe (VXX, SVXY, and variants) and has no meaningful generalisation to arbitrary baskets. The remaining five rule-based strategies (ema_crossover, ibs_mean_reversion, intraday_momentum, vix_mean_reversion, vwap_trend, orb, overnight) are candidates for basket expansion once short-term OHLCV data for a broader instrument set is available.

---

### ETF Signal Is Degenerate

**low_volatility** — The strategy ranks assets by trailing realised volatility and goes long the lowest-volatility decile. At the stock level (CRSP universe of ~5,000 names) this is a meaningful ranking with substantial cross-sectional dispersion. Applied to our ETF baskets, the ranking is almost entirely predetermined: in the US factor basket, USMV (Minimum Volatility) always has the lowest realised volatility by construction — it is explicitly designed to minimise volatility. Ranking the basket always selects USMV. The strategy reduces to "always hold USMV," which is not a signal — it is a static allocation. The strategy is only meaningful at the stock level, where the volatility ranking is not mechanically determined by the fund's mandate. Unblocked by the CRSP stock-level runner.
