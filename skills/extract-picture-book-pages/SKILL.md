---
name: extract-picture-book-pages
description: Extract, reconstruct, clean, order, and enhance picture-book pages from MP4, MOV, MKV, AVI, and other reading, storytelling, page-turning, slideshow, screen-recording, or book-preview videos. Use when Codex needs to compare frames to detect page changes, merge pans or zooms of the same page, recover pages from multiple frames, distinguish covers, single pages and two-page spreads, remove backgrounds, hands, player chrome, watermarks, advertisements, intros or outros, normalize page proportions without stretching, correct perspective, create scan-like page images, or improve resolution while preserving every printed character and illustration.
---

# Extract Picture Book Pages

Convert a book video into an ordered, reviewable set of faithful page images. Prefer source fidelity over aggressive cleanup. Never invent, rewrite, translate, or generatively reconstruct printed text or unseen artwork.

## Start with the deterministic pipeline

Probe the video and run the bundled processor:

```powershell
python scripts/process_book_video.py --input "<video>" --output "<output-dir>"
```

Use `--help` to select sampling, canvas, spread, preservation, and resolution options. Require `ffmpeg`, `ffprobe`, Pillow, and NumPy. Use OpenCV when available for advanced alignment and perspective work; retain the conservative fallback otherwise.

Read the generated `manifest.json` and inspect `review/contact-sheet.png` before treating the results as final. Run:

```powershell
python scripts/verify_pages.py --input "<output-dir>"
```

## Follow this workflow

1. Probe duration, frame rate, dimensions, rotation, and streams.
2. Classify the video profile: slideshow, animated pan/zoom, physical book, screen recording, or mixed content.
3. Sample coarsely across the full timeline, then sample densely around candidate page changes.
4. Model page states as `entering`, `stable`, `leaving`, `transition`, or `unrelated`.
5. Cluster frames that show the same printed page after compensating for pan, zoom, rotation, perspective, lighting, and overlays.
6. Prefer multi-frame reconstruction when no single clean, complete frame exists.
7. Classify each canonical result as `front-cover`, `inside-cover`, `title-page`, `single-page`, `two-page-spread`, `endpaper`, `back-cover`, `partial-page`, or `uncertain`.
8. Quarantine advertisements, intros, outros, subscription cards, player UI, unrelated presenters, and channel screens instead of deleting uncertain candidates.
9. Detect the physical page boundary, crop surrounding background, and correct perspective only when geometry is reliable.
10. Normalize pages without stretching or cropping meaningful content.
11. Apply the selected preservation mode and protect original text pixels.
12. Verify order, completeness, duplicates, exclusions, geometry, text fidelity, and visual consistency.

Read [detection-profiles.md](references/detection-profiles.md) for segmentation and same-page rules. Read [page-geometry.md](references/page-geometry.md) for covers, spreads, cropping, padding, dewarping, and page topology. Read [reconstruction.md](references/reconstruction.md) before fusing multiple frames. Read [enhancement-and-text.md](references/enhancement-and-text.md) before cleanup or super-resolution. Read [quality-gates.md](references/quality-gates.md) before final delivery.

## Distinguish page turns from motion

Do not treat a large adjacent-frame difference as sufficient evidence of a new page. Combine structural difference, perceptual similarity, color distribution, feature geometry, text layout, page boundary, and persistence over time.

Treat translated, zoomed, rotated, partially cropped, differently lit, or animated views as the same page when their printed illustration and text layout still agree after alignment. Confirm a new page only when a changed view persists across multiple samples.

Do not use narration pauses as the primary signal. Use audio only as supporting evidence.

## Reconstruct from real frames

Prefer aligned multi-frame fusion over one-frame extraction when a page is panned, zoomed, blurred, glared, partly obscured, or never shown completely. Recover each region only from frames assigned to the same canonical page.

Use temporal median or best-pixel selection after alignment to suppress moving hands, glare, particles, or overlays. Never use generative fill for book content. If a region is absent from every source frame, mark the page `incomplete` and keep a conservative result.

## Preserve book structure

Keep a single-page cover as a single page even when the body uses spreads. Preserve complete two-page spreads by default. Do not split a spread when artwork, text, or layout crosses the gutter. When splitting is requested or safe, retain the master spread alongside left and right derivatives.

Treat non-contiguous repeats conservatively: merge contiguous pan/zoom duplicates, but mark a later repeated page as `repeat` unless it is clearly an outro recap.

## Normalize without distortion

Support three canvas policies:

- `natural`: preserve each page's natural ratio.
- `group-normalized`: normalize covers, single pages, and spreads separately; use this by default.
- `single-canvas-pad`: fit every complete page inside one canvas and add sampled paper-color padding.

Never stretch a page, crop printed content, duplicate a cover to create a spread, or discard half of a spread to match another ratio.

## Remove only unrelated content

Remove black bars, tables, walls, player controls, channel elements outside the page, unrelated overlays, and transition remnants. Preserve printed borders, page numbers, intentional white space, paper texture, decorative marks, and shadows that belong to the artwork.

Place uncertain exclusions under `review/excluded-candidates/` and record timestamps, confidence, and reason codes in the manifest. Use book-wide style and timeline continuity when an advertisement resembles an illustration.

## Choose a preservation mode

- `archive`: use deterministic crop, geometry correction, and resampling only.
- `scan`: add conservative illumination, denoise, local contrast, sharpening, and text-protected restoration; use this by default.
- `enhanced`: allow stronger super-resolution, require before/after review, and mark reconstructed pixels and low-confidence pages.

Use OCR only for comparison, page identity, and verification. Never redraw visible text from OCR output. Protect detected neutral-dark ink with the source-derived text layer when using super-resolution. Reject or fall back when text regions change materially.

## Deliver reviewable outputs

Produce:

```text
output/
├── pages/
│   ├── 001-front-cover.png
│   ├── 002.png
│   └── ...
├── review/
│   ├── contact-sheet.png
│   ├── review.html
│   └── excluded-candidates/
├── manifest.json
├── verification.json
└── pages.zip
```

Record source timestamps, state intervals, page class, frame cluster, crop and transform geometry, original and output dimensions, reconstruction and enhancement methods, text checks, confidence, exclusions, and warnings.

Do not claim completion until low-confidence results have been visually inspected and every quality gate in [quality-gates.md](references/quality-gates.md) passes or is explicitly reported.
