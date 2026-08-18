---
name: pcb-review
description: Automated first-pass review of a KiCad PCB/schematic change already committed to a branch/PR in this repo. Regenerates ERC/DRC and gerber diffs from source, cross-checks the actual diff against changelog/v<X>/Changelog*.xlsx and the PR description, fills a Claude-reviewed copy of the Internal Peer Checklist, and writes changelog/v<X>/claude_review/ with a checkmark/warning/stop verdict. Use when asked to review a PCB or schematic PR/branch, run "the PCB review" or "Claude review", or check a board revision before merge.
---

You are running the second automated review pass described in this
repo's [README.md](../../../README.md#review-process) (after GitHub
Copilot's pass, defined in
[.github/skills/kicad-review/SKILL.md](../../../.github/skills/kicad-review/SKILL.md),
before human sign-off). This skill both builds the plain-English
changelog Copilot's pass does, and — because you have real tool
execution, unlike Copilot's PR-diff-only review — backs it with
actually-regenerated ERC/DRC reports and a real visual gerber diff,
and persists the result as a tracked artifact instead of only a chat
reply.

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
in step 3) or by asking if ambiguous.

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

## 3. Read the stated changelog

```bash
tools/xlsx-tools/read_xlsx.py "changelog/v<X>/Changelog X1-<board> <date>.xlsx"
```

This gives you the header fields (board, designer, updated/previous
version, software) and the numbered list of stated changes — a second,
more structured "stated intent" source alongside the PR description.

## 4. Build the actual changelog from the diff

Read the `git diff` of every `.kicad_sch`/`.kicad_pcb` file on this
branch vs. the previous version. Translate it into plain English,
covering the same categories as
[.github/skills/kicad-review/SKILL.md](../../../.github/skills/kicad-review/SKILL.md)
§1 (component value/part/footprint changes, new/removed components,
net changes — especially power/ground/reset/clock, new floating pins,
refdes changes, placement/rotation, layer changes, trace
width/clearance, vias, copper pours, board outline, silkscreen).

Cross-check against **both**:
- the stated Changelog workbook (step 3)
- the PR title/description

Flag: anything changed but unstated in either; anything stated but not
actually in the diff; anything implausible as an engineering response
to the stated reasoning. If the PR description is missing or too vague
to check against, say so explicitly rather than guessing at intent.

## 5. Check for introduced problems

Same criteria as the Copilot skill §3 (unconnected/floating pins,
shorted/merged nets, footprint mismatches, missing decoupling near ICs
that had it before, reversed-polarity parts, clearance issues) — now
backed by the regenerated ERC/DRC delta and gerber diff images from
steps 1–2, not diff text alone.

## 6. Create the output folder

```bash
mkdir -p changelog/v<X>/claude_review
```

Git-tracked (unlike `gerber_*/` and `fresh_reports/`, which are
gitignored scratch output) — this folder's contents are the persisted
review artifact.

## 7. Fill the Checker column of a copy of the Peer Checklist

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

For items requiring physical/visual judgement you cannot make from
files alone — ADF logo displayed, silkscreen legibility, mechanical
fit, connector orientation/keying, title-block *visual* correctness
beyond text-matching — **leave the Checker cell blank and say so
explicitly in the review report**. Never guess `YES` on something you
didn't actually check.

State clearly, both in the copy's filename (already has `(Claude)`
appended) and in the review report, that this is a first-pass aid for
the human Checker — it does not replace their sign-off on the real
`Internal Peer Checklist - X1_<board>.xlsx`.

## 8. Write the review report

Write or update (if this version's report already exists — see below)
`changelog/v<X>/claude_review/REVIEW_<board>_<new-version>.md`:

- **Stated changes** — from the changelog workbook (step 3)
- **Actual changes** — from the diff (step 4)
- **Stated vs. actual** — the cross-check flags from step 4
- **ERC/DRC delta** — what changed vs. committed reports (step 1)
- **Gerber visual diff** — per-layer triage + what you opened and
  confirmed (step 2), or the explicit "folder doesn't exist" note
- **Checklist coverage** — what you could and couldn't verify (step 7),
  pointing at the filled copy
- **Verdict** — end with:
  - ✅ Matches stated intent, looks fine
  - ⚠️ Worth a second look
  - 🛑 Likely error / should go back to the engineer before merging

If this PR is a revision of a previous round (the report file for this
same `<new-version>` already exists), **update it and the checklist
copy in place** rather than creating a second dated file — one review
artifact per version, matching how the real Changelog/Checklist
workbooks already work per-version.

## 9. Summarize in chat

Give the short verdict (✅/⚠️/🛑 + the one or two things that drove it)
and point at the two files written. Don't paste the full report inline
— it's already saved.
