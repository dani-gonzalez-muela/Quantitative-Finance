"""
Multi-Asset Expansion Pipeline V2
Basket-level performance measurement.

For each (strategy, category_basket) pair:
  - Per-instrument strategies: run on each ticker, combine returns EW and InvVol
  - Portfolio strategies: run on basket tickers as universe, single equity curve

Outputs: results_basket.csv and basket_report.md
"""
import os, sys, zipfile, warnings
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from _shared.loaders_wrds import load_fred_rates

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────
# -- fable path bootstrap (Phase C fix) --
import os as _os, sys as _sys
_bd = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_bd, '.project_root')):
    _bp = _os.path.dirname(_bd)
    assert _bp != _bd, '.project_root not found'
    _bd = _bp
_sys.path.insert(0, _bd)
from _shared.paths import data_dir, data_file
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR)))
DATA_DIR    = data_dir('daily_tickers')
RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

MACROS_CSV  = data_file('macros', 'macros_daily.csv')
VIX_PARQUET = data_file('wrds_parquet', '15_cboe_vix.parquet')
FRED_ZIP    = os.path.join(data_dir('wrds_datasets_raw'), "THIRD PARTY [done]", "4. Federal Reserve [d]", "Interest Rates", "Daily", "e2fzdw3jkcrhxisb.csv.zip")
FF_CSV      = data_file('regime_factor_rotation_cache', 'ff_factors_monthly.csv')

TC_BPS = 0.0005
STARTING_CAPITAL = 100_000
MIN_DAYS = 252

# ─────────────────────────────────────────────────────────────
# V2: BASKET DEFINITIONS AND STRATEGY ELIGIBILITY
# ─────────────────────────────────────────────────────────────
CATEGORY_BASKETS = {
    "us_equity_broad":  ["SPY", "QQQ", "IWM", "MDY"],
    "us_factor":        ["IWF", "USMV", "MTUM", "IWD", "DVY", "PKW"],
    "us_sectors":       ["XLK", "XLC", "XLI", "XLV", "XLY", "XLF", "XLE", "XLU", "XLB", "XLP", "XLRE"],
    "bonds_us":         ["TLT", "IEF", "SHY", "TIP", "LQD", "HYG", "BIL", "BNDX"],
    "commodities":      ["GLD", "SLV", "USO", "GDX", "PDBC", "DBC", "UNG"],
    "em_regional":      ["EEM", "EWZ", "INDA", "EWW"],
    "intl_developed":   ["EFA", "EZU", "EWJ", "EWG", "EWU", "EWC", "EWA", "EWL", "EWQ", "EWI", "EWP", "EWD"],
    "intl_country_all": ["EWJ", "EWG", "EWU", "EWC", "EWA", "EWL", "EWQ", "EWI", "EWP", "EWD",
                         "EWZ", "EWY", "EWT", "MCHI", "TUR", "EEM", "INDA", "EWW"],
    "real_assets":      ["VNQ", "VNQI", "AMLP"],
    "currencies":       ["UUP", "FXE", "FXY", "FXA", "FXF", "FXB", "FXC"],
    "all_equity":       ["SPY", "QQQ", "IWM", "MDY", "IWF", "USMV", "MTUM", "IWD", "DVY", "PKW",
                         "XLK", "XLC", "XLI", "XLV", "XLY", "XLF", "XLE", "XLU", "XLB", "XLP", "XLRE",
                         "EFA", "EZU", "EWJ", "EWG", "EWU", "EWC", "EWA", "EWL", "EWQ", "EWI", "EWP", "EWD",
                         "EEM", "EWZ", "INDA", "EWW", "VNQ", "VNQI", "AMLP"],
    "gtaa_core":        ["SPY", "EFA", "EEM", "TLT", "GLD", "VNQ", "PDBC"],
    "all_68":           None,   # populated dynamically after data load
}

STRATEGY_ELIGIBLE_BASKETS = {
    "cross_asset_momentum":       ["all_68"],
    "cross_asset_carry":          ["all_68"],
    "gtaa":                       ["gtaa_core"],
    "low_volatility":             ["all_equity"],
    "sentiment_timing":           ["us_equity_broad", "us_factor", "us_sectors", "intl_developed", "em_regional"],
    "quality_timing":             ["us_equity_broad", "us_factor", "us_sectors", "intl_developed", "em_regional"],
    "turn_of_month":              ["us_equity_broad", "us_factor", "us_sectors", "real_assets"],
    "ibs_mean_reversion":         ["us_equity_broad", "us_factor", "us_sectors"],
    "vix_mean_reversion":         ["us_equity_broad", "us_factor", "us_sectors"],
    "us_cross_sectional_momentum":["us_equity_broad", "us_factor", "us_sectors"],
    "industry_trend":             ["us_sectors"],
    "country_cape_rotation":      ["intl_country_all"],
    "em_dm_carry":                ["intl_country_all", "em_regional"],
    "bond_trend":                 ["bonds_us"],
    "bond_duration_carry":        ["bonds_us"],
    "yield_curve_duration":       ["bonds_us"],
    "commodity_trend":            ["commodities"],
    "vol_overlay":                ["us_equity_broad", "us_factor", "us_sectors", "bonds_us",
                                   "commodities", "intl_developed", "em_regional", "real_assets"],
    "donchian_channel":           ["us_equity_broad", "us_factor", "us_sectors", "bonds_us",
                                   "commodities", "intl_developed", "em_regional", "real_assets"],
}

# Strategy type classification
PER_INSTRUMENT = {
    "ibs_mean_reversion", "donchian_channel", "vix_mean_reversion", "vol_overlay",
    "bond_trend", "commodity_trend", "turn_of_month", "sentiment_timing",
    "quality_timing", "yield_curve_duration", "bond_duration_carry",
}
PORTFOLIO_STRATS = {
    "cross_asset_momentum", "cross_asset_carry", "gtaa", "low_volatility",
    "industry_trend", "us_cross_sectional_momentum", "country_cape_rotation", "em_dm_carry",
}

# EM/DM classification for em_dm_carry generalisation
EM_COUNTRIES = {"EEM", "EWZ", "EWY", "EWT", "INDA", "MCHI", "EWW", "TUR"}
DM_COUNTRIES = {"EFA", "EZU", "EWJ", "EWG", "EWU", "EWC", "EWA", "EWL", "EWQ", "EWI", "EWP", "EWD"}

# ─────────────────────────────────────────────────────────────
# STEP 1: LOAD ALL 68 ETF CSVs
# ─────────────────────────────────────────────────────────────
print("Loading ETF price data...")
ETF_DATA = {}
AVAILABLE = []

for fname in sorted(os.listdir(DATA_DIR)):
    if not fname.endswith(".csv"):
        continue
    ticker = fname.replace(".csv", "")
    csv_path = os.path.join(DATA_DIR, fname)
    try:
        df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
        df = df.sort_index()
        df.index = pd.to_datetime(df.index)
        if len(df) >= MIN_DAYS:
            ETF_DATA[ticker] = df
            AVAILABLE.append(ticker)
    except Exception as e:
        print(f"  {ticker}: load error {e}")

CATEGORY_BASKETS["all_68"] = AVAILABLE
print(f"Loaded {len(AVAILABLE)} tickers: {AVAILABLE}\n")

# ─────────────────────────────────────────────────────────────
# STEP 2: LOAD AUXILIARY DATA
# ─────────────────────────────────────────────────────────────
print("Loading auxiliary data...")

# VIX
try:
    macros = pd.read_csv(MACROS_CSV, parse_dates=["date"], index_col="date").sort_index()
    VIX = macros["vix"].dropna()
    VIX = VIX[~VIX.index.duplicated(keep="last")]   # deduplicate dates
    print(f"  VIX from macros: {len(VIX)} rows, {VIX.index[0].date()} -> {VIX.index[-1].date()}")
except Exception as e:
    print(f"  macros VIX failed: {e}, trying parquet...")
    try:
        vix_df = pd.read_parquet(VIX_PARQUET)
        vix_df["date"] = pd.to_datetime(vix_df["date"])
        vix_df = vix_df.set_index("date").sort_index()
        VIX = vix_df["vix"].dropna()
        VIX = VIX[~VIX.index.duplicated(keep="last")]
        print(f"  VIX from parquet: {len(VIX)} rows")
    except Exception as e2:
        print(f"  VIX parquet also failed: {e2}")
        VIX = pd.Series(dtype=float)

# FRED
FRED = None
try:
    FRED = load_fred_rates()
except Exception as e:
    print(f"  FRED failed: {e}")

# FF Factors
FF = None
try:
    ff = pd.read_csv(FF_CSV, parse_dates=["Date"], index_col="Date").sort_index()
    ff.index = ff.index + pd.offsets.MonthEnd(0)
    FF = ff
    print(f"  FF factors: {len(FF)} rows, {FF.index[0].date()} -> {FF.index[-1].date()}")
except Exception as e:
    print(f"  FF factors failed: {e}")

print()

# ─────────────────────────────────────────────────────────────
# HELPERS (identical to pipeline.py)
# ─────────────────────────────────────────────────────────────

def build_equity(daily_ret, position, starting_capital=STARTING_CAPITAL):
    pos = position.reindex(daily_ret.index).fillna(0)
    delta = pos.diff().fillna(pos.iloc[0])
    tc = delta.abs() * TC_BPS
    strat_ret = pos.shift(1).fillna(0) * daily_ret - tc
    equity = starting_capital * (1 + strat_ret).cumprod()
    return equity.dropna()


# ─────────────────────────────────────────────────────────────
# STRATEGY FUNCTIONS — verbatim from pipeline.py
# ─────────────────────────────────────────────────────────────

def run_ibs(ticker):
    """IBS < 0.2 → buy next open; exit IBS > 0.8 or 3-day max hold."""
    df = ETF_DATA[ticker].copy()
    ibs = (df["close"] - df["low"]) / (df["high"] - df["low"])
    ibs = ibs.replace([np.inf, -np.inf], np.nan).fillna(0.5)

    df["open_ret"]  = df["open"] / df["close"].shift(1) - 1
    df["close_ret"] = df["close"].pct_change()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    days_held = 0
    equity = STARTING_CAPITAL
    eq_series = [STARTING_CAPITAL]

    for i in range(1, len(df)):
        prev_ibs = ibs.iloc[i - 1]
        cur_ibs  = ibs.iloc[i]

        if not in_pos:
            if prev_ibs < 0.2:
                in_pos = True
                days_held = 1
                day_ret = df["open_ret"].iloc[i] - TC_BPS
                equity *= (1 + day_ret)
            else:
                equity *= 1.0
        else:
            days_held += 1
            if cur_ibs > 0.8 or days_held >= 3:
                day_ret = df["close_ret"].iloc[i] - TC_BPS
                equity *= (1 + day_ret)
                in_pos = False
                days_held = 0
            else:
                day_ret = df["close_ret"].iloc[i]
                equity *= (1 + day_ret)

        eq_series.append(equity)

    return pd.Series(eq_series, index=df.index)


def run_donchian(ticker, period=20):
    """20-day channel breakout."""
    df = ETF_DATA[ticker].copy()
    upper = df["high"].rolling(period).max().shift(1)
    lower = df["low"].rolling(period).min().shift(1)
    close_ret = df["close"].pct_change()

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    for i in range(period, len(df)):
        if not in_pos:
            if df["close"].iloc[i] >= upper.iloc[i]:
                in_pos = True
        else:
            if df["close"].iloc[i] <= lower.iloc[i]:
                in_pos = False
        pos.iloc[i] = 1.0 if in_pos else 0.0

    return build_equity(close_ret, pos)


def run_vix_mr(ticker):
    """Enter when VIX 1-day spike > +15% AND VIX > 20. Exit when VIX < 20."""
    df = ETF_DATA[ticker].copy()
    close_ret = df["close"].pct_change()
    vix_aligned = VIX.reindex(df.index, method="ffill")
    vix_chg = vix_aligned.pct_change()

    entry_signal = (vix_chg > 0.15) & (vix_aligned > 20)
    exit_signal  = vix_aligned < 20

    pos = pd.Series(0.0, index=df.index)
    in_pos = False
    for i in range(1, len(df)):
        if not in_pos:
            if entry_signal.iloc[i - 1]:
                in_pos = True
        else:
            if exit_signal.iloc[i]:
                in_pos = False
        pos.iloc[i] = 1.0 if in_pos else 0.0

    return build_equity(close_ret, pos)


def run_vol_overlay(ticker, target_vol=0.10, window=21):
    """21-day realized vol. Position = min(target_vol/realized_vol, 1.5)."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    realized_vol = ret.rolling(window).std() * np.sqrt(252)
    position = (target_vol / realized_vol).clip(0, 1.5)
    position = position.shift(1).fillna(1.0)
    return build_equity(ret, position)


def run_tsmom_monthly(ticker, window_months=12):
    """12m TSMOM: long if 12m return > 0, else cash. Monthly rebalancing."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    monthly = df["close"].resample('M').last()
    signal = (monthly.pct_change(window_months) > 0).astype(float)
    signal_daily = signal.reindex(df.index, method="ffill").shift(1).fillna(0)
    return build_equity(ret, signal_daily)


def run_turn_of_month(ticker, last_n=3, first_n=2):
    """Long on last 3 + first 2 trading days of month."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    dates = df.index

    pos = pd.Series(0.0, index=dates)
    months = dates.to_period("M")
    for m in months.unique():
        mask = months == m
        month_dates = dates[mask]
        n = len(month_dates)
        invested_dates = set(list(month_dates[:first_n]) + list(month_dates[max(0, n - last_n):]))
        pos.loc[list(invested_dates)] = 1.0

    return build_equity(ret, pos)


def run_sentiment_timing(ticker):
    """VIX < 20 → long. VIX > 30 → cash. Between → hold previous."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    vix_daily = VIX.resample('M').last().reindex(df.index, method="ffill")

    pos = pd.Series(np.nan, index=df.index)
    for i in range(len(df)):
        v = vix_daily.iloc[i]
        if pd.isna(v):
            pos.iloc[i] = 1.0
        elif v < 20:
            pos.iloc[i] = 1.0
        elif v > 30:
            pos.iloc[i] = 0.0
        else:
            pos.iloc[i] = np.nan  # hold previous

    pos = pos.ffill().fillna(1.0)
    pos = pos.shift(1).fillna(1.0)
    return build_equity(ret, pos)


def run_quality_timing(ticker):
    """quality-on = 1.0 exposure, quality-off = 0.7 exposure."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()

    rmw = FF["RMW"] / 100
    rmw_12m = rmw.rolling(12).apply(lambda x: (1 + x).prod() - 1, raw=True)
    quality_signal = (rmw_12m > 0).astype(float).shift(1)
    quality_daily = quality_signal.reindex(df.index, method="ffill").fillna(0)
    position = quality_daily * 1.0 + (1 - quality_daily) * 0.7
    return build_equity(ret, position)


def run_yield_curve_duration(ticker):
    """T10Y2Y > 0 → hold. T10Y2Y < 0 → cash."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    t10y2y = FRED["t10y2y"].dropna()
    t10y2y_daily = t10y2y.reindex(df.index, method="ffill")
    signal = (t10y2y_daily > 0).astype(float)
    signal = signal.shift(1).fillna(1.0)
    return build_equity(ret, signal)


def run_bond_carry(ticker):
    """DFII10 > 0 → hold bond ETF. DFII10 < 0 → cash."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    dfii10 = FRED["dfii10"].dropna()
    dfii10_daily = dfii10.reindex(df.index, method="ffill")
    signal = (dfii10_daily > 0).astype(float)
    signal = signal.shift(1).fillna(1.0)
    return build_equity(ret, signal)


def run_gtaa_universe(tickers, label, top_n):
    """Monthly GTAA: eligible = close > 10m SMA; pick top_n by 12-1m momentum."""
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < 2:
        return None

    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in avail})
    prices = prices.sort_index().ffill()
    monthly = prices.resample('M').last()
    sma10 = monthly.rolling(10).mean()
    ret12_1 = monthly.pct_change(12) - monthly.pct_change(1)

    daily_dates = prices.index
    all_ret = prices.pct_change()
    pos = pd.DataFrame(0.0, index=daily_dates, columns=avail)

    rebal_dates = monthly.index[13:]
    for rd in rebal_dates:
        if rd not in sma10.index:
            continue
        eligible_mask = monthly.loc[rd] > sma10.loc[rd]
        eligible = [t for t in avail if eligible_mask.get(t, False)]
        mom = ret12_1.loc[rd, eligible].dropna() if eligible else pd.Series()
        if len(mom) >= 1:
            selected = mom.nlargest(min(top_n, len(mom))).index.tolist()
            w = 1.0 / len(selected)
            next_rd_idx = monthly.index.get_loc(rd) + 1
            if next_rd_idx < len(monthly):
                next_rd = monthly.index[next_rd_idx]
                mask = (daily_dates > rd) & (daily_dates <= next_rd)
                for t in selected:
                    pos.loc[mask, t] = w

    port_ret = (pos.shift(1) * all_ret).sum(axis=1)
    tc = (pos.diff().abs().sum(axis=1)) * TC_BPS
    net_ret = port_ret - tc
    equity = STARTING_CAPITAL * (1 + net_ret).cumprod()
    return equity.dropna()


def run_xsec_momentum(tickers, label, top_n, skip_months=1):
    """12-1 month cross-sectional momentum. Long top_n. Monthly rebal."""
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < max(2, top_n):
        return None

    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in avail}).sort_index().ffill()
    all_ret = prices.pct_change()
    monthly = prices.resample('M').last()
    mom = monthly.pct_change(12) - (monthly.pct_change(skip_months) if skip_months > 0 else 0)

    daily_dates = prices.index
    pos = pd.DataFrame(0.0, index=daily_dates, columns=avail)

    rebal_dates = monthly.index[13:]
    for rd in rebal_dates:
        m = mom.loc[rd].dropna()
        if len(m) < 1:
            continue
        selected = m.nlargest(min(top_n, len(m))).index.tolist()
        w = 1.0 / len(selected)
        next_rd_idx = monthly.index.get_loc(rd) + 1
        if next_rd_idx < len(monthly):
            next_rd = monthly.index[next_rd_idx]
            mask = (daily_dates > rd) & (daily_dates <= next_rd)
            for t in selected:
                pos.loc[mask, t] = w

    port_ret = (pos.shift(1) * all_ret).sum(axis=1)
    tc = pos.diff().abs().sum(axis=1) * TC_BPS
    equity = STARTING_CAPITAL * (1 + port_ret - tc).cumprod()
    return equity.dropna()


def run_cross_asset_carry(tickers, label, top_n=10, window_months=12):
    """Monthly. Rank by trailing 12m Sharpe proxy. Long top_n."""
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < 2:
        return None

    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in avail}).sort_index().ffill()
    all_ret = prices.pct_change()
    monthly_ret = prices.resample('M').last().pct_change()

    daily_dates = prices.index
    pos = pd.DataFrame(0.0, index=daily_dates, columns=avail)

    monthly_dates = monthly_ret.index[window_months:]
    for rd in monthly_dates:
        idx = monthly_ret.index.get_loc(rd)
        window_rets = monthly_ret.iloc[idx - window_months:idx]
        ret12 = (1 + window_rets).prod() - 1
        vol12 = window_rets.std() * np.sqrt(12)
        sharpe_proxy = (ret12 / vol12.replace(0, np.nan)).dropna()
        if len(sharpe_proxy) < 1:
            continue
        selected = sharpe_proxy.nlargest(min(top_n, len(sharpe_proxy))).index.tolist()
        w = 1.0 / len(selected)
        next_idx = monthly_ret.index.get_loc(rd) + 1
        if next_idx < len(monthly_ret):
            next_rd = monthly_ret.index[next_idx]
            mask = (daily_dates > rd) & (daily_dates <= next_rd)
            for t in selected:
                pos.loc[mask, t] = w

    port_ret = (pos.shift(1) * all_ret).sum(axis=1)
    tc = pos.diff().abs().sum(axis=1) * TC_BPS
    equity = STARTING_CAPITAL * (1 + port_ret - tc).cumprod()
    return equity.dropna()


def run_low_volatility(tickers, label, bottom_pct=0.30, vol_window=63):
    """Monthly. Long bottom_pct by 63-day realized vol (lowest vol). Equal weight."""
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < 3:
        return None

    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in avail}).sort_index().ffill()
    all_ret = prices.pct_change()
    daily_vol = all_ret.rolling(vol_window).std() * np.sqrt(252)
    monthly_vol = daily_vol.resample('M').last()

    daily_dates = prices.index
    pos = pd.DataFrame(0.0, index=daily_dates, columns=avail)

    rebal_dates = monthly_vol.index[1:]
    for rd in rebal_dates:
        vols = monthly_vol.loc[rd].dropna()
        if len(vols) < 2:
            continue
        n_sel = max(1, int(len(vols) * bottom_pct))
        selected = vols.nsmallest(n_sel).index.tolist()
        w = 1.0 / len(selected)
        next_idx = monthly_vol.index.get_loc(rd) + 1
        if next_idx < len(monthly_vol):
            next_rd = monthly_vol.index[next_idx]
            mask = (daily_dates > rd) & (daily_dates <= next_rd)
            for t in selected:
                pos.loc[mask, t] = w

    port_ret = (pos.shift(1) * all_ret).sum(axis=1)
    tc = pos.diff().abs().sum(axis=1) * TC_BPS
    equity = STARTING_CAPITAL * (1 + port_ret - tc).cumprod()
    return equity.dropna()


def run_country_cape(tickers, label, top_n=4, value=True):
    """Monthly. Rank by 12m return. value=True → long cheapest (value). Else momentum."""
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < max(2, top_n):
        return None

    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in avail}).sort_index().ffill()
    all_ret = prices.pct_change()
    monthly = prices.resample('M').last()
    ret12 = monthly.pct_change(12)

    daily_dates = prices.index
    pos = pd.DataFrame(0.0, index=daily_dates, columns=avail)
    rebal_dates = ret12.index[12:]

    for rd in rebal_dates:
        m = ret12.loc[rd].dropna()
        if len(m) < 1:
            continue
        if value:
            selected = m.nsmallest(min(top_n, len(m))).index.tolist()
        else:
            selected = m.nlargest(min(top_n, len(m))).index.tolist()
        w = 1.0 / len(selected)
        next_idx = monthly.index.get_loc(rd) + 1
        if next_idx < len(monthly):
            next_rd = monthly.index[next_idx]
            mask = (daily_dates > rd) & (daily_dates <= next_rd)
            for t in selected:
                pos.loc[mask, t] = w

    port_ret = (pos.shift(1) * all_ret).sum(axis=1)
    tc = pos.diff().abs().sum(axis=1) * TC_BPS
    equity = STARTING_CAPITAL * (1 + port_ret - tc).cumprod()
    return equity.dropna()


# ─────────────────────────────────────────────────────────────
# V2: BASKET-LEVEL HELPERS
# ─────────────────────────────────────────────────────────────

def get_instrument_return_series(strategy_name, ticker):
    """
    Run per-instrument strategy on a single ticker.
    Returns daily return series, or None if unavailable / insufficient history.
    """
    if ticker not in ETF_DATA:
        return None
    try:
        if strategy_name == "ibs_mean_reversion":
            eq = run_ibs(ticker)
        elif strategy_name == "donchian_channel":
            eq = run_donchian(ticker)
        elif strategy_name == "vix_mean_reversion":
            if len(VIX) == 0:
                return None
            eq = run_vix_mr(ticker)
        elif strategy_name == "vol_overlay":
            eq = run_vol_overlay(ticker)
        elif strategy_name in ("bond_trend", "commodity_trend"):
            eq = run_tsmom_monthly(ticker)
        elif strategy_name == "turn_of_month":
            eq = run_turn_of_month(ticker)
        elif strategy_name == "sentiment_timing":
            if len(VIX) == 0:
                return None
            eq = run_sentiment_timing(ticker)
        elif strategy_name == "quality_timing":
            if FF is None:
                return None
            eq = run_quality_timing(ticker)
        elif strategy_name == "yield_curve_duration":
            if FRED is None:
                return None
            eq = run_yield_curve_duration(ticker)
        elif strategy_name == "bond_duration_carry":
            if FRED is None:
                return None
            eq = run_bond_carry(ticker)
        else:
            return None

        if eq is None or len(eq) < MIN_DAYS:
            return None
        ret = eq.pct_change().dropna()
        return ret if len(ret) >= MIN_DAYS else None

    except Exception:
        return None


def run_em_dm_carry_basket(basket_tickers):
    """
    Generalised EM/DM carry: overweight the group with stronger 12m momentum.
    For all-EM baskets, uses EFA as external DM benchmark if available.
    Logic mirrors pipeline.py run_em_dm_carry() basket variant.
    """
    avail = [t for t in basket_tickers if t in ETF_DATA]
    em_t = [t for t in avail if t in EM_COUNTRIES]
    dm_t = [t for t in avail if t in DM_COUNTRIES]

    # Fall back: if basket has no DM, use EFA as benchmark (if loaded)
    if not dm_t and "EFA" in ETF_DATA:
        dm_t = ["EFA"]

    if not em_t or not dm_t:
        return None

    all_t = list(dict.fromkeys(em_t + dm_t))
    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in all_t}).sort_index().ffill()
    ret_df = prices.pct_change()
    monthly_p = prices.resample('M').last()

    em_ret12 = monthly_p[em_t].pct_change(12).mean(axis=1)
    dm_ret12 = monthly_p[dm_t].pct_change(12).mean(axis=1)
    signal = (em_ret12 > dm_ret12).astype(float)      # 1 = overweight EM

    # signal=1 → EM 60%, DM 40%;  signal=0 → EM 40%, DM 60%
    em_total = signal * 0.60 + (1 - signal) * 0.40
    dm_total = 1.0 - em_total
    em_each  = em_total / len(em_t)
    dm_each  = dm_total / len(dm_t)

    daily_dates = prices.index
    pos = pd.DataFrame(0.0, index=daily_dates, columns=all_t)
    for t in em_t:
        pos[t] = em_each.reindex(daily_dates, method="ffill").fillna(0.5 / len(em_t))
    for t in dm_t:
        pos[t] = dm_each.reindex(daily_dates, method="ffill").fillna(0.5 / len(dm_t))

    port_ret = (pos.shift(1) * ret_df).sum(axis=1)
    tc = pos.diff().abs().sum(axis=1) * TC_BPS
    equity = STARTING_CAPITAL * (1 + port_ret - tc).cumprod().dropna()
    return equity


def run_portfolio_on_basket(strategy_name, basket_name, avail_tickers):
    """Run a portfolio-level strategy on a given basket's available tickers."""
    label = f"{strategy_name}_{basket_name}"
    n = len(avail_tickers)

    try:
        if strategy_name == "cross_asset_momentum":
            top_n = max(1, int(n * 0.20))
            return run_xsec_momentum(avail_tickers, label, top_n)

        elif strategy_name == "cross_asset_carry":
            top_n = max(1, int(n * 0.20))
            return run_cross_asset_carry(avail_tickers, label, top_n)

        elif strategy_name == "gtaa":
            top_n = min(5, max(1, n // 2))
            return run_gtaa_universe(avail_tickers, label, top_n)

        elif strategy_name == "low_volatility":
            return run_low_volatility(avail_tickers, label, bottom_pct=0.30)

        elif strategy_name == "industry_trend":
            top_n = max(1, int(n * 0.30))
            return run_xsec_momentum(avail_tickers, label, top_n)

        elif strategy_name == "us_cross_sectional_momentum":
            top_n = max(1, int(n * 0.30))
            return run_xsec_momentum(avail_tickers, label, top_n)

        elif strategy_name == "country_cape_rotation":
            top_n = min(4, max(1, n // 4))
            return run_country_cape(avail_tickers, label, top_n=top_n, value=True)

        elif strategy_name == "em_dm_carry":
            return run_em_dm_carry_basket(avail_tickers)

        else:
            return None

    except Exception as e:
        print(f"    Portfolio error [{strategy_name}/{basket_name}]: {e}")
        return None


def compute_basket_metrics(ret_df):
    """
    Given a DataFrame of aligned daily returns (one column per instrument),
    compute EW and InvVol basket Sharpe, tstat, CAGR, MaxDD.

    InvVol: 63-day rolling vol; falls back to EW on first 63 days.
    Returns dict or None if insufficient data.
    """
    if ret_df is None or len(ret_df) < MIN_DAYS:
        return None

    n = ret_df.shape[1]

    # EW basket
    ew_ret = ret_df.mean(axis=1)

    # InvVol basket
    rolling_vol = ret_df.rolling(63).std() * np.sqrt(252)
    inv_vol = 1.0 / rolling_vol.replace(0.0, np.nan)
    row_sum = inv_vol.sum(axis=1)
    iv_weights = inv_vol.div(row_sum, axis=0)
    # Fall back to EW where row_sum is NaN (first 63 days) or zero
    iv_weights = iv_weights.where(row_sum > 0, other=1.0 / n)
    invvol_ret = (iv_weights * ret_df).sum(axis=1)

    def _stats(ret_series):
        r = ret_series.dropna()
        if len(r) < MIN_DAYS or r.std() == 0:
            return None
        sharpe = r.mean() / r.std() * np.sqrt(252)
        n_days = len(r)
        tstat  = sharpe * np.sqrt(n_days / 252)
        eq = (1 + r).cumprod()
        years = (r.index[-1] - r.index[0]).days / 365.25
        cagr  = eq.iloc[-1] ** (1 / max(years, 0.1)) - 1
        roll_max = eq.expanding().max()
        maxdd = ((eq - roll_max) / roll_max).min()
        return dict(
            sharpe=round(float(sharpe), 4),
            tstat=round(float(tstat), 4),
            cagr=round(float(cagr * 100), 3),
            maxdd=round(float(maxdd * 100), 3),
        )

    ew_s = _stats(ew_ret)
    iv_s = _stats(invvol_ret)

    if ew_s is None or iv_s is None:
        return None

    return dict(
        sharpe_ew=ew_s["sharpe"],
        sharpe_invvol=iv_s["sharpe"],
        tstat_ew=ew_s["tstat"],
        tstat_invvol=iv_s["tstat"],
        cagr_ew=ew_s["cagr"],
        cagr_invvol=iv_s["cagr"],
        maxdd_ew=ew_s["maxdd"],
        maxdd_invvol=iv_s["maxdd"],
        pass_ew=bool(ew_s["sharpe"] >= 0.60 and ew_s["tstat"] >= 2.0),
        pass_invvol=bool(iv_s["sharpe"] >= 0.60 and iv_s["tstat"] >= 2.0),
    )


# ─────────────────────────────────────────────────────────────
# MAIN BASKET LOOP
# ─────────────────────────────────────────────────────────────
BASKET_RESULTS = []

for strategy_name, eligible_baskets in STRATEGY_ELIGIBLE_BASKETS.items():
    print(f"\n{'='*60}")
    print(f"STRATEGY: {strategy_name}")
    print(f"{'='*60}")

    for basket_name in eligible_baskets:
        basket_tickers = CATEGORY_BASKETS[basket_name]
        if basket_tickers is None:
            print(f"  {basket_name}: basket definition is None (all_68 not populated?)")
            continue

        avail = [t for t in basket_tickers if t in ETF_DATA]
        print(f"\n  Basket: {basket_name}  ({len(avail)}/{len(basket_tickers)} instruments available)")

        if not avail:
            print(f"    No available tickers — skipping.")
            continue

        if strategy_name in PER_INSTRUMENT:
            # ── Per-instrument path ──
            returns_dict = {}
            for ticker in avail:
                ret = get_instrument_return_series(strategy_name, ticker)
                if ret is not None:
                    returns_dict[ticker] = ret

            n_used = len(returns_dict)
            if n_used == 0:
                print(f"    No instruments with valid returns — skipping.")
                continue

            # Inner join: common date range
            ret_df = pd.DataFrame(returns_dict).dropna()
            instruments_used = list(returns_dict.keys())

        elif strategy_name in PORTFOLIO_STRATS:
            # ── Portfolio path ──
            eq = run_portfolio_on_basket(strategy_name, basket_name, avail)
            if eq is None or len(eq) < MIN_DAYS:
                print(f"    Portfolio returned no data — skipping.")
                continue
            port_ret = eq.pct_change().dropna()
            ret_df = pd.DataFrame({"portfolio": port_ret})
            instruments_used = avail
            n_used = len(avail)

        else:
            print(f"    Unknown strategy type — skipping.")
            continue

        metrics = compute_basket_metrics(ret_df)

        if metrics is None:
            print(f"    Insufficient common data ({len(ret_df)} days after inner join) — skipping.")
            continue

        status = "PASS" if metrics["pass_ew"] else "FAIL"
        print(f"    Sharpe EW={metrics['sharpe_ew']:.3f}  InvVol={metrics['sharpe_invvol']:.3f}  "
              f"Tstat={metrics['tstat_ew']:.2f}  CAGR={metrics['cagr_ew']:.1f}%  "
              f"MaxDD={metrics['maxdd_ew']:.1f}%  [{status}]  "
              f"({n_used} instruments, {len(ret_df)} days)")

        BASKET_RESULTS.append({
            "strategy":         strategy_name,
            "category":         basket_name,
            "n_instruments":    n_used,
            "sharpe_ew":        metrics["sharpe_ew"],
            "sharpe_invvol":    metrics["sharpe_invvol"],
            "tstat_ew":         metrics["tstat_ew"],
            "tstat_invvol":     metrics["tstat_invvol"],
            "cagr_ew":          metrics["cagr_ew"],
            "cagr_invvol":      metrics["cagr_invvol"],
            "maxdd_ew":         metrics["maxdd_ew"],
            "maxdd_invvol":     metrics["maxdd_invvol"],
            "pass_ew":          metrics["pass_ew"],
            "pass_invvol":      metrics["pass_invvol"],
            "instruments_used": ",".join(instruments_used),
        })

# ─────────────────────────────────────────────────────────────
# SAVE results_basket.csv
# ─────────────────────────────────────────────────────────────
results_df = pd.DataFrame(BASKET_RESULTS)
if results_df.empty:
    print("\nNo results to save.")
else:
    csv_path = os.path.join(RESULTS_DIR, "results_basket.csv")
    results_df.to_csv(csv_path, index=False)
    print(f"\nSaved {len(results_df)} rows to {csv_path}")

# ─────────────────────────────────────────────────────────────
# GENERATE basket_report.md
# ─────────────────────────────────────────────────────────────
def generate_report(df):
    lines = []
    lines.append("# Multi-Asset ETF Basket Backtest Report")
    lines.append("")
    lines.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d')}")
    lines.append(f"**Strategies tested:** {df['strategy'].nunique()}")
    lines.append(f"**Total (strategy, basket) pairs:** {len(df)}")
    lines.append(f"**Passing EW (Sharpe ≥ 0.60 & t-stat ≥ 2.0):** {df['pass_ew'].sum()}")
    lines.append(f"**Passing InvVol:** {df['pass_invvol'].sum()}")
    lines.append(f"**Transaction costs:** 5 bps one-way (baked into individual strategy returns)")
    lines.append("")

    # ── Summary table ──
    lines.append("## Summary Table")
    lines.append("")
    lines.append("Sorted by Sharpe EW descending. ✓ = Sharpe ≥ 0.60 AND t-stat ≥ 2.0.")
    lines.append("")
    lines.append("| Strategy | Category | N | Sharpe EW | Sharpe InvVol | t-stat EW | CAGR EW | MaxDD EW | Pass EW | Pass InvVol |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")

    for _, row in df.sort_values("sharpe_ew", ascending=False).iterrows():
        pe  = "✓" if row["pass_ew"]     else "✗"
        piv = "✓" if row["pass_invvol"] else "✗"
        lines.append(
            f"| {row['strategy']} | {row['category']} | {row['n_instruments']} "
            f"| {row['sharpe_ew']:.3f} | {row['sharpe_invvol']:.3f} "
            f"| {row['tstat_ew']:.2f} | {row['cagr_ew']:.1f}% "
            f"| {row['maxdd_ew']:.1f}% | {pe} | {piv} |"
        )

    lines.append("")

    # ── Per-strategy section ──
    lines.append("## Strategy Analysis")
    lines.append("")
    lines.append("For each strategy: which baskets passed, and how EW vs InvVol compare.")
    lines.append("")

    for strategy in STRATEGY_ELIGIBLE_BASKETS.keys():
        sdf = df[df["strategy"] == strategy]
        if sdf.empty:
            continue
        n_pass = sdf["pass_ew"].sum()
        lines.append(f"### {strategy}")
        lines.append("")
        lines.append(f"Eligible baskets: **{len(sdf)}** | Passing (EW): **{n_pass}**")
        lines.append("")

        for _, row in sdf.sort_values("sharpe_ew", ascending=False).iterrows():
            tag = "**PASS**" if row["pass_ew"] else "FAIL"
            div = row["sharpe_invvol"] - row["sharpe_ew"]
            div_str = f"+{div:.3f}" if div >= 0 else f"{div:.3f}"
            lines.append(
                f"- **{row['category']}**: "
                f"EW={row['sharpe_ew']:.3f} | InvVol={row['sharpe_invvol']:.3f} (Δ{div_str})  "
                f"t={row['tstat_ew']:.2f}  CAGR={row['cagr_ew']:.1f}%  "
                f"MaxDD={row['maxdd_ew']:.1f}%  [{tag}]"
            )

        if n_pass == 0:
            lines.append("")
            lines.append(
                f"> **Interpretation:** No basket reaches the Sharpe/t-stat threshold. "
                f"Strategy may lack edge across these asset classes, or signal is too noisy "
                f"when diversified at basket level."
            )
        elif n_pass == len(sdf):
            lines.append("")
            lines.append(
                f"> **Interpretation:** Consistent edge across all eligible baskets — "
                f"robust, broad-based alpha."
            )
        else:
            best_basket = sdf.loc[sdf["sharpe_ew"].idxmax(), "category"]
            lines.append("")
            lines.append(
                f"> **Interpretation:** Selective edge — strongest in **{best_basket}**. "
                f"Consider narrowing deployment to passing baskets."
            )

        lines.append("")

    # ── Per-category section ──
    lines.append("## Category Analysis")
    lines.append("")
    lines.append("Which strategies have genuine edge (EW) in each asset class?")
    lines.append("")

    for cat in sorted(df["category"].unique()):
        cdf = df[df["category"] == cat]
        passed = cdf[cdf["pass_ew"]]
        lines.append(f"### {cat}")
        lines.append("")
        lines.append(
            f"Strategies tested: **{len(cdf)}** | "
            f"Strategies with edge (Sharpe ≥ 0.60 & t-stat ≥ 2.0): **{len(passed)}**"
        )
        lines.append("")

        for _, row in cdf.sort_values("sharpe_ew", ascending=False).iterrows():
            tag = "**PASS**" if row["pass_ew"] else "fail"
            lines.append(
                f"- {row['strategy']}: Sharpe EW={row['sharpe_ew']:.3f}  "
                f"InvVol={row['sharpe_invvol']:.3f}  t={row['tstat_ew']:.2f}  [{tag}]"
            )

        if len(passed) == 0:
            verdict = "No strategy shows a statistically reliable edge in this basket."
        elif len(passed) >= 3:
            verdict = (
                "Multiple strategies pass — this basket is fertile ground. "
                "Consider a multi-strategy allocation here."
            )
        else:
            top_strats = " + ".join(passed["strategy"].tolist())
            verdict = f"Edge is concentrated in: **{top_strats}**."
        lines.append("")
        lines.append(f"> **Verdict:** {verdict}")
        lines.append("")

    return "\n".join(lines)


if not results_df.empty:
    report_md = generate_report(results_df)
    report_path = os.path.join(RESULTS_DIR, "basket_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"Saved report to {report_path}")

# Quick summary
if not results_df.empty:
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total (strategy, basket) pairs: {len(results_df)}")
    print(f"Passing EW:     {results_df['pass_ew'].sum()}")
    print(f"Passing InvVol: {results_df['pass_invvol'].sum()}")
    print("\nTop 10 by Sharpe EW:")
    top = results_df.nlargest(10, "sharpe_ew")[
        ["strategy", "category", "sharpe_ew", "sharpe_invvol", "tstat_ew", "cagr_ew", "pass_ew"]
    ]
    print(top.to_string(index=False))
    print("\nDone.")
