"""Single source of truth for the MIDI 3V3/5V board: parts, footprints, LCSC numbers and nets.

Both the schematic generator and the PCB generator import this module, so the
schematic and the layout can never disagree on connectivity.
"""

PROJECT = "midiboard"

# Footprint rotation offsets (deg) between KiCad and JLCPCB placement conventions.
JLC_ROTATION = {
    "Package_TO_SOT_SMD:SOT-23-5": -90,
    "Package_DIP:SMDIP-6_W9.53mm": -90,
}

# Each part: reference -> dict.
#   sym:   KiCad library symbol
#   fp:    footprint
#   lcsc:  LCSC/JLCPCB part number, or None when the part is not assembled by JLCPCB
#   pins:  pin number -> net name (None = not connected)
#   bom:   False for board features (mounting holes) that are not bill-of-materials items
PARTS = {
    "J1": dict(sym="Connector:DIN-5_180degree", value="MIDI IN",
               fp="midiboard:DIN-5_Female_Horizontal_DIN-504", lcsc=None,
               mpn="Legion DIN-504 (LCSC C23689428)",
               pins={"1": None, "2": None, "3": None, "4": "MIDI_IN_4", "5": "MIDI_IN_5"}),
    "J2": dict(sym="Connector:DIN-5_180degree", value="MIDI OUT/THRU",
               fp="midiboard:DIN-5_Female_Horizontal_DIN-504", lcsc=None,
               mpn="Legion DIN-504 (LCSC C23689428)",
               pins={"1": None, "2": "GND", "3": None, "4": "MIDI_OUT_4", "5": "MIDI_OUT_5"}),
    "R1": dict(sym="Device:R", value="220", fp="Resistor_SMD:R_0603_1608Metric", lcsc="C22962",
               mpn="0603WAF2200T5E", pins={"1": "MIDI_IN_4", "2": "OPTO_A"}),
    "D1": dict(sym="Device:D", value="1N4148W", fp="Diode_SMD:D_SOD-123", lcsc="C81598",
               mpn="1N4148W", pins={"1": "OPTO_A", "2": "MIDI_IN_5"}),
    "U1": dict(sym="Isolator:H11L1", value="H11L1SM", fp="Package_DIP:SMDIP-6_W9.53mm", lcsc="C899473",
               mpn="onsemi H11L1SM",
               pins={"1": "OPTO_A", "2": "MIDI_IN_5", "3": None, "4": "RX", "5": "GND", "6": "VCC"}),
    "R2": dict(sym="Device:R", value="470", fp="Resistor_SMD:R_0603_1608Metric", lcsc="C23179",
               mpn="0603WAF4700T5E", pins={"1": "VCC", "2": "RX"}),
    "C1": dict(sym="Device:C", value="100nF", fp="Capacitor_SMD:C_0603_1608Metric", lcsc="C14663",
               mpn="CC0603KRX7R9BB104", pins={"1": "VCC", "2": "GND"}),
    # 2-pin header for a removable 2.54 mm jumper cap: fitted = hard THRU (RX drives the OUT buffer).
    "JP1": dict(sym="Jumper:Jumper_2_Open", value="HARD THRU",
                fp="Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical", lcsc=None,
                mpn="2.54mm pin header 1x2 + jumper cap", pins={"1": "RX", "2": "TX"}),
    "R3": dict(sym="Device:R", value="10k", fp="Resistor_SMD:R_0603_1608Metric", lcsc="C25804",
               mpn="0603WAF1002T5E", pins={"1": "VCC", "2": "TX"}),
    "U2": dict(sym="74xGxx:74LVC1G17", value="74LVC1G17", fp="Package_TO_SOT_SMD:SOT-23-5", lcsc="C151394",
               mpn="Diodes 74LVC1G17W5-7",
               pins={"1": None, "2": "TX", "3": "GND", "4": "BUF_OUT", "5": "VCC"}),
    "C2": dict(sym="Device:C", value="100nF", fp="Capacitor_SMD:C_0603_1608Metric", lcsc="C14663",
               mpn="CC0603KRX7R9BB104", pins={"1": "VCC", "2": "GND"}),
    # MIDI OUT source resistors: 220R each for 5 V (MIDI 1.0). In the 3V3 position SW1 puts R6/R7 in
    # parallel: 220R || 33R = 28.7R on pin 4 and 220R || 10R = 9.6R on pin 5 (CA-033: 33R / 10R).
    "R4": dict(sym="Device:R", value="220", fp="Resistor_SMD:R_0603_1608Metric", lcsc="C22962",
               mpn="0603WAF2200T5E", pins={"1": "BUF_OUT", "2": "MIDI_OUT_5"}),
    "R5": dict(sym="Device:R", value="220", fp="Resistor_SMD:R_0603_1608Metric", lcsc="C22962",
               mpn="0603WAF2200T5E", pins={"1": "VCC", "2": "MIDI_OUT_4"}),
    "R6": dict(sym="Device:R", value="33", fp="Resistor_SMD:R_0805_2012Metric", lcsc="C17634",
               mpn="0805W8F330JT5E", pins={"1": "VCC", "2": "SEL_4"}),
    "R7": dict(sym="Device:R", value="10", fp="Resistor_SMD:R_0805_2012Metric", lcsc="C17415",
               mpn="0805W8F100JT5E", pins={"1": "BUF_OUT", "2": "SEL_5"}),
    # Slider towards pins 1/4 = 3V3 (1-2 and 4-5 closed); towards pins 3/6 = 5V (R6/R7 out of circuit).
    "SW1": dict(sym="Switch:SW_DPDT_x2", value="3V3/5V", fp="Button_Switch_SMD:SW_DPDT_CK_JS202011JCQN",
                lcsc="C221665", mpn="C&K JS202011JCQN",
                pins={"1": "MIDI_OUT_4", "2": "SEL_4", "3": None, "4": "MIDI_OUT_5", "5": "SEL_5", "6": None}),
    "J3": dict(sym="Connector_Generic:Conn_01x04", value="MCU",
               fp="Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical", lcsc=None,
               mpn="2.54mm pin header 1x4",
               pins={"1": "TX", "2": "RX", "3": "GND", "4": "VCC"}),
    "J4": dict(sym="Connector_Generic:Conn_01x05", value="JACKS",
               fp="Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical", lcsc=None,
               mpn="2.54mm pin header 1x5",
               pins={"1": "MIDI_IN_4", "2": "MIDI_IN_5", "3": "MIDI_OUT_5", "4": "GND", "5": "MIDI_OUT_4"}),
    "H1": dict(sym="Mechanical:MountingHole", value="M3", fp="MountingHole:MountingHole_3.2mm_M3",
               lcsc=None, mpn="", bom=False, pins={}),
    "H2": dict(sym="Mechanical:MountingHole", value="M3", fp="MountingHole:MountingHole_3.2mm_M3",
               lcsc=None, mpn="", bom=False, pins={}),
}

POWER_NETS = ("VCC", "GND")
