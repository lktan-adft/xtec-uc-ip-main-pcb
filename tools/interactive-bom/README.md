# interactive-bom

Generates a self-contained, clickable HTML board+BOM viewer from a
`.kicad_pcb`, using [InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom)
(a third-party, MIT-licensed KiCad plugin). Click a BOM row to highlight
every footprint on that row on the rendered board, or click a footprint to
see its row -- useful for exactly the kind of finding this repo's review
process cares about: is this refdes actually where the engineer says it is,
does its silkscreen-visible orientation/keying look right, is it really
DNP. Runs entirely in Docker -- no local KiCad or Python install required.

## Usage

```bash
tools/interactive-bom/run.sh <board.kicad_pcb> [output-dir] [-- extra args]
```

```bash
# Output next to the source file: IOB/IOB_v3.2.1_ibom.html
tools/interactive-bom/run.sh IOB/IOB_v3.2.1.kicad_pcb

# Output into a review folder
tools/interactive-bom/run.sh IOB/IOB_v3.2.1.kicad_pcb changelog/v3.2.1/claude_review

# Pass extra flags through to generate_interactive_bom (note the --)
tools/interactive-bom/run.sh IOB/IOB_v3.2.1.kicad_pcb -- --dark-mode --highlight-pin1 all
```

Output is `<board-basename>_ibom.html`, fully self-contained (board
geometry, BOM data, and the viewer's JS/CSS are all embedded in the one
file -- opening it needs a browser, not a server or internet connection).
Run `docker run --rm interactive-bom:local --help` after building once (or
see [the project's own docs](https://github.com/openscopeproject/InteractiveHtmlBom/wiki/Usage))
for the full flag list -- `--dark-mode`, `--highlight-pin1`,
`--board-rotation`, `--layer-view {F,FB,B}`, etc.

## Why this needed its own Dockerfile (not just `pip install`)

`InteractiveHtmlBom` imports `pcbnew` directly, so it has to run inside an
actual KiCad install (`pcbnew` isn't a plain pip package -- it's part of
`kicad-cli`'s own Python bindings) -- hence `FROM kicad/kicad:10.0.4`
rather than a plain `python` base image, matching `tools/kicad-reports`.

Getting a clean, non-hanging headless run took three fixes, in case a
future KiCad/InteractiveHtmlBom version bump changes this:

1. **`pip install --no-deps`** -- the PyPI package declares `wxPython` as a
   hard dependency, but wx is only used for the interactive GUI config
   dialog (`--show-dialog`) and the live "Generate Interactive HTML BOM"
   button inside Pcbnew's own toolbar -- neither of which CLI-only usage
   touches. `wxPython` has no prebuilt wheel for this base image and fails
   to build from source (needs system GTK/build headers this image doesn't
   have) -- skip it entirely with `--no-deps`.
2. **`INTERACTIVE_HTML_BOM_CLI_MODE=1`** -- without this, importing the
   package tries to register itself as a live Pcbnew GUI action plugin,
   which hits `assert "PgmOrNull()" failed in register_action()` -- that
   registration path assumes it's running inside a live KiCad GUI process,
   not a standalone script.
3. **`INTERACTIVE_HTML_BOM_NO_DISPLAY=1`** -- without this (even with
   `--no-deps`, no `wx` importable), `generate_interactive_bom.py`'s
   `main()` still refuses to run: it exits with "wxpython is required
   unless INTERACTIVE_HTML_BOM_NO_DISPLAY environment variable is set".
   This is the one that actually matters for headless CLI use -- reading
   `InteractiveHtmlBom/compat.py`'s `should_create_wx_app()` is what
   revealed it; it isn't mentioned in the project's own CLI `--help` text.

`xvfb-run` (a virtual X display) was tried first and made things *worse* --
with both wx's import graph present and a real (virtual) display available,
the process hangs indefinitely instead of failing fast. Skip xvfb; the two
env vars above are the actual fix.

## Files

- `Dockerfile` -- `kicad/kicad:10.0.4` + pip-installed `InteractiveHtmlBom`
  (no-deps) + the two env vars above.
- `run.sh` -- builds the image and runs it against a `.kicad_pcb` in one step.
