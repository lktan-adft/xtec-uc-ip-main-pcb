---
name: kicad-review
description: Review checklist for KiCad schematic (.kicad_sch) and PCB layout (.kicad_pcb) changes in a pull request. Use whenever a PR modifies KiCad project files, to check the diff against the PR description and flag design issues.
---

You are reviewing a pull request that changes a KiCad project (schematic and/or PCB layout files, which are plain-text S-expression format). Follow this process:

## 1. Build a plain-English changelog
Read the diff of any `.kicad_sch` and `.kicad_pcb` files changed in this PR. Translate it into a plain-English list of what actually changed — do not just describe the raw text diff. Call out:
- Component value, part number, or footprint changes
- New or removed components
- Net/connection changes, especially power, ground, reset, and clock lines
- New unconnected or floating pins
- Reference designator changes
- Component placement/rotation changes
- Layer changes (a signal moved to a different copper layer)
- Trace width or clearance changes
- Via additions or removals
- Copper pour / zone changes
- Board outline or mechanical changes
- Silkscreen changes affecting assembly or readability

## 2. Compare against stated intent
Read the PR title and description. It should describe what the engineer changed and why (and ideally what they tested). Check the actual diff against that description and flag:
- Anything that changed but wasn't mentioned in the description
- Anything the description claims changed but the diff doesn't show
- Whether the change is a plausible engineering response to the stated reasoning (e.g. a component value change that matches a described test result)

If the PR description is missing or too vague to check against (e.g. just "fixes issue"), say so explicitly and ask for a more specific description rather than guessing at intent.

## 3. Check for introduced problems
Independent of stated intent, flag anything in the diff that looks like it could be an error:
- Unconnected or floating pins
- Shorted or unintentionally merged nets
- Footprint/component mismatches
- Missing decoupling near ICs that previously had it
- Reversed polarity parts (electrolytic caps, diodes, connectors)
- Clearance or spacing issues visible in the layout diff

## 4. Check ERC/DRC reports if present
Board projects live under a per-family folder (e.g. `IOB/`), with generated reports in `<board>/Deliverables/ERC_report.rpt` and `<board>/DRC_report.rpt`. If the PR updates these, diff them against the previous revision and call out any new violations that weren't present before. Also check `changelog/` for the changelog workbook, peer checklist, and any `gerber_<new>_v.<old>/` old/new gerber pairs — cross-reference these against the raw `.kicad_sch`/`.kicad_pcb` diff rather than trusting them blindly.

## 5. Summarize
End the review with a short summary using this format:
- ✅ Matches stated intent, looks fine
- ⚠️ Worth a second look
- 🛑 Likely error / should go back to the engineer before merging

Keep the summary concise — this is a first-pass flag for a human reviewer, not a full engineering sign-off.
