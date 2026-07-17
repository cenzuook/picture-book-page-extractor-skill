# Page geometry and book structure

## Page classes

Classify canonical results as `front-cover`, `inside-cover`, `title-page`, `single-page`, `two-page-spread`, `endpaper`, `back-cover`, `partial-page`, or `uncertain`.

Use the whole-book sequence to correct local ambiguity. A common topology is a single cover, optional single title pages, repeated spreads, and a single back cover; do not assume every book follows it.

## Detect the page boundary

Prefer, in order:

1. a reliable four-corner page or spread quadrilateral;
2. two page rectangles separated by a stable gutter;
3. a conservative axis-aligned crop from persistent page/background contrast;
4. the full frame when cropping confidence is low.

Reject a geometric transform when corners jump between adjacent stable frames, the candidate omits printed marks, or the estimated quadrilateral is implausibly narrow or skewed.

## Curved pages

Use text baselines, page edges, and gutter curvature for dewarping. Avoid flattening decorative curved typography. When confidence is low, correct only global rotation and perspective.

## Single pages and spreads

- Preserve a complete spread by default.
- Split only when a gutter is reliable and content does not cross it.
- Retain the master spread when derivatives are created.
- Keep covers single; do not synthesize a blank partner.
- Mark partially visible sheets as `partial-page` rather than pretending they are complete.

## Canvas policies

### natural

Keep each natural ratio. Resize only when a target long edge or height is requested.

### group-normalized

Group covers, single pages, and spreads separately. Select a canvas ratio that contains every complete page in its group, scale each page proportionally, and pad with a color sampled from its paper edge.

### single-canvas-pad

Select one containing canvas for all groups. Never stretch or crop to fill it.

## Orientation

Use page geometry and text direction to correct 90-degree rotation. Do not infer orientation from the video canvas alone; portrait pages often appear inside landscape video.

## Output consistency

Preserve a stable gutter position, page scale, paper color, and margin treatment within each group. Avoid page-to-page brightness or padding drift.
