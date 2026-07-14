"""
Multi-Asset Expansion Pipeline
20 strategies × 43 available ETFs
Produces results_matrix.csv and supporting reports.
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

TC_BPS = 0.0005   # 5 bps one-way
STARTING_CAPITAL = 100_000
MIN_DAYS = 252

# ─────────────────────────────────────────────────────────────
# UNIVERSE
# ─────────────────────────────────────────────────────────────
UNIVERSE = {
    "us_equity_broad":         ["SPY", "QQQ", "IWM", "MDY"],
    "us_factor":               ["IWD", "IWF", "USMV", "MTUM", "QUAL", "DVY", "PKW"],
    "us_factor_quality":        ["IWF", "IWD", "QUAL", "USMV", "MTUM", "PKW", "DVY", "IWM"],
    "us_sectors":              ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE", "XLC"],
    "intl_developed_regional": ["EFA", "EZU"],
    "intl_developed_country":  ["EWJ", "EWG", "EWU", "EWC", "EWA", "EWL", "EWQ", "EWI", "EWP", "EWD"],
    "em_regional":             ["EEM"],
    "em_country":              ["EWZ", "EWY", "EWT", "INDA", "MCHI", "EWW", "TUR"],
    "bonds_us":                ["TLT", "IEF", "SHY", "TIP", "BIL", "LQD", "HYG"],
    "bonds_intl":              ["EMB", "BNDX"],
    "commodities":             ["GLD", "SLV", "DBC", "USO", "UNG", "GDX", "PDBC"],
    "real_assets":             ["VNQ", "VNQI", "AMLP"],
    "currencies":              ["UUP", "FXE", "FXY", "FXB", "FXA", "FXC", "FXF"],
}
TICKER_TO_CAT = {t: cat for cat, tickers in UNIVERSE.items() for t in tickers}
ALL_TICKERS   = [t for tickers in UNIVERSE.values() for t in tickers]

CURRENCIES = ["UUP", "FXE", "FXY", "FXB", "FXA", "FXC", "FXF"]
EQUITY_CATS = {"us_equity_broad", "us_factor", "us_sectors",
               "intl_developed_regional", "intl_developed_country", "em_regional", "em_country"}
BOND_TICKERS   = ["TLT", "IEF", "SHY", "TIP", "BIL", "LQD", "HYG", "EMB", "BNDX"]
COMM_TICKERS   = ["GLD", "SLV", "DBC", "USO", "UNG", "GDX", "PDBC"]
REIT_TICKERS   = ["VNQ", "VNQI", "AMLP", "XLU", "XLRE"]

# ─────────────────────────────────────────────────────────────
# STEP 1: LOAD ALL AVAILABLE ETF DATA
# ─────────────────────────────────────────────────────────────
print("Loading ETF price data...")
ETF_DATA = {}
AVAILABLE = []

for ticker in ALL_TICKERS:
    csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, parse_dates=["date"], index_col="date")
            df = df.sort_index()
            df.index = pd.to_datetime(df.index)
            if len(df) >= MIN_DAYS:
                ETF_DATA[ticker] = df
                AVAILABLE.append(ticker)
        except Exception as e:
            print(f"  {ticker}: load error {e}")

print(f"Loaded {len(AVAILABLE)} tickers: {AVAILABLE}\n")

# ─────────────────────────────────────────────────────────────
# STEP 2: LOAD AUXILIARY DATA
# ─────────────────────────────────────────────────────────────
print("Loading auxiliary data...")

# VIX
try:
    macros = pd.read_csv(MACROS_CSV, parse_dates=["date"], index_col="date").sort_index()
    VIX = macros["vix"].dropna()
    print(f"  VIX from macros: {len(VIX)} rows, {VIX.index[0].date()} -> {VIX.index[-1].date()}")
except Exception as e:
    print(f"  macros VIX failed: {e}, trying parquet...")
    try:
        vix_df = pd.read_parquet(VIX_PARQUET)
        vix_df["date"] = pd.to_datetime(vix_df["date"])
        vix_df = vix_df.set_index("date").sort_index()
        VIX = vix_df["vix"].dropna()
        print(f"  VIX from parquet: {len(VIX)} rows")
    except Exception as e2:
        print(f"  VIX parquet also failed: {e2}")
        VIX = pd.Series(dtype=float)

# FRED (T10Y2Y, DFII10, DGS10, DGS2, DGS20)
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
# HELPERS
# ─────────────────────────────────────────────────────────────

def get_returns(ticker):
    """Daily close-to-close returns for a ticker."""
    return ETF_DATA[ticker]["close"].pct_change()


def build_equity(daily_ret, position, starting_capital=STARTING_CAPITAL):
    """
    Build equity curve from daily position series and daily returns.
    position: pd.Series (0 to 1+), indexed same as daily_ret
    Applies TC on position changes.
    """
    pos = position.reindex(daily_ret.index).fillna(0)
    delta = pos.diff().fillna(pos.iloc[0])
    tc = delta.abs() * TC_BPS
    strat_ret = pos.shift(1).fillna(0) * daily_ret - tc
    equity = starting_capital * (1 + strat_ret).cumprod()
    equity = equity.dropna()
    return equity


def compute_metrics(equity):
    """Compute performance metrics from a daily equity curve."""
    if equity is None or len(equity) < MIN_DAYS:
        return None
    dr = equity.pct_change().dropna()
    if len(dr) < MIN_DAYS or dr.std() == 0:
        return None
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / max(years, 0.1)) - 1
    sharpe = dr.mean() / dr.std() * np.sqrt(252)
    downside = dr[dr < 0].std()
    sortino = dr.mean() / downside * np.sqrt(252) if downside > 0 else np.nan
    roll_max = equity.expanding().max()
    drawdown = (equity - roll_max) / roll_max
    maxdd = drawdown.min()
    calmar = cagr / abs(maxdd) if abs(maxdd) > 0.001 else np.nan
    return dict(
        cagr=round(float(cagr * 100), 3),
        sharpe=round(float(sharpe), 4),
        sortino=round(float(sortino), 4) if not np.isnan(sortino) else None,
        maxdd=round(float(maxdd * 100), 3),
        calmar=round(float(calmar), 4) if calmar is not None and not np.isnan(calmar) else None,
        n_days=len(dr),
        start_date=str(equity.index[0].date()),
        end_date=str(equity.index[-1].date()),
    )


RESULTS = []
COMBO_COUNT = 0

def record(strategy, instrument, category, equity, note=""):
    global COMBO_COUNT
    COMBO_COUNT += 1
    metrics = compute_metrics(equity)
    if metrics is None:
        print(f"  {strategy} | {instrument}: INSUFFICIENT_HISTORY")
        row = dict(strategy=strategy, instrument=instrument, category=category,
                   cagr=None, sharpe=None, sortino=None, maxdd=None, calmar=None,
                   n_days=0, start_date=None, end_date=None, note="INSUFFICIENT_HISTORY")
    else:
        print(f"  {strategy} | {instrument}: Sharpe={metrics['sharpe']:.3f}  CAGR={metrics['cagr']:.1f}%  MaxDD={metrics['maxdd']:.1f}%")
        row = dict(strategy=strategy, instrument=instrument, category=category, note=note, **metrics)
    RESULTS.append(row)
    # Save partial every 20 combos
    if COMBO_COUNT % 20 == 0:
        save_partial()


def save_partial():
    df = pd.DataFrame(RESULTS)
    df.to_csv(os.path.join(RESULTS_DIR, "results_matrix_partial.csv"), index=False)


# ─────────────────────────────────────────────────────────────
# STRATEGY 1: IBS MEAN REVERSION
# ─────────────────────────────────────────────────────────────
def run_ibs(ticker):
    """IBS < 0.2 → buy next open; exit IBS > 0.8 or 3-day max hold."""
    df = ETF_DATA[ticker].copy()
    ibs = (df["close"] - df["low"]) / (df["high"] - df["low"])
    ibs = ibs.replace([np.inf, -np.inf], np.nan).fillna(0.5)

    close_ret = df["close"].pct_change()
    # Use open/prev_close for entry days and close/prev_close otherwise
    df["open_ret"]  = df["open"] / df["close"].shift(1) - 1
    df["close_ret"] = close_ret

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
                # Buy at today's open
                in_pos = True
                days_held = 1
                day_ret = df["open_ret"].iloc[i] - TC_BPS  # bought at open
                equity *= (1 + day_ret)
            else:
                day_ret = 0.0
                equity *= 1.0
        else:
            days_held += 1
            if cur_ibs > 0.8 or days_held >= 3:
                # Exit at close today
                day_ret = df["close_ret"].iloc[i] - TC_BPS
                equity *= (1 + day_ret)
                in_pos = False
                days_held = 0
            else:
                day_ret = df["close_ret"].iloc[i]
                equity *= (1 + day_ret)

        eq_series.append(equity)

    return pd.Series(eq_series, index=df.index)


print("=" * 60)
print("STRATEGY 1: IBS MEAN REVERSION")
print("=" * 60)
IBS_EXCLUDE_CATS = {"currencies", "bonds_intl"}
for ticker in AVAILABLE:
    cat = TICKER_TO_CAT[ticker]
    if cat in IBS_EXCLUDE_CATS:
        continue
    try:
        eq = run_ibs(ticker)
        record("ibs_mean_reversion", ticker, cat, eq)
    except Exception as e:
        print(f"  ibs | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 2: DONCHIAN CHANNEL
# ─────────────────────────────────────────────────────────────
def run_donchian(ticker, period=20):
    """20-day channel breakout: long when close > prior 20-day high; exit at 20-day low."""
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


print("\n" + "=" * 60)
print("STRATEGY 2: DONCHIAN CHANNEL")
print("=" * 60)
for ticker in AVAILABLE:
    try:
        eq = run_donchian(ticker)
        record("donchian_channel", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  donchian | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 3: VIX MEAN REVERSION (simplified ETF version)
# ─────────────────────────────────────────────────────────────
def run_vix_mr(ticker):
    """Enter when VIX 1-day spike > +15% AND VIX > 20. Exit when VIX < 20."""
    df = ETF_DATA[ticker].copy()
    close_ret = df["close"].pct_change()

    # Align VIX to ETF dates
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


print("\n" + "=" * 60)
print("STRATEGY 3: VIX MEAN REVERSION")
print("=" * 60)
VIX_ELIGIBLE = [t for t in AVAILABLE if TICKER_TO_CAT[t] in
                {"us_equity_broad", "us_factor", "us_sectors"}]
if len(VIX) == 0:
    print("  VIX data unavailable — skipping strategy 3")
else:
    for ticker in VIX_ELIGIBLE:
        try:
            eq = run_vix_mr(ticker)
            record("vix_mean_reversion", ticker, TICKER_TO_CAT[ticker], eq)
        except Exception as e:
            print(f"  vix_mr | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 4: GTAA
# ─────────────────────────────────────────────────────────────
def run_gtaa_universe(tickers, label, top_n):
    """Monthly GTAA: eligible = close > 10m SMA; pick top_n by 12-1m momentum."""
    # Build price matrix from available tickers
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < 2:
        print(f"  gtaa | {label}: insufficient tickers ({len(avail)})")
        return None

    prices = pd.DataFrame({t: ETF_DATA[t]["close"] for t in avail})
    prices = prices.sort_index().ffill()

    # Monthly close
    monthly = prices.resample('M').last()
    sma10 = monthly.rolling(10).mean()
    ret12_1 = monthly.pct_change(12) - monthly.pct_change(1)

    # Build monthly weights
    daily_dates = prices.index
    # For each month-end, compute position. Apply next month.
    all_ret = prices.pct_change()
    pos = pd.DataFrame(0.0, index=daily_dates, columns=avail)

    rebal_dates = monthly.index[13:]  # need 13 months of history for 12-1
    for rd in rebal_dates:
        if rd not in sma10.index:
            continue
        eligible_mask = monthly.loc[rd] > sma10.loc[rd]
        eligible = [t for t in avail if eligible_mask.get(t, False)]
        mom = ret12_1.loc[rd, eligible].dropna() if eligible else pd.Series()
        if len(mom) >= 1:
            selected = mom.nlargest(min(top_n, len(mom))).index.tolist()
            w = 1.0 / len(selected)
            # Assign to next month
            next_rd_idx = monthly.index.get_loc(rd) + 1
            if next_rd_idx < len(monthly):
                next_rd = monthly.index[next_rd_idx]
                start = rd + pd.Timedelta(days=1)
                end   = next_rd
                mask  = (daily_dates > rd) & (daily_dates <= next_rd)
                for t in selected:
                    pos.loc[mask, t] = w

    # Compute portfolio daily return
    port_ret = (pos.shift(1) * all_ret).sum(axis=1)
    tc = (pos.diff().abs().sum(axis=1)) * TC_BPS
    net_ret = port_ret - tc
    equity = STARTING_CAPITAL * (1 + net_ret).cumprod()
    return equity.dropna()


GTAA_UNIVERSES = {
    "gtaa_us_sectors":    (["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"], 3),
    "gtaa_dm_countries":  (["EWJ","EWG","EWU","EWC","EWA","EWL","EWQ","EWI","EWP","EWD","EFA"], 4),
    "gtaa_em_countries":  (["EEM","EWZ","EWY","EWT","INDA","MCHI","EWW","TUR"], 3),
    "gtaa_bonds":         (["TLT","IEF","SHY","TIP","LQD","HYG","EMB","BNDX"], 3),
    "gtaa_commodities":   (["GLD","SLV","DBC","USO","UNG","GDX","PDBC"], 2),
    "gtaa_real_assets":   (["VNQ","VNQI","AMLP"], 1),
    "gtaa_full_universe": (ALL_TICKERS, 10),
}

print("\n" + "=" * 60)
print("STRATEGY 4: GTAA")
print("=" * 60)
for label, (tickers, top_n) in GTAA_UNIVERSES.items():
    try:
        eq = run_gtaa_universe(tickers, label, top_n)
        if eq is not None:
            record("gtaa", label, "multi_asset", eq)
    except Exception as e:
        print(f"  gtaa | {label}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 5: VOL OVERLAY
# ─────────────────────────────────────────────────────────────
def run_vol_overlay(ticker, target_vol=0.10, window=21):
    """21-day realized vol. Position = min(target_vol/realized_vol, 1.5)."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    realized_vol = ret.rolling(window).std() * np.sqrt(252)
    position = (target_vol / realized_vol).clip(0, 1.5)
    position = position.shift(1).fillna(1.0)
    return build_equity(ret, position)


print("\n" + "=" * 60)
print("STRATEGY 5: VOL OVERLAY")
print("=" * 60)
for ticker in AVAILABLE:
    try:
        eq = run_vol_overlay(ticker)
        record("vol_overlay", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  vol_overlay | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 6: BOND TREND
# ─────────────────────────────────────────────────────────────
def run_tsmom_monthly(ticker, window_months=12):
    """12m TSMOM: long if 12m return > 0, else cash. Monthly rebalancing."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    monthly = df["close"].resample('M').last()
    signal = (monthly.pct_change(window_months) > 0).astype(float)
    signal_daily = signal.reindex(df.index, method="ffill").shift(1).fillna(0)
    return build_equity(ret, signal_daily)


print("\n" + "=" * 60)
print("STRATEGY 6: BOND TREND")
print("=" * 60)
BOND_AVAIL = [t for t in BOND_TICKERS if t in AVAILABLE]
for ticker in BOND_AVAIL:
    try:
        eq = run_tsmom_monthly(ticker)
        record("bond_trend", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  bond_trend | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 7: COMMODITY TREND
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STRATEGY 7: COMMODITY TREND")
print("=" * 60)
COMM_AVAIL = [t for t in COMM_TICKERS if t in AVAILABLE]
for ticker in COMM_AVAIL:
    try:
        eq = run_tsmom_monthly(ticker)
        record("commodity_trend", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  commodity_trend | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 8: INDUSTRY TREND (Cross-Sectional Momentum)
# ─────────────────────────────────────────────────────────────
def run_xsec_momentum(tickers, label, top_n, skip_months=1):
    """12-1 month cross-sectional momentum. Long top_n. Monthly rebal."""
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < max(2, top_n):
        print(f"  industry_trend | {label}: insufficient ({len(avail)} tickers)")
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


INDUSTRY_TREND_UNIVERSES = {
    "industry_trend_us_sectors":   (["XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC"], 3),
    "industry_trend_intl_dm":      (["EWJ","EWG","EWU","EWC","EWA","EWL","EWQ","EWI","EWP","EWD","EFA"], 4),
    "industry_trend_em":           (["EEM","EWZ","EWY","EWT","INDA","MCHI","EWW","TUR"], 3),
    "industry_trend_all_equity":   (
        ["SPY","QQQ","IWM","MDY","IWD","IWF","USMV","MTUM","DVY","PKW",
         "XLK","XLF","XLE","XLV","XLI","XLP","XLY","XLU","XLB","XLRE","XLC",
         "EFA","EZU","EWJ","EWG","EWU","EWC","EWA","EWL","EWQ","EWI","EWP","EWD",
         "EEM","EWZ","EWY","EWT","INDA","MCHI","EWW","TUR"], 5),
}

print("\n" + "=" * 60)
print("STRATEGY 8: INDUSTRY TREND")
print("=" * 60)
for label, (tickers, top_n) in INDUSTRY_TREND_UNIVERSES.items():
    try:
        eq = run_xsec_momentum(tickers, label, top_n)
        if eq is not None:
            record("industry_trend", label, "multi_asset", eq)
    except Exception as e:
        print(f"  industry_trend | {label}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 9: CROSS-ASSET MOMENTUM
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STRATEGY 9: CROSS-ASSET MOMENTUM")
print("=" * 60)
for pct_label, pct in [("top10", 0.10), ("top20", 0.20), ("top30", 0.30)]:
    label = f"cross_asset_mom_{pct_label}"
    top_n = max(1, int(len(AVAILABLE) * pct))
    try:
        eq = run_xsec_momentum(AVAILABLE, label, top_n)
        if eq is not None:
            record("cross_asset_momentum", label, "multi_asset", eq)
    except Exception as e:
        print(f"  cross_asset_mom | {label}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 10: CROSS-ASSET CARRY (Sharpe-proxy ranking)
# ─────────────────────────────────────────────────────────────
def run_cross_asset_carry(tickers, label, top_n=10, window_months=12):
    """Monthly. Rank by trailing 12m return / trailing 12m vol. Long top_n."""
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
        # trailing 12m return and vol
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


print("\n" + "=" * 60)
print("STRATEGY 10: CROSS-ASSET CARRY")
print("=" * 60)
try:
    eq = run_cross_asset_carry(AVAILABLE, "cross_asset_carry_top10", top_n=10)
    if eq is not None:
        record("cross_asset_carry", "cross_asset_carry_top10", "multi_asset", eq)
except Exception as e:
    print(f"  cross_asset_carry: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 11: LOW VOLATILITY
# ─────────────────────────────────────────────────────────────
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


print("\n" + "=" * 60)
print("STRATEGY 11: LOW VOLATILITY")
print("=" * 60)
ALL_EQUITY = [t for t in AVAILABLE if TICKER_TO_CAT[t] in EQUITY_CATS]
for label, tickers in [("low_vol_all_equity", ALL_EQUITY), ("low_vol_all_68", AVAILABLE)]:
    try:
        eq = run_low_volatility(tickers, label)
        if eq is not None:
            record("low_volatility", label, "multi_asset", eq)
    except Exception as e:
        print(f"  low_vol | {label}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 12: TURN OF MONTH
# ─────────────────────────────────────────────────────────────
def run_turn_of_month(ticker, last_n=3, first_n=2):
    """Long on last 3 + first 2 trading days of month. Cash otherwise."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    dates = df.index

    # Build position: 1 if last_n or first_n trading days of month
    pos = pd.Series(0.0, index=dates)
    months = dates.to_period("M")
    for m in months.unique():
        mask = months == m
        month_dates = dates[mask]
        n = len(month_dates)
        invested_dates = set(list(month_dates[:first_n]) + list(month_dates[max(0, n - last_n):]))
        pos.loc[list(invested_dates)] = 1.0

    return build_equity(ret, pos)


print("\n" + "=" * 60)
print("STRATEGY 12: TURN OF MONTH")
print("=" * 60)
TOM_TICKERS = [t for t in AVAILABLE
               if TICKER_TO_CAT[t] in EQUITY_CATS or TICKER_TO_CAT[t] == "real_assets"]
for ticker in TOM_TICKERS:
    try:
        eq = run_turn_of_month(ticker)
        record("turn_of_month", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  turn_of_month | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 13: OVERNIGHT PREMIUM
# ─────────────────────────────────────────────────────────────
def run_overnight_premium(ticker):
    """Buy at close, sell at next open. Returns: next_open/close - 1."""
    df = ETF_DATA[ticker].copy()
    # overnight return = next day's open / today's close - 1
    overnight = df["open"].shift(-1) / df["close"] - 1
    overnight = overnight.dropna()
    # Apply TC daily (entry at close + exit at next open = round trip per day)
    overnight_net = overnight - 2 * TC_BPS  # buy+sell each day
    equity = STARTING_CAPITAL * (1 + overnight_net).cumprod()
    equity.index = df.index[:len(equity)]
    return equity


print("\n" + "=" * 60)
print("STRATEGY 13: OVERNIGHT PREMIUM")
print("=" * 60)
ONP_TICKERS = [t for t in AVAILABLE
               if TICKER_TO_CAT[t] in EQUITY_CATS or TICKER_TO_CAT[t] == "real_assets"]
for ticker in ONP_TICKERS:
    try:
        eq = run_overnight_premium(ticker)
        record("overnight_premium", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  overnight | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 14: EM/DM CARRY
# ─────────────────────────────────────────────────────────────
def run_em_dm_carry():
    """Monthly: EEM 12m > EFA 12m → overweight EM (60%), else overweight DM (60%)."""
    variants = [
        ("em_dm_carry_EEM_EFA", "EEM", "EFA"),
        ("em_dm_carry_EEM_SPY", "EEM", "SPY"),
    ]
    for label, em_t, dm_t in variants:
        if em_t not in AVAILABLE or dm_t not in AVAILABLE:
            print(f"  em_dm_carry | {label}: missing tickers")
            continue
        try:
            em_prices = ETF_DATA[em_t]["close"]
            dm_prices = ETF_DATA[dm_t]["close"]
            em_ret    = em_prices.pct_change()
            dm_ret    = dm_prices.pct_change()

            em_monthly = em_prices.resample('M').last()
            dm_monthly = dm_prices.resample('M').last()
            em_12m = em_monthly.pct_change(12)
            dm_12m = dm_monthly.pct_change(12)

            signal = (em_12m > dm_12m).astype(float)  # 1 = overweight EM
            # signal 1 → EM 60%, DM 40%; signal 0 → EM 40%, DM 60%
            em_w_monthly = signal * 0.60 + (1 - signal) * 0.40
            dm_w_monthly = 1 - em_w_monthly
            em_w = em_w_monthly.reindex(em_ret.index, method="ffill").shift(1).fillna(0.5)
            dm_w = dm_w_monthly.reindex(dm_ret.index, method="ffill").shift(1).fillna(0.5)

            port_ret = em_w * em_ret + dm_w * dm_ret
            # TC on EM position changes only (DM is complementary)
            tc = em_w.diff().abs() * TC_BPS
            net_ret = port_ret - tc
            equity = STARTING_CAPITAL * (1 + net_ret).cumprod().dropna()
            record("em_dm_carry", label, "multi_asset", equity)
        except Exception as e:
            print(f"  em_dm_carry | {label}: ERROR {e}")

    # EM country basket vs DM regional
    em_basket_t = [t for t in ["EEM","INDA","EWW"] if t in AVAILABLE]
    dm_basket_t = [t for t in ["EFA","EZU"] if t in AVAILABLE]
    if em_basket_t and dm_basket_t:
        try:
            prices = pd.DataFrame(
                {t: ETF_DATA[t]["close"] for t in em_basket_t + dm_basket_t}
            ).sort_index().ffill()
            ret_df = prices.pct_change()
            monthly_p = prices.resample('M').last()
            em_basket_ret12 = monthly_p[em_basket_t].pct_change(12).mean(axis=1)
            dm_basket_ret12 = monthly_p[dm_basket_t].pct_change(12).mean(axis=1)
            signal = (em_basket_ret12 > dm_basket_ret12).astype(float)
            # em_weight signal applied to EM basket (equal-weight within basket)
            em_each = signal * 0.60 / len(em_basket_t)
            dm_each = (1 - signal) * 0.60 / len(dm_basket_t)

            daily_dates = prices.index
            pos = pd.DataFrame(0.0, index=daily_dates, columns=em_basket_t + dm_basket_t)
            for t in em_basket_t:
                pos[t] = em_each.reindex(daily_dates, method="ffill").fillna(0.2)
            for t in dm_basket_t:
                pos[t] = dm_each.reindex(daily_dates, method="ffill").fillna(0.2)

            port_ret = (pos.shift(1) * ret_df).sum(axis=1)
            tc = pos.diff().abs().sum(axis=1) * TC_BPS
            equity = STARTING_CAPITAL * (1 + port_ret - tc).cumprod().dropna()
            record("em_dm_carry", "em_dm_carry_baskets", "multi_asset", equity)
        except Exception as e:
            print(f"  em_dm_carry | baskets: ERROR {e}")


print("\n" + "=" * 60)
print("STRATEGY 14: EM/DM CARRY")
print("=" * 60)
run_em_dm_carry()

# ─────────────────────────────────────────────────────────────
# STRATEGY 15: COUNTRY CAPE ROTATION
# ─────────────────────────────────────────────────────────────
def run_country_cape(tickers, label, top_n=4, value=True):
    """
    Monthly. Rank by 12m return.
    value=True: long cheapest (lowest return = mean-reversion / value proxy).
    value=False: long best momentum (highest return).
    """
    avail = [t for t in tickers if t in ETF_DATA]
    if len(avail) < max(2, top_n):
        print(f"  country_cape | {label}: insufficient ({len(avail)})")
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


print("\n" + "=" * 60)
print("STRATEGY 15: COUNTRY CAPE ROTATION")
print("=" * 60)
COUNTRY_ETFS = (
    ["EWJ","EWG","EWU","EWC","EWA","EWL","EWQ","EWI","EWP","EWD"] +  # DM
    ["EEM","EWZ","EWY","EWT","INDA","MCHI","EWW","TUR"]                 # EM
)
for value_flag, label in [(True, "country_cape_value"), (False, "country_cape_momentum")]:
    try:
        eq = run_country_cape(COUNTRY_ETFS, label, top_n=4, value=value_flag)
        if eq is not None:
            record("country_cape_rotation", label, "multi_asset", eq)
    except Exception as e:
        print(f"  country_cape | {label}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 16: YIELD CURVE DURATION
# ─────────────────────────────────────────────────────────────
def run_yield_curve_duration(ticker):
    """
    T10Y2Y > 0 (normal curve) → hold long-duration bond ETF.
    T10Y2Y < 0 (inverted) → cash.
    """
    if FRED is None:
        return None
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()

    t10y2y = FRED["t10y2y"].dropna()
    t10y2y_daily = t10y2y.reindex(df.index, method="ffill")
    signal = (t10y2y_daily > 0).astype(float)
    signal = signal.shift(1).fillna(1.0)  # 1-day lag, default to invested
    return build_equity(ret, signal)


print("\n" + "=" * 60)
print("STRATEGY 16: YIELD CURVE DURATION")
print("=" * 60)
YC_TICKERS = [t for t in ["TLT","IEF","SHY","LQD","HYG"] if t in AVAILABLE]
if FRED is None:
    print("  FRED data unavailable — skipping strategy 16")
else:
    for ticker in YC_TICKERS:
        try:
            eq = run_yield_curve_duration(ticker)
            if eq is not None:
                record("yield_curve_duration", ticker, TICKER_TO_CAT[ticker], eq)
        except Exception as e:
            print(f"  yield_curve | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 17: BOND DURATION CARRY
# ─────────────────────────────────────────────────────────────
def run_bond_carry(ticker):
    """DFII10 > 0 → hold bond ETF. DFII10 < 0 → cash."""
    if FRED is None:
        return None
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()

    dfii10 = FRED["dfii10"].dropna()
    dfii10_daily = dfii10.reindex(df.index, method="ffill")
    signal = (dfii10_daily > 0).astype(float)
    signal = signal.shift(1).fillna(1.0)
    return build_equity(ret, signal)


print("\n" + "=" * 60)
print("STRATEGY 17: BOND DURATION CARRY")
print("=" * 60)
BC_TICKERS = [t for t in ["TLT","IEF","TIP","LQD","HYG","EMB"] if t in AVAILABLE]
if FRED is None:
    print("  FRED data unavailable — skipping strategy 17")
else:
    for ticker in BC_TICKERS:
        try:
            eq = run_bond_carry(ticker)
            if eq is not None:
                record("bond_duration_carry", ticker, TICKER_TO_CAT[ticker], eq)
        except Exception as e:
            print(f"  bond_carry | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 18: REIT DIVIDEND CARRY
# ─────────────────────────────────────────────────────────────
def run_reit_carry(ticker, threshold=0.03):
    """Trailing 12m total return > 3% threshold → long. Else cash."""
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()
    monthly = df["close"].resample('M').last()
    trailing_12m = monthly.pct_change(12)
    signal = (trailing_12m > threshold).astype(float)
    signal_daily = signal.reindex(df.index, method="ffill").shift(1).fillna(0)
    return build_equity(ret, signal_daily)


print("\n" + "=" * 60)
print("STRATEGY 18: REIT DIVIDEND CARRY")
print("=" * 60)
REIT_AVAIL = [t for t in REIT_TICKERS if t in AVAILABLE]
for ticker in REIT_AVAIL:
    try:
        eq = run_reit_carry(ticker)
        record("reit_dividend_carry", ticker, TICKER_TO_CAT[ticker], eq)
    except Exception as e:
        print(f"  reit_carry | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 19: QUALITY PROFITABILITY TIMING
# ─────────────────────────────────────────────────────────────
def run_quality_timing(ticker):
    """
    When trailing 12m cumulative RMW > 0 → hold ETF.
    When ≤ 0 → hold ETF (no change in vehicle, just signal timing).
    Actually: quality-on = 1.0 exposure, quality-off = 0.7 exposure.
    """
    if FF is None:
        return None
    df = ETF_DATA[ticker].copy()
    ret = df["close"].pct_change()

    rmw = FF["RMW"] / 100
    rmw_12m = rmw.rolling(12).apply(lambda x: (1 + x).prod() - 1, raw=True)
    quality_signal = (rmw_12m > 0).astype(float).shift(1)
    # Map to daily
    quality_daily = quality_signal.reindex(df.index, method="ffill").fillna(0)
    # Quality-on: full exposure (1.0), quality-off: reduced (0.7)
    position = quality_daily * 1.0 + (1 - quality_daily) * 0.7
    return build_equity(ret, position)


print("\n" + "=" * 60)
print("STRATEGY 19: QUALITY TIMING")
print("=" * 60)
EQUITY_AVAIL = [t for t in AVAILABLE if TICKER_TO_CAT[t] in EQUITY_CATS]
if FF is None:
    print("  FF data unavailable — skipping strategy 19")
else:
    for ticker in EQUITY_AVAIL:
        try:
            eq = run_quality_timing(ticker)
            if eq is not None:
                record("quality_timing", ticker, TICKER_TO_CAT[ticker], eq)
        except Exception as e:
            print(f"  quality | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# STRATEGY 20: SENTIMENT TIMING
# ─────────────────────────────────────────────────────────────
def run_sentiment_timing(ticker):
    """VIX < 20 → long. VIX > 30 → cash. Between → hold previous."""
    if len(VIX) == 0:
        return None
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


print("\n" + "=" * 60)
print("STRATEGY 20: SENTIMENT TIMING")
print("=" * 60)
if len(VIX) == 0:
    print("  VIX data unavailable — skipping strategy 20")
else:
    for ticker in EQUITY_AVAIL:
        try:
            eq = run_sentiment_timing(ticker)
            if eq is not None:
                record("sentiment_timing", ticker, TICKER_TO_CAT[ticker], eq)
        except Exception as e:
            print(f"  sentiment | {ticker}: ERROR {e}")

# ─────────────────────────────────────────────────────────────
# FINAL SAVE
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("SAVING FINAL RESULTS")
print("=" * 60)

results_df = pd.DataFrame(RESULTS)
results_path = os.path.join(RESULTS_DIR, "results_matrix.csv")
results_df.to_csv(results_path, index=False)
print(f"Saved {len(results_df)} rows to {results_path}")

# Summary
valid = results_df[results_df["sharpe"].notna()]
print(f"\nTotal combinations: {len(results_df)}")
print(f"Valid (sufficient history): {len(valid)}")
print(f"\nTop 10 by Sharpe:")
print(valid.nlargest(10, "sharpe")[["strategy","instrument","cagr","sharpe","maxdd"]].to_string())
print("\nDone.")
