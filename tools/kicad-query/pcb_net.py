#!/usr/bin/env python3
"""Query pad<->net connectivity directly from a .kicad_pcb file.

Stdlib-only (see sexpr.py) -- no KiCad install, Docker, or pcbnew Python
module required. Built to verify changelog claims like "U6 pin 35 now
connects to ADC_B" without hand-tracing the schematic: the .kicad_pcb file
is authoritative here because after layout, every pad already carries its
resolved net name (`(net "ADC_B")`), which is exactly the "match the PCB"
ground truth this repo's changelogs describe changes against. This does
NOT parse .kicad_sch -- schematic net resolution requires walking
hierarchical labels/wires across sheets, which is a different, harder
problem this tool doesn't attempt.

Usage:
    pcb_net.py <board.kicad_pcb> --ref U6                 # all pads on U6
    pcb_net.py <board.kicad_pcb> --ref U6 --pad 35         # just pad 35's net
    pcb_net.py <board.kicad_pcb> --net ADC_B               # everything on net ADC_B
    pcb_net.py <board.kicad_pcb> --dnp                     # every footprint with dnp=yes
"""
import argparse
import sys

from sexpr import parse, find_all, find_first, text_of


def load_footprints(board):
    return list(find_all(board, "footprint"))


def footprint_ref(fp):
    for prop in find_all(fp, "property"):
        if len(prop) >= 3 and prop[1] == "Reference":
            return prop[2]
    return None


def footprint_dnp(fp):
    attr = find_first(fp, "attr")
    if attr is None:
        return False
    return "dnp" in attr[1:]


def pad_entries(fp):
    """Yield (pad_number, net_name_or_None) for every pad in a footprint."""
    for pad in find_all(fp, "pad"):
        pad_num = pad[1] if len(pad) > 1 else None
        net_node = find_first(pad, "net")
        net_name = text_of(net_node) if net_node else None
        yield pad_num, net_name


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("board", help="path to a .kicad_pcb file")
    ap.add_argument("--ref", help="footprint reference designator, e.g. U6")
    ap.add_argument("--pad", help="pad number/name, requires --ref")
    ap.add_argument("--net", help="net name to look up every pad on")
    ap.add_argument(
        "--dnp", action="store_true", help="list every footprint marked Do Not Populate"
    )
    args = ap.parse_args(argv[1:])

    with open(args.board, encoding="utf-8") as f:
        text = f.read()
    board = parse(text)
    footprints = load_footprints(board)

    if args.dnp:
        found = False
        for fp in footprints:
            if footprint_dnp(fp):
                print(footprint_ref(fp))
                found = True
        if not found:
            print("(no footprints marked dnp=yes)", file=sys.stderr)
        return 0

    if args.net:
        found = False
        for fp in footprints:
            ref = footprint_ref(fp)
            for pad_num, net_name in pad_entries(fp):
                if net_name == args.net:
                    print(f"{ref} pad {pad_num}")
                    found = True
        if not found:
            print(f"(no pads found on net {args.net!r})", file=sys.stderr)
            return 1
        return 0

    if args.ref:
        matches = [fp for fp in footprints if footprint_ref(fp) == args.ref]
        if not matches:
            print(f"error: no footprint with reference {args.ref!r}", file=sys.stderr)
            return 1
        fp = matches[0]
        dnp = footprint_dnp(fp)
        if args.pad:
            for pad_num, net_name in pad_entries(fp):
                if pad_num == args.pad:
                    print(f"{args.ref} pad {args.pad}: net={net_name!r} dnp={dnp}")
                    return 0
            print(f"error: {args.ref} has no pad {args.pad!r}", file=sys.stderr)
            return 1
        print(f"{args.ref} (dnp={dnp}):")
        for pad_num, net_name in pad_entries(fp):
            print(f"  pad {pad_num}: {net_name}")
        return 0

    ap.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
