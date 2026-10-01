---
name: indesign-portfolio
description: Analyze a user-supplied work folder, select and write portfolio case studies, and build an editable Adobe InDesign document plus PDF on macOS or Windows. Use for InDesign portfolio creation or updates, not Wix site edits.
---

# InDesign portfolio

The user can provide **only a folder path**. Inventory and analyze its work, draft the portfolio content, then produce an editable `.indd` and review PDF. Keep the resulting `portfolio.json` as the source for later revisions. This skill handles the InDesign stage; website publishing is separate.

## Start from the folder

Do not require the user to prepare a JSON file or curate assets first. Run:

```bash
python3 scripts/scan_folder.py --folder "/absolute/path/to/work"
```

This creates `.indesign-portfolio/inventory.json` and `coverage-ledger.json` in that folder; use `--output` to place both beside an inventory in a writable workspace when the source is read-only. `--ledger-output` can place the ledger elsewhere. Repeat scans preserve reviewed ledger decisions. The scanner records every non-hidden file, provisional folder groups, metadata, and bounded text from common documents. PDF text extraction and media metadata use `pdftotext` and `ffprobe` when available. Their absence is a cue for agent review, not a reason to omit those files.

Prepare media paths and video frames:

```bash
python3 scripts/media_previews.py --inventory "/absolute/path/to/work/.indesign-portfolio/inventory.json"
```

`preview-manifest.json` points to original raster images and sampled frames across each video. `ffmpeg` is optional; when absent, open videos in an available player or editor. A preview is an aid to inspection, not a content analysis result. Use `--output-dir` for previews when the inventory directory is read-only.

Read the inventory and inspect **every file**, including every image or design as an image, every PDF page, and every video's sampled frames plus playback for motion, pacing, titles, and transitions. Inspect more frames around cuts or unclear sequences. Listen to or transcribe audio when it carries relevant work; do not infer its content from a waveform or filename. Open native designs such as `.indd`, `.psd`, and `.ai` in a compatible app or inspect a faithful export; if neither is possible, mark them unreadable. Read source documents in context. Identify distinct projects, variants, drafts, final exports, credits, dates, and usable visual assets. The agent must interpret the actual visual or audiovisual content; the scanner and preview script only provide metadata and viewing material.

Fill in the generated coverage ledger: map each file to a project and mark it `selected`, `supporting`, `duplicate`, `excluded`, or `unreadable`, with a reason for exclusions and limitations. For each image, video, audio file, PDF, or native design, set `inspection_status` to `viewed` and write a specific `inspection_note` after review. If the content cannot be inspected, set both inspection and decision status to `unreadable` with the limitation in the note and reason. No `unreviewed` or `pending` entries may remain before delivery. Folder names and timestamps are clues, not proof of a role, result, or publication. Choose the strongest work for the intended audience; account for the rest in the ledger. If the audience is unspecified, create a broad selected-work portfolio based on the evidence.

Draft concise case studies and a visual direction from the sources. Distinguish verified facts from editorial wording. Do not invent results, client names, credits, or contact details. If identity is unavailable, use a neutral title and profile name such as “Selected Work,” a factual headline like “Creative Portfolio,” and flag the missing detail for review; do not block the draft. For reference PDFs or images, inspect the actual pages and derive page size, margins, palette, type hierarchy, and image rhythm. A reference guides design; it does not guarantee pixel-identical reconstruction.

## Optional Laya decision aid

Use ordinary evidence and the user's explicit preferences for routine choices. **Only when two or more plausible project groupings, selections, orders, or visual directions remain after review**, create a short evidence state file and a JSON object of candidate options, then call:

```bash
python3 scripts/laya_decision.py --state-file /path/to/evidence.txt --question "Which layout best fits these references?" --criteria-file /path/to/options.json --ambiguous --reason "Both options fit the reviewed references"
```

The script does not load Laya without `--ambiguous`. Laya is optional and is never used to assert factual credits or outcomes, inspect files, or execute InDesign. If unavailable or uncertain, decide from the evidence and flag unresolved choices. Treat its answer as a suggestion, not authorization.

## Build from the analysis

Save the edited content as `portfolio.json` using [the example](examples/portfolio.json). Record source evidence and any unresolved facts in the coverage ledger; do not put speculative claims in the final copy. Image paths may be relative to the JSON file; the CLI resolves them to absolute paths. The standard builder makes a cover, an about/index page, one case-study page per project, and an optional detail/gallery page when a project has images or facts. It leaves every text frame and placed image editable in InDesign. For a different page architecture, adapt the JSX builder deliberately rather than forcing content into an unsuitable template.

Use exportable stills or faithful frame grabs from selected videos and compatible visual exports from native design files as placed InDesign assets. Preserve the original work files and link the portfolio to the approved stills/exports. Do not describe a video's story or outcome based only on sampled frames.

Before building, verify full folder coverage (pass the actual scan output paths when `--output` was used):

```bash
python3 scripts/check_coverage.py --inventory "/absolute/path/to/work/.indesign-portfolio/inventory.json" --ledger "/absolute/path/to/work/.indesign-portfolio/coverage-ledger.json"
```

## Build

From this skill's directory:

```bash
python3 scripts/portfolio_cli.py status
python3 scripts/portfolio_cli.py validate --spec /absolute/path/to/portfolio.json
python3 scripts/portfolio_cli.py prepare --spec /absolute/path/to/portfolio.json
python3 scripts/portfolio_cli.py run --spec /absolute/path/to/portfolio.json
```

`prepare` emits `portfolio-build.jsx` beside the JSON and may refresh that generated file. It can also be run from InDesign's **Window > Utilities > Scripts** panel. `run` executes it through AppleScript on macOS or InDesign's COM `DoScript` interface through PowerShell on Windows. Use versioned output names for revisions. `--force` permits replacing existing output files or a non-generated runner. InDesign is required for `.indd` creation and PDF export. Do not claim a successful InDesign build from `prepare` alone.

## Review and delivery

Read `portfolio-report.json`. If `ok` is false, resolve missing fonts, image placement failures, or overset text. Inspect the exported PDF page by page for hierarchy, image crops, contrast, spelling, alignment, and correct project order. Open the `.indd` in InDesign to confirm editability and that the document saved. Reconcile all selected case studies with the coverage ledger. Revise the JSON/theme or JSX layout, rebuild, and keep the final `.indd`, PDF, JSON, ledger, and linked assets together.

If InDesign is unavailable, finish the approved content, validate the spec, and prepare the JSX. Report that application execution and visual verification are pending; do not substitute a static PDF for the requested editable InDesign file.

## References

- [Adobe: automate workflows with scripts](https://helpx.adobe.com/indesign/desktop/automation-and-scripting/document-automation/automate-workflows-with-scripts.html)
- [Adobe: InDesign scripting and UXP overview](https://developer.adobe.com/indesign/uxp/scripts/)
- [Laya Router API](https://github.com/NandhaKishorM/laya)
