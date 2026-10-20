#!/bin/bash
# Regenerate schematic, layout, routing and JLCPCB files from scripts/design.py.
#
# Needs: KiCad 7 python module (pcbnew), kiutils + numpy + scipy + pillow (pip), gerbv,
#        Java 21+, Freerouting 2.1.0 jar,
#        and a KiCad >= 8 kicad-cli (ERC/DRC/exports).
#
#   FREEROUTING_JAR=/path/freerouting-2.1.0.jar KICAD_CLI="kicad-cli" ./build.sh
set -euo pipefail
cd "$(dirname "$0")"

: "${FREEROUTING_JAR:?set FREEROUTING_JAR to the Freerouting jar}"
KICAD_CLI=${KICAD_CLI:-"flatpak run --command=kicad-cli org.kicad.KiCad"}
PYTHON_KIUTILS=${PYTHON_KIUTILS:-python3}

mkdir -p build jlcpcb

$PYTHON_KIUTILS scripts/gen_sch.py
$KICAD_CLI sch erc --severity-all -o build/erc.rpt midiboard.kicad_sch
$KICAD_CLI sch export netlist --format kicadsexpr -o build/midiboard.net midiboard.kicad_sch
python3 scripts/check_netlist.py build/midiboard.net

python3 scripts/gen_switch_model.py
python3 scripts/gen_pcb.py
python3 scripts/route.py "$FREEROUTING_JAR"
$KICAD_CLI pcb drc --schematic-parity --severity-all -o build/drc.rpt midiboard.kicad_pcb
# KiCad 7 library footprints differ cosmetically from newer library copies; everything else is fatal.
if grep -E '^\[' build/drc.rpt | grep -v lib_footprint_mismatch; then
    echo "DRC failed, see build/drc.rpt" >&2; exit 1
fi
grep -q 'Found 0 unconnected pads' build/drc.rpt

python3 scripts/jlc_export.py "$KICAD_CLI"
$PYTHON_KIUTILS scripts/check_gerbers.py
$KICAD_CLI sch export pdf -o jlcpcb/midiboard-schematic.pdf midiboard.kicad_sch
