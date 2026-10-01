# InDesign Portfolio Skill

An agent skill and Adobe InDesign builder for a repeatable, editable portfolio. Give the agent a folder of work; it inventories the files, develops case studies, creates a native `.indd`, exports a PDF, and writes a build report.

## What it creates

- Cover, about/index, project pages, and optional gallery/detail pages.
- Editable InDesign text and placed image frames.
- A PDF for review and an issue report for fonts, images, and overset text.
- A file coverage ledger so every scanned work is included, excluded, or flagged for review.

## Requirements

- Python 3.9 or newer for scanning, validation, and runner generation.
- Adobe InDesign for building the `.indd` and PDF. The CLI runs it on macOS and Windows.
- Optional: `pdftotext` for PDF text, `ffprobe` for media metadata, and `laya` on Python 3.10+ for rare ambiguous decisions. The skill works without these optional tools.

## Quick start

1. Tell the agent: **“Use `indesign-portfolio` on `/path/to/my-work-folder`.”** It will scan and inspect the folder, complete a file coverage ledger, and draft `portfolio.json`. No curated input file is required from you.
2. For direct CLI use, scan the folder and review the inventory and generated `coverage-ledger.json`. The agent then creates the edited portfolio spec from the evidence:

   ```bash
   python3 scripts/scan_folder.py --folder /path/to/my-work-folder
   ```

3. Validate and prepare the script:

   ```bash
   python3 scripts/check_coverage.py --inventory /path/to/.indesign-portfolio/inventory.json --ledger /path/to/.indesign-portfolio/coverage-ledger.json
   python3 scripts/portfolio_cli.py validate --spec /path/to/portfolio.json
   python3 scripts/portfolio_cli.py prepare --spec /path/to/portfolio.json
   ```

4. On macOS or Windows, build directly:

   ```bash
   python3 scripts/portfolio_cli.py run --spec /path/to/portfolio.json
   ```

   You can also run the generated `portfolio-build.jsx` from **Window > Utilities > Scripts** in InDesign.

5. Inspect the report, PDF, and native InDesign document before delivery. Keep linked images beside the source content for future revisions.

Laya is deliberately optional. The agent calls [`scripts/laya_decision.py`](scripts/laya_decision.py) only when evidence leaves multiple credible editorial or layout choices; routine file analysis and rendering never call it.

The builder does not upload project material or publish to Wix. The full agent workflow is in [`SKILL.md`](SKILL.md).
