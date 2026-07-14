"""fix_imports.py — switch `shared` imports to `_shared`, then verify the resolver.
  python _shared/fix_imports.py          # DRY-RUN: list changes, touch nothing
  python _shared/fix_imports.py --apply  # rewrite files, then verify
  python _shared/fix_imports.py --verify # only check the resolver"""
import os, sys, re, json, io
APPLY = "--apply" in sys.argv
VERIFY = "--verify" in sys.argv or APPLY
_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, ".project_root")):
    _p = os.path.dirname(_d); assert _p != _d, ".project_root not found"; _d = _p
ROOT = _d
SKIP = {".git", ".ipynb_checkpoints", "__pycache__", "node_modules", "_delete"}
SELF = os.path.abspath(__file__)
_SUBS = [(re.compile(r'(^\s*from\s+)shared(\.\w+)'), r'\1_shared\2'),
         (re.compile(r'(^\s*from\s+)shared(\s+import\b)'), r'\1_shared\2'),
         (re.compile(r'(^\s*import\s+)shared(\.|\s|,|$)'), r'\1_shared\2')]
def fix_line(l):
    for rx, rp in _SUBS: l = rx.sub(rp, l)
    return l
def fix_text(t):
    out, n = [], 0
    for ln in t.splitlines(keepends=True):
        nl = fix_line(ln); n += nl != ln; out.append(nl)
    return "".join(out), n
def fix_nb(t):
    nb = json.loads(t); n = 0
    for c in nb.get("cells", []):
        if c.get("cell_type") != "code": continue
        s = c.get("source", [])
        joined = s if isinstance(s, str) else "".join(s)
        fixed, k = fix_text(joined)          # split on lines -> robust to embedded \n
        if k:
            c["source"] = fixed if isinstance(s, str) else fixed.splitlines(keepends=True)
            n += k
    return json.dumps(nb, ensure_ascii=False, indent=1), n
def walk():
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP]
        for fn in fns:
            if fn.endswith((".py", ".ipynb")): yield os.path.join(dp, fn)
def rewrite():
    tf = tl = 0
    for p in walk():
        if os.path.abspath(p) == SELF: continue
        try:
            with io.open(p, encoding="utf-8") as f: t = f.read()
        except (UnicodeDecodeError, OSError): continue
        if "shared" not in t: continue
        new, n = (fix_nb if p.endswith(".ipynb") else fix_text)(t)
        if not n: continue
        tf += 1; tl += n
        print(f"  {'wrote' if APPLY else 'would fix'} {n:>3}  {os.path.relpath(p, ROOT)}")
        if APPLY:
            with io.open(p, "w", encoding="utf-8") as f: f.write(new)
    print(f"\n{'Rewrote' if APPLY else 'Would rewrite'} {tl} line(s) in {tf} file(s).")
    if not APPLY: print("DRY-RUN only. Re-run with --apply to write.")
def verify():
    print("\n--- verifying resolver ---")
    if ROOT not in sys.path: sys.path.insert(0, ROOT)
    try:
        from _shared.paths import data_dir, _stores, PROJECT_ROOT
    except Exception as e:
        print(f"  FAILED to import _shared.paths: {e}"); return
    print(f"  PROJECT_ROOT = {PROJECT_ROOT}")
    ok = True
    for st in sorted(_stores()):
        p = data_dir(st); ex = os.path.exists(p); ok &= ex
        print(f"  [{'ok ' if ex else 'MISSING'}] {st:<30} -> {os.path.relpath(p, PROJECT_ROOT)}")
    print("  all stores resolve." if ok else "  some MISSING — check DATASETS.md registry.")
if __name__ == "__main__":
    print(f"[{'APPLY' if APPLY else 'DRY-RUN'}] root: {ROOT}\n")
    rewrite()
    if VERIFY: verify()
