"""
_shared/paths.py
================
Single source of truth for project-root discovery and data-store locations.

Scripts call:

    from _shared.paths import PROJECT_ROOT, data_dir, data_file

    DATA_DIR = data_dir('daily_tickers')      # daily ETF OHLCV CSVs
    INTRA    = data_dir('intraday_5min')      # 5-min gzipped OHLCV CSVs
    VIX_CSV  = data_file('vix', 'VIXCLS.csv') # a file inside a store

Root discovery walks UP from this file until it finds the `.project_root`
marker, so it works from any folder depth and survives any folder move.

Data stores are declared once, in `0. Data/README.md`, inside the
`STORE-REGISTRY` markers (a simple `store | path` pipe table). To relocate a
store physically, edit that table only; no script changes needed.

Bootstrapping note: scripts that can't import `_shared` yet should use the
snippet below to find the root and put it on sys.path (works at any depth):

    import os, sys
    _d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(_d, '.project_root')):
        _p = os.path.dirname(_d)
        assert _p != _d, '.project_root marker not found above ' + __file__
        _d = _p
    sys.path.insert(0, _d)
"""
import os
import re
import functools

# Where the dataset registry lives, relative to the project root.
# 2026-07-11: DATASETS.md consolidated into 0. Data/README.md (same STORE-REGISTRY markers).
_REGISTRY_DOC = os.path.join('0. Data', 'README.md')
_REGISTRY_RE = re.compile(
    r'<!--\s*STORE-REGISTRY:START\s*-->(.*?)<!--\s*STORE-REGISTRY:END\s*-->',
    re.DOTALL | re.IGNORECASE,
)


def find_project_root(start=None):
    d = os.path.abspath(start or os.path.dirname(__file__))
    while True:
        if os.path.exists(os.path.join(d, '.project_root')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise RuntimeError(f'.project_root marker not found above {start}')
        d = parent


PROJECT_ROOT = find_project_root()


@functools.lru_cache(maxsize=1)
def _stores():
    """Parse the store->path table out of the registry doc (0. Data/README.md)."""
    doc = os.path.join(PROJECT_ROOT, _REGISTRY_DOC)
    with open(doc, encoding='utf-8') as f:
        text = f.read()
    m = _REGISTRY_RE.search(text)
    if not m:
        raise RuntimeError(
            f'STORE-REGISTRY markers not found in {doc!r}. The dataset '
            f'registry must sit between <!-- STORE-REGISTRY:START --> and '
            f'<!-- STORE-REGISTRY:END -->.'
        )
    stores = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip().strip('`').strip() for c in line.strip('|').split('|')]
        if len(cells) < 2:
            continue
        key, path = cells[0], cells[1]
        # skip the header row and the |---|---| separator
        if not key or key.lower() == 'store' or set(key) <= set('-: '):
            continue
        stores[key] = path
    if not stores:
        raise RuntimeError(f'No stores parsed from the registry in {doc!r}.')
    return stores


def data_dir(store):
    """Absolute path to a named data store (see 0. Data/README.md)."""
    stores = _stores()
    if store not in stores:
        raise KeyError(f"Unknown data store '{store}'. Known: {sorted(stores)}")
    return os.path.normpath(os.path.join(PROJECT_ROOT, stores[store]))


def data_file(store, *parts):
    """Absolute path to a file inside a named data store."""
    return os.path.join(data_dir(store), *parts)
