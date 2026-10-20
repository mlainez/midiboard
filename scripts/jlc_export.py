"""Write JLCPCB fabrication files: gerber zip, BOM and CPL (pick & place).

usage: python3 jlc_export.py "<kicad-cli command>"
"""
import csv
import os
import shlex
import shutil
import subprocess
import sys
from collections import defaultdict

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
from design import JLC_ROTATION, PARTS, PROJECT  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, PROJECT + ".kicad_pcb")
OUT = os.path.join(ROOT, "jlcpcb")
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def gerbers(kicad_cli):
    gdir = os.path.join(ROOT, "build", "gerbers")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    cli = shlex.split(kicad_cli)
    subprocess.run(cli + ["pcb", "export", "gerbers", "-o", gdir + "/", "-l", LAYERS,
                          "--subtract-soldermask", "--check-zones", PCB], check=True)
    subprocess.run(cli + ["pcb", "export", "drill", "-o", gdir + "/", "--format", "excellon",
                          "--excellon-units", "mm", "--excellon-zeros-format", "decimal",
                          "--excellon-oval-format", "alternate", "--excellon-separate-th", PCB], check=True)
    zip_base = os.path.join(OUT, PROJECT + "-gerbers")
    shutil.make_archive(zip_base, "zip", gdir)
    print("wrote", zip_base + ".zip", sorted(os.listdir(gdir)))


def bom_and_cpl():
    board = pcbnew.LoadBoard(PCB)
    groups = defaultdict(list)
    rows = []
    for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
        ref = fp.GetReference()
        part = PARTS.get(ref)
        if not part or not part["lcsc"]:
            continue
        fpid = part["fp"]
        groups[(part["value"], fpid.split(":")[1], part["lcsc"])].append(ref)
        pos = fp.GetPosition()
        rot = (fp.GetOrientationDegrees() + JLC_ROTATION.get(fpid, 0)) % 360
        rows.append([ref, f"{pcbnew.ToMM(pos.x):.4f}mm", f"{-pcbnew.ToMM(pos.y):.4f}mm",
                     "Top" if fp.GetLayer() == pcbnew.F_Cu else "Bottom", f"{rot:.0f}"])

    with open(os.path.join(OUT, PROJECT + "-BOM.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fpname, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            w.writerow([value, ",".join(refs), fpname, lcsc])

    with open(os.path.join(OUT, PROJECT + "-CPL.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        w.writerows(rows)
    print("wrote BOM and CPL:", ", ".join(r[0] for r in rows))


def main():
    os.makedirs(OUT, exist_ok=True)
    gerbers(sys.argv[1])
    bom_and_cpl()


if __name__ == "__main__":
    main()
