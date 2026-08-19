#!/usr/bin/env python3
"""Dump every sheet of an .xlsx workbook to plain text.

Stdlib-only (zipfile + xml.etree.ElementTree) -- no openpyxl/pip/Docker
required. Meant for reading the small workbooks this repo tracks in
changelog/ (Changelog *.xlsx, Internal Peer Checklist *.xlsx), which are
a handful of sheets/rows, not for general-purpose spreadsheet work.

Usage:
    read_xlsx.py <workbook.xlsx> [sheet_number ...]

With no sheet numbers, dumps all sheets (in workbook order, 1-indexed --
sheet 1 is the first tab). Empty cells are skipped; each non-empty row
is printed as "row: A1=... | B1=... | ...".
"""
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def load_shared_strings(zf):
    try:
        data = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    strings = []
    for si in root.findall("a:si", NS):
        texts = si.findall(".//a:t", NS)
        strings.append("".join(t.text or "" for t in texts))
    return strings


def load_sheet_names(zf):
    root = ET.fromstring(zf.read("xl/workbook.xml"))
    return [s.get("name") for s in root.findall(".//a:sheets/a:sheet", NS)]


def cell_value(c, shared):
    t = c.get("t")
    if t == "inlineStr":
        is_el = c.find("a:is", NS)
        if is_el is None:
            return ""
        return "".join(t_el.text or "" for t_el in is_el.findall(".//a:t", NS))
    v = c.find("a:v", NS)
    if v is None or v.text is None:
        return ""
    if t == "s":
        try:
            return shared[int(v.text)]
        except (ValueError, IndexError):
            return v.text
    return v.text


def dump_sheet(zf, sheet_num, shared, sheet_name):
    path = f"xl/worksheets/sheet{sheet_num}.xml"
    try:
        data = zf.read(path)
    except KeyError:
        print(f"(no {path} in workbook)", file=sys.stderr)
        return
    root = ET.fromstring(data)
    print(f"=== Sheet {sheet_num}: {sheet_name} ({path}) ===")
    for row in root.findall(".//a:row", NS):
        cells = []
        for c in row.findall("a:c", NS):
            val = cell_value(c, shared)
            if val:
                cells.append(f"{c.get('r')}={val}")
        if cells:
            print(" | ".join(cells))
    print()


def main(argv):
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1
    path = argv[1]
    requested = [int(x) for x in argv[2:]] if len(argv) > 2 else None

    with zipfile.ZipFile(path) as zf:
        shared = load_shared_strings(zf)
        sheet_names = load_sheet_names(zf)
        sheet_nums = requested or list(range(1, len(sheet_names) + 1))
        for n in sheet_nums:
            name = sheet_names[n - 1] if 0 < n <= len(sheet_names) else "?"
            dump_sheet(zf, n, shared, name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
