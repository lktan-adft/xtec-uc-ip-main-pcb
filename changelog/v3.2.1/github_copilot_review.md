## Pull request overview

Adds generated Gerber comparison artifacts for IOB v3.2.1 and updates generated-file handling. No KiCad source or changelog workbook changes are included, so the stated port cannot be verified.

**Changes:**
- Adds old/new solder-mask and paste-layer snapshots.
- Ignores rendered diff output and suppresses PNG diffs.
- 🛑 Generated artifacts and inconsistent layer comparisons require correction.

### Reviewed changes

Copilot reviewed 9 out of 22 changed files in this pull request and generated 4 comments.

<details>
<summary>Show a summary per file</summary>

| File | Description |
| ---- | ----------- |
| `Solder_bottom_old.pho` | Old bottom-mask snapshot |
| `Solder_bottom_new.pho` | New bottom-mask snapshot |
| `Paste_top_old.pho` | Old top-paste snapshot |
| `Paste_top_new.pho` | New top-paste snapshot |
| `Paste_bottom_old.pho` | Old bottom-paste snapshot |
| `Paste_bottom_new.pho` | New bottom-paste snapshot |
| `.gitignore` | Ignores rendered diff output |
| `.gitattributes` | Marks PNGs as generated |
</details>





<details>
<summary>Suppressed comments (1)</summary>

**changelog/v3.2.1/gerber_v3.2.1_v.3.2.0/Solder_bottom_new.pho:1017**
* This new bottom-solder-mask snapshot contains the board outline and mounting-hole circles, while `Solder_bottom_old.pho` contains only mask flashes. The visual comparison will therefore report mechanical geometry as mask changes (or, if this is the fabrication layer, expose unintended mask geometry). Regenerate the pair with identical overlays and only the target mask layer.
```
G01X4566927Y7165357D02*
G75*
G02X4685037Y7283468I0118110J0000000D01*
G01X4566927Y3110239D02*
G01X4566927Y7165357D01*
```
</details>



---
**changelog/v3.2.1/gerber_v3.2.1_v.3.2.0/Solder_bottom_old.pho**

This raw Gerber comparison directory is committed under `changelog/v3.2.1/gerber_*`, which bypasses the existing `changelog/gerber_*/` ignore rule. Both the PR description and `README.md:97` require these regenerable snapshots to be zipped and attached, not committed. Remove the directory from the PR and either place future output at the documented path or make the ignore rule recursive.


**changelog/v3.2.1/gerber_v3.2.1_v.3.2.0/Solder_bottom_new.pho**

The new bottom-mask apertures are consistently 0.004 in smaller than their old equivalents (for example 0.106 vs 0.110, 0.0847 vs 0.0887, and 0.066 vs 0.070). This changes mask expansion by 0.002 in per side during a stated software port and is not documented or validated. Restore the old clearance in the KiCad source and regenerate, or explicitly document and verify the manufacturing change.

This issue also appears on line 1013 of the same file.

**changelog/v3.2.1/gerber_v3.2.1_v.3.2.0/Paste_top_new.pho**

The new top-paste snapshot adds the board outline and mounting-hole circles, but `Paste_top_old.pho` contains only paste flashes. This makes the old/new visual diff show non-paste geometry as a change and can conceal real stencil differences. Regenerate both snapshots with identical overlays and only the paste layer.

**changelog/v3.2.1/gerber_v3.2.1_v.3.2.0/Paste_bottom_new.pho**

The new bottom-paste snapshot adds the board outline and mounting-hole circles, whereas `Paste_bottom_old.pho` contains only paste flashes. This contaminates the layer comparison with mechanical geometry and prevents a reliable stencil diff. Regenerate both snapshots with identical overlays and only the paste layer.
