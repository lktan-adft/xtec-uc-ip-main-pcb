#!/usr/bin/env bash
# Regenerate ERC, DRC, gerbers, drill files, BOM, schematic PDF, and
# top/bottom board renders directly from a board's .kicad_sch/.kicad_pcb
# source, instead of trusting whatever report/export files the PCB
# engineer included with their change.
#
# Runs kicad-cli (v10.0.4, matching this repo's toolchain) via Docker --
# no local KiCad install required.
#
# Usage:
#   tools/kicad-reports/generate_reports.sh <board-folder> [output-dir] [--in-place]
#
# <board-folder> is a folder containing one project's .kicad_pro and its
# root .kicad_sch/.kicad_pcb (e.g. IOB/, following this repo's
# one-folder-per-board-family convention). The folder can be named
# anything -- the script locates the project files via the .kicad_pro
# basename (the KiCad convention: root schematic/PCB share the project's
# basename), not by globbing "*.kicad_sch", which would just as happily
# match a sub-sheet file and silently ERC the wrong one.
#
# By default ALL output (ERC, DRC, gerbers, drill, BOM, PDF) is written
# to [output-dir], which defaults to <board-folder>/fresh_reports/ --
# never touching files inside <board-folder> itself, so you can diff the
# fresh output against what's committed without clobbering it.
#
# ERC and DRC are each generated TWICE, at two severity scopes (units
# always mm, via --units mm):
#   *_errors_only.rpt  -- --severity-error. Matches a report generated
#                         with that same explicit flag (check the
#                         submitted report's own "Report includes:"
#                         line -- kicad-cli's plain default, with no
#                         --severity flag at all, is already
#                         errors+warnings, not errors-only).
#   *_full.rpt          -- --severity-all (errors + warnings + exclusions).
# A report that shows 0 violations vs. this tool's *_full showing a few
# hundred is very likely just that scope difference, not a real
# discrepancy -- compare *_errors_only against an errors-only submitted
# report, and *_full against a warnings-inclusive one.
#
# Pass --in-place to instead write DRC_report_*.rpt and Gerber/ directly
# into <board-folder> (matching this repo's existing layout convention)
# and ERC/BOM/PDF into <board-folder>/Deliverables/. Only use this once
# you've already compared and are intentionally replacing the committed
# reports.
#
# Examples:
#   tools/kicad-reports/generate_reports.sh IOB
#   tools/kicad-reports/generate_reports.sh IOB /tmp/fresh-reports
#   tools/kicad-reports/generate_reports.sh IOB --in-place
set -euo pipefail

IMAGE_TAG="kicad/kicad:10.0.4"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <board-folder> [output-dir] [--in-place]" >&2
    exit 1
fi

BOARD_DIR="$1"; shift
if [[ ! -d "$BOARD_DIR" ]]; then
    echo "Error: '$BOARD_DIR' is not a directory" >&2
    exit 1
fi
BOARD_DIR="$(cd "$BOARD_DIR" && pwd)"

IN_PLACE=0
OUT_ARG=""
for arg in "$@"; do
    if [[ "$arg" == "--in-place" ]]; then
        IN_PLACE=1
    else
        OUT_ARG="$arg"
    fi
done

# The root schematic and PCB always share their basename with the
# project's .kicad_pro (KiCad convention, not this repo's choice) --
# anchor on that rather than globbing *.kicad_sch.
PRO_FILE="$(find "$BOARD_DIR" -maxdepth 1 -iname '*.kicad_pro' | head -n1)"
if [[ -z "$PRO_FILE" ]]; then
    echo "Error: no .kicad_pro found directly inside '$BOARD_DIR'" >&2
    exit 1
fi
PROJECT_BASENAME="$(basename "$PRO_FILE" .kicad_pro)"

PCB_FILE="${BOARD_DIR}/${PROJECT_BASENAME}.kicad_pcb"
SCH_FILE="${BOARD_DIR}/${PROJECT_BASENAME}.kicad_sch"

if [[ ! -f "$PCB_FILE" ]]; then
    echo "Error: expected '${PROJECT_BASENAME}.kicad_pcb' (matching ${PRO_FILE##*/}) not found in '$BOARD_DIR'" >&2
    exit 1
fi
if [[ ! -f "$SCH_FILE" ]]; then
    echo "Error: expected root schematic '${PROJECT_BASENAME}.kicad_sch' (matching ${PRO_FILE##*/}) not found in '$BOARD_DIR'" >&2
    exit 1
fi
PCB_NAME="$(basename "$PCB_FILE")"
SCH_NAME="$(basename "$SCH_FILE")"

if [[ $IN_PLACE -eq 1 ]]; then
    DELIVERABLES_DIR="${OUT_ARG:-${BOARD_DIR}/Deliverables}"
    GERBER_DIR="${BOARD_DIR}/Gerber"
    DRC_OUT_DIR="$BOARD_DIR"
    mkdir -p "$DELIVERABLES_DIR" "$GERBER_DIR"
else
    OUT_ROOT="${OUT_ARG:-${BOARD_DIR}/fresh_reports}"
    mkdir -p "$OUT_ROOT"
    OUT_ROOT="$(cd "$OUT_ROOT" && pwd)"
    DELIVERABLES_DIR="$OUT_ROOT"
    GERBER_DIR="${OUT_ROOT}/Gerber"
    DRC_OUT_DIR="$OUT_ROOT"
    mkdir -p "$GERBER_DIR"
fi
DELIVERABLES_DIR="$(cd "$DELIVERABLES_DIR" && pwd)"
GERBER_DIR="$(cd "$GERBER_DIR" && pwd)"
DRC_OUT_DIR="$(cd "$DRC_OUT_DIR" && pwd)"

echo "Board folder:  $BOARD_DIR" >&2
echo "PCB source:    $PCB_NAME" >&2
echo "Sch source:    $SCH_NAME" >&2
if [[ $IN_PLACE -eq 1 ]]; then
    echo "Mode:          --in-place (writing into $BOARD_DIR)" >&2
else
    echo "Mode:          sandboxed output at $DRC_OUT_DIR (source folder untouched)" >&2
fi
echo >&2

run_cli() {
    docker run --rm \
        -v "${BOARD_DIR}:/board:ro" \
        -v "${DELIVERABLES_DIR}:/deliverables" \
        -v "${GERBER_DIR}:/gerber" \
        -v "${DRC_OUT_DIR}:/drc_out" \
        -w /board \
        "$IMAGE_TAG" \
        kicad-cli "$@"
}

# Two DRC/ERC reports are generated, at different severity scopes.
# NOTE: kicad-cli's own default (no --severity-* flag at all) is
# "Errors, Warnings" -- NOT errors-only. To get an errors-only report
# you must explicitly pass --severity-error. This matters because a
# report that says "Report includes: Errors" (singular category) was
# generated with an explicit --severity-error flag, not kicad-cli's
# plain default -- if you're comparing against a submitted report,
# check its own "Report includes:" header line to know which of the
# two reports below is the fair comparison.
#
#   *_errors_only.rpt  -- --severity-error. Matches a report generated
#                          with that same explicit flag.
#   *_full.rpt          -- --severity-all (errors + warnings +
#                          exclusions; kicad-cli's plain default is
#                          already errors+warnings, --severity-all only
#                          adds exclusions on top of that).
#                          A submitted report showing 0 violations vs.
#                          this tool's *_full showing a few hundred is
#                          very likely just that scope difference, not a
#                          real design change -- always check both
#                          reports' "Report includes:" line before
#                          treating a gap as a red flag.
echo "==> ERC (schematic) -- errors only (--severity-error)" >&2
run_cli sch erc "$SCH_NAME" \
    --output "/deliverables/ERC_report_errors_only.rpt" \
    --severity-error \
    --units mm

echo "==> ERC (schematic) -- full (errors + warnings + exclusions)" >&2
run_cli sch erc "$SCH_NAME" \
    --output "/deliverables/ERC_report_full.rpt" \
    --severity-all \
    --units mm

echo "==> DRC (PCB) -- errors only (--severity-error)" >&2
run_cli pcb drc "$PCB_NAME" \
    --output "/drc_out/DRC_report_errors_only.rpt" \
    --severity-error \
    --schematic-parity \
    --units mm

echo "==> DRC (PCB) -- full (errors + warnings + exclusions)" >&2
run_cli pcb drc "$PCB_NAME" \
    --output "/drc_out/DRC_report_full.rpt" \
    --severity-all \
    --schematic-parity \
    --units mm

echo "==> Gerbers" >&2
run_cli pcb export gerbers "$PCB_NAME" --output "/gerber/"

echo "==> Drill files" >&2
run_cli pcb export drill "$PCB_NAME" --output "/gerber/" --generate-map

echo "==> BOM" >&2
BOM_NAME="$(basename "$PCB_FILE" .kicad_pcb)_BOM.csv"
# kicad-cli's plain default (no --fields/--group-by/etc) exports one row
# per component, not grouped by value+footprint like this repo's
# committed IOB/Deliverables/*_BOM.csv -- making every fresh export a
# useless diff against the committed one even when nothing changed.
#
# The flags below reproduce the committed format exactly (verified
# byte-for-byte against IOB/Deliverables/IOB_BOM.csv, aside from one
# single-row ordering quirk noted below) -- they're not guessed, they're
# read straight out of this project's own stored BOM export settings in
# <board>.kicad_pro (schematic.bom_settings / bom_fmt_settings), i.e.
# whatever was last configured in KiCad's own Tools > Generate BOM
# dialog. If that dialog's settings are ever changed and re-saved, these
# flags should be re-derived from the .kicad_pro rather than assumed.
#
# Known imperfection: kicad-cli's --sort-asc flag crashes
# ("bad any_cast") on this KiCad 10.0.4 build, so ascending order isn't
# passed explicitly (it's the tool's own default already). Sorting by
# Value alone also doesn't tie-break identical-prefix values quite the
# same way the original export did (e.g. "330uF ; 50V" vs
# "330uF ; 50V ; DNI" can land one row out of order) -- cosmetic only,
# never affects which components are grouped or their quantities.
run_cli sch export bom "$SCH_NAME" --output "/deliverables/${BOM_NAME}" \
    --fields "Reference,QUANTITY,Value,DNP,EXCLUDE_FROM_BOARD,Footprint" \
    --labels "Reference,Qty,Value,DNP,Exclude from Board,Footprint" \
    --group-by "Value,DNP,EXCLUDE_FROM_BOARD,Footprint" \
    --sort-field "Value" \
    --ref-delimiter " ," \
    --ref-range-delimiter ""

echo "==> Schematic PDF" >&2
PDF_NAME="$(basename "$PCB_FILE" .kicad_pcb).pdf"
run_cli sch export pdf "$SCH_NAME" --output "/deliverables/${PDF_NAME}"

# Board renders (top/bottom, full color -- copper+silkscreen+soldermask+
# component bodies) for the visual checks kicad-cli can't otherwise
# automate: ADF logo present, board name/version silkscreen legible,
# connector placement. --quality basic is a ~1s flat-lit render; the
# board only looks right with --preset follow_pcb_editor (the plain
# default preset, follow_plot_settings, renders bare copper only --
# this project's plot settings hide soldermask/silkscreen/3D bodies).
# Bump to --quality high (raytraced, ~15-40s) for a sharper image if
# basic isn't clear enough for a specific check.
echo "==> Board render, top" >&2
TOP_RENDER_NAME="$(basename "$PCB_FILE" .kicad_pcb)_render_top.png"
run_cli pcb render --side top --quality basic --background opaque \
    --preset follow_pcb_editor --output "/deliverables/${TOP_RENDER_NAME}" "$PCB_NAME"

echo "==> Board render, bottom" >&2
BOTTOM_RENDER_NAME="$(basename "$PCB_FILE" .kicad_pcb)_render_bottom.png"
run_cli pcb render --side bottom --quality basic --background opaque \
    --preset follow_pcb_editor --output "/deliverables/${BOTTOM_RENDER_NAME}" "$PCB_NAME"

echo >&2
echo "Done. Freshly regenerated from source:" >&2
echo "  ${DELIVERABLES_DIR}/ERC_report_errors_only.rpt" >&2
echo "  ${DELIVERABLES_DIR}/ERC_report_full.rpt" >&2
echo "  ${DRC_OUT_DIR}/DRC_report_errors_only.rpt" >&2
echo "  ${DRC_OUT_DIR}/DRC_report_full.rpt" >&2
echo "  ${GERBER_DIR}/" >&2
echo "  ${DELIVERABLES_DIR}/${BOM_NAME}" >&2
echo "  ${DELIVERABLES_DIR}/${PDF_NAME}" >&2
echo "  ${DELIVERABLES_DIR}/${TOP_RENDER_NAME}" >&2
echo "  ${DELIVERABLES_DIR}/${BOTTOM_RENDER_NAME}" >&2
echo >&2
echo "When comparing against a submitted report, check ITS OWN 'Report" >&2
echo "includes:' header line first -- kicad-cli's plain default (no" >&2
echo "--severity flag) is already errors+warnings, so an errors-only" >&2
echo "submitted report was necessarily generated with an explicit" >&2
echo "--severity-error flag. Match _errors_only against that; match" >&2
echo "_full against anything generated with --severity-all. A gap between" >&2
echo "a 0-violation submitted report and this tool's _full report is very" >&2
echo "likely just that scope difference, not a real discrepancy -- check" >&2
echo "_full's violation types (and any local severity overrides already" >&2
echo "in the board file) before treating any of them as new problems." >&2
echo >&2
if [[ $IN_PLACE -eq 0 ]]; then
    echo "Source folder was NOT modified (mounted read-only). Compare the" >&2
    echo "output above against what's committed, e.g.:" >&2
    echo "  diff ${DRC_OUT_DIR}/DRC_report_errors_only.rpt ${BOARD_DIR}/DRC_report.rpt" >&2
    echo "Re-run with --in-place once you're intentionally replacing the" >&2
    echo "committed reports." >&2
else
    echo "Compare these against what the PCB engineer submitted (git diff) --" >&2
    echo "differences may indicate a stale/hand-edited report, a schematic/PCB" >&2
    echo "parity issue, or a change that wasn't actually re-run before submission." >&2
fi
