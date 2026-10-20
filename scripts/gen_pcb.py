"""Place footprints, board outline and silkscreen for midiboard.kicad_pcb (KiCad 7 pcbnew API).

Routing is done afterwards by route.sh (Freerouting); add_zones.py then adds the ground pours.
"""
import os
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

sys.path.insert(0, os.path.dirname(__file__))
from design import PARTS, PROJECT  # noqa: E402
from sexpr import find, parse, val  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPDIR = "/usr/share/kicad/footprints"

# Board: 46 x 39 mm, front edge (jack faces) at y = Y0.
X0, Y0, W, H = 100.0, 100.0, 46.0, 39.0
CORNER = 1.0

# (x, y, rotation) in mm / degrees.
PLACE = {
    "J1": (111.5, 100.0, 0), "J2": (134.5, 100.0, 0),
    "R1": (105.0, 122.0, 0), "D1": (104.0, 126.5, 90),
    "U1": (113.5, 125.5, 0),
    "C1": (121.5, 123.0, 90), "R2": (121.5, 128.0, 90),
    "JP1": (124.3, 124.73, 0), "R3": (127.0, 126.0, 90),
    "R5": (128.6, 122.2, 90),
    "U2": (131.8, 126.2, 0), "C2": (132.0, 122.4, 0),
    "R4": (136.2, 126.5, 90), "R7": (138.6, 126.5, 90), "R6": (138.6, 122.0, 90),
    # Rotated so pins 1/4 (the 3V3 slider position) face the jacks.
    "SW1": (142.8, 125.5, 270),
    "J4": (109.0, 135.5, 90), "J3": (128.0, 135.5, 90),
    "H1": (103.5, 135.5, 0), "H2": (142.5, 135.5, 0),
}

# KiCad's library has no 3D model for the SMD JS202011JCQN; scripts/gen_switch_model.py writes one.
MODELS = {"SW1": "${KIPRJMOD}/lib/midiboard.3dshapes/SW_DPDT_CK_JS202011JCQN.wrl"}

HEADER_LABELS = {"J4": ["i4", "i5", "o5", "o2", "o4"], "J3": ["TX", "RX", "GND", "VCC"]}


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(ROOT, "lib", lib + ".pretty") if lib == PROJECT else os.path.join(FPDIR, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def text(board, s, x, y, layer=pcbnew.F_SilkS, size=0.8, thick=0.15, angle=0, bold=False, width=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(mm(x, y))
    t.SetLayer(layer)
    t.SetTextSize(mm(width or size, size))
    t.SetTextThickness(FromMM(thick))
    t.SetTextAngleDegrees(angle)
    t.SetBold(bold)
    if layer in (pcbnew.B_SilkS, pcbnew.B_Cu):
        t.SetMirrored(True)
    board.Add(t)


def edge_line(board, a, b):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(mm(*a))
    s.SetEnd(mm(*b))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(FromMM(0.1))
    board.Add(s)


def edge_arc(board, center, start_deg):
    import math
    cx, cy = center
    pts = []
    for d in (start_deg, start_deg + 45, start_deg + 90):
        r = math.radians(d)
        pts.append(mm(cx + CORNER * math.cos(r), cy + CORNER * math.sin(r)))
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(*pts)
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(FromMM(0.1))
    board.Add(s)


def outline(board):
    x1, y1, x2, y2, r = X0, Y0, X0 + W, Y0 + H, CORNER
    edge_line(board, (x1 + r, y1), (x2 - r, y1))
    edge_line(board, (x2, y1 + r), (x2, y2 - r))
    edge_line(board, (x2 - r, y2), (x1 + r, y2))
    edge_line(board, (x1, y2 - r), (x1, y1 + r))
    edge_arc(board, (x1 + r, y1 + r), 180)
    edge_arc(board, (x2 - r, y1 + r), 270)
    edge_arc(board, (x2 - r, y2 - r), 0)
    edge_arc(board, (x1 + r, y2 - r), 90)


def design_rules(board):
    ds = board.GetDesignSettings()
    board.SetCopperLayerCount(2)
    # JLCPCB standard 2-layer capabilities, with margin.
    ds.m_MinClearance = FromMM(0.15)
    ds.m_TrackMinWidth = FromMM(0.15)
    ds.m_ViasMinSize = FromMM(0.5)
    ds.m_ViasMinAnnularWidth = FromMM(0.13)
    ds.m_MinThroughDrill = FromMM(0.3)
    ds.m_HoleClearance = FromMM(0.25)
    ds.m_HoleToHoleMin = FromMM(0.5)
    ds.m_CopperEdgeClearance = FromMM(0.3)
    ds.m_SilkClearance = FromMM(0.0)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(FromMM(0.2))
    nc.SetTrackWidth(FromMM(0.3))
    nc.SetViaDiameter(FromMM(0.6))
    nc.SetViaDrill(FromMM(0.3))


def main():
    out = os.path.join(ROOT, PROJECT + ".kicad_pcb")
    board = pcbnew.NewBoard(out)
    design_rules(board)
    outline(board)

    uuids = dict(line.split() for line in open(os.path.join(ROOT, "scripts", "symbol_uuids.txt")))

    # Net names come from the schematic netlist so the board matches the schematic exactly.
    pad_net = {}
    nets = {}
    netlist = parse(open(os.path.join(ROOT, "build", PROJECT + ".net")).read())
    for net in find(find(netlist, "nets")[0], "net"):
        name = val(net, "name")
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
        for node in find(net, "node"):
            pad_net[(val(node, "ref"), val(node, "pin"))] = name

    for ref, p in PARTS.items():
        fp = load_fp(p["fp"])
        fp.SetReference(ref)
        fp.SetValue(p["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + uuids[ref]))
        x, y, rot = PLACE[ref]
        board.Add(fp)
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        if p["lcsc"]:
            fp.SetProperty("LCSC", p["lcsc"])
        if p.get("mpn"):
            fp.SetProperty("MPN", p["mpn"])
        for pad in fp.Pads():
            net = pad_net.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(nets[net])
        # Keep designators small and out of the way of the dense area.
        r = fp.Reference()
        r.SetTextSize(mm(0.8, 0.8))
        r.SetTextThickness(FromMM(0.12))
        fp.Value().SetVisible(False)
        if ref in MODELS:
            model = pcbnew.FP_3DMODEL()
            model.m_Filename = MODELS[ref]
            fp.Models().clear()
            fp.Models().push_back(model)

    place_refs(board)
    silkscreen(board)
    pcbnew.SaveBoard(out, board)
    print("wrote", out)


def place_refs(board):
    """Designator positions (absolute, mm). Header and jack designators are hidden; their silk labels say enough."""
    pos = {
        "R1": (105.0, 120.8), "D1": (102.3, 126.5, 90), "U1": (113.5, 125.5),
        "C1": (120.0, 120.9), "R2": (120.0, 130.6), "JP1": (124.3, 122.6), "R3": (127.5, 128.4),
        "R5": (126.4, 121.0), "U2": (131.8, 129.0), "C2": (132.0, 121.1), "R4": (136.2, 129.2),
        "R7": (138.6, 129.4), "R6": (136.6, 120.9),
    }
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        r = fp.Reference()
        if ref in pos:
            x, y, *a = pos[ref]
            r.SetPosition(mm(x, y))
            # Footprint text angles are stored relative to the footprint.
            r.SetTextAngleDegrees((a[0] if a else 0) - fp.GetOrientationDegrees())
        else:
            r.SetVisible(False)


def silkscreen(board):
    for ref, labels in HEADER_LABELS.items():
        x, y, _ = PLACE[ref]
        for i, s in enumerate(labels):
            text(board, s, x + 2.54 * i, y - 2.0, size=0.8, thick=0.13, width=0.6)
    text(board, "JACKS", 114.08, 137.9, size=0.8, thick=0.15)
    text(board, "MCU", 131.81, 137.9, size=0.8, thick=0.15)
    text(board, "THRU", 124.3, 129.4, size=0.8, thick=0.15)
    text(board, "MIDI IN", 111.5, 118.0, size=1.2, thick=0.2, bold=True)
    text(board, "MIDI OUT/THRU", 134.5, 118.0, size=1.2, thick=0.2, bold=True)
    text(board, "3V3", 142.8, 120.1, size=0.8, thick=0.15)
    text(board, "5V", 142.8, 130.9, size=0.8, thick=0.15)

    text(board, "MIDI IN", 111.5, 108.0, layer=pcbnew.B_SilkS, size=1.5, thick=0.25, bold=True)
    text(board, "MIDI OUT / THRU", 134.5, 108.0, layer=pcbnew.B_SilkS, size=1.5, thick=0.25, bold=True)
    text(board, "MIDI IN/OUT 3V3/5V v1.2", 134.5, 105.5, layer=pcbnew.B_SilkS, size=1.0, thick=0.15)
    text(board, "Set SW1 to match VCC", 123.0, 132.8, layer=pcbnew.B_SilkS, size=0.8, thick=0.15)
    text(board, "HARD THRU: jumper on JP1, leave TX open", 123.0, 130.5, layer=pcbnew.B_SilkS, size=0.8, thick=0.15)


if __name__ == "__main__":
    main()
