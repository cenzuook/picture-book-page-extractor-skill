#!/usr/bin/env python3
"""Align and median-fuse frames that show the same printed page."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Align same-page frames and create a conservative fused image.")
    parser.add_argument("--input", required=True, type=Path, help="Directory of same-page frames")
    parser.add_argument("--output", required=True, type=Path, help="Output PNG")
    parser.add_argument("--reference", type=int, default=-1, help="Reference frame index; -1 chooses the middle frame")
    parser.add_argument("--minimum-inliers", type=int, default=18)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise SystemExit("OpenCV and NumPy are required for multi-frame reconstruction.") from exc

    paths = sorted([*args.input.glob("*.png"), *args.input.glob("*.jpg"), *args.input.glob("*.jpeg")])
    if len(paths) < 2:
        raise SystemExit("Provide at least two frames that show the same page.")
    images = [cv2.imread(str(path), cv2.IMREAD_COLOR) for path in paths]
    if any(image is None for image in images):
        raise SystemExit("One or more frames could not be read.")
    reference_index = args.reference if 0 <= args.reference < len(images) else len(images) // 2
    reference = images[reference_index]
    gray_reference = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    detector = cv2.ORB_create(nfeatures=5000)
    keypoints_reference, descriptors_reference = detector.detectAndCompute(gray_reference, None)
    if descriptors_reference is None:
        raise SystemExit("Reference frame has insufficient features.")
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    aligned = [reference.astype(np.float32)]
    for index, image in enumerate(images):
        if index == reference_index:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        keypoints, descriptors = detector.detectAndCompute(gray, None)
        if descriptors is None:
            continue
        pairs = matcher.knnMatch(descriptors, descriptors_reference, k=2)
        good = [first for first, second in pairs if first.distance < 0.74 * second.distance]
        if len(good) < args.minimum_inliers:
            continue
        source_points = np.float32([keypoints[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        target_points = np.float32([keypoints_reference[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        transform, inliers = cv2.findHomography(source_points, target_points, cv2.RANSAC, 3.0)
        if transform is None or inliers is None or int(inliers.sum()) < args.minimum_inliers:
            continue
        warped = cv2.warpPerspective(image, transform, (reference.shape[1], reference.shape[0]))
        aligned.append(warped.astype(np.float32))
    if len(aligned) < 2:
        raise SystemExit("Alignment failed; use the best single frame.")
    fused = np.median(np.stack(aligned), axis=0).clip(0, 255).astype(np.uint8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), fused):
        raise SystemExit(f"Could not write {args.output}")
    print(f"Aligned {len(aligned)} of {len(images)} frames -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
