#!/usr/bin/env bash
# Build (if needed) the gerber-diff Docker image and run gerber_diff.py
# against a changelog gerber folder, with no local gerbv/numpy/Pillow
# install required.
#
# Usage:
#   tools/gerber-diff/run.sh <path-to-gerber-folder> [output-dir] [-- extra gerber_diff.py args]
#
# <path-to-gerber-folder> follows this repo's convention:
#   changelog/<version>/gerber_<new>_v.<old>/
# containing files named "<Layer>_old.<ext>" / "<Layer>_new.<ext>"
# (e.g. TOP_old.pho / TOP_new.pho). The folder can be named anything --
# this script doesn't assume "IOB", a version number, or any fixed name.
#
# [output-dir] defaults to <gerber-folder>/diff_output
#
# Examples:
#   tools/gerber-diff/run.sh changelog/v3.2.1/gerber_v3.2.1_v.3.2.0
#   tools/gerber-diff/run.sh changelog/v4.0.0/gerber_v4.0.0_v.3.2.1 /tmp/my-diff-out
#   tools/gerber-diff/run.sh changelog/v3.2.1/gerber_v3.2.1_v.3.2.0 -- --dpi 1200 --include-drill
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_TAG="gerber-diff:local"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <path-to-gerber-folder> [output-dir] [-- extra args]" >&2
    exit 1
fi

ROOT_DIR="$1"; shift
if [[ ! -d "$ROOT_DIR" ]]; then
    echo "Error: '$ROOT_DIR' is not a directory" >&2
    exit 1
fi
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"

OUTPUT_DIR="${ROOT_DIR}/diff_output"
if [[ $# -gt 0 && "$1" != "--" ]]; then
    OUTPUT_DIR="$1"; shift
fi
if [[ "${1:-}" == "--" ]]; then
    shift
fi
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"

docker build \
    --build-arg UID="$(id -u)" \
    --build-arg GID="$(id -g)" \
    -t "$IMAGE_TAG" \
    "$SCRIPT_DIR" >&2

docker run --rm \
    -v "${ROOT_DIR}:/root_in:ro" \
    -v "${OUTPUT_DIR}:/output" \
    -v "${SCRIPT_DIR}/gerber_diff.py:/gerber_diff.py:ro" \
    "$IMAGE_TAG" \
    /gerber_diff.py --root /root_in --output /output "$@"

echo "Output written to: $OUTPUT_DIR" >&2
