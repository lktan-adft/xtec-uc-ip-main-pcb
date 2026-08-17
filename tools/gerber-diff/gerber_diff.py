#!/usr/bin/env python3
"""
gerber_diff.py -- Render matched pairs of Gerber layers (old vs new) to
precisely registered PNGs and produce a highlighted diff image per layer,
suitable for feeding to Claude or Copilot for interpretation.

Requires the `gerbv` CLI tool and Python packages Pillow and numpy --
see ../Dockerfile / ../README.md to run this without installing anything
on the host.

Two input modes:

  1. --root ROOT_DIR   (matches this repo's changelog/<version>/gerber_*/
     convention: one folder containing every layer for BOTH revisions,
     named "<Layer>_old.<ext>" / "<Layer>_new.<ext>", e.g.
     "TOP_old.pho" / "TOP_new.pho". Files are split by the old/new
     suffix automatically -- the root folder itself can be named
     anything.)

  2. --old OLD_DIR --new NEW_DIR   (two separate directories, one file
     per layer in each, matched by filename with any old/new marker
     stripped.)

Layers are matched between the two revisions by filename with the
old/new marker removed (e.g. "TOP_old.pho" <-> "TOP_new.pho",
"Silkscreen_top_old.pho" <-> "Silkscreen_top_new.pho"). Excellon drill
files are skipped by default; this tool is meant for Gerber (RS-274X)
copper/silkscreen/soldermask/paste/outline layers.

IMPORTANT: each layer is rendered and diffed on its own (one solid
color, one file at a time). Do not merge multiple layers (copper +
silkscreen + soldermask + paste) into a single composite before
diffing -- opaque layers will overpaint each other in the render, and
the resulting "diff" mostly reflects that overpainting rather than
real per-layer changes.

Output (written to OUT_DIR/<layer>/):
    old.png            -- old revision, this layer only
    new.png            -- new revision, this layer only, same scale/origin
    diff.png           -- red = removed (old only), green = added (new only)
Plus OUT_DIR/diff_summary.txt with a percentage-changed table across all
layers, for quick triage of which layers actually changed.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

GERBER_EXTENSIONS = {
    '.gtl', '.gbl', '.gts', '.gbs', '.gto', '.gbo', '.gko', '.gm1', '.gm2',
    '.gbr', '.g2l', '.g3l', '.gtp', '.gbp', '.top', '.bot', '.gpt', '.gpb',
    '.cmp', '.sol', '.pho',
}
SKIP_EXTENSIONS = {'.txt', '.zip', '.pdf', '.csv', '.xln', '.json', '.rpt'}
DRILL_EXTENSIONS = {'.drl'}

# Matches a trailing old/new revision marker in a filename stem, so
# "TOP_old" / "TOP_new" both normalize to the layer key "TOP", and lets
# --root mode decide which side of the comparison a file belongs to.
REVISION_MARKER_RE = re.compile(r'[_\-\.](old|new)$', re.IGNORECASE)

LAYER_COLOR = '#B87333'  # single solid color per render -- see module docstring

# Qualitative bands for the "Changed %" column, so the summary can be read
# at a glance instead of requiring the reader to know what a "normal"
# percentage looks like for this board. Thresholds are deliberately loose
# triage bands, not a pass/fail gate -- always look at diff.png for any
# layer flagged SIGNIFICANT or above before treating it as a real change
# (a shifted board outline can move every layer's bbox and pixel count
# without any copper/silkscreen actually changing).
CHANGE_BANDS = [
    (0.5, 'negligible'),
    (3.0, 'minor'),
    (10.0, 'SIGNIFICANT'),
    (float('inf'), 'MAJOR'),
]


def change_band(changed_pct):
    for threshold, label in CHANGE_BANDS:
        if changed_pct < threshold:
            return label
    return CHANGE_BANDS[-1][1]


def revision_of(path):
    m = re.search(r'[_\-\.](old|new)$', path.stem, re.IGNORECASE)
    return m.group(1).lower() if m else None


def layer_key(path):
    """Filename stem with any trailing _old/_new marker stripped, so old
    and new files for the same physical layer map to the same key."""
    return REVISION_MARKER_RE.sub('', path.stem).lower()


def find_candidate_files(directory, include_drill):
    exts = GERBER_EXTENSIONS | (DRILL_EXTENSIONS if include_drill else set())
    files = [f for f in sorted(Path(directory).iterdir())
             if f.is_file() and f.suffix.lower() in exts]
    if not files:
        skip = SKIP_EXTENSIONS if include_drill else (SKIP_EXTENSIONS | DRILL_EXTENSIONS)
        files = [f for f in sorted(Path(directory).iterdir())
                  if f.is_file() and f.suffix.lower() not in skip]
    return files


def split_root(root_dir, include_drill):
    """--root mode: one folder with both revisions' files mixed together,
    distinguished by an _old/_new filename suffix."""
    old_files, new_files, unmarked = [], [], []
    for f in find_candidate_files(root_dir, include_drill):
        rev = revision_of(f)
        if rev == 'old':
            old_files.append(f)
        elif rev == 'new':
            new_files.append(f)
        else:
            unmarked.append(f)
    if unmarked:
        names = ', '.join(f.name for f in unmarked)
        sys.exit(
            f'--root mode: could not tell old vs new for: {names}\n'
            f'(expected filenames ending in _old / _new). '
            f'Use --old/--new instead if your files are pre-split into directories.'
        )
    return old_files, new_files


def match_layers(old_files, new_files):
    old_by_key = {layer_key(f): f for f in old_files}
    new_by_key = {layer_key(f): f for f in new_files}
    common = sorted(set(old_by_key) & set(new_by_key))
    only_old = sorted(set(old_by_key) - set(new_by_key))
    only_new = sorted(set(new_by_key) - set(old_by_key))
    pairs = [(k, old_by_key[k], new_by_key[k]) for k in common]
    return pairs, only_old, only_new


def parse_gerber_bounds(path):
    """Rough bounding box (mm) from coordinate commands. Good enough for
    framing a render window -- does not need to be exact."""
    try:
        text = open(path, 'r', errors='ignore').read()
    except OSError:
        return None

    fs_match = re.search(r'%FSLA?X(\d)(\d)Y(\d)(\d)\*%', text)
    x_dec = int(fs_match.group(2)) if fs_match else 6
    y_dec = int(fs_match.group(4)) if fs_match else 6
    unit_scale = 25.4 if '%MOIN*%' in text else 1.0

    last_x = last_y = 0.0
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    found = False

    coord_re = re.compile(r'X(-?\d+)?Y(-?\d+)?[^*XYD]*D0[123]\*')
    for m in coord_re.finditer(text):
        xs, ys = m.group(1), m.group(2)
        if xs is not None:
            last_x = int(xs) / (10 ** x_dec) * unit_scale
        if ys is not None:
            last_y = int(ys) / (10 ** y_dec) * unit_scale
        if xs is not None or ys is not None:
            found = True
            min_x, max_x = min(min_x, last_x), max(max_x, last_x)
            min_y, max_y = min(min_y, last_y), max(max_y, last_y)

    return (min_x, min_y, max_x, max_y) if found else None


def combined_bounds(paths):
    bounds = [b for b in (parse_gerber_bounds(p) for p in paths) if b]
    if not bounds:
        return None
    return (
        min(b[0] for b in bounds), min(b[1] for b in bounds),
        max(b[2] for b in bounds), max(b[3] for b in bounds),
    )


def render_layer(file_path, origin_mm, window_mm, dpi, out_png):
    origin_in = (origin_mm[0] / 25.4, origin_mm[1] / 25.4)
    window_in = (window_mm[0] / 25.4, window_mm[1] / 25.4)
    cmd = [
        'gerbv', '-x', 'png', '-a',
        '-D', str(dpi),
        '-O', f'{origin_in[0]:.6f}x{origin_in[1]:.6f}',
        '-W', f'{window_in[0]:.6f}x{window_in[1]:.6f}',
        '-b', '#1a1a1a',
        '-f', LAYER_COLOR,
        '-o', str(out_png),
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'gerbv failed on {file_path}: {result.stderr}')


def make_diff(old_png, new_png, out_png, threshold=24):
    old = np.array(Image.open(old_png).convert('RGB'), dtype=np.int16)
    new = np.array(Image.open(new_png).convert('RGB'), dtype=np.int16)
    if old.shape != new.shape:
        raise RuntimeError('Rendered images differ in size -- renders were not aligned.')

    diff = np.abs(old - new).sum(axis=2)
    changed = diff > threshold

    # Faded grayscale of both renders as context, so unchanged geometry
    # is still visible around the highlighted differences.
    base_gray = ((old.mean(axis=2) + new.mean(axis=2)) / 2 * 0.35).astype(np.uint8)
    out = np.stack([base_gray] * 3, axis=2)

    old_only = changed & (old.sum(axis=2) > new.sum(axis=2))
    new_only = changed & ~old_only

    out[old_only] = [220, 60, 60]   # red   = present in OLD, gone in NEW
    out[new_only] = [60, 200, 90]   # green = present in NEW, not in OLD

    Image.fromarray(out.astype(np.uint8)).save(out_png)

    changed_pct = 100.0 * changed.sum() / changed.size
    ys, xs = np.where(changed)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())) if len(xs) else None
    return changed_pct, bbox


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', help='Folder with both revisions mixed together '
                                    '(files named <Layer>_old.* / <Layer>_new.*). '
                                    'Folder itself can be named anything.')
    ap.add_argument('--old', help='Directory of OLD revision Gerber files (alternative to --root)')
    ap.add_argument('--new', help='Directory of NEW revision Gerber files (alternative to --root)')
    ap.add_argument('--output', required=True, help='Output directory for renders + diffs')
    ap.add_argument('--dpi', type=int, default=600, help='Render resolution (default 600)')
    ap.add_argument('--margin-mm', type=float, default=2.0, help='Margin around board bounds (mm)')
    ap.add_argument('--include-drill', action='store_true',
                     help='Also diff Excellon drill files (*.drl). Skipped by default -- '
                          'this tool targets Gerber layers, and drill files render '
                          'poorly as flat silhouettes.')
    args = ap.parse_args()

    if bool(args.root) == bool(args.old or args.new):
        sys.exit('Pass either --root, or both --old and --new (not both modes).')

    try:
        if args.root:
            old_files, new_files = split_root(Path(args.root), args.include_drill)
        else:
            if not (args.old and args.new):
                sys.exit('--old and --new must both be given.')
            old_files = find_candidate_files(args.old, args.include_drill)
            new_files = find_candidate_files(args.new, args.include_drill)

        if not old_files or not new_files:
            sys.exit('No Gerber-like files found for one side of the comparison.')

        pairs, only_old, only_new = match_layers(old_files, new_files)
        if not pairs:
            sys.exit('No layers could be matched by name between old and new.')

        # Shared render window across all layers/both revisions, so every
        # layer pair (and every pair's old vs new) lines up pixel-for-pixel.
        bounds = combined_bounds([p for _, p, _ in pairs] + [p for _, _, p in pairs])
        if not bounds:
            sys.exit('Could not determine board extents from the Gerber coordinates.')

        min_x, min_y, max_x, max_y = bounds
        m = args.margin_mm
        origin_mm = (min_x - m, min_y - m)
        window_mm = (max_x - min_x + 2 * m, max_y - min_y + 2 * m)

        out_root = Path(args.output)
        out_root.mkdir(parents=True, exist_ok=True)

        summary_lines = [
            f'Render window (mm): origin={origin_mm}, size={window_mm}, dpi={args.dpi}',
            '',
        ]
        if only_old:
            summary_lines.append(f'Layers only in OLD (no match in NEW): {", ".join(only_old)}')
        if only_new:
            summary_lines.append(f'Layers only in NEW (no match in OLD): {", ".join(only_new)}')
        if only_old or only_new:
            summary_lines.append('')

        summary_lines.append(f'{"Layer":<28} {"Changed %":>10}  {"Flag":<12}  Bbox (px)')
        summary_lines.append('-' * 84)

        results = []
        for key, old_path, new_path in pairs:
            layer_dir = out_root / key
            layer_dir.mkdir(parents=True, exist_ok=True)
            old_png = layer_dir / 'old.png'
            new_png = layer_dir / 'new.png'
            diff_png = layer_dir / 'diff.png'

            print(f'[{key}] rendering old ({old_path.name}) and new ({new_path.name})...')
            render_layer(old_path, origin_mm, window_mm, args.dpi, old_png)
            render_layer(new_path, origin_mm, window_mm, args.dpi, new_png)

            changed_pct, bbox = make_diff(old_png, new_png, diff_png)
            flag = change_band(changed_pct)
            print(f'[{key}] changed {changed_pct:.3f}%  [{flag}]  bbox(px)={bbox}')
            results.append((key, changed_pct, flag, bbox))

        for key, changed_pct, flag, bbox in sorted(results, key=lambda r: -r[1]):
            summary_lines.append(f'{key:<28} {changed_pct:>9.3f}%  {flag:<12}  {bbox}')

        summary_lines.append('')
        summary_lines.append(
            f'Flag bands: negligible <{CHANGE_BANDS[0][0]:g}%, minor <{CHANGE_BANDS[1][0]:g}%, '
            f'SIGNIFICANT <{CHANGE_BANDS[2][0]:g}%, MAJOR >={CHANGE_BANDS[2][0]:g}%. '
            f'These are triage bands, not a verdict -- open diff.png for any layer flagged '
            f'SIGNIFICANT or above before concluding it is a real design change (a shifted '
            f'board outline or re-registered origin can inflate every layer\'s number at once).'
        )

        summary_path = out_root / 'diff_summary.txt'
        summary_path.write_text('\n'.join(summary_lines) + '\n')

        print(f'\nDone. Per-layer renders/diffs under {out_root}/<layer>/, summary at {summary_path}')
    except OSError as e:
        sys.exit(str(e))


if __name__ == '__main__':
    main()
