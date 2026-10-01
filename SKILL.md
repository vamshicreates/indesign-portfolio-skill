---
name: indesign-portfolio
description: Create or update an editable Adobe InDesign portfolio and matching PDF from approved project copy, images, and visual references. Use when the user wants a portfolio made in InDesign, not for a PDF-only document or Wix site edits.
---

# InDesign portfolio

Produce an editable `.indd` and a review PDF from a structured portfolio specification. Use the same content file for revisions so later updates do not require rebuilding the editorial work. This skill handles the InDesign stage; website publishing is separate.

## Inputs and editorial pass

Gather the user's projects, role, credits, outcomes, approved images, contact information, and visual references. Distinguish verified facts from proposed copy. Do not invent results, client names, or credits. Edit and order the content before layout. For reference PDFs or images, inspect the actual pages and derive a small theme: page size, margins, palette, type hierarchy, and image rhythm. A reference is design guidance, not a guarantee of pixel-identical reconstruction.

Save the content as `portfolio.json` using [the example](examples/portfolio.json). Image paths may be relative to that JSON file; the CLI resolves them to absolute paths. The standard builder makes a cover, an about/index page, one case-study page per project, and an optional detail/gallery page when a project has images or facts. It leaves every text frame and placed image editable in InDesign. For a different page architecture, adapt the JSX builder deliberately rather than forcing content into an unsuitable template.

## Build

From this skill's directory:

```bash
python3 scripts/portfolio_cli.py status
python3 scripts/portfolio_cli.py validate --spec /absolute/path/to/portfolio.json
python3 scripts/portfolio_cli.py prepare --spec /absolute/path/to/portfolio.json
python3 scripts/portfolio_cli.py run --spec /absolute/path/to/portfolio.json
```

`prepare` emits `portfolio-build.jsx` beside the JSON and may refresh that generated file. It can be run from InDesign's **Window > Utilities > Scripts** panel on macOS or Windows. `run` drives installed InDesign on macOS through AppleScript; the operating system may request normal Automation permission. Use versioned output names for revisions. `--force` permits replacing existing output files or a non-generated runner. InDesign is required for `.indd` creation and PDF export. Do not claim a successful InDesign build from `prepare` alone.

## Review and delivery

Read `portfolio-report.json`. If `ok` is false, resolve missing fonts, image placement failures, or overset text. Inspect the exported PDF page by page for hierarchy, image crops, contrast, spelling, alignment, and correct project order. Open the `.indd` in InDesign to confirm editability and that the document saved. Revise the JSON/theme or JSX layout, rebuild, and keep the final `.indd`, PDF, JSON, and linked assets together.

If InDesign is unavailable, finish the approved content, validate the spec, and prepare the JSX. Report that application execution and visual verification are pending; do not substitute a static PDF for the requested editable InDesign file.

## References

- [Adobe: automate workflows with scripts](https://helpx.adobe.com/indesign/desktop/automation-and-scripting/document-automation/automate-workflows-with-scripts.html)
- [Adobe: InDesign scripting and UXP overview](https://developer.adobe.com/indesign/uxp/scripts/)
