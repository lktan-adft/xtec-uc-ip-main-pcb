---
name: pcb-review
description: Automated first-pass review of a KiCad PCB/schematic change already committed to a branch/PR in this repo. Regenerates ERC/DRC, gerber diffs, and board renders from source, verifies net/DNP-level changelog claims directly against the .kicad_pcb, cross-checks the actual diff against changelog/v<X>/Changelog*.xlsx and the PR description, fills a Claude-reviewed copy of the Internal Peer Checklist, generates an interactive HTML BOM, and writes changelog/v<X>/claude_review/ with a checkmark/warning/stop verdict. Use when asked to review a PCB or schematic PR/branch, run "the PCB review" or "Claude review", or check a board revision before merge.
---

You are running the second automated review pass described in this
repo's [README.md](../../../README.md#review-process) (after GitHub
Copilot's pass, defined in
[.github/skills/kicad-review/SKILL.md](../../../.github/skills/kicad-review/SKILL.md),
before human sign-off). This skill both builds the plain-English
changelog Copilot's pass does, and — because you have real tool
execution, unlike Copilot's PR-diff-only review — backs it with
actually-regenerated ERC/DRC reports, a real visual gerber diff, board
renders, and direct net/DNP queries against the PCB source instead of
guesswork, and persists the result as a tracked artifact instead of
only a chat reply.

## Preconditions

This skill starts from an **already-open PR/branch** with the PCB
engineer's changes committed. It does not create branches, commit, or
open PRs. Before doing anything else, confirm both of these exist for
the version being reviewed — if either is missing, say so explicitly
and stop rather than fabricating them:

- `changelog/v<X>/Changelog *.xlsx` — the engineer/reviewer's stated
  changelog for this revision
- `changelog/v<X>/Internal Peer Checklist *.xlsx` — the Designer's
  self-check (already filled), Checker column blank

(Both are created/updated by the human reviewer per README step 5,
*before* kicking off this skill — not something this skill authors.)

Identify `<board-folder>` (e.g. `IOB/`), `<new-version>` and
`<old-version>` from the changelog workbook's own header fields (read
in step 4) or by asking if ambiguous.

## 1. Regenerate fresh reports from source

Don't trust whatever `ERC_report.rpt`/`DRC_report.rpt` the PR includes
— regenerate from the actual `.kicad_sch`/`.kicad_pcb` on the branch:

```bash
tools/kicad-reports/generate_reports.sh <board-folder>
```

(Sandboxed by default to `<board-folder>/fresh_reports/` — do **not**
pass `--in-place` for a review pass.) Read
[tools/kicad-reports/README.md](../../../tools/kicad-reports/README.md)'s
"Two severity scopes" section before comparing: check the committed
report's own `Report includes:` header line first, then diff the
freshly-generated report of matching scope (`*_errors_only.rpt` or
`*_full.rpt`) against it. A scope mismatch (e.g. comparing an
errors-only submitted report against this tool's `*_full.rpt`) is not
itself a violation — read the diff, don't just count lines.

This also produces `<board>_render_top.png` / `<board>_render_bottom.png`
— full-color board renders (copper+silkscreen+soldermask+component
bodies). Look at both before filling the checklist (step 8) — these are
what let you actually check items that used to have to be left blank:
ADF logo present, board name/version silkscreen legible and *matches the
revision under review* (this exact check caught a stale "V1.0" silkscreen
mark on a v3.2.1 board — read the text in the render, don't just confirm
something is printed there), connector placement/keying as drawn. Crop
into a region with the `Read` tool's image support if small text isn't
legible at full-board scale. This still isn't a substitute for a human
looking at the physical board or the actual manufactured silkscreen
contrast/registration — say so in the report — but it closes the gap for
anything that's a real error in the source file.

## 2. Visual gerber diff

If `changelog/v<X>/gerber_<new>_v.<old>/` exists (old/new Gerber pairs,
per README step 4 — this folder is gitignored, so it may only exist
locally, not on the PR):

```bash
tools/gerber-diff/run.sh changelog/v<X>/gerber_<new>_v.<old>
```

Read `diff_output/diff_summary.txt` first (percent-changed + triage
flag per layer), then open `diff.png` for any layer flagged
SIGNIFICANT or MAJOR before concluding it's a real design change (see
that tool's README — a shifted board outline can inflate every layer's
number at once).

If the folder doesn't exist yet, say so explicitly in the review output
— don't skip this step silently. It means raw Gerbers for both
revisions still need to be placed there before a visual diff is
possible.

## 3. Verify net- and DNP-level changelog claims directly

Changelogs in this repo routinely make specific, checkable claims like
"U6 pin 35 now connects to ADC_B" or "C32 is now DNI/DNP" — don't leave
these as "not individually confirmed." Query the actual `.kicad_pcb`
directly:

```bash
tools/kicad-query/pcb_net.py <board-folder>/<board>.kicad_pcb --ref U6 --pad 35
tools/kicad-query/pcb_net.py <board-folder>/<board>.kicad_pcb --ref C32
```

The PCB is the right source of truth for this — every pad already carries
its resolved net name after layout, so this is a direct, cheap check
rather than schematic net tracing (which this tool doesn't do — see
[tools/kicad-query/README.md](../../../tools/kicad-query/README.md)).
**Note on `--dnp`:** it only reads the PCB footprint's own `attr` block;
in this project DNP is set at the schematic symbol level and does not
reliably propagate an `attr dnp` marker onto the matching PCB footprint
— cross-check a DNP claim against the BOM's DNP column (reflects the
schematic-side flag) and the schematic symbol itself, not `--dnp` alone.

## 4. Read the stated changelog

```bash
tools/xlsx-tools/read_xlsx.py "changelog/v<X>/Changelog X1-<board> <date>.xlsx"
```

This gives you the header fields (board, designer, updated/previous
version, software) and the numbered list of stated changes — a second,
more structured "stated intent" source alongside the PR description.

## 5. Build the actual changelog from the diff

Read the `git diff` of every `.kicad_sch`/`.kicad_pcb` file on this
branch vs. the previous version. Translate it into plain English,
covering the same categories as
[.github/skills/kicad-review/SKILL.md](../../../.github/skills/kicad-review/SKILL.md)
§1 (component value/part/footprint changes, new/removed components,
net changes — especially power/ground/reset/clock, new floating pins,
refdes changes, placement/rotation, layer changes, trace
width/clearance, vias, copper pours, board outline, silkscreen).

Cross-check against **both**:
- the stated Changelog workbook (step 4)
- the PR title/description

Use step 3's `pcb_net.py` output to settle any net/DNP-level claim
precisely rather than describing it as "consistent with" or "plausible."

Flag: anything changed but unstated in either; anything stated but not
actually in the diff; anything implausible as an engineering response
to the stated reasoning. If the PR description is missing or too vague
to check against, say so explicitly rather than guessing at intent.

## 6. Check for introduced problems

Same criteria as the Copilot skill §3 (unconnected/floating pins,
shorted/merged nets, footprint mismatches, missing decoupling near ICs
that had it before, reversed-polarity parts, clearance issues) — now
backed by the regenerated ERC/DRC delta, gerber diff images, and board
renders from steps 1–2, not diff text alone.

## 7. Create the output folder and generate the interactive BOM

```bash
mkdir -p changelog/v<X>/claude_review
tools/interactive-bom/run.sh <board-folder>/<board>.kicad_pcb changelog/v<X>/claude_review
```

The output folder is git-tracked (unlike `gerber_*/` and
`fresh_reports/`, which are gitignored scratch output) — everything
written into it is the persisted review artifact. The interactive BOM
(`<board>_ibom.html`) is a clickable board+BOM viewer for the human
reviewer — click a refdes to highlight it on the board, useful for
spot-checking placement, orientation, and DNP status alongside the
renders from step 1.

## 8. Fill the Checker column of a copy of the Peer Checklist

```bash
cp "changelog/v<X>/Internal Peer Checklist - X1_<board>.xlsx" \
   "changelog/v<X>/claude_review/Internal Peer Checklist - X1_<board> (Claude).xlsx"
```

For every checklist item you can actually evaluate from the diff,
regenerated reports, and changelog workbook — naming/version bump,
BOM vs. changelog match, refdes/value/footprint vs. changelog,
ERC/DRC zero-errors + every waived item has a comment, required files
present, every PCB update documented in the changelog, gerber overlay
diff performed — set the Checker cell to `YES`/`NO`/`N/A` and a
one-line remark, via
[`tools/xlsx-tools/fill_checklist.py`](../../../tools/xlsx-tools/README.md)
against the **copy**, never the original:

```bash
tools/xlsx-tools/fill_checklist.py \
  "changelog/v<X>/claude_review/Internal Peer Checklist - X1_<board> (Claude).xlsx" \
  patches.json
```

Use `read_xlsx.py` on the copy first (or the original) to find each
item's exact row number — row numbers are stable per this checklist's
template but don't hardcode them from this file; read them fresh.

Items you can now check using step 1's renders — ADF logo displayed,
board name/version silkscreen legible *and correct for this revision*,
connector placement as drawn — should get a real `YES`/`NO`, not a
blank, unless the render genuinely doesn't show it clearly enough. Items
that still need a physical board or a level of judgement no render can
give — mechanical fit, silkscreen legibility under real print/etch
tolerances, connector *keying* (vs. just placement) — **leave the
Checker cell blank and say so explicitly in the review report**. Never
guess `YES` on something you didn't actually check.

State clearly, both in the copy's filename (already has `(Claude)`
appended) and in the review report, that this is a first-pass aid for
the human Checker — it does not replace their sign-off on the real
`Internal Peer Checklist - X1_<board>.xlsx`.

## 9. Write the review report

Write or update (if this version's report already exists — see below)
`changelog/v<X>/claude_review/REVIEW_<board>_<new-version>.md`:

- **Stated changes** — from the changelog workbook (step 4)
- **Actual changes** — from the diff (step 5)
- **Stated vs. actual** — the cross-check flags from step 5, backed by
  step 3's direct net/DNP verification where applicable
- **ERC/DRC delta** — what changed vs. committed reports (step 1)
- **Board renders** — what the step-1 renders confirmed or contradicted
  (e.g. a stale version mark, a missing logo)
- **Gerber visual diff** — per-layer triage + what you opened and
  confirmed (step 2), or the explicit "folder doesn't exist" note
- **Checklist coverage** — what you could and couldn't verify (step 8),
  pointing at the filled copy and the interactive BOM (step 7)
- **Verdict** — end with:
  - ✅ Matches stated intent, looks fine
  - ⚠️ Worth a second look
  - 🛑 Likely error / should go back to the engineer before merging

If this PR is a revision of a previous round (the report file for this
same `<new-version>` already exists), **update it, the checklist copy,
and the interactive BOM in place** rather than creating second dated
files — one review artifact per version, matching how the real
Changelog/Checklist workbooks already work per-version.

## 10. Summarize in chat

Give the short verdict (✅/⚠️/🛑 + the one or two things that drove it)
and point at what got written to `claude_review/` (report, checklist
copy, interactive BOM). Don't paste the full report inline — it's
already saved.
