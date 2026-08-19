# kicad-query

Queries pad<->net connectivity and DNP status directly from a `.kicad_pcb`
file. Stdlib-only Python (a small hand-rolled S-expression parser in
`sexpr.py`) -- no KiCad install, `pcbnew` Python module, or Docker
required, unlike every other tool in `tools/`.

Built to verify changelog claims like "U6 pin 35 now connects to ADC_B"
without hand-tracing the schematic. The `.kicad_pcb` is authoritative for
this: after layout, every pad already carries its resolved net name
(`(net "ADC_B")`), which is exactly the "match the PCB" ground truth this
repo's changelogs describe engineering changes against. This does **not**
parse `.kicad_sch` -- resolving schematic-side nets means walking
hierarchical labels/wires across sheets, a different and harder problem
this tool doesn't attempt.

## Usage

```bash
# Everything on component U6
tools/kicad-query/pcb_net.py IOB/IOB_v3.2.1.kicad_pcb --ref U6

# Just one pad's net
tools/kicad-query/pcb_net.py IOB/IOB_v3.2.1.kicad_pcb --ref U6 --pad 35
# -> U6 pad 35: net='ADC_B' dnp=False

# Everything on a given net
tools/kicad-query/pcb_net.py IOB/IOB_v3.2.1.kicad_pcb --net ADC_B

# Every footprint marked Do Not Populate
tools/kicad-query/pcb_net.py IOB/IOB_v3.2.1.kicad_pcb --dnp
```

Parses a full ~17 MB board file in under 3 seconds.

**On `--dnp`:** this checks the PCB footprint's own `(attr ...)` block for
a `dnp` flag. In this repo's IOB v3.2.1 board, DNP status is set at the
*schematic* symbol level (`(dnp yes)` on the symbol instance) but does not
appear to propagate to an `attr dnp` marker on the corresponding PCB
footprint -- so `--dnp` against `.kicad_pcb` alone may under-report
schematic-side DNP components. Cross-check against the schematic (or the
exported BOM's DNP column, which does reflect the schematic-side flag)
rather than trusting `--dnp` as the sole source of truth for this project.

## Files

- `sexpr.py` -- the S-expression tokenizer/parser (generic, not
  KiCad-specific beyond what KiCad's format happens to look like).
- `pcb_net.py` -- the actual query CLI, built on top of `sexpr.py`.
