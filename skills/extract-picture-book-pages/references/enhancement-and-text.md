# Enhancement and text preservation

## Preservation modes

### archive

Allow deterministic crop, rotation, perspective correction, color-profile conversion, and high-quality resampling. Avoid learned restoration.

### scan

Add conservative illumination correction, mild denoise, local contrast, sharpening, and optional text-protected super-resolution. Preserve paper texture and watercolor variation.

### enhanced

Allow stronger restoration and super-resolution. Require before/after inspection, record the model and scale, and quarantine pages whose text or geometry changes.

## Processing order

1. Correct geometry.
2. Reconstruct from aligned frames when needed.
3. Normalize illumination and white balance across the book.
4. Apply mild denoise.
5. Restore local contrast.
6. Protect the source-derived text and neutral line-art layer.
7. Apply optional super-resolution.
8. Reinsert protected source ink when necessary.
9. Normalize canvas and encode losslessly.

## Text rules

- Never redraw printed text from OCR output.
- Never use a generative image editor on text regions.
- Use OCR only for page identity, ordering, comparison, and warnings.
- Preserve original text geometry and source pixels under deterministic scaling.
- Compare text boxes, connected strokes, and OCR hypotheses before and after enhancement.
- Fall back to `archive` processing when text changes materially.

## Scan appearance

Do not clip paper highlights, bleach intentional off-white paper, remove watercolor granulation, oversaturate paint, or create sharpening halos. Normalize page-to-page color using a robust book-wide paper reference rather than pure white.

## Resolution

Prefer lossless PNG. Preserve aspect ratio. Generate 1080p, 1440p, 2160p, or print-size derivatives from one highest-quality master. Do not claim that deterministic enlargement creates new true detail.

If a super-resolution executable is provided, use a model suited to illustrations and protect neutral-dark ink from the source layer.
