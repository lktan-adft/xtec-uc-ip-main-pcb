#!/usr/bin/env bash
# Build (if needed) the interactive-bom Docker image and generate a
# self-contained, clickable HTML board+BOM viewer from a .kicad_pcb --
# no local KiCad install required.
#
# Usage:
#   tools/interactive-bom/run.sh <board.kicad_pcb> [output-dir] [-- extra generate_interactive_bom args]
#
# [output-dir] defaults to the same directory as <board.kicad_pcb>.
# Output filename is <board-basename>_ibom.html.
#
# Examples:
#   tools/interactive-bom/run.sh IOB/IOB_v3.2.1.kicad_pcb
#   tools/interactive-bom/run.sh IOB/IOB_v3.2.1.kicad_pcb changelog/v3.2.1/claude_review
#   tools/interactive-bom/run.sh IOB/IOB_v3.2.1.kicad_pcb /tmp/out -- --dark-mode --highlight-pin1 all
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_TAG="interactive-bom:local"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <board.kicad_pcb> [output-dir] [-- extra args]" >&2
    exit 1
fi

PCB_FILE="$1"; shift
if [[ ! -f "$PCB_FILE" ]]; then
    echo "Error: '$PCB_FILE' is not a file" >&2
    exit 1
fi
PCB_DIR="$(cd "$(dirname "$PCB_FILE")" && pwd)"
PCB_NAME="$(basename "$PCB_FILE")"
BASENAME="$(basename "$PCB_FILE" .kicad_pcb)"

OUTPUT_DIR="$PCB_DIR"
if [[ $# -gt 0 && "$1" != "--" ]]; then
    OUTPUT_DIR="$1"; shift
fi
if [[ "${1:-}" == "--" ]]; then
    shift
fi
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

docker build -q -t "$IMAGE_TAG" "$SCRIPT_DIR" >&2

docker run --rm \
    -v "${PCB_DIR}:/board:ro" \
    -v "${OUTPUT_DIR}:/out" \
    "$IMAGE_TAG" \
    --dest-dir /out --name-format "${BASENAME}_ibom" "$@" "/board/${PCB_NAME}"

echo "Output written to: ${OUTPUT_DIR}/${BASENAME}_ibom.html" >&2
