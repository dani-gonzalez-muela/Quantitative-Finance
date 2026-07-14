# Sector Rotation Hybrid

**Portfolio:** Long-Term | **Status:** ❌ Superseded by `sector_momentum` | **Canonical:** none (prototype only)

## 1. Strategy

Early prototype combining momentum-ranked sector rotation with a second composite
signal (blend ranking over the 11 sector ETFs, monthly rebalance).

## 2. Status & verdict — SUPERSEDED

The validated `sector_momentum` (selection family) covers the momentum-rotation space
with the full v2 pipeline; the *hybrid's* additional signal was never validated, and a
pre-v2-era standalone run isn't comparable to current methodology. Additionally, this
folder's `v1/` turned out to be a mixed dump of pre-v2 research outputs (dual momentum,
January effect, best-six-months, EM–DM rotation, country rotation) — most of which
later became proper strategies elsewhere in the tree. Verdict: archived as superseded;
the only revivable idea is the hybrid blend itself, whose null hypothesis (adds nothing
over plain sector momentum) would be the first test.

## 3. Files

| File | Description |
|---|---|
| `v1/` | Prototype notebook + mixed pre-v2 research outputs (historical record) |
