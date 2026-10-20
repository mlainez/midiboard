"""Compare a KiCad netlist (kicadsexpr) against design.py connectivity."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from design import PARTS  # noqa: E402
from sexpr import find, parse, val  # noqa: E402

root = parse(open(sys.argv[1]).read())
got = {}
for net in find(find(root, "nets")[0], "net"):
    name = val(net, "name").lstrip("/")
    for node in find(net, "node"):
        ref = val(node, "ref")
        if not ref.startswith("#"):
            got[(ref, val(node, "pin"))] = name
want = {(r, n): net for r, p in PARTS.items() for n, net in p["pins"].items() if net}
bad = 0
for k, v in sorted(want.items()):
    if got.get(k) != v:
        print("MISMATCH", k, "want", v, "got", got.get(k))
        bad += 1
for k, v in sorted(got.items()):
    if k not in want and not v.startswith("unconnected-"):
        print("EXTRA", k, v)
        bad += 1
print(f"{len(want)} connections checked, {bad} problems")
sys.exit(1 if bad else 0)
