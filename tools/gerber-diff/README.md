# gerber-diff

Renders two revisions of a Gerber layer set to precisely registered PNGs
and produces a highlighted diff per layer (red = removed, green = added).
Meant to produce something a human, Copilot, or Claude Code can look at
and interpret quickly, instead of eyeballing raw Gerber coordinates.

Runs entirely in Docker — no need to install `gerbv`, `numpy`, or `Pillow`
on the host.

## Usage

```bash
tools/gerber-diff/run.sh <path-to-gerber-folder> [output-dir] [-- extra args]
```

`<path-to-gerber-folder>` follows this repo's convention
(`changelog/<version>/gerber_<new>_v.<old>/`) — a folder containing every
layer for **both** revisions, named `<Layer>_old.<ext>` / `<Layer>_new.<ext>`
(e.g. `TOP_old.pho` / `TOP_new.pho`, `Silkscreen_top_old.pho` /
`Silkscreen_top_new.pho`). **The folder itself can be named anything** —
the script only cares about the `_old` / `_new` suffix on each filename,
not the parent directory name.

Output defaults to `<gerber-folder>/diff_output/`, with one subfolder per
matched layer:

```
diff_output/
  top/            old.png  new.png  diff.png
  bottom/         old.png  new.png  diff.png
  silkscreen_top/ old.png  new.png  diff.png
  ...
  diff_summary.txt
```

`diff_summary.txt` lists percent-changed per layer, sorted with the most
changed layer first, and flags each one `negligible` / `minor` /
`SIGNIFICANT` / `MAJOR` so you can tell how much something changed
without having to know what a "normal" percentage looks like for this
board. Use it to triage which layers actually moved before opening every
image. Real example, IOB v3.2.1 vs v3.2.0:

```
Render window (mm): origin=(-2.0, -149.0), size=(339.5, 347.3), dpi=400

Layer                         Changed %  Flag          Bbox (px)
------------------------------------------------------------------------------------
bottom                           9.529%  SIGNIFICANT   (1149, 3856, 4142, 5574)
top                              5.020%  SIGNIFICANT   (1991, 345, 4984, 2062)
drill_document_map               2.433%  minor         (1959, 338, 5450, 2482)
solder_top                       1.131%  minor         (2008, 347, 4934, 2059)
silkscreen_top                   0.535%  minor         (1830, 166, 4985, 2112)
solder_bottom                    0.284%  negligible    (1991, 345, 4984, 2062)
silkscreen_bottom                0.249%  negligible    (1991, 345, 4984, 2062)
paste_bottom                     0.039%  negligible    (1991, 345, 4984, 2062)
paste_top                        0.039%  negligible    (1991, 345, 4984, 2062)

Flag bands: negligible <0.5%, minor <3%, SIGNIFICANT <10%, MAJOR >=10%.
These are triage bands, not a verdict -- open diff.png for any layer
flagged SIGNIFICANT or above before concluding it is a real design
change (a shifted board outline or re-registered origin can inflate
every layer's number at once).
```

Reading this: the copper layers (`top`, `bottom`) genuinely reworked —
worth opening `top/diff.png` and `bottom/diff.png`. Everything else is
paste/silkscreen/soldermask drift well under 3%, consistent with the
copper rework rather than an independent problem — the flag column makes
that distinction obvious without eyeballing raw percentages.

### Examples

```bash
# Default: output goes to changelog/v3.2.1/gerber_v3.2.1_v.3.2.0/diff_output/
tools/gerber-diff/run.sh changelog/v3.2.1/gerber_v3.2.1_v.3.2.0

# Custom output location
tools/gerber-diff/run.sh changelog/v4.0.0/gerber_v4.0.0_v.3.2.1 /tmp/my-diff

# Pass extra flags through to gerber_diff.py (note the --)
tools/gerber-diff/run.sh changelog/v3.2.1/gerber_v3.2.1_v.3.2.0 -- --dpi 1200 --include-drill
```

## Why per-layer, not one merged render

`gerber_diff.py` renders and diffs **one layer at a time** (copper vs
copper, silkscreen vs silkscreen, etc.), each as a single solid color.

Earlier iterations of this tool rendered all layers of a side (copper +
paste + silkscreen + soldermask) merged into one flat-colored composite
per revision, then diffed the two composites. That produces a diff
dominated by opaque layers overpainting each other in the render, not by
real design changes — on the IOB v3.2.1 vs v3.2.0 comparison it reported
~21% of the board "changed" when the real, per-layer numbers were 5% on
`TOP` copper, 9.5% on `BOTTOM` copper, and under 1.2% on every other
layer. Always diff layer-by-layer.

## Direct script usage (without run.sh)

If you already have `gerbv` + `numpy` + `Pillow` installed locally:

```bash
python3 tools/gerber-diff/gerber_diff.py --root changelog/v3.2.1/gerber_v3.2.1_v.3.2.0 --output /tmp/diff
```

Or point it at two pre-split directories instead of one mixed folder:

```bash
python3 tools/gerber-diff/gerber_diff.py --old old_dir --new new_dir --output /tmp/diff
```

Run `python3 tools/gerber-diff/gerber_diff.py --help` for all options
(`--dpi`, `--margin-mm`, `--include-drill`).

## Files

- `Dockerfile` — Debian + `gerbv` + `numpy` + `Pillow`, running as your host UID/GID so output files aren't root-owned.
- `gerber_diff.py` — the actual render/diff logic.
- `run.sh` — builds the image and runs the script against a folder in one step.
