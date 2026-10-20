"""Autoroute midiboard.kicad_pcb with Freerouting (headless), then add GND pours on both layers.

usage: python3 route.py <freerouting.jar>
"""
import os
import subprocess
import sys

import pcbnew
from pcbnew import FromMM, VECTOR2I

sys.path.insert(0, os.path.dirname(__file__))
from sexpr import find, parse  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, "midiboard.kicad_pcb")
BUILD = os.path.join(ROOT, "build")

# The MIDI IN side is galvanically isolated: no ground copper under the IN jack or the opto LED circuit.
IN_KEEPOUT = [(100, 100), (123, 100), (123, 120.3), (110.6, 120.3), (110.6, 131), (100, 131)]


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def autoroute(jar):
    os.makedirs(BUILD, exist_ok=True)
    dsn, ses = os.path.join(BUILD, "midiboard.dsn"), os.path.join(BUILD, "midiboard.ses")
    board = pcbnew.LoadBoard(PCB)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise RuntimeError("DSN export failed")
    env = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}
    subprocess.run(["java", "-Djava.awt.headless=true", "-jar", jar, "--gui.enabled=false",
                    "-de", dsn, "-do", ses, "-mp", "40", "-mt", "1"], check=True, env=env, cwd=BUILD)
    import_ses(board, ses)
    return board


def import_ses(board, path):
    """Add the wires and vias of a Specctra session to the board (KiCad 7's importer needs the GUI)."""
    routes = find(parse(open(path).read()), "routes")[0]
    res = find(routes, "resolution")[0]
    assert res[1] == "um", res
    scale = 1000.0 * float(res[2])  # session units per mm

    def pt(x, y):
        return VECTOR2I(FromMM(float(x) / scale), FromMM(-float(y) / scale))

    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    for net in find(find(routes, "network_out")[0], "net"):
        ni = board.FindNet(net[1])
        for wire in find(net, "wire"):
            path = find(wire, "path")[0]
            layer, width, coords = layers[path[1]], FromMM(float(path[2]) / scale), path[3:]
            pts = [pt(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(a)
                t.SetEnd(b)
                t.SetWidth(width)
                t.SetLayer(layer)
                t.SetNet(ni)
                board.Add(t)
        for via in find(net, "via"):
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pt(via[2], via[3]))
            v.SetDrill(FromMM(0.3))
            v.SetWidth(FromMM(0.6))
            v.SetNet(ni)
            board.Add(v)


def remove_dangling(board):
    """Delete track stubs Freerouting sometimes leaves past a via (an end touching nothing)."""
    removed = 0
    while True:
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
        vias = [v for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]
        pads = list(board.GetPads())

        def connected(t, pt):
            for o in tracks:
                if o is not t and o.GetLayer() == t.GetLayer() and pt in (o.GetStart(), o.GetEnd()):
                    return True
            if any(v.GetPosition() == pt for v in vias):
                return True
            return any(p.IsOnLayer(t.GetLayer()) and p.HitTest(pt) for p in pads)

        dangling = [t for t in tracks if not (connected(t, t.GetStart()) and connected(t, t.GetEnd()))]
        if not dangling:
            return removed
        for t in dangling:
            board.Remove(t)
        removed += len(dangling)


def add_zones(board):
    gnd = board.FindNet("GND")
    outline = [(100, 100), (146, 100), (146, 139), (100, 139)]
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(gnd)
        z.SetLocalClearance(FromMM(0.4))
        z.SetMinThickness(FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(FromMM(0.4))
        z.SetThermalReliefSpokeWidth(FromMM(0.4))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        poly = z.Outline()
        poly.NewOutline()
        for p in outline:
            poly.Append(FromMM(p[0]), FromMM(p[1]))
        board.Add(z)

        k = pcbnew.ZONE(board)
        k.SetIsRuleArea(True)
        k.SetLayer(layer)
        k.SetDoNotAllowCopperPour(True)
        k.SetDoNotAllowTracks(False)
        k.SetDoNotAllowVias(False)
        k.SetDoNotAllowPads(False)
        k.SetDoNotAllowFootprints(False)
        kp = k.Outline()
        kp.NewOutline()
        for p in IN_KEEPOUT:
            kp.Append(FromMM(p[0]), FromMM(p[1]))
        board.Add(k)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())


def main():
    board = autoroute(sys.argv[1])
    print("removed dangling track segments:", remove_dangling(board))
    add_zones(board)
    pcbnew.SaveBoard(PCB, board)
    print("routed and saved", PCB)


if __name__ == "__main__":
    main()
