"""Re-export of `0. Data/loaders/data.py` (market-data fetching; gitignored — holds API keys).

Import as:  from _shared.loaders_data import fetch_historical_data, get_api_keys
Replaces the retired root `data/` package (removed 2026-07-11).
"""
import importlib.util as _ilu
import os as _os

_d = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.exists(_os.path.join(_d, '.project_root')):
    _parent = _os.path.dirname(_d)
    assert _parent != _d, '.project_root marker not found'
    _d = _parent

_p = _os.path.join(_d, '0. Data', 'loaders', 'data.py')
if not _os.path.exists(_p):
    raise ImportError(
        f"Loader module not found: {_p}\n"
        "The '0. Data/loaders/' folder is gitignored (contains API keys) - "
        "restore it locally to run backtests.")
_spec = _ilu.spec_from_file_location('_loaders_data_impl', _p)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith('__')})
