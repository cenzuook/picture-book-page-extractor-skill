# Quality gates

Do not report final completion until the following checks pass or the remaining exceptions are clearly reported.

## Completeness and order

- Every stable book page or spread has one canonical output.
- Page order follows the book presentation after unrelated segments are removed.
- Contiguous pan and zoom views are deduplicated.
- Non-contiguous repeats are labeled rather than silently removed.
- Covers, title pages, endpapers, and short end pages are not lost.

## Geometry

- No page is stretched.
- No crop intersects text, illustration, page numbers, printed borders, or intentional whitespace.
- Covers remain single pages.
- Spreads remain complete unless explicitly split.
- Perspective correction has no warped text or implausible corners.
- Padding is consistent within each page class.

## Content fidelity

- Visible text originates from source frames.
- No character, punctuation mark, illustration element, or page number is invented or removed.
- Multi-frame fusion has no ghost text, double outlines, or seams.
- Super-resolution has no altered characters, ringing, tiled artifacts, or plastic textures.
- Paper and watercolor textures remain plausible and consistent.

## Exclusions

- No advertisement, intro, outro, player UI, channel card, unrelated presenter, or subscription screen appears in `pages/`.
- Every uncertain exclusion remains recoverable under `review/excluded-candidates/`.
- Exclusion reasons and timestamps are present in the manifest.

## Technical output

- Numbering is continuous.
- Images open successfully and use the requested format and color mode.
- Manifest page count matches the filesystem.
- Contact sheet and review page include every output and exclusion.
- Duplicate and low-confidence warnings are recorded in `verification.json`.

## Human review triggers

Require visual review for confidence below 0.82, partial pages, persistent hands or glare, uncertain advertisements, reconstructed mosaics, spread splitting, dewarping, enhanced-mode output, or any text-fidelity warning.
