"""Write a simple VRML model of the C&K JS202011JCQN slide switch (KiCad ships none for the SMD variant).

Dimensions from the C&K JS series datasheet: body 9.0 x 3.6 x 3.5 mm, actuator 1.5 x 1.5 mm standing
2.0 mm above the body with 2.0 mm travel, six J-leads on a 2.5 mm pitch, rows 2.4 mm apart.
The actuator is drawn in the pin-1 position (3V3 on this board).
Coordinates follow the footprint: x along the switch, y = -footprint y, z up from the board.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "lib", "midiboard.3dshapes", "SW_DPDT_CK_JS202011JCQN.wrl")
INCH = 2.54  # KiCad VRML units are 0.1 inch

BODY = (0.15, 0.15, 0.15)
ACTUATOR = (0.85, 0.85, 0.82)
METAL = (0.82, 0.82, 0.78)


def box(x0, x1, y0, y1, z0, z1, color):
    v = [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    pts = ", ".join(f"{x / INCH:.4f} {y / INCH:.4f} {z / INCH:.4f}" for x, y, z in v)
    faces = "0 2 3 1 -1, 4 5 7 6 -1, 0 1 5 4 -1, 2 6 7 3 -1, 0 4 6 2 -1, 1 3 7 5 -1"
    r, g, b = color
    return f"""Shape {{
  appearance Appearance {{ material Material {{ diffuseColor {r} {g} {b} specularColor 0.3 0.3 0.3 shininess 0.4 }} }}
  geometry IndexedFaceSet {{ solid FALSE coord Coordinate {{ point [ {pts} ] }} coordIndex [ {faces} ] }}
}}
"""


def main():
    shapes = [box(-4.5, 4.5, -1.8, 1.8, 0.1, 3.5, BODY),
              box(-1.0 - 0.75, -1.0 + 0.75, -0.75, 0.75, 3.5, 5.5, ACTUATOR)]
    for x in (-2.5, 0.0, 2.5):
        for side in (-1, 1):
            # J-lead: down the body side, then tucked under onto the pad.
            shapes.append(box(x - 0.3, x + 0.3, side * 1.8, side * 1.95, 0.0, 1.0, METAL))
            shapes.append(box(x - 0.3, x + 0.3, side * 0.9, side * 1.95, 0.0, 0.15, METAL))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write("#VRML V2.0 utf8\n" + "".join(shapes))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
