#!/usr/bin/env python3
"""Extract ordered picture-book page candidates from a video.

This is a conservative baseline pipeline. It intentionally leaves ambiguous
editorial decisions for review instead of deleting uncertain content.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
except ImportError as exc:  # pragma: no cover - dependency message
    raise SystemExit("Pillow and NumPy are required. Install pillow and numpy.") from exc


@dataclass
class Candidate:
    index: int
    segment_start: float
    segment_end: float
    timestamp: float
    source_frame: str
    page_class: str
    crop_box: list[int]
    source_size: list[int]
    output_size: list[int]
    confidence: float
    reconstruction: str = "best-single-frame"
    enhancement: str = "archive"
    text_protection: str = "source-derived-neutral-ink"
    warnings: list[str] | None = None
    output_file: str = ""


def command_path(name: str, override: str | None = None) -> str:
    if override:
        return override
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"Required executable not found: {name}")
    return found


def run_checked(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True)


def probe_video(ffprobe: str, video: Path) -> dict:
    result = run_checked([
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=index,codec_type,width,height,avg_frame_rate:stream_tags=rotate",
        "-of", "json",
        str(video),
    ])
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0.0))
    video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    return {
        "duration": duration,
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "frame_rate": video_stream.get("avg_frame_rate", "0/0"),
        "rotation": int(video_stream.get("tags", {}).get("rotate", 0) or 0),
    }


def extract_samples(ffmpeg: str, video: Path, sample_dir: Path, fps: float, resume: bool) -> list[Path]:
    sample_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(sample_dir.glob("frame-*.png"))
    if resume and existing:
        return existing
    pattern = sample_dir / "frame-%06d.png"
    subprocess.run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video),
        "-vf", f"fps={fps}",
        str(pattern),
    ], check=True)
    return sorted(sample_dir.glob("frame-*.png"))


def frame_feature(path: Path) -> tuple[np.ndarray, np.ndarray, float]:
    with Image.open(path) as image:
        thumb = image.convert("RGB").resize((96, 96), Image.Resampling.BOX)
    rgb = np.asarray(thumb, dtype=np.float32)
    gray = rgb.mean(axis=2)
    hist, _ = np.histogram(gray, bins=32, range=(0, 256))
    hist = hist.astype(np.float32)
    hist /= max(float(hist.sum()), 1.0)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    sharpness = float(gx + gy)
    return rgb, hist, sharpness


def change_scores(features: list[tuple[np.ndarray, np.ndarray, float]]) -> np.ndarray:
    scores = np.zeros(len(features), dtype=np.float32)
    for i in range(1, len(features)):
        previous_rgb, previous_hist, _ = features[i - 1]
        current_rgb, current_hist, _ = features[i]
        mae = float(np.mean(np.abs(current_rgb - previous_rgb)) / 255.0)
        affinity = float(np.sqrt(previous_hist * current_hist).sum())
        hellinger = math.sqrt(max(0.0, 1.0 - affinity))
        scores[i] = 0.72 * mae + 0.28 * hellinger
    return scores


def adaptive_threshold(scores: np.ndarray, explicit: float) -> float:
    useful = scores[1:]
    if explicit > 0:
        return explicit
    if useful.size == 0:
        return 1.0
    median = float(np.median(useful))
    mad = float(np.median(np.abs(useful - median)))
    percentile = float(np.quantile(useful, 0.86))
    return max(0.055, percentile, median + 3.5 * max(mad, 0.003))


def collapse_peaks(scores: np.ndarray, threshold: float, fps: float, min_stable_seconds: float) -> list[int]:
    raw = [int(i) for i in np.where(scores >= threshold)[0]]
    if not raw:
        return []
    cluster_gap = max(1, round(fps * 0.8))
    clusters: list[list[int]] = [[raw[0]]]
    for index in raw[1:]:
        if index - clusters[-1][-1] <= cluster_gap:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    peaks = [max(cluster, key=lambda i: float(scores[i])) for cluster in clusters]
    min_frames = max(1, round(fps * min_stable_seconds))
    accepted: list[int] = []
    for peak in peaks:
        if peak < min_frames:
            continue
        if accepted and peak - accepted[-1] < min_frames:
            if scores[peak] > scores[accepted[-1]]:
                accepted[-1] = peak
            continue
        accepted.append(peak)
    return accepted


def make_segments(frame_count: int, boundaries: list[int], fps: float, min_stable_seconds: float) -> list[tuple[int, int]]:
    min_frames = max(1, round(fps * min_stable_seconds))
    cuts = [0] + [b for b in boundaries if 0 < b < frame_count] + [frame_count]
    if len(cuts) > 2 and cuts[-1] - cuts[-2] < min_frames:
        cuts.pop(-2)
    segments: list[tuple[int, int]] = []
    for start, end in zip(cuts, cuts[1:]):
        if end - start >= min_frames or not segments:
            segments.append((start, end))
        else:
            previous_start, _ = segments[-1]
            segments[-1] = (previous_start, end)
    return segments


def centered_bright_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    gray = rgb.mean(axis=2)
    height, width = gray.shape
    bright = gray > 42
    active_columns = bright.sum(axis=0) > max(20, round(height * 0.18))
    center = width // 2
    if not active_columns[center]:
        return (0, 0, width, height)
    left = center
    while left > 0 and active_columns[left - 1]:
        left -= 1
    right = center
    while right < width - 1 and active_columns[right + 1]:
        right += 1
    region = bright[:, left:right + 1]
    active_rows = region.sum(axis=1) > max(20, round(region.shape[1] * 0.14))
    rows = np.where(active_rows)[0]
    top = int(rows[0]) if rows.size else 0
    bottom = int(rows[-1] + 1) if rows.size else height
    area_ratio = ((right + 1 - left) * (bottom - top)) / max(width * height, 1)
    if area_ratio < 0.14 or area_ratio > 0.985:
        return (0, 0, width, height)
    return (max(0, left + 1), max(0, top), min(width, right), min(height, bottom))


def frame_quality(path: Path, source_sharpness: float) -> tuple[float, tuple[int, int, int, int]]:
    with Image.open(path) as image:
        box = centered_bright_bbox(image)
        area = (box[2] - box[0]) * (box[3] - box[1])
        completeness = area / max(image.width * image.height, 1)
    return source_sharpness * (0.75 + 0.25 * min(1.0, completeness / 0.55)), box


def choose_frame(segment: tuple[int, int], paths: list[Path], features: list[tuple[np.ndarray, np.ndarray, float]]) -> tuple[int, tuple[int, int, int, int]]:
    start, end = segment
    margin = max(0, round((end - start) * 0.12))
    candidates = list(range(start + margin, max(start + margin + 1, end - margin)))
    candidates = [i for i in candidates if i < len(paths)] or [min(start, len(paths) - 1)]
    scored = []
    for index in candidates:
        quality, box = frame_quality(paths[index], features[index][2])
        scored.append((quality, index, box))
    _, best_index, best_box = max(scored, key=lambda item: item[0])
    return best_index, best_box


def paper_color(image: Image.Image) -> tuple[int, int, int]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    strips = np.concatenate([
        rgb[: max(1, rgb.shape[0] // 50)].reshape(-1, 3),
        rgb[-max(1, rgb.shape[0] // 50):].reshape(-1, 3),
        rgb[:, : max(1, rgb.shape[1] // 50)].reshape(-1, 3),
        rgb[:, -max(1, rgb.shape[1] // 50):].reshape(-1, 3),
    ])
    med = np.median(strips, axis=0).astype(np.uint8)
    return tuple(int(x) for x in med)


def ink_mask(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    enlarged = source.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    pixels = np.asarray(enlarged, dtype=np.int16)
    gray = pixels.mean(axis=2)
    chroma = pixels.max(axis=2) - pixels.min(axis=2)
    mask = ((gray < 170) & (chroma < 62)).astype(np.uint8) * 255
    return Image.fromarray(mask, "L").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(0.7))


def restore_image(
    image: Image.Image,
    mode: str,
    target_height: int,
    realesrgan: str | None,
    temporary: Path,
) -> tuple[Image.Image, list[str]]:
    warnings: list[str] = []
    source = image.convert("RGB")
    if target_height > 0 and source.height != target_height:
        width = round(source.width * target_height / source.height)
        source = source.resize((width, target_height), Image.Resampling.LANCZOS)
    if mode == "archive":
        return source, warnings
    restored = ImageEnhance.Contrast(source).enhance(1.03)
    restored = restored.filter(ImageFilter.UnsharpMask(radius=1.0, percent=55, threshold=4))
    if mode != "enhanced":
        return restored, warnings
    if not realesrgan:
        warnings.append("enhanced_requested_without_realesrgan; used scan mode")
        return restored, warnings
    temporary.mkdir(parents=True, exist_ok=True)
    input_path = temporary / "input.png"
    output_path = temporary / "output.png"
    restored.save(input_path)
    subprocess.run([
        realesrgan, "-i", str(input_path), "-o", str(output_path),
        "-n", "realesr-animevideov3", "-s", "2", "-f", "png",
    ], check=True)
    with Image.open(output_path) as enhanced:
        enhanced = enhanced.convert("RGB")
        deterministic = restored.resize(enhanced.size, Image.Resampling.LANCZOS)
        protected = Image.composite(deterministic, enhanced, ink_mask(restored, enhanced.size))
    if target_height > 0 and protected.height != target_height:
        width = round(protected.width * target_height / protected.height)
        protected = protected.resize((width, target_height), Image.Resampling.LANCZOS)
    return protected, warnings


def normalize_canvases(items: list[tuple[Candidate, Image.Image]], mode: str) -> list[tuple[Candidate, Image.Image]]:
    if mode == "natural":
        return items
    if mode == "single-canvas-pad":
        groups = {"all": items}
    else:
        groups: dict[str, list[tuple[Candidate, Image.Image]]] = {}
        for item in items:
            page_class = item[0].page_class
            key = "cover" if "cover" in page_class else ("spread" if page_class == "two-page-spread" else "single")
            groups.setdefault(key, []).append(item)
    normalized: list[tuple[Candidate, Image.Image]] = []
    for group in groups.values():
        target_width = max(image.width for _, image in group)
        target_height = max(image.height for _, image in group)
        for candidate, image in group:
            canvas = Image.new("RGB", (target_width, target_height), paper_color(image))
            x = (target_width - image.width) // 2
            y = (target_height - image.height) // 2
            canvas.paste(image, (x, y))
            normalized.append((candidate, canvas))
    return sorted(normalized, key=lambda item: item[0].index)


def create_contact_sheet(items: list[tuple[Candidate, Image.Image]], path: Path) -> None:
    cell_w, cell_h, columns = 200, 270, 5
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), "#eeeeee")
    draw = ImageDraw.Draw(sheet)
    for offset, (candidate, image) in enumerate(items):
        thumb = image.copy()
        thumb.thumbnail((cell_w - 12, cell_h - 38), Image.Resampling.LANCZOS)
        x = (offset % columns) * cell_w + (cell_w - thumb.width) // 2
        y = (offset // columns) * cell_h + 28
        sheet.paste(thumb, (x, y))
        label = f"{candidate.index:03d} {candidate.page_class} {candidate.timestamp:.1f}s"
        draw.text(((offset % columns) * cell_w + 5, (offset // columns) * cell_h + 6), label, fill="black")
    sheet.save(path, optimize=True)


def create_review_html(candidates: list[Candidate], path: Path) -> None:
    cards = []
    for item in candidates:
        warnings = ", ".join(item.warnings or []) or "none"
        cards.append(
            f'<article><img src="../{html.escape(item.output_file)}"><h2>{item.index:03d} {html.escape(item.page_class)}</h2>'
            f'<p>{item.timestamp:.2f}s · confidence {item.confidence:.2f}</p><p>Warnings: {html.escape(warnings)}</p></article>'
        )
    document = """<!doctype html><meta charset="utf-8"><title>Picture-book page review</title>
<style>body{font-family:system-ui;margin:20px;background:#eee}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}article{background:white;padding:12px;border-radius:8px}img{width:100%;height:360px;object-fit:contain;background:#ddd}h2{font-size:16px}p{font-size:13px}</style>
<h1>Picture-book page review</h1><main>""" + "".join(cards) + "</main>"
    path.write_text(document, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract and normalize picture-book pages from a video.")
    parser.add_argument("--input", required=True, type=Path, help="Source video path")
    parser.add_argument("--output", required=True, type=Path, help="Output directory")
    parser.add_argument("--sample-fps", type=float, default=2.0, help="Coarse sample rate (default: 2)")
    parser.add_argument("--min-stable-seconds", type=float, default=1.0, help="Minimum stable interval")
    parser.add_argument("--change-threshold", type=float, default=0.0, help="Explicit change score; 0 uses adaptive")
    parser.add_argument("--canvas-mode", choices=["natural", "group-normalized", "single-canvas-pad"], default="group-normalized")
    parser.add_argument("--preservation-mode", choices=["archive", "scan", "enhanced"], default="scan")
    parser.add_argument("--target-height", type=int, default=1440, help="Output height; 0 preserves source")
    parser.add_argument("--ffmpeg", help="Path to ffmpeg")
    parser.add_argument("--ffprobe", help="Path to ffprobe")
    parser.add_argument("--realesrgan", help="Optional Real-ESRGAN executable for enhanced mode")
    parser.add_argument("--max-pages", type=int, default=0, help="Limit outputs for testing")
    parser.add_argument("--no-resume", action="store_true", help="Re-extract cached samples")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video = args.input.resolve()
    output = args.output.resolve()
    if not video.exists():
        raise SystemExit(f"Input video not found: {video}")
    ffmpeg = command_path("ffmpeg", args.ffmpeg)
    ffprobe = command_path("ffprobe", args.ffprobe)
    metadata = probe_video(ffprobe, video)
    work = output / "_work"
    pages_dir = output / "pages"
    review_dir = output / "review"
    excluded_dir = review_dir / "excluded-candidates"
    for directory in (work, pages_dir, review_dir, excluded_dir):
        directory.mkdir(parents=True, exist_ok=True)

    paths = extract_samples(ffmpeg, video, work / "samples", args.sample_fps, not args.no_resume)
    if not paths:
        raise SystemExit("No sample frames were extracted.")
    features = [frame_feature(path) for path in paths]
    scores = change_scores(features)
    threshold = adaptive_threshold(scores, args.change_threshold)
    boundaries = collapse_peaks(scores, threshold, args.sample_fps, args.min_stable_seconds)
    segments = make_segments(len(paths), boundaries, args.sample_fps, args.min_stable_seconds)
    if args.max_pages > 0:
        segments = segments[: args.max_pages]

    prepared: list[tuple[Candidate, Image.Image]] = []
    for number, segment in enumerate(segments, 1):
        frame_index, box = choose_frame(segment, paths, features)
        with Image.open(paths[frame_index]) as frame:
            source_size = [frame.width, frame.height]
            cropped = frame.convert("RGB").crop(box)
        ratio = cropped.width / max(cropped.height, 1)
        page_class = "front-cover" if number == 1 else ("two-page-spread" if ratio >= 1.24 else "single-page")
        area_ratio = (cropped.width * cropped.height) / max(source_size[0] * source_size[1], 1)
        confidence = min(0.96, 0.64 + 0.26 * min(1.0, area_ratio / 0.55))
        restored, warnings = restore_image(
            cropped,
            args.preservation_mode,
            args.target_height,
            args.realesrgan,
            work / "enhance" / f"{number:03d}",
        )
        candidate = Candidate(
            index=number,
            segment_start=segment[0] / args.sample_fps,
            segment_end=segment[1] / args.sample_fps,
            timestamp=frame_index / args.sample_fps,
            source_frame=str(paths[frame_index].relative_to(output)),
            page_class=page_class,
            crop_box=list(box),
            source_size=source_size,
            output_size=[restored.width, restored.height],
            confidence=round(confidence, 3),
            enhancement=args.preservation_mode,
            warnings=warnings,
        )
        prepared.append((candidate, restored))

    prepared = normalize_canvases(prepared, args.canvas_mode)
    candidates: list[Candidate] = []
    for candidate, image in prepared:
        suffix = "-front-cover" if candidate.page_class == "front-cover" else ""
        filename = f"{candidate.index:03d}{suffix}.png"
        destination = pages_dir / filename
        image.save(destination, optimize=True)
        candidate.output_size = [image.width, image.height]
        candidate.output_file = str(destination.relative_to(output)).replace("\\", "/")
        candidates.append(candidate)

    create_contact_sheet(prepared, review_dir / "contact-sheet.png")
    create_review_html(candidates, review_dir / "review.html")
    manifest = {
        "schema_version": 1,
        "source": str(video),
        "video": metadata,
        "settings": {
            "sample_fps": args.sample_fps,
            "min_stable_seconds": args.min_stable_seconds,
            "change_threshold": threshold,
            "canvas_mode": args.canvas_mode,
            "preservation_mode": args.preservation_mode,
            "target_height": args.target_height,
        },
        "page_count": len(candidates),
        "boundaries": [round(index / args.sample_fps, 3) for index in boundaries],
        "pages": [asdict(candidate) for candidate in candidates],
        "requires_visual_review": True,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "pages": len(candidates), "threshold": threshold}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
