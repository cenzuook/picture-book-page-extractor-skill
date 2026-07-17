#!/usr/bin/env python3
"""Validate extracted picture-book page outputs and flag review items."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Pillow and NumPy are required. Install pillow and numpy.") from exc


def average_hash(image: Image.Image, size: int = 16) -> np.ndarray:
    gray = image.convert("L").resize((size, size), Image.Resampling.BOX)
    values = np.asarray(gray, dtype=np.float32)
    return values >= values.mean()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify picture-book page extraction output.")
    parser.add_argument("--input", required=True, type=Path, help="Output directory containing pages/ and manifest.json")
    parser.add_argument("--duplicate-distance", type=int, default=7, help="Maximum hash distance for duplicate warning")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when warnings exist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.input.resolve()
    manifest_path = root / "manifest.json"
    pages_dir = root / "pages"
    if not manifest_path.exists() or not pages_dir.exists():
        raise SystemExit("Expected manifest.json and pages/ under the input directory.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = sorted(pages_dir.glob("*.png"))
    errors: list[str] = []
    warnings: list[str] = []
    page_results = []
    numbers = []
    hashes: list[tuple[int, np.ndarray]] = []
    for path in files:
        match = re.match(r"^(\d{3})", path.name)
        if not match:
            warnings.append(f"unrecognized filename: {path.name}")
            continue
        number = int(match.group(1))
        numbers.append(number)
        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                mode = image.mode
                digest = average_hash(image)
        except Exception as exc:
            errors.append(f"cannot open {path.name}: {exc}")
            continue
        if width < 320 or height < 320:
            warnings.append(f"low dimensions: {path.name} is {width}x{height}")
        if mode not in {"RGB", "RGBA"}:
            warnings.append(f"unexpected color mode: {path.name} is {mode}")
        hashes.append((number, digest))
        page_results.append({"number": number, "file": path.name, "size": [width, height], "mode": mode})
    expected_numbers = list(range(1, len(numbers) + 1))
    if numbers != expected_numbers:
        errors.append(f"non-continuous numbering: found {numbers}, expected {expected_numbers}")
    if len(files) != int(manifest.get("page_count", -1)):
        errors.append(f"manifest page_count={manifest.get('page_count')} but filesystem has {len(files)} PNG files")
    duplicates = []
    for i, (left_number, left_hash) in enumerate(hashes):
        for right_number, right_hash in hashes[i + 1:]:
            distance = int(np.count_nonzero(left_hash != right_hash))
            if distance <= args.duplicate_distance:
                duplicates.append({"left": left_number, "right": right_number, "hash_distance": distance})
    if duplicates:
        warnings.append(f"possible duplicate pairs: {len(duplicates)}")
    low_confidence = [
        {"index": page.get("index"), "confidence": page.get("confidence"), "warnings": page.get("warnings", [])}
        for page in manifest.get("pages", [])
        if float(page.get("confidence", 0)) < 0.82 or page.get("warnings")
    ]
    if low_confidence:
        warnings.append(f"pages requiring visual review: {len(low_confidence)}")
    review_required = not (root / "review" / "contact-sheet.png").exists() or not (root / "review" / "review.html").exists()
    if review_required:
        errors.append("review/contact-sheet.png or review/review.html is missing")
    report = {
        "schema_version": 1,
        "page_count": len(files),
        "errors": errors,
        "warnings": warnings,
        "possible_duplicates": duplicates,
        "low_confidence": low_confidence,
        "pages": page_results,
        "visual_review_required": True,
        "passed_technical_checks": not errors,
    }
    report_path = root / "verification.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "errors": len(errors), "warnings": len(warnings)}, ensure_ascii=False))
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
