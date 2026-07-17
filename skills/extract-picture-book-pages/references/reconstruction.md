# Multi-frame page reconstruction

Use multi-frame reconstruction when no single frame is simultaneously complete, sharp, unobstructed, and transition-free.

## Source restrictions

- Fuse only frames assigned to the same canonical page.
- Recover pixels only from the source video.
- Never use generative inpainting for missing printed content.
- Mark unrecoverable regions and lower confidence.

## Alignment

1. Select a sharp, geometrically complete reference frame.
2. Detect local features in the physical page region.
3. Match features with ratio and mutual-consistency checks.
4. Estimate translation, affine transform, or homography with robust outlier rejection.
5. Reject transforms with insufficient inliers, implausible scale, reflection, or severe distortion.
6. Warp candidates into the reference page coordinate system.

Use translation for screen slides, homography for planar pages, and page-aware dewarping for curved physical books.

## Fusion

Prefer region-wise best-pixel selection based on sharpness, exposure, glare, occlusion, and distance from frame edges. Use temporal median after alignment to remove moving hands, particles, cursors, and transient overlays.

Do not median-blend unaligned text; it creates ghost strokes. Preserve the sharpest source observation for each text region.

## Panoramic page recovery

When a camera pans over one page or spread, create a mosaic from overlapping regions. Verify that repeated text and illustrations align before accepting the canvas. Crop the mosaic to the recovered physical page boundary.

## Failure handling

Fall back to the best single frame when alignment is unstable. Record `alignment_failed`, `incomplete_source_coverage`, `persistent_occlusion`, or `glare_unresolved` in the manifest.

Use `scripts/reconstruct_page.py` for aligned fusion when OpenCV is available.
