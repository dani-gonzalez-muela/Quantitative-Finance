"""
app.py — Portfolio Dashboard (v3, 2026-07-10 feedback pass)
===========================================================
Tabs: Overview | Short-Term | Long-Term | Archived Strategies
 - Overview: intro + full end-to-end methodology write-up.
 - Portfolio tabs: equity/drawdown/greedy path + CLICKABLE members table
   (click a row -> strategy description + assets below).
 - Archived Strategies: the decision pipeline + the candidates that did NOT
   make the books, split long-term / short-term, sorted by Sharpe, clickable.
Reads only dashboard_data/ (python build_dashboard_data.py regenerates it).
"""
import os, json, glob
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, State, MATCH, dash_table

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "dashboard_data")

COLORS = {"short_term": "#22d3ee", "long_term": "#a78bfa", "reference": "#fbbf24",
          "combined": "#34d399", "grid": "#2a3240", "text": "#e6e9ef", "muted": "#8b93a3",
          "panel": "#151a24"}
PORTS = ["short_term", "long_term"]
GRAPH_CFG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showAxisDragHandles": False}
PLABEL = {"short_term": "Short-Term", "long_term": "Long-Term",
          "combined": "Combined (50/50)", "reference": "Reference"}
HORIZON = {"short_term": "positions held from minutes up to a few days (intraday session, "
                         "overnight and short-swing daily strategies)",
           "long_term": "positions held for more than ~30 days (monthly-rebalanced timing "
                        "and cross-sectional selection strategies)"}

# ─────────────────────────── data loading ───────────────────────────

def load_equity(name):
    p = os.path.join(DATA, "portfolios", f"{name}_portfolio_equity.csv")
    if not os.path.exists(p):
        return None
    return pd.read_csv(p, parse_dates=["date"]).set_index("date")["equity"]

def load_meta(name):
    p = os.path.join(DATA, "portfolios", f"{name}_portfolio_meta.json")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def load_strategies():
    out = {}
    for d in sorted(glob.glob(os.path.join(DATA, "strategies", "*"))):
        if not os.path.isdir(d):
            continue
        name = os.path.basename(d)
        meta_p = os.path.join(d, "meta.json")
        meta = json.load(open(meta_p, encoding="utf-8")) if os.path.exists(meta_p) else {}
        out[name] = {"meta": meta}
    return out

EQ = {p: load_equity(p) for p in PORTS + ["combined"]}
META = {p: load_meta(p) for p in PORTS + ["combined"]}
STRATS = load_strategies()

# ─────────────────────────── figure helpers ─────────────────────────

def base_layout(fig, height=340):
    fig.update_layout(
        template=None, height=height, margin=dict(l=80, r=25, t=30, b=60),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=COLORS["text"], size=12),
        dragmode=False,
        xaxis=dict(gridcolor=COLORS["grid"], zeroline=False, fixedrange=True,
                   title_font=dict(size=14, color=COLORS["text"]), title_standoff=18,
                   tickfont=dict(size=13, color=COLORS["text"]), automargin=True),
        yaxis=dict(gridcolor=COLORS["grid"], zeroline=False, fixedrange=True,
                   title_font=dict(size=14, color=COLORS["text"]), title_standoff=18,
                   tickfont=dict(size=13, color=COLORS["text"]), automargin=True),
        legend=dict(orientation="h", y=1.1, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(size=12)),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#10141c", bordercolor=COLORS["grid"],
                        font=dict(family="Inter", size=12, color=COLORS["text"])))
    return fig

def equity_fig(series_map, log_y=True):
    fig = go.Figure()
    for name, s in series_map.items():
        if s is None:
            continue
        norm = s / s.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm.values, name=PLABEL.get(name, name),
            line=dict(width=2, color=COLORS.get(name)),
            hovertemplate="%{y:,.0f}<extra>" + PLABEL.get(name, name) + "</extra>"))
    fig.update_xaxes(title="Date")
    fig.update_yaxes(type="log" if log_y else "linear",
                     title="Portfolio value in $ (start = $100" + (", log scale)" if log_y else ")"),
                     tickprefix="$", tickformat=",.0f")
    return base_layout(fig)

def drawdown_fig(s, color):
    dd = (s - s.cummax()) / s.cummax() * 100
    fig = go.Figure(go.Scatter(x=dd.index, y=dd.values, fill="tozeroy",
                               line=dict(width=1, color=color), name="Drawdown",
                               hovertemplate="%{y:.1f}%<extra>Drawdown</extra>"))
    fig.update_xaxes(title="Date")
    fig.update_yaxes(title="Drawdown from peak (%)", ticksuffix="%")
    return base_layout(fig, height=220)

def selection_path_fig(meta, color, n_selected):
    path = meta.get("selection_path", [])
    if not path:
        return None
    xs = [p["step"] for p in path]; ys = [p["sharpe"] for p in path]
    labels = [p["added"] for p in path]
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers+text", text=labels,
        textposition="top center", textfont=dict(size=10, color=COLORS["muted"]),
        line=dict(color=color, width=2),
        hovertemplate="Step %{x}: add %{text}<br>Cumulative Sharpe %{y:.2f}<extra></extra>"))
    fig.add_vline(x=n_selected + 0.5, line_dash="dot", line_color=COLORS["muted"],
                  annotation_text="selection stops", annotation_font_color=COLORS["muted"])
    fig.update_xaxes(title="Greedy step (strategies added one by one)", dtick=1)
    fig.update_yaxes(title="Cumulative portfolio Sharpe (monthly)")
    return base_layout(fig, height=300)

# ─────────────────────────── table helpers ──────────────────────────

TABLE_STYLE = dict(
    style_as_list_view=True,
    style_table={"overflowX": "auto"},
    sort_action="native",
    style_header={"backgroundColor": "transparent", "color": COLORS["muted"],
                  "fontWeight": "600", "fontSize": 12, "border": "none",
                  "borderBottom": f"1px solid {COLORS['grid']}"},
    style_cell={"backgroundColor": "transparent", "color": COLORS["text"],
                "fontFamily": "Inter", "fontSize": 13, "border": "none",
                "padding": "8px 12px", "textAlign": "left", "cursor": "pointer"},
    style_data_conditional=[
        {"if": {"state": "active"},
         "backgroundColor": "rgba(255,255,255,0.07)",
         "border": f"1px solid {COLORS['grid']}", "color": COLORS["text"]},
        {"if": {"state": "selected"},
         "backgroundColor": "rgba(255,255,255,0.07)",
         "border": f"1px solid {COLORS['grid']}", "color": COLORS["text"]},
    ],
    css=[{"selector": "tr:hover td",
          "rule": f"background-color: rgba(255,255,255,0.05) !important; color: {COLORS['text']} !important;"}],
)

def strat_row(key):
    m = STRATS.get(key, {}).get("meta", {})
    st = m.get("stats", {})
    return {"key": key,
            "Strategy": m.get("label", key),
            "Sharpe": st.get("sharpe", None),
            "CAGR %": st.get("cagr_pct", None),
            "MaxDD %": st.get("maxdd_pct", None),
            "3-gate": m.get("gates_passed", "-"),
            "Months": st.get("months", None)}

def clickable_table(rows, group, columns=None, sortable=True):
    if not rows:
        return html.Div("No strategies here.", className="hint")
    cols = columns or ["Strategy", "Sharpe", "CAGR %", "MaxDD %", "3-gate", "Months"]
    kwargs = dict(TABLE_STYLE)
    if not sortable:
        kwargs["sort_action"] = "none"
    return dash_table.DataTable(
        id={"type": "stable", "group": group},
        data=rows, columns=[{"name": c, "id": c} for c in cols],
        **kwargs)

def gate_badge(v):
    m = {"pass": ("PASS", "pass"), "fail": ("FAIL", "fail"),
         "rescued": ("RESCUED", "rescued"), "na": ("N/A", "na")}
    txt, cls = m.get(str(v).lower(), (str(v), "na"))
    return html.Span(txt, className=f"badge {cls}")

def strategy_description_block(key):
    """Description + assets + stats + validation for one strategy (used on click)."""
    if key not in STRATS:
        return html.Div("Click a row in the table to see the strategy's description.", className="hint")
    m = STRATS[key]["meta"]
    st = m.get("stats", {})
    v = m.get("validation", {})
    fields = [(lbl, m.get(k)) for lbl, k in
              [("Type", "type"), ("Timeframe", "timeframe"),
               ("Assets / universe", "universe"), ("Signal", "signal"),
               ("Exit", "exit"), ("Sizing", "sizing")] if m.get(k)]
    desc = m.get("description") or m.get("signal") or "No description on file."
    return html.Div(className="row2", children=[
        html.Div(className="panel", children=[
            html.H3(m.get("label", key)),
            html.Div(className="strategy-desc", children=(
                [html.P(p) for p in desc.split("\n") if p.strip()] +
                [html.P([html.B(f"{k}: "), str(val)]) for k, val in fields]))]),
        html.Div(className="panel", children=[
            html.H3("Key stats & validation"),
            html.Table(style={"width": "100%", "fontSize": "13px", "borderSpacing": "0 6px"}, children=[
                html.Tr([html.Td(html.B("Sharpe")), html.Td(st.get("sharpe", "-"))]),
                html.Tr([html.Td(html.B("CAGR")), html.Td(f'{st.get("cagr_pct", "-")}%')]),
                html.Tr([html.Td(html.B("Max drawdown")), html.Td(f'{st.get("maxdd_pct", "-")}%')]),
                html.Tr([html.Td(html.B("Track record")), html.Td(f'{st.get("months", "-")} months')]),
                html.Tr([html.Td(html.B("Basket 3-gate test")), html.Td(gate_badge(v.get("basket", "na")))]),
                html.Tr([html.Td(html.B("Selected into book")), html.Td(gate_badge("pass" if m.get("in_portfolio") else "fail"))]),
            ]),
            html.Div(style={"marginTop": "10px", "fontSize": "13px", "color": COLORS["muted"]},
                     children=[html.B("Reference: ", style={"color": COLORS["text"]}),
                               m.get("reference", "—")])])])

# ─────────────────────────── overview text ──────────────────────────

N_TOTAL = len(STRATS)
N_IN = sum(1 for v in STRATS.values() if v["meta"].get("in_portfolio"))

INTRO_MD = f"""
**{N_TOTAL} systematic strategies** were researched, backtested on multi-asset ETF baskets with
realistic costs, and filtered through a statistical validation pipeline (see *Archived
Strategies*). The **{N_IN} survivors** were assembled into **two portfolios**: a **Short-Term
book** (holds of minutes to a few days) and a **Long-Term book** (30+ day holds). Everything
below explains how, end to end.

**Full code & documentation:** [github.com/dani-gonzalez-muela/Quantitative-Finance — 1. Quantitative Portfolio](https://github.com/dani-gonzalez-muela/Quantitative-Finance/tree/main/1.%20Quantitative%20Portfolio)
"""

METHODOLOGY_SECTIONS = [
    ("1 · Objective & structure",
     "Build an allocatable, risk-managed book of systematic strategies: research broadly, "
     "validate ruthlessly, keep only what survives statistics and transaction costs, and "
     "combine the survivors for diversification. Two books run side by side — SHORT-TERM "
     "(minutes to a few days: intraday session trading, overnight carry, short-swing mean "
     "reversion, volatility carry, congressional-flow momentum) and LONG-TERM (30+ day holds: "
     "monthly asset-class timing and cross-sectional selection). The books are ~0.2 "
     "correlated, so a 50/50 blend is reported as well."),
    ("2 · Data & universe",
     """Data sources: (i) ten years of **5-minute intraday bars from Alpaca** for ~44 liquid
US-listed ETFs; (ii) daily ETF price histories, including the VIX ETNs (SVXY, VIXY, VXX);
(iii) **WRDS** institutional datasets — CRSP security daily prices, S&P 500 constituent
history and index portfolios, plus **Compustat fundamentals and financial ratios**;
(iv) CBOE VIX and VIX term-structure series; (v) FRED interest-rate series;
(vi) QuiverQuant congressional-trading disclosures. All access goes through one
machine-readable registry, so every result is reproducible from the raw stores.

Strategies are never tested on a cherry-picked ticker — they are evaluated per **basket**
of related instruments:

1. **US broad equity:** SPY, QQQ, IWM, DIA, MDY, IVV, VOO
2. **US factors:** IWF, IWD, MTUM, USMV, VTV, VUG, DVY, QUAL
3. **US sectors:** the 11 XL* SPDRs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLU, XLB, XLC, XLRE)
4. **US bonds:** TLT, IEF, SHY, HYG, LQD
5. **Commodities:** GLD, SLV, USO, GDX
6. **EM regional:** EEM, EWZ, INDA, EWW
7. **International developed:** EFA, EZU, EWJ, EWG, EWU"""),
    ("3 · Backtesting methodology (two phases)",
     """**Phase 1 — parameter search & basket acceptance.** For each basket, the strategy's
full parameter grid is evaluated on every instrument. The canonical parameter set is the
one that maximizes the **median Sharpe across the basket's instruments** — parameters must
work across a whole family of related instruments, not on one lucky ticker. A basket is
accepted only if two things hold: (a) a **binomial test** on the count of individually
significant instruments — if, say, 6 of 7 tickers are significant on their own, the
probability of that happening by chance is far below 5% — and (b) the basket's composite
monthly returns pass all **three statistical gates** described in the next section.

**Phase 2 — trade generation.** Accepted baskets (plus any Bonferroni-rescued instruments,
next section) emit trade-level records — entry/exit timestamps and prices per instrument —
which are the sole input to the sizing layer.

Realistic costs are charged on every trade in both phases: SEC fee + FINRA TAF + slippage
at $0.005/share per side for intraday strategies (a marketable-limit / half-spread estimate
for penny-wide ETFs), with a full 0 / $0.005 / $0.01 fee-sensitivity table kept per
intraday strategy."""),
    ("4 · Statistical validation — the three gates + Bonferroni rescue",
     """Each gate is applied to the basket's composite monthly returns:

**Gate 1 — t-test.** One-sided t-test on the mean monthly return (p < 0.05): the average
return is positive beyond what noise explains.

**Gate 2 — bootstrap.** The return series is resampled 5,000 times and the Sharpe
recomputed each time; the 5th percentile of that distribution must stay above zero — the
edge survives resampling of its own history.

**Gate 3 — sign-permutation.** Return signs are randomly flipped 5,000 times; the real
Sharpe must beat 95% of the sign-scrambled ones — the edge is directional, not a
volatility artifact.

**Bonferroni rescue.** Baskets that fail get one more chance, instrument by instrument:
each ticker is retested at a corrected threshold (α = 0.05/N, N = instruments in the
basket) and individually significant tickers are *rescued* into the strategy's tradeable
universe. Basket-first testing plus corrected per-instrument rescue is what controls the
multiple-testing problem: with dozens of strategies × grids × instruments, something
always looks good by chance."""),
    ("5 · Implementation & sizing",
     """A strategy's validated universe = every instrument of its accepted baskets plus its
Bonferroni-rescued tickers, each on an equal 1/N capital sleeve. The validated trades are
sized three independent ways — fixed-fraction (85% of sleeve equity), asset-volatility
targeting (2% daily target, 4× cap, recomputed daily) and strategy-volatility targeting
(10% annualized, 2× cap). Each variant produces a full equity curve across the **entire**
validated universe, and the best variant by portfolio Sharpe becomes the strategy's single
canonical curve — so what enters portfolio construction is each strategy's **best
implementation across all instruments and baskets that passed the gates**."""),
    ("6 · Portfolio assembly",
     """Each book is assembled by **greedy forward selection** on monthly returns over the
candidates' common window: start from the best-Sharpe candidate, then repeatedly add the
candidate that maximizes the Sharpe of the equal-weight blend — the algorithm naturally
prefers low-correlation additions over high-Sharpe clones. SHORT-TERM selects the top-5 of
a merged pool of 9 candidates; LONG-TERM the top-9 of 29."""),
    ("7 · Results",
     """The results **are** the equity curves: the chart above shows both books and the 50/50
blend; the Short-Term and Long-Term tabs have each book's equity, drawdown, selection path
and members. All figures are in-sample and net of modeled fees — read Sharpes as upper
bounds. Short-volatility strategies carry left-tail risk; long-term curves are
monthly-marked, so their daily volatility is understated."""),
]

# ─────────────────────────── pipeline flow ──────────────────────────

def pipeline_flow():
    stages = [
        ("01", "Signal research",
         "Notebook exploration of an economic rationale (trend, mean reversion, carry, flow). "
         "Entry/exit rules are written down and a bounded parameter grid is fixed BEFORE testing."),
        ("02", "v2 multi-asset backtest",
         "Phase 1: grid search per basket; canonical params = best MEDIAN Sharpe across the "
         "basket's instruments; binomial test on how many tickers work individually. "
         "Phase 2: trade-level records. SEC + TAF + $0.005/share slippage on every trade."),
        ("03", "Basket 3-gate test",
         "On the basket's composite monthly returns: one-sided t-test p<0.05, bootstrap "
         "5th-percentile Sharpe > 0 (5,000 resamples), sign-permutation p<0.05 (5,000 flips). "
         "All three must pass."),
        ("04", "Bonferroni rescue",
         "Failed baskets get a per-instrument retest at the corrected threshold α = 0.05/N. "
         "Individually significant tickers are rescued into the strategy's tradeable universe; "
         "the rest are dropped."),
        ("05", "Implementation & sizing",
         "Validated trades sized 3 ways: fixed-fraction 85%, asset-vol targeting (2% daily, 4×), "
         "strategy-vol targeting (10% ann, 2×). Best variant by portfolio Sharpe across the FULL "
         "validated universe becomes the canonical curve."),
        ("06", "Portfolio assembly",
         "Greedy forward selection on monthly returns over the common window: repeatedly add the "
         "candidate that maximizes the blend's Sharpe. SHORT-TERM keeps top-5 of 9; LONG-TERM "
         "top-9 of 29. Not selected -> archived here."),
    ]
    def row(items):
        flow = []
        for i, (num, name, desc) in enumerate(items):
            flow.append(html.Div(className="stage", children=[
                html.Div(num, className="num"), html.Div(name, className="name"),
                html.Div(desc, className="desc")]))
            if i < len(items) - 1:
                flow.append(html.Div("→", className="arrow"))
        return html.Div(className="pipeline", children=flow)
    return html.Div(children=[
        row(stages[:3]),
        html.Div("↓", className="arrow", style={"textAlign": "center", "margin": "6px 0"}),
        row(stages[3:])])

# ─────────────────────────── pages ──────────────────────────────────

def metric_card(label, meta, accent, sub=""):
    sharpe = meta.get("sharpe", "—"); cagr = meta.get("cagr_pct", "—")
    mdd = meta.get("maxdd_pct", "—"); n = len(meta.get("members", [])) or "—"
    return html.Div(className=f"card accent-{accent}", children=[
        html.Div(label, className="label"),
        html.Div(f"Sharpe {sharpe}", className="value"),
        html.Div(f"CAGR {cagr}%  ·  MaxDD {mdd}%  ·  {n} strategies{sub}", className="detail")])

def page_overview():
    return html.Div(className="page", children=[
        html.Div(className="panel", children=[
            html.H3("What is this project?"),
            dcc.Markdown(INTRO_MD, className="strategy-desc", link_target="_blank")]),
        html.Div(className="cards", children=[
            metric_card("Combined (50/50 books)", META["combined"], "combined"),
            metric_card("Short-Term book", META["short_term"], "short_term"),
            metric_card("Long-Term book", META["long_term"], "long_term")]),
        html.Div(className="panel", children=[
            html.H3("Growth of $100 — both books and the 50/50 blend"),
            html.Div("Y axis: value of $100 invested at inception (log scale, daily marks; "
                     "long-term curve steps monthly). X axis: date.", className="hint"),
            dcc.Graph(figure=equity_fig({**{p: EQ[p] for p in PORTS}, "combined": EQ["combined"]}),
                      config=GRAPH_CFG)]),
        html.Div(className="panel", children=[
            html.H3("Combined blend — drawdown"),
            dcc.Graph(figure=drawdown_fig(EQ["combined"], COLORS["combined"])
                      if EQ["combined"] is not None else go.Figure(),
                      config=GRAPH_CFG)]),
        html.Div(className="panel", children=[
            html.H3("The project, end to end")] + [
            html.Div(className="strategy-desc", children=[
                html.H4(t, style={"color": COLORS["text"], "marginBottom": "4px"}),
                dcc.Markdown(body)]) for t, body in METHODOLOGY_SECTIONS]),
    ])

def page_portfolio(p):
    meta, s = META[p], EQ[p]
    color = COLORS[p]
    members = meta.get("member_stats", [])
    rows = []
    for i, mrow in enumerate(members, 1):
        r = strat_row(mrow["strategy"])
        r = {"Step": i, **r}
        rows.append(r)
    intro = (f"The {PLABEL[p]} book: {HORIZON[p]}. "
             f"{len(members)} equal-weight strategies, listed in SELECTION ORDER (not Sharpe order): "
             "#1 is the best standalone Sharpe; each later pick is whichever candidate most "
             "improved the blend's Sharpe — diversification, not raw performance. "
             "Click a row for the strategy's rules, assets and reference.")
    blocks = [
        html.Div(className="panel", children=[
            html.H3(f"{PLABEL[p]} portfolio"),
            html.Div(intro, className="strategy-desc")]),
        html.Div(className="cards", children=[metric_card(PLABEL[p], meta, p)]),
    ]
    if s is not None:
        blocks.append(html.Div(className="panel", children=[
            html.H3("Equity curve"),
            html.Div("Y axis: value of $100 invested at inception (log scale). X axis: date.",
                     className="hint"),
            dcc.Graph(figure=equity_fig({p: s}), config=GRAPH_CFG)]))
        blocks.append(html.Div(className="panel", children=[
            html.H3("Drawdown"),
            dcc.Graph(figure=drawdown_fig(s, color), config=GRAPH_CFG)]))
    spf = selection_path_fig(meta, color, len(members))
    if spf is not None:
        blocks.append(html.Div(className="panel", children=[
            html.H3("Greedy selection path"),
            html.Div("Each step adds the candidate that maximizes the blend's Sharpe; "
                     "the dotted line marks where selection stops.", className="hint"),
            dcc.Graph(figure=spf, config=GRAPH_CFG)]))
    blocks.append(html.Div(className="panel", children=[
        html.H3("Members — in greedy selection order (Step) — click a row for details"),
        clickable_table(rows, f"members-{p}", sortable=False,
                        columns=["Step", "Strategy", "Sharpe", "CAGR %", "MaxDD %", "3-gate", "Months"]),
        html.Div(id={"type": "sdetail", "group": f"members-{p}"},
                 children=strategy_description_block(None))]))
    return html.Div(className="page", children=blocks)

def page_archived():
    def not_in_book(sleeve):
        keys = [k for k, v in STRATS.items()
                if v["meta"].get("sleeve") == sleeve and not v["meta"].get("in_portfolio")]
        rows = [strat_row(k) for k in keys]
        return sorted(rows, key=lambda r: -(r["Sharpe"] if isinstance(r["Sharpe"], (int, float)) else -9))
    lt_rows = not_in_book("long_term")
    st_rows = not_in_book("short_term")
    return html.Div(className="page", children=[
        html.Div(className="panel", children=[
            html.H3("Archived strategies"),
            html.Div("Candidates that went through the full pipeline below but were NOT "
                     "selected into the books — usually too correlated with a member, or the "
                     "edge didn't survive costs. Click a row for details.",
                     className="strategy-desc")]),
        html.Div(className="panel", children=[
            html.H3("The decision pipeline"), pipeline_flow()]),
        html.Div(className="panel", children=[
            html.H3(f"Long-term candidates not selected ({len(lt_rows)})"),
            clickable_table(lt_rows, "arch-lt"),
            html.Div(id={"type": "sdetail", "group": "arch-lt"},
                     children=strategy_description_block(None))]),
        html.Div(className="panel", children=[
            html.H3(f"Short-term candidates not selected ({len(st_rows)})"),
            clickable_table(st_rows, "arch-st"),
            html.Div(id={"type": "sdetail", "group": "arch-st"},
                     children=strategy_description_block(None))]),
    ])

# ─────────────────────────── app ────────────────────────────────────

app = dash.Dash(__name__, title="Portfolio Dashboard")
server = app.server

app.layout = html.Div([
    html.Div(className="header", children=[
        html.H1("Portfolio Dashboard"),
        html.Div("Short-Term · Long-Term — systematic strategy research, validation and assembly",
                 className="sub")]),
    dcc.Tabs(id="tabs", value="overview", className="tabs-bar", children=[
        dcc.Tab(label="Overview", value="overview", className="tab", selected_className="tab--selected"),
        dcc.Tab(label="Short-Term", value="short_term", className="tab", selected_className="tab--selected"),
        dcc.Tab(label="Long-Term", value="long_term", className="tab", selected_className="tab--selected"),
        dcc.Tab(label="Archived Strategies", value="archived", className="tab", selected_className="tab--selected")]),
    html.Div(id="page"),
    html.Div("Backtest results — in-sample, net of modeled fees. Not investment advice.",
             className="footer")])

@app.callback(Output("page", "children"), Input("tabs", "value"))
def route(tab):
    if tab == "overview": return page_overview()
    if tab in PORTS: return page_portfolio(tab)
    if tab == "archived": return page_archived()
    return html.Div()

@app.callback(Output({"type": "sdetail", "group": MATCH}, "children"),
              Input({"type": "stable", "group": MATCH}, "active_cell"),
              State({"type": "stable", "group": MATCH}, "derived_viewport_data"))
def show_detail(active_cell, rows):
    if not active_cell or not rows:
        return strategy_description_block(None)
    i = active_cell.get("row")
    if i is None or i >= len(rows):
        return strategy_description_block(None)
    return strategy_description_block(rows[i].get("key"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 7860)),
            debug=os.environ.get("DASH_DEBUG", "false").lower() == "true")
