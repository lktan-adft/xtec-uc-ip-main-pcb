# kicad-reports

Regenerates ERC, DRC, gerbers, drill files, BOM, and schematic PDF
directly from a board's `.kicad_sch`/`.kicad_pcb` source, instead of
trusting whatever report/export files a PR includes. Runs `kicad-cli`
(KiCad 10.0.4, matching this repo's toolchain) via Docker — no local
KiCad install required.

This exists because a submitted `ERC_report.rpt` / `DRC_report.rpt` /
`Gerber/` folder is just files — nothing guarantees they were actually
regenerated from the schematic/PCB in the same PR, or regenerated at
all. Running this tool against the PR's source files and diffing the
output against what was submitted closes that gap.

## Usage

```bash
tools/kicad-reports/generate_reports.sh <board-folder> [output-dir] [--in-place]
```

`<board-folder>` is a folder containing one project's `.kicad_pro` and
its root `.kicad_sch`/`.kicad_pcb` (e.g. `IOB/`). **The folder can be
named anything** — the script locates the project files via the
`.kicad_pro` basename (root schematic and PCB always share the
project's basename, per KiCad's own convention), not by globbing
`*.kicad_sch`, which would just as happily match a sub-sheet file and
silently ERC the wrong one.

### Safe by default: sandboxed output, source is read-only

By default, **all** output (ERC, DRC, gerbers, drill, BOM, PDF) is
written to `[output-dir]`, which defaults to
`<board-folder>/fresh_reports/`. The board folder is mounted read-only
into the container — nothing inside it can be modified, even by a bug
in this script.

```bash
tools/kicad-reports/generate_reports.sh IOB
# -> IOB/fresh_reports/{ERC_report_errors_only.rpt, ERC_report_full.rpt,
#                        DRC_report_errors_only.rpt, DRC_report_full.rpt,
#                        Gerber/, IOB_v3.2.1_BOM.csv, IOB_v3.2.1.pdf}

diff IOB/fresh_reports/DRC_report_errors_only.rpt IOB/DRC_report.rpt
```

### `--in-place`: replace the committed reports

Once you've compared and are intentionally replacing what's committed,
re-run with `--in-place` to write `DRC_report_*.rpt` and `Gerber/`
directly into `<board-folder>`, and `ERC_report_*.rpt`/BOM/PDF into
`<board-folder>/Deliverables/` — matching this repo's existing layout
convention (see the top-level [README.md](../../README.md#repo-conventions)).

```bash
tools/kicad-reports/generate_reports.sh IOB --in-place
git diff IOB/DRC_report_errors_only.rpt IOB/Deliverables/ERC_report_errors_only.rpt
```

`--in-place` is the only mode that writes inside `<board-folder>` —
always sandbox first, review the diff, then re-run with `--in-place`
once you're sure.

## What it runs

| Step | kicad-cli command | Notes |
|---|---|---|
| ERC (errors only) | `sch erc --severity-error --units mm` | |
| ERC (full) | `sch erc --severity-all --units mm` | errors + warnings + exclusions |
| DRC (errors only) | `pcb drc --severity-error --schematic-parity --units mm` | Includes PCB↔schematic parity check |
| DRC (full) | `pcb drc --severity-all --schematic-parity --units mm` | errors + warnings + exclusions |
| Gerbers | `pcb export gerbers` | All layers, kicad-cli's default naming (`<board>-<Layer>.<ext>`) |
| Drill | `pcb export drill --generate-map` | Excellon + drill map |
| BOM | `sch export bom` | Default field set |
| PDF | `sch export pdf` | Full schematic print |

All coordinates in the ERC/DRC reports are in **mm** (`--units mm`),
not mils — this repo's originally submitted `ERC_report.rpt` used mils
(`@(1250 mils, 2550 mils)`), which was inconvenient to cross-reference
against `.kicad_pcb`/`.kicad_sch` coordinates (also mm). All four
reports from this tool use mm consistently.

Note: kicad-cli's default Gerber filenames (`IOB_v3.2.1-F_Cu.gtl`, etc.)
differ from the shop's original CAM export names in this repo's
committed `IOB/Gerber/` (`IOB_v3.2.1-B_Silkscreen.gbr`, etc.) — they're
the same layers, just named by KiCad's own convention rather than the
fab house's. Use [tools/gerber-diff](../gerber-diff) to compare fresh
vs. committed gerbers visually regardless of naming differences.

### Two severity scopes, and why

ERC/DRC are each run twice, producing `*_errors_only.rpt` and
`*_full.rpt`. This exists because comparing a freshly-generated report
against a submitted one is only meaningful if both used the same
severity scope — and **kicad-cli's plain default (no `--severity-*`
flag at all) is already "Errors, Warnings"**, not errors-only. Getting
a true errors-only report requires the explicit `--severity-error`
flag.

This repo's IOB v3.2.1 baseline `ERC_report.rpt` / `DRC_report.rpt`
each say `Report includes: Errors` in their header — meaning they were
generated with an explicit `--severity-error` flag — and both show 0
violations. Running this tool's `*_full.rpt` (errors + warnings +
exclusions) against the same source shows 1041 ERC and 430 DRC
"violations." **This is not a discrepancy** — every one of those extra
items is a warning (`grep` the report: 0 errors either way), largely
pre-existing findings like dangling track stubs, isolated copper fill,
and footprint/symbol value-label mismatches (e.g. a resistor footprint
labeled `R118` whose linked schematic symbol value is generic `RES`) —
already locally overridden to warning-level inside the board file
itself. It only looks alarming because the two reports used different
severity scopes.

**When comparing against a submitted report: read its own `Report
includes:` header line first**, then diff against whichever of
`*_errors_only.rpt` / `*_full.rpt` matches that scope. If a submitted
report doesn't state its scope at all, treat that as worth asking the
engineer about — silently-narrower-scope reports are exactly the kind
of thing this tool exists to catch.

## Incident: why the source folder is read-only

An earlier version of this script wrote DRC/Gerber output directly into
the board folder by default, and located the root schematic with
`find *.kicad_sch | head -n1` — which picked an arbitrary sub-sheet file
alphabetically instead of the actual root schematic. Running it against
`IOB/` overwrote two tracked Gerber files with regenerated-but-differently-named
output and wrote a wrong, single-sheet ERC report over the committed one.
Caught via `git status` immediately after and reverted with
`git checkout`, but it's why the script now (a) resolves the root
schematic/PCB via the `.kicad_pro` basename instead of globbing, and
(b) mounts the board folder read-only and defaults to writing outside
it entirely, requiring `--in-place` as an explicit opt-in to touch
committed files.

## Files

- `Dockerfile` — thin wrapper around `kicad/kicad:10.0.4` (already runs as uid 1000, matching a typical host user).
- `generate_reports.sh` — the actual regeneration logic.
