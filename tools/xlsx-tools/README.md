# xlsx-tools

Two small, stdlib-only Python scripts for reading and patching the
`.xlsx` workbooks this repo tracks in `changelog/` (`Changelog *.xlsx`,
`Internal Peer Checklist *.xlsx`). No `openpyxl`, no `pip`, no Docker —
unlike `tools/gerber-diff` and `tools/kicad-reports`, which need Docker
for `gerbv`/`kicad-cli`, these two just need `python3` (they work
directly off the raw OOXML: an `.xlsx` is a zip of XML parts).

Built for [`.claude/skills/pcb-review`](../../.claude/skills/pcb-review/SKILL.md)
to read the stated changelog and fill the Checker column of a *copy* of
the peer checklist during an automated review pass — see that skill for
the end-to-end usage. Both scripts are also fine to run standalone.

## `read_xlsx.py` — dump a workbook to plain text

```bash
tools/xlsx-tools/read_xlsx.py "changelog/v3.2.1/Changelog X1-IOB_v3.2.1 2026-08-13.xlsx"
tools/xlsx-tools/read_xlsx.py "changelog/v3.2.1/Internal Peer Checklist - X1_IOB_v3.2.1.xlsx" 1 2
```

Dumps every sheet (or just the sheet numbers given, 1-indexed by tab
order) as `row: A7=... | D7=... | ...`, resolving shared strings and
inline strings. Empty cells are skipped. Note: Excel date cells (e.g.
`Date | 46247`) come through as their raw serial-day-number, not a
calendar date — `46247` is days since 1899-12-30.

## `fill_checklist.py` — patch specific cells in a copy of a workbook

```bash
cp "changelog/v3.2.1/Internal Peer Checklist - X1_IOB_v3.2.1.xlsx" \
   "changelog/v3.2.1/claude_review/Internal Peer Checklist - X1_IOB_v3.2.1 (Claude).xlsx"

cat > /tmp/patches.json <<'EOF'
[
  {"sheet": 1, "cell": "E7", "value": "YES"},
  {"sheet": 1, "cell": "H7", "value": "v3.2.0 -> v3.2.1, minor bump confirmed"}
]
EOF

tools/xlsx-tools/fill_checklist.py \
  "changelog/v3.2.1/claude_review/Internal Peer Checklist - X1_IOB_v3.2.1 (Claude).xlsx" \
  /tmp/patches.json
```

**Always run this against a copy**, never the tracked original — it
patches the file in place and does not make a backup.

Patches the given cells (by 1-indexed sheet number + cell ref) and
nothing else. Existing cells (even empty styled placeholders like
`<c r="E7" s="1"/>`, which is how most of the checklist's blank Checker
cells are actually stored) are patched in place, keeping their style.
Cells with no existing `<c>` element in that row are inserted in
correct column order. A target row that doesn't exist at all is a hard
error — this tool fills existing checklist rows, it never fabricates
new ones.

Values are written as inline strings (`t="inlineStr"`), so
`xl/sharedStrings.xml` is never touched. Everything else in the
workbook — styles, the reference-image sheet (`xl/media/*`), formulas,
every other cell — is left byte-identical; only the exact `<c r="...">`
elements named in the patch list are replaced. Any completion-percentage
formula that reads a patched cell (e.g. `E1`/`E3` on each checklist
sheet) keeps its stale cached value until Excel recalculates on open —
normal Excel behavior, not something this script handles.

## Why not `openpyxl`

This host has no `pip`, and adding a Docker image (like `kicad-reports`
and `gerber-diff` do) for two small, well-understood XML patches would
be a heavier dependency than the job needs. If a future job needs
general-purpose spreadsheet editing (arbitrary formulas, new sheets,
formatting), reach for `openpyxl` in a container rather than extending
these regexes — they're intentionally narrow.
