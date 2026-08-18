# changelog/

Cross-revision artifacts for each board family, one subfolder per
version (e.g. `v3.2.1/`). See the top-level
[README.md](../README.md#review-process) for how these fit into the
overall review process.

Each `changelog/v<X>/` contains:

- **`Changelog X1-<board> <date>.xlsx`** — tracked. The
  designer/reviewer's structured, plain-English list of what changed
  in this revision and why. Read with
  [`tools/xlsx-tools/read_xlsx.py`](../tools/xlsx-tools/README.md) if
  you don't have Excel/LibreOffice handy.
- **`Internal Peer Checklist - X1_<board>.xlsx`** — tracked. Designer
  self-check (filled by the designer) + human Checker sign-off column
  (filled by the peer reviewer). This is the record of manual review,
  not something any automated tool should overwrite.
- **`gerber_<new>_v.<old>/`** — **not tracked** (gitignored, see
  `.gitignore`). Raw old/new Gerber pairs for visual diffing via
  [`tools/gerber-diff`](../tools/gerber-diff/README.md) — each file can
  run 100K+ lines, far past what's reasonable to commit or what
  GitHub Copilot's PR review can handle. Zip it and attach the zip to
  the PR instead (`Gerber_old_vs_new.zip`).
- **`claude_review/`** — tracked. Output of the
  [`pcb-review`](../.claude/skills/pcb-review/SKILL.md) Claude Code
  skill: `REVIEW_<board>_<version>.md` (plain-English changelog,
  stated-vs-actual cross-check, ERC/DRC delta, gerber diff triage, and
  a ✅/⚠️/🛑 verdict) plus a Claude-filled *copy* of the Internal Peer
  Checklist (`Internal Peer Checklist - X1_<board> (Claude).xlsx`) with
  the Checker column pre-filled for whatever items could be verified
  from the diff/reports/changelog alone. This is a first-pass aid for
  the human Checker — it never replaces their sign-off on the real,
  un-suffixed checklist file above.

Naming convention for `<new>`/`<old>` version folders and gerber pairs
follows the top-level README's
[repo conventions](../README.md#repo-conventions) — version lives in
filenames, not folder names, and old/new Gerber files inside
`gerber_<new>_v.<old>/` are named `<Layer>_old.<ext>` /
`<Layer>_new.<ext>`.
