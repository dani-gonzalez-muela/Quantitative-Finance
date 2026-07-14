---
title: Portfolio Dashboard
emoji: 📈
colorFrom: gray
colorTo: green
sdk: docker
pinned: false
---

# Portfolio Dashboard

Unified view of the TWO-portfolio system — **Short-Term / Long-Term** — plus the
Combined 50/50 book blend (reporting only), clickable per-strategy details, and
the validation decision pipeline.

## Pages

| Tab | Contents |
|---|---|
| Overview | Project intro, metric cards, growth-of-$100 comparison, drawdown, full end-to-end methodology write-up (7 sections) |
| Short-Term / Long-Term | Horizon intro, equity/drawdown/greedy-path plots, clickable member table (greedy selection order) -> per-strategy rules, assets, reference |
| Archived Strategies | Decision-pipeline flow + the candidates NOT selected into the books (LT and ST tables, 3-gate + Bonferroni columns, clickable rows) |

## Run

```
pip install -r requirements.txt
python app.py            # http://127.0.0.1:7860
```

## Files

| File | Role |
|---|---|
| `app.py` | The Dash app (reads only `dashboard_data/`) |
| `assets/style.css` | Theme + table/hover styling |
| `dashboard_data/` | Display copies: per-strategy `equity.csv` + `meta.json`, portfolio curves + metas |
| `build_dashboard_data.py` | Regenerates `dashboard_data/` from `3. Portfolio_construction` + strategy results (`BUILD_dashboard_data.bat` wraps it) |
| `Dockerfile`, `requirements.txt` | Local/HF-Spaces deploy of THIS app |

## Deploy to Hugging Face Spaces

Push this folder to a Docker Space (Dockerfile included, listens on 7860).
No repo data needed — the app reads only `dashboard_data/`.

To edit a strategy's description/reference shown in the UI: edit its
`dashboard_data/strategies/<name>/meta.json` (`description`, `reference` fields);
custom text survives `build_dashboard_data.py` rebuilds.
