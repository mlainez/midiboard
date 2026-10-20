"""Generate midiboard.kicad_sch from design.py (requires kiutils)."""
import copy
import os
import sys
import uuid

from kiutils.items.common import Effects, Font, Justify, Position, Property
from kiutils.items.schitems import (LocalLabel, NoConnect, SchematicSymbol, SymbolProjectInstance,
                                    SymbolProjectPath, Text)
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib

sys.path.insert(0, os.path.dirname(__file__))
from design import PARTS, POWER_NETS, PROJECT  # noqa: E402

SYMDIR = "/usr/share/kicad/symbols"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

G = 2.54


def g(v):
    return round(v / G) * G


# Symbol placement on the A4 sheet (grid-aligned).
PLACE = {
    "J1": (40, 60), "R1": (75, 60), "D1": (95, 60), "U1": (125, 60), "R2": (155, 60), "C1": (175, 60),
    "JP1": (200, 60),
    "J2": (40, 115), "R5": (75, 115), "R4": (95, 115), "U2": (130, 115), "R3": (160, 115), "C2": (180, 115),
    "R6": (75, 140), "R7": (95, 140), "SW1": (215, 110),
    "J3": (50, 165), "J4": (100, 165), "H1": (150, 165), "H2": (170, 165),
}

_libs = {}


def lib_symbol(lib_id):
    lib, name = lib_id.split(":")
    if lib not in _libs:
        _libs[lib] = SymbolLib.from_file(os.path.join(SYMDIR, lib + ".kicad_sym"))
    for s in _libs[lib].symbols:
        if s.entryName == name:
            return s
    raise KeyError(lib_id)


def uid():
    return str(uuid.uuid4())


def font_effects(hide=False, justify=None):
    e = Effects(font=Font(width=1.27, height=1.27), hide=hide)
    if justify:
        e.justify = Justify(horizontally=justify)
    return e


sch = Schematic.create_new()
sch.uuid = uid()
sch.paper.paperSize = "A4"
sch.titleBlock = None
root_path = "/" + sch.uuid

lib_added = set()
pwr_count = 0


def add_lib(lib_id):
    if lib_id in lib_added:
        return lib_symbol(lib_id)
    s = copy.deepcopy(lib_symbol(lib_id))
    s.libraryNickname = lib_id.split(":")[0]
    sch.libSymbols.append(s)
    lib_added.add(lib_id)
    return lib_symbol(lib_id)


def unit_count(sym):
    return max([u.unitId for u in sym.units] + [1])


def pins_of(sym, unit=None):
    """Pins of the symbol, or only those of one unit (plus pins common to all units)."""
    out = {}
    for u in sym.units:
        if unit is None or u.unitId in (0, unit):
            for p in u.pins:
                out[p.number] = p
    return out


def place_symbol(lib_id, ref, value, x, y, props=None, in_bom=True, on_board=True, ref_hidden=False, unit=1):
    sym = add_lib(lib_id)
    s = SchematicSymbol()
    s.libraryNickname, s.entryName = lib_id.split(":")
    s.position = Position(X=x, Y=y, angle=0)
    s.unit = unit
    s.inBom = in_bom
    s.onBoard = on_board
    s.uuid = uid()
    s.properties = [
        Property(key="Reference", value=ref, id=0, position=Position(X=x, Y=y - 7.62, angle=0),
                 effects=font_effects(hide=ref_hidden)),
        Property(key="Value", value=value, id=1, position=Position(X=x, Y=y + 7.62, angle=0),
                 effects=font_effects()),
    ]
    for i, (k, v) in enumerate((props or {}).items()):
        s.properties.append(Property(key=k, value=v, id=2 + i, position=Position(X=x, Y=y, angle=0),
                                     effects=font_effects(hide=True)))
    s.pins = {num: uid() for num in pins_of(sym, unit)}
    s.instances = [SymbolProjectInstance(name=PROJECT, paths=[
        SymbolProjectPath(sheetInstancePath=root_path, reference=ref, unit=unit)])]
    sch.schematicSymbols.append(s)
    return sym, s


def add_power(net, x, y):
    global pwr_count
    pwr_count += 1
    place_symbol("power:" + net, f"#PWR{pwr_count:02d}", net, x, y,
                 props={"Footprint": "", "Datasheet": ""}, in_bom=False, on_board=True, ref_hidden=True)


def place_pins(sym, p, x, y, unit):
    """Attach a net label, power symbol or no-connect flag to every pin of one placed unit."""
    for num, pin in pins_of(sym, unit).items():
        px, py = x + pin.position.X, y - pin.position.Y
        net = p["pins"].get(num)
        if net is None:
            if pin.electricalType != "no_connect":
                sch.noConnects.append(NoConnect(position=Position(X=px, Y=py), uuid=uid()))
        elif net in POWER_NETS:
            add_power(net, px, py)
        else:
            angle = (pin.position.angle + 180) % 360
            sch.labels.append(LocalLabel(text=net, position=Position(X=px, Y=py, angle=angle),
                                         effects=font_effects(justify="right" if angle == 180 else "left"),
                                         uuid=uid()))


symbol_uuids = {}
for ref, p in PARTS.items():
    x, y = (g(v) for v in PLACE[ref])
    props = {"Footprint": p["fp"], "Datasheet": "~"}
    if p["lcsc"]:
        props["LCSC"] = p["lcsc"]
    if p.get("mpn"):
        props["MPN"] = p["mpn"]
    sym = lib_symbol(p["sym"])
    for unit in range(1, unit_count(sym) + 1):
        uy = y + g(20) * (unit - 1)
        sym, s = place_symbol(p["sym"], ref, p["value"], x, uy, props=props, in_bom=p.get("bom", True), unit=unit)
        if unit == 1:
            symbol_uuids[ref] = s.uuid
        place_pins(sym, p, x, uy, unit)

# Power enters through J3, so flag both rails as driven.
for i, net in enumerate(POWER_NETS):
    fx, fy = g(200 + 15 * i), g(165)
    place_symbol("power:PWR_FLAG", f"#FLG{i + 1:02d}", "PWR_FLAG", fx, fy,
                 props={"Footprint": "", "Datasheet": ""}, in_bom=False, on_board=True, ref_hidden=True)
    add_power(net, fx, fy)

notes = [
    (g(20), g(20), "MIDI IN / OUT interface, 3.3 V or 5 V (SW1 must match VCC)"),
    (g(20), g(27), "J3: TX RX GND VCC to the MCU UART.  J4: i4 i5 o5 o2 o4 for panel jacks."),
    (g(20), g(32), "JP1 HARD THRU: fit a jumper cap to echo MIDI IN on the OUT jack; then leave J3 TX unconnected."),
    (g(20), g(37), "J1/J2 DIN jacks, J3/J4 headers: hand-soldered, not assembled by JLCPCB."),
]
for x, y, t in notes:
    sch.texts.append(Text(text=t, position=Position(X=x, Y=y, angle=0),
                          effects=font_effects(justify="left"), uuid=uid()))

out = os.path.join(ROOT, PROJECT + ".kicad_sch")
sch.to_file(out)

with open(os.path.join(ROOT, "scripts", "symbol_uuids.txt"), "w") as f:
    for ref, u in symbol_uuids.items():
        f.write(f"{ref} {u}\n")
    f.write(f"ROOT {sch.uuid}\n")
print("wrote", out)
