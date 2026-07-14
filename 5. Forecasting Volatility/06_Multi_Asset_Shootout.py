"""
08_Multi_Asset_Shootout.py — rank vol-forecasting models across products.

Same protocol per asset: target = 20d forward realized vol; 4 simple models
(HAR-RV, AR(5) on RV, EWMA/RiskMetrics, Naive persistence), expanding-window
walk-forward (monthly refit, 60d embargo); ranked by OOS R2/corr AND by the
Sharpe of a vol-targeted position (exposure = target_vol / predicted_vol,
clamped [0.25, 2.0]) vs buy & hold.

Data: tries the Quantitative Portfolio daily_tickers store first, then any CSV
in ./data/raw/daily/<TICKER>.csv (date,close), then yfinance.

Run:  python 08_Multi_Asset_Shootout.py SPY QQQ GLD
Out:  results/multi_asset_shootout.md
"""
import os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = r"C:\Users\danie\Desktop\GitHub\Quantitative-Finance\1. Quantitative Portfolio\0. Data\alpaca\daily_tickers\tickers"
TICKERS = sys.argv[1:] or ["SPY", "QQQ", "GLD"]
TARGET_VOL, CLAMP, FWD, EMBARGO = 0.15, (0.25, 2.0), 20, 60

def load_close(t):
    p1 = os.path.join(STORE, f"{t}.csv")
    p2 = os.path.join(HERE, "data", "raw", "daily", f"{t}.csv")
    for p in (p1, p2):
        if os.path.exists(p):
            df = pd.read_csv(p, parse_dates=[0]).set_index(df_col(p))
            c = [c for c in df.columns if c.lower() == "close"][0] if "close" in [c.lower() for c in df.columns] else df.columns[-1]
            return pd.to_numeric(df[c], errors="coerce").dropna()
    import yfinance as yf
    return yf.download(t, start="2015-06-01", progress=False, auto_adjust=True)["Close"].dropna()

def df_col(p):
    return pd.read_csv(p, nrows=1).columns[0]

def realized_vol(r, w=20):
    return r.rolling(w).std() * np.sqrt(252)

def run_asset(t, close):
    r = close.pct_change().dropna()
    rv1 = ((r**2) * 252) ** 0.5                        # daily point vol (HAR 'daily' term)
    rv5, rv21 = realized_vol(r, 5), realized_vol(r, 21)
    target = realized_vol(r, FWD).shift(-FWD)          # 20d FORWARD realized vol
    X = pd.DataFrame({"rv1": rv1, "rv5": rv5, "rv21": rv21,
                      **{f"lag{i}": realized_vol(r, 20).shift(i) for i in range(1, 6)}})
    ewma_var = (r**2).ewm(alpha=0.06).mean()           # RiskMetrics lambda=0.94
    ewma = (ewma_var * 252) ** 0.5
    naive = realized_vol(r, 20)
    df = pd.concat([X, target.rename("y"), ewma.rename("ewma"), naive.rename("naive")], axis=1).dropna()

    # expanding-window monthly-refit predictions for HAR and AR
    preds = {m: pd.Series(index=df.index, dtype=float) for m in ("HAR-RV", "AR(5)")}
    idx = df.index
    start = 756  # 3y burn-in
    lr = None
    for i in range(start, len(df), 21):
        tr = df.iloc[:max(0, i - EMBARGO)]
        te = df.iloc[i:i + 21]
        if len(tr) < 252 or te.empty: continue
        for name, cols in (("HAR-RV", ["rv1", "rv5", "rv21"]), ("AR(5)", [f"lag{j}" for j in range(1, 6)])):
            A = np.c_[np.ones(len(tr)), tr[cols].values]
            beta, *_ = np.linalg.lstsq(A, tr["y"].values, rcond=None)
            preds[name].loc[te.index] = np.c_[np.ones(len(te)), te[cols].values] @ beta
    preds["EWMA"] = df["ewma"]; preds["Naive-20d"] = df["naive"]

    rows = []
    for name, p in preds.items():
        both = pd.concat([p.rename("p"), df["y"]], axis=1).dropna()
        both = both[both.index >= idx[start]]
        if both.empty: continue
        ss = 1 - ((both.p - both.y) ** 2).sum() / ((both.y - both.y.mean()) ** 2).sum()
        corr = both.p.corr(both.y)
        # vol-target backtest on the OOS window
        expo = (TARGET_VOL / both.p).clip(*CLAMP).shift(1)
        rr = r.reindex(both.index)
        strat = (expo * rr).dropna(); bh = rr.reindex(strat.index)
        sh = lambda x: x.mean() / x.std() * np.sqrt(252)
        dd = lambda x: (((1+x).cumprod() - (1+x).cumprod().cummax()) / (1+x).cumprod().cummax()).min()
        cagr = lambda x: (1+x).prod() ** (252/len(x)) - 1
        rows.append(dict(model=name, r2=round(ss,3), corr=round(corr,3),
                         vt_sharpe=round(sh(strat),3), bh_sharpe=round(sh(bh),3),
                         sharpe_impr=round(sh(strat)-sh(bh),3),
                         vt_dd=f"{dd(strat)*100:.1f}%", bh_dd=f"{dd(bh)*100:.1f}%",
                         vt_cagr=f"{cagr(strat)*100:.1f}%", bh_cagr=f"{cagr(bh)*100:.1f}%",
                         n=len(strat)))
    out = pd.DataFrame(rows).sort_values("sharpe_impr", ascending=False)
    out.insert(0, "asset", t)
    return out

def main():
    all_out = []
    for t in TICKERS:
        try:
            close = load_close(t)
            res = run_asset(t, close)
            all_out.append(res)
            print(f"\n== {t} ({close.index[0].date()} -> {close.index[-1].date()})")
            print(res.to_string(index=False))
        except Exception as e:
            print(f"{t}: FAILED — {e}")
    if all_out:
        md = pd.concat(all_out)
        path = os.path.join(HERE, "results", "multi_asset_shootout.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Multi-asset vol-model shootout (OOS, expanding window, 60d embargo)\n\n")
            f.write(md.to_markdown(index=False))
            f.write("\n\nColumns: r2/corr = 20d-forward realized-vol forecast quality; "
                    "vt_* = vol-targeted position (15% target, exposure clamp 0.25-2.0x) vs bh_* = buy & hold.\n")
        print(f"\nSaved -> {path}")

if __name__ == "__main__":
    main()
