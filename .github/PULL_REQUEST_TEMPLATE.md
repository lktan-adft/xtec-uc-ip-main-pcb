<!--
Fill this out before requesting review. Copilot will auto-review against
.github/skills/kicad-review/SKILL.md, and this description is what Claude Code
and the human reviewer will check the diff against.
-->

## Summary

**Engineer:**
**Board / revision:**

What changed and why:

<!-- Describe the change in plain English: which nets, components, or areas of the board, and the reason (bug fix, DFM feedback, new requirement, etc.) -->

## Testing

<!-- What did you actually test, and what was the result? Bench test, continuity check, fit check, simulation, etc. Be specific — "looks fine" is not a test result. -->

## Files changed

- [ ] `.kicad_sch` (schematic, e.g. `IOB/IOB_v3.2.1.kicad_sch` + sheets)
- [ ] `.kicad_pcb` (PCB layout, e.g. `IOB/IOB_v3.2.1.kicad_pcb`)
- [ ] Updated ERC report (`IOB/Deliverables/ERC_report.rpt`)
- [ ] Updated DRC report (`IOB/DRC_report.rpt`)
- [ ] Updated Gerbers / drill files (`IOB/Gerber/`)
- [ ] Updated BOM (`IOB/Deliverables/*_BOM.csv`)
- [ ] Updated changelog workbook + peer checklist (`changelog/`)
- [ ] Zipped old/new gerber diff attached to this PR (**not committed** — `changelog/gerber_*/` is gitignored, see [changelog/README.md](../changelog/README.md))

## Reviewer checklist (manual sign-off)

- [ ] Copilot auto-review comment posted and reviewed
- [ ] Claude Code review run and reviewed (changelog + ✅/⚠️/🛑 summary)
- [ ] Diff images cross-checked against Copilot + Claude findings
- [ ] Mechanical fit / clearances verified
- [ ] Silkscreen legibility verified
- [ ] Connector orientation / keying verified
- [ ] Stated test result actually supports the change
- [ ] No new ERC/DRC violations vs. previous revision

## DFM (post-merge, before fabrication)

- [ ] Fabrication package sent to manufacturer
- [ ] DFM report received
- [ ] DFM issues resolved (or N/A)
