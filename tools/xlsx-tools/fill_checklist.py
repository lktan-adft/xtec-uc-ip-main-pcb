#!/usr/bin/env python3
"""Patch specific cells in a copy of an .xlsx workbook, in place.

Built for one job: filling the Checker-verdict and Remarks cells of a
*copy* of this repo's "Internal Peer Checklist" workbook
(changelog/v<X>/Internal Peer Checklist - X1_<board>.xlsx) without
disturbing anything else in the file -- styles, the reference-image
sheet, shared strings, formulas, or any other cell. Stdlib-only
(zipfile + regex over the raw sheet XML) -- no openpyxl/pip/Docker.

Why regex over raw XML instead of parsing with ElementTree and writing
it back: a full parse/reserialize round-trip risks normalizing or
dropping namespace declarations and attribute formatting elsewhere in
the file. This script only ever touches the exact `<c r="...">`
elements named in the patch list, leaving every other byte of every
other zip entry (including xl/media/* images) untouched.

ALWAYS operate on a copy, never the original tracked workbook -- this
script does not make one for you.

Usage:
    fill_checklist.py <workbook.xlsx> <patches.json>

patches.json:
    [
      {"sheet": 1, "cell": "E7", "value": "YES"},
      {"sheet": 1, "cell": "H7", "value": "ERC report clean, 0 errors"},
      {"sheet": 2, "cell": "E24", "value": "N/A"}
    ]

`sheet` is the 1-indexed sheet/tab number (matches read_xlsx.py's
numbering). Cells that already exist in the sheet (even as an empty
styled placeholder, e.g. `<c r="E7" s="1"/>`) are patched in place,
preserving their style (`s="..."`). Cells with no existing `<c>`
element in that row are inserted in correct column order among the
row's other cells. A target row that doesn't exist at all is an error
-- this tool fills existing checklist rows, it does not author new
ones.

Values are written as inline strings (`t="inlineStr"`), which need no
changes to xl/sharedStrings.xml. Any formula cells elsewhere in the
row (e.g. a completion-percentage formula referencing this cell) keep
their cached value until Excel recalculates on open -- normal
behavior, not something this script needs to handle.
"""
import json
import re
import sys
import zipfile
from xml.sax.saxutils import escape

CELL_RE_TMPL = r'<c r="{ref}"((?:\s+[\w:]+="[^"]*")*)\s*(?:/>|>((?:(?!</c>).)*)</c>)'
ROW_RE_TMPL = r'(<row r="{row}"[^>]*>)(.*?)(</row>)'


def col_letters(cell_ref):
    return re.match(r"[A-Z]+", cell_ref).group(0)


def col_key(letters):
    # Base-26 column ordering (A < B < ... < Z < AA < AB ...).
    key = 0
    for ch in letters:
        key = key * 26 + (ord(ch) - ord("A") + 1)
    return key


def build_cell_xml(ref, value, style_attr):
    return f'<c r="{ref}"{style_attr} t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def patch_cell_in_place(xml_text, ref, value):
    """Try to replace an existing <c r="ref".../> or <c r="ref">...</c>.

    Returns the patched text, or None if the cell doesn't exist yet.
    """
    pattern = re.compile(CELL_RE_TMPL.format(ref=re.escape(ref)), re.DOTALL)
    m = pattern.search(xml_text)
    if not m:
        return None
    attrs = m.group(1) or ""
    style_match = re.search(r'\ss="(\d+)"', attrs)
    style_attr = f' s="{style_match.group(1)}"' if style_match else ""
    new_cell = build_cell_xml(ref, value, style_attr)
    return xml_text[: m.start()] + new_cell + xml_text[m.end() :]


def insert_cell_into_row(xml_text, ref, value):
    """Insert a new <c> into its row in correct column order.

    Raises ValueError if the target row doesn't exist in the sheet.
    """
    row_num = re.match(r"[A-Z]+(\d+)", ref).group(1)
    pattern = re.compile(ROW_RE_TMPL.format(row=row_num), re.DOTALL)
    m = pattern.search(xml_text)
    if not m:
        raise ValueError(
            f"row {row_num} not found in sheet -- refusing to fabricate a new "
            f"checklist row for {ref}"
        )
    row_open, row_body, row_close = m.group(1), m.group(2), m.group(3)
    target_key = col_key(col_letters(ref))

    existing_cells = list(re.finditer(r'<c r="([A-Z]+)\d+"', row_body))
    insert_at = len(row_body)
    for cm in existing_cells:
        if col_key(cm.group(1)) > target_key:
            insert_at = cm.start()
            break

    new_cell = build_cell_xml(ref, value, style_attr="")
    new_body = row_body[:insert_at] + new_cell + row_body[insert_at:]
    return xml_text[: m.start()] + row_open + new_body + row_close + xml_text[m.end() :]


def apply_patches_to_sheet(xml_text, patches):
    for p in patches:
        ref, value = p["cell"], str(p["value"])
        patched = patch_cell_in_place(xml_text, ref, value)
        if patched is None:
            patched = insert_cell_into_row(xml_text, ref, value)
        xml_text = patched
    return xml_text


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 1
    workbook_path, patches_path = argv[1], argv[2]

    with open(patches_path, encoding="utf-8") as f:
        all_patches = json.load(f)

    by_sheet = {}
    for p in all_patches:
        by_sheet.setdefault(p["sheet"], []).append(p)

    with zipfile.ZipFile(workbook_path) as zf_in:
        entries = zf_in.infolist()
        contents = {info.filename: zf_in.read(info.filename) for info in entries}

    for sheet_num, patches in by_sheet.items():
        path = f"xl/worksheets/sheet{sheet_num}.xml"
        if path not in contents:
            print(f"error: {path} not in {workbook_path}", file=sys.stderr)
            return 1
        text = contents[path].decode("utf-8")
        text = apply_patches_to_sheet(text, patches)
        contents[path] = text.encode("utf-8")

    tmp_path = workbook_path + ".tmp"
    with zipfile.ZipFile(workbook_path) as zf_in, zipfile.ZipFile(
        tmp_path, "w", zipfile.ZIP_DEFLATED
    ) as zf_out:
        for info in zf_in.infolist():
            zf_out.writestr(info, contents[info.filename])

    import os

    os.replace(tmp_path, workbook_path)
    print(f"Patched {sum(len(v) for v in by_sheet.values())} cell(s) in {workbook_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
