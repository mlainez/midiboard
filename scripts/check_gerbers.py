"""Independent connectivity check of the manufacturing files.

Rasterizes the copper gerbers with gerbv, joins the layers through every plated hole of the
drill file, and derives which pads are electrically connected purely from copper geometry.
The result is compared with the nets in design.py. KiCad net assignments are not used; KiCad
is only asked where each pad is.

usage: python3 check_gerbers.py   (needs gerbv, numpy, scipy, pillow and the KiCad 7 pcbnew module)
"""
import itertools
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(__file__))
from design import PARTS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDIR = os.path.join(ROOT, "build", "gerbers")
DPI = 2000
# Gerber-coordinate window (mm), slightly larger than the board.
X0, Y0, W, H = 99.0, -140.0, 48.0, 41.0

Image.MAX_IMAGE_PIXELS = None


def render(layer_file, tmp):
    out = os.path.join(tmp, os.path.basename(layer_file) + ".png")
    subprocess.run(["gerbv", "-x", "png", "-D", str(DPI), "-B", "0",
                    f"--origin={X0 / 25.4:.5f}x{Y0 / 25.4:.5f}", f"--window_inch={W / 25.4:.5f}x{H / 25.4:.5f}",
                    "-b", "#000000", "-f", "#FFFFFFFF", "-o", out, layer_file],
                   check=True, env={k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")})
    img = np.asarray(Image.open(out).convert("L")) > 127
    labels, n = ndimage.label(img)
    return labels, n


def px(x_mm, y_gerber_mm, shape):
    col = (x_mm - X0) * DPI / 25.4
    row = (Y0 + H - y_gerber_mm) * DPI / 25.4
    r, c = int(round(row)), int(round(col))
    assert 0 <= r < shape[0] and 0 <= c < shape[1], (x_mm, y_gerber_mm)
    return r, c


def drill_hits(path):
    hits, tools, cur = [], {}, None
    for line in open(path):
        line = line.strip()
        m = re.match(r"^(T\d+)C([\d.]+)", line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        if re.fullmatch(r"T\d+", line):
            cur = line
            continue
        m = re.match(r"^X(-?[\d.]+)Y(-?[\d.]+)", line)
        if m and cur:
            hits.append((float(m.group(1)), float(m.group(2)), tools[cur]))
    return hits


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def main():
    import pcbnew

    with tempfile.TemporaryDirectory() as tmp:
        front, nf = render(os.path.join(GDIR, "midiboard-F_Cu.gtl"), tmp)
        back, nb = render(os.path.join(GDIR, "midiboard-B_Cu.gbl"), tmp)
    print(f"copper regions: F.Cu {nf}, B.Cu {nb}")

    dsu = DSU()
    holes = drill_hits(os.path.join(GDIR, "midiboard-PTH.drl"))
    for x, y, d in holes:
        f, b = front[px(x, y, front.shape)], back[px(x, y, back.shape)]
        assert f and b, f"plated hole at ({x}, {y}) has no copper on both layers"
        dsu.union(("F", f), ("B", b))
    print(f"plated holes joining layers: {len(holes)}")

    board = pcbnew.LoadBoard(os.path.join(ROOT, "midiboard.kicad_pcb"))
    pad_region = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for i, pad in enumerate(fp.Pads()):
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            num = pad.GetNumber() or f"MP{i}"
            pos = pad.GetPosition()
            x, y = pcbnew.ToMM(pos.x), -pcbnew.ToMM(pos.y)
            layer = "B" if pad.GetLayerSet().Contains(pcbnew.B_Cu) and not pad.GetLayerSet().Contains(pcbnew.F_Cu) else "F"
            img = front if layer == "F" else back
            lab = img[px(x, y, img.shape)]
            assert lab, f"{ref}.{num}: no copper under pad centre (raster misaligned?)"
            pad_region[(ref, num)] = dsu.find((layer, lab))

    groups = {}
    for k, root in pad_region.items():
        groups.setdefault(root, []).append(k)

    errors = 0
    want = {}
    for ref, p in PARTS.items():
        for num, net in p["pins"].items():
            want[(ref, num)] = net
    for net in sorted({n for n in want.values() if n}):
        pads = [k for k, v in want.items() if v == net]
        roots = {pad_region[k] for k in pads}
        if len(roots) != 1:
            print(f"OPEN   {net}: pads split over {len(roots)} copper regions: {sorted(pads)}")
            errors += 1
    for a, b in itertools.combinations(sorted({n for n in want.values() if n}), 2):
        ra = {pad_region[k] for k, v in want.items() if v == a}
        rb = {pad_region[k] for k, v in want.items() if v == b}
        if ra & rb:
            print(f"SHORT  {a} <-> {b}")
            errors += 1
    for k, root in pad_region.items():
        if want.get(k) is None:
            others = [o for o in groups[root] if o != k]
            if others:
                print(f"NC pad {k} touches {others}")
                errors += 1

    print("\nnetlist derived from gerber copper:")
    for root, pads in sorted(groups.items(), key=lambda kv: sorted(kv[1])):
        if len(pads) > 1:
            nets = {want.get(p) for p in pads}
            print(f"  {'/'.join(str(n) for n in nets):12s} {' '.join(f'{r}.{n}' for r, n in sorted(pads))}")
    print(f"\n{len(pad_region)} pads probed, {errors} connectivity errors")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
