# InDesign Portfolio Skill

An agent skill and a small Adobe InDesign builder for a repeatable, editable portfolio. It takes approved copy and local images from `portfolio.json`, creates a native `.indd`, exports a PDF, and writes a build report.

## What it creates

- Cover, about/index, project pages, and optional gallery/detail pages.
- Editable InDesign text and placed image frames.
- A PDF for review and an issue report for fonts, images, and overset text.

## Requirements

- Python 3.9 or newer for validation and runner generation.
- Adobe InDesign for building the `.indd` and PDF. The CLI runs it automatically on macOS. On Windows, run the generated JSX through InDesign's Scripts panel.

## Quick start

1. Copy [`examples/portfolio.json`](examples/portfolio.json) into your project and replace the sample copy. Set your image and output paths.
2. Validate and prepare the script:

   ```bash
   python3 scripts/portfolio_cli.py validate --spec /path/to/portfolio.json
   python3 scripts/portfolio_cli.py prepare --spec /path/to/portfolio.json
   ```

3. On macOS, build directly:

   ```bash
   python3 scripts/portfolio_cli.py run --spec /path/to/portfolio.json
   ```

   On Windows, run the generated `portfolio-build.jsx` from **Window > Utilities > Scripts** in InDesign.

4. Inspect the report, PDF, and native InDesign document before delivery. Keep linked images beside the source content for future revisions.

The builder does not upload project material or publish to Wix. The full agent workflow is in [`SKILL.md`](SKILL.md).
