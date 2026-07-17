# Detection profiles

Select a profile before tuning thresholds. Use adaptive statistics from the video; treat the values below as starting points, not universal constants.

## Slideshow or hard-cut video

- Sample at 1-2 fps for the coarse pass.
- Detect sustained structural changes and collapse adjacent transition peaks.
- Keep brief title or end pages when they are book-consistent.
- Expect no reliable physical page contour when the page fills the frame.

## Animated pan or zoom

- Use feature alignment, text layout, and local descriptors to cluster same-page views.
- Do not split on gradual histogram drift alone.
- Increase dense sampling around high-change intervals.
- Reconstruct a mosaic when different regions of one page appear over time.

## Physical book and hand-held camera

- Track the page quadrilateral, gutter, hands, glare, curvature, and camera motion.
- Require a stable state after the moving sheet settles.
- Prefer frames with all corners visible; fuse aligned frames when occlusion moves.
- Use dewarping only with reliable page edges or text baselines.

## Screen recording

- Detect player chrome, mouse pointers, captions, progress bars, and app panels.
- Do not crop printed content merely because the page touches a screen edge.
- Treat recurring UI regions as removable overlays only when they are not part of the book.

## Mixed content

- Combine page-likeness with book-wide continuity: palette, illustration style, recurring characters, paper color, text layout, and aspect family.
- Use OCR only to flag calls to action, prices, URLs, QR codes, subscription prompts, and channel branding.
- Quarantine uncertain non-book segments; never discard them irreversibly.

## Page state model

Assign each sampled interval one of:

- `unknown`
- `entering-page`
- `stable-page`
- `leaving-page`
- `transition`
- `unrelated-content`

Confirm a canonical page from a stable interval. Allow recovery from non-stable frames only after they are aligned to a confirmed page.

## Coarse-to-fine sampling

1. Sample the full video at 1-2 fps.
2. Compute structural, histogram, and perceptual differences.
3. Find adaptive outliers using median and median absolute deviation.
4. Densely resample candidate boundaries at 10-30 fps.
5. Collapse transition bursts into one boundary.
6. Require the new visual state to persist for at least 0.75-1.5 seconds unless the frame is clearly a cover, title, or end page.

## Same-page evidence

Strong evidence for the same page includes:

- geometric feature matches after homography;
- identical text block positions;
- overlapping illustration regions under pan or zoom;
- stable page border or gutter geometry;
- compatible local color and texture distributions.

Do not merge two pages solely because they share a template or mostly white paper.
