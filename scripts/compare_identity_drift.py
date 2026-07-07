#!/usr/bin/env python3
"""Compare extracted animation frames against the approved canonical base."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from PIL import Image

CELL_WIDTH = 192
CELL_HEIGHT = 208
IMAGE_SUFFIXES = {".png", ".webp", ".jpg", ".jpeg"}
ROW_FRAME_COUNTS = {
    "idle": 6,
    "running-right": 8,
    "running-left": 8,
    "waving": 4,
    "jumping": 5,
    "failed": 8,
    "waiting": 6,
    "running": 6,
    "review": 6,
}

STATE_POLICIES = {
    "idle": (4.0, 6.0, 0.58, 82.0, 0.45),
    "waiting": (12.0, 12.0, 0.52, 88.0, 0.52),
    "running": (14.0, 14.0, 0.48, 92.0, 0.58),
    "review": (14.0, 14.0, 0.48, 92.0, 0.58),
    "waving": (16.0, 16.0, 0.44, 96.0, 0.62),
    "jumping": (16.0, 44.0, 0.36, 104.0, 0.68),
    "failed": (18.0, 18.0, 0.40, 104.0, 0.78),
    "running-right": (90.0, 22.0, 0.30, 112.0, 0.78),
    "running-left": (90.0, 22.0, 0.30, 112.0, 0.78),
}


def parse_states(raw: str) -> list[str]:
    if raw.strip().lower() == "all":
        return list(ROW_FRAME_COUNTS)
    states = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = sorted(set(states) - set(ROW_FRAME_COUNTS))
    if unknown:
        raise SystemExit(f"unknown state(s): {', '.join(unknown)}")
    if not states:
        raise SystemExit("--states must include at least one state")
    return states


def parse_hex_color(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise SystemExit(f"invalid chroma key color: {value}; expected #RRGGBB")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_chroma_key(run_dir: Path, override: str | None) -> tuple[int, int, int]:
    if override:
        return parse_hex_color(override)
    chroma = load_json(run_dir / "pet_request.json").get("chroma_key")
    if isinstance(chroma, dict) and isinstance(chroma.get("hex"), str):
        return parse_hex_color(chroma["hex"])
    return parse_hex_color("#00FF00")


def color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def remove_chroma_background(
    image: Image.Image,
    chroma_key: tuple[int, int, int],
    threshold: float,
) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    visited = bytearray(width * height)

    def pixel_index(x: int, y: int) -> int:
        return y * width + x

    def is_key(x: int, y: int) -> bool:
        red, green, blue, alpha = pixels[x, y]
        return alpha > 16 and color_distance((red, green, blue), chroma_key) <= threshold

    stack: list[tuple[int, int]] = []
    for x in range(width):
        for y in (0, height - 1):
            index = pixel_index(x, y)
            if not visited[index] and is_key(x, y):
                visited[index] = 1
                stack.append((x, y))
    for y in range(height):
        for x in (0, width - 1):
            index = pixel_index(x, y)
            if not visited[index] and is_key(x, y):
                visited[index] = 1
                stack.append((x, y))

    while stack:
        x, y = stack.pop()
        pixels[x, y] = (0, 0, 0, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            index = pixel_index(nx, ny)
            if visited[index] or not is_key(nx, ny):
                continue
            visited[index] = 1
            stack.append((nx, ny))
    return rgba


def alpha_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.convert("RGBA").getchannel("A").getbbox()


def fit_to_cell(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    bbox = alpha_bbox(rgba)
    target = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    if bbox is None:
        return target
    sprite = rgba.crop(bbox)
    scale = min((CELL_WIDTH - 10) / sprite.width, (CELL_HEIGHT - 10) / sprite.height, 1.0)
    if scale != 1.0:
        sprite = sprite.resize(
            (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))),
            Image.Resampling.LANCZOS,
        )
    target.alpha_composite(sprite, ((CELL_WIDTH - sprite.width) // 2, (CELL_HEIGHT - sprite.height) // 2))
    return target


def normalize_reference(path: Path, chroma_key: tuple[int, int, int], threshold: float) -> Image.Image:
    with Image.open(path) as opened:
        return fit_to_cell(remove_chroma_background(opened, chroma_key, threshold))


def frame_files(state_dir: Path) -> list[Path]:
    if not state_dir.is_dir():
        return []
    return sorted(path for path in state_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)


def load_frame(path: Path) -> Image.Image:
    with Image.open(path) as opened:
        return opened.convert("RGBA")


def alpha_area(image: Image.Image, threshold: int = 16) -> int:
    return sum(1 for value in image.getchannel("A").tobytes() if value > threshold)


def alpha_center(image: Image.Image, threshold: int = 16) -> tuple[float, float] | None:
    alpha = image.getchannel("A").tobytes()
    total = x_sum = y_sum = 0
    for index, value in enumerate(alpha):
        if value <= threshold:
            continue
        total += 1
        x_sum += index % CELL_WIDTH
        y_sum += index // CELL_WIDTH
    if total == 0:
        return None
    return (x_sum / total, y_sum / total)


def shifted(image: Image.Image, dx: int, dy: int) -> Image.Image:
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    result.alpha_composite(image, (dx, dy))
    return result


def alpha_iou(left: Image.Image, right: Image.Image, threshold: int = 16) -> float:
    left_alpha = left.getchannel("A").tobytes()
    right_alpha = right.getchannel("A").tobytes()
    intersection = union = 0
    for left_value, right_value in zip(left_alpha, right_alpha):
        left_on = left_value > threshold
        right_on = right_value > threshold
        intersection += int(left_on and right_on)
        union += int(left_on or right_on)
    return 1.0 if union == 0 else intersection / union


def mean_rgb_delta(left: Image.Image, right: Image.Image, threshold: int = 16) -> float:
    left_data = left.convert("RGBA").tobytes()
    right_data = right.convert("RGBA").tobytes()
    total = count = 0
    for index in range(0, len(left_data), 4):
        left_alpha = left_data[index + 3]
        right_alpha = right_data[index + 3]
        if left_alpha <= threshold and right_alpha <= threshold:
            continue
        if left_alpha <= threshold or right_alpha <= threshold:
            total += 255
            count += 1
            continue
        total += (
            abs(left_data[index] - right_data[index])
            + abs(left_data[index + 1] - right_data[index + 1])
            + abs(left_data[index + 2] - right_data[index + 2])
        ) / 3
        count += 1
    return 0.0 if count == 0 else total / count


def area_delta_ratio(reference_area: int, frame_area: int) -> float:
    if reference_area == 0:
        return 0.0 if frame_area == 0 else 1.0
    return abs(frame_area - reference_area) / reference_area


def best_alignment(reference: Image.Image, frame: Image.Image, radius: int) -> tuple[Image.Image, int, int, float]:
    ref_center = alpha_center(reference)
    frame_center = alpha_center(frame)
    start_x = start_y = 0
    if ref_center is not None and frame_center is not None:
        start_x = round(frame_center[0] - ref_center[0])
        start_y = round(frame_center[1] - ref_center[1])
    best = (shifted(reference, start_x, start_y), start_x, start_y, -1.0)
    for dx in range(start_x - radius, start_x + radius + 1):
        for dy in range(start_y - radius, start_y + radius + 1):
            candidate = shifted(reference, dx, dy)
            score = alpha_iou(candidate, frame)
            if score > best[3]:
                best = (candidate, dx, dy, score)
    return best


def tile_metrics(reference: Image.Image, frame: Image.Image, cols: int, rows: int, limit: int) -> list[dict[str, object]]:
    tiles: list[dict[str, object]] = []
    for row in range(rows):
        top = round(row * CELL_HEIGHT / rows)
        bottom = round((row + 1) * CELL_HEIGHT / rows)
        for col in range(cols):
            left = round(col * CELL_WIDTH / cols)
            right = round((col + 1) * CELL_WIDTH / cols)
            box = (left, top, right, bottom)
            ref_crop = reference.crop(box)
            frame_crop = frame.crop(box)
            ref_area = alpha_area(ref_crop)
            frame_area = alpha_area(frame_crop)
            if ref_area < 8 and frame_area < 8:
                continue
            tiles.append(
                {
                    "row": row,
                    "col": col,
                    "box": list(box),
                    "mask_iou": round(alpha_iou(ref_crop, frame_crop), 4),
                    "rgb_delta": round(mean_rgb_delta(ref_crop, frame_crop), 2),
                    "area_delta_ratio": round(area_delta_ratio(ref_area, frame_area), 4),
                }
            )
    return sorted(tiles, key=lambda item: (item["rgb_delta"], 1 - item["mask_iou"]), reverse=True)[:limit]


def write_overlay(path: Path, reference: Image.Image, frame: Image.Image) -> None:
    diff = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    ref_data = reference.convert("RGBA").tobytes()
    frame_data = frame.convert("RGBA").tobytes()
    pixels = diff.load()
    for index in range(0, len(ref_data), 4):
        pixel = index // 4
        x = pixel % CELL_WIDTH
        y = pixel // CELL_WIDTH
        ref_alpha = ref_data[index + 3]
        frame_alpha = frame_data[index + 3]
        if ref_alpha <= 16 and frame_alpha <= 16:
            continue
        if ref_alpha > 16 and frame_alpha <= 16:
            pixels[x, y] = (70, 120, 255, 210)
        elif ref_alpha <= 16 and frame_alpha > 16:
            pixels[x, y] = (255, 210, 0, 210)
        else:
            delta = int(
                (
                    abs(ref_data[index] - frame_data[index])
                    + abs(ref_data[index + 1] - frame_data[index + 1])
                    + abs(ref_data[index + 2] - frame_data[index + 2])
                )
                / 3
            )
            pixels[x, y] = (0, 180, 70, 90) if delta <= 18 else (255, 40, 30, min(255, 90 + delta))

    sheet = Image.new("RGBA", (CELL_WIDTH * 3, CELL_HEIGHT), (255, 255, 255, 255))
    sheet.alpha_composite(reference, (0, 0))
    sheet.alpha_composite(frame, (CELL_WIDTH, 0))
    sheet.alpha_composite(diff, (CELL_WIDTH * 2, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def inspect_frame(
    reference: Image.Image,
    frame: Image.Image,
    state: str,
    index: int,
    args: argparse.Namespace,
    overlay_dir: Path | None,
) -> dict[str, object]:
    max_span_x, max_span_y, min_iou, max_rgb_delta, max_area_delta = STATE_POLICIES[state]
    aligned, dx, dy, mask_iou = best_alignment(reference, frame, args.align_search_radius)
    ref_area = alpha_area(reference)
    frame_area = alpha_area(frame)
    rgb_delta = mean_rgb_delta(aligned, frame)
    area_delta = area_delta_ratio(ref_area, frame_area)
    errors: list[str] = []
    warnings: list[str] = []
    if mask_iou < min_iou:
        errors.append(f"{state} frame {index:02d} silhouette IoU {mask_iou:.3f} is below {min_iou:.3f}")
    if rgb_delta > max_rgb_delta:
        errors.append(f"{state} frame {index:02d} mean RGB drift {rgb_delta:.1f} exceeds {max_rgb_delta:.1f}")
    if area_delta > max_area_delta:
        errors.append(f"{state} frame {index:02d} alpha area drift {area_delta:.2f} exceeds {max_area_delta:.2f}")
    worst_tiles = tile_metrics(aligned, frame, args.grid_cols, args.grid_rows, args.max_tiles)
    for tile in worst_tiles[:3]:
        if tile["rgb_delta"] > max_rgb_delta * 1.15:
            warnings.append(f"{state} frame {index:02d} tile r{tile['row']}c{tile['col']} has high local RGB drift {tile['rgb_delta']:.1f}")

    overlay_path = None
    if overlay_dir is not None:
        overlay_path = overlay_dir / state / f"{index:02d}.png"
        write_overlay(overlay_path, aligned, frame)

    return {
        "index": index,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "alignment_shift": {"dx": dx, "dy": dy},
        "reference_pixels": ref_area,
        "frame_pixels": frame_area,
        "area_delta_ratio": round(area_delta, 4),
        "mask_iou": round(mask_iou, 4),
        "rgb_delta": round(rgb_delta, 2),
        "worst_tiles": worst_tiles,
        "overlay": str(overlay_path) if overlay_path else None,
        "policy": {
            "max_center_span_x": max_span_x,
            "max_center_span_y": max_span_y,
            "min_mask_iou": min_iou,
            "max_rgb_delta": max_rgb_delta,
            "max_area_delta_ratio": max_area_delta,
        },
    }


def inspect_state(
    frames_root: Path,
    reference: Image.Image,
    state: str,
    args: argparse.Namespace,
    overlay_dir: Path | None,
) -> dict[str, object]:
    files = frame_files(frames_root / state)
    expected = ROW_FRAME_COUNTS[state]
    errors: list[str] = []
    warnings: list[str] = []
    if len(files) != expected:
        errors.append(f"expected {expected} frame files for {state}, found {len(files)}")

    loaded = [load_frame(path) for path in files[:expected]]
    frames = [
        inspect_frame(reference, frame, state, index, args, overlay_dir)
        for index, frame in enumerate(loaded)
    ]
    for frame in frames:
        errors.extend(frame["errors"])
        warnings.extend(frame["warnings"])

    centers = [alpha_center(frame) for frame in loaded]
    centers = [center for center in centers if center is not None]
    row_motion = None
    if centers:
        max_span_x, max_span_y, *_rest = STATE_POLICIES[state]
        span_x = max(center[0] for center in centers) - min(center[0] for center in centers)
        span_y = max(center[1] for center in centers) - min(center[1] for center in centers)
        row_motion = {
            "center_span_x": round(span_x, 2),
            "center_span_y": round(span_y, 2),
            "max_center_span_x": max_span_x,
            "max_center_span_y": max_span_y,
        }
        if span_x > max_span_x:
            errors.append(f"{state} row center slides {span_x:.1f}px horizontally; max for state is {max_span_x:.1f}px")
        if span_y > max_span_y:
            errors.append(f"{state} row center slides {span_y:.1f}px vertically; max for state is {max_span_y:.1f}px")

    return {
        "state": state,
        "ok": not errors,
        "expected_frames": expected,
        "actual_frames": len(files),
        "row_motion": row_motion,
        "errors": errors,
        "warnings": warnings,
        "frames": frames,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--frames-root")
    parser.add_argument("--base", default="references/canonical-base.png")
    parser.add_argument("--states", default="all")
    parser.add_argument("--json-out")
    parser.add_argument("--overlay-dir")
    parser.add_argument("--chroma-key")
    parser.add_argument("--chroma-threshold", type=float, default=80.0)
    parser.add_argument("--align-search-radius", type=int, default=4)
    parser.add_argument("--grid-cols", type=int, default=4)
    parser.add_argument("--grid-rows", type=int, default=4)
    parser.add_argument("--max-tiles", type=int, default=6)
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    frames_root = Path(args.frames_root).expanduser().resolve() if args.frames_root else run_dir / "frames"
    base_path = (run_dir / args.base).resolve()
    chroma_key = load_chroma_key(run_dir, args.chroma_key)
    reference = normalize_reference(base_path, chroma_key, args.chroma_threshold)
    overlay_dir = Path(args.overlay_dir).expanduser().resolve() if args.overlay_dir else None
    rows = [
        inspect_state(frames_root, reference, state, args, overlay_dir)
        for state in parse_states(args.states)
    ]
    errors = [error for row in rows for error in row["errors"]]
    warnings = [warning for row in rows for warning in row["warnings"]]
    result = {
        "ok": not errors,
        "run_dir": str(run_dir),
        "frames_root": str(frames_root),
        "base": str(base_path),
        "errors": errors,
        "warnings": warnings,
        "rows": rows,
    }
    json_out = Path(args.json_out).expanduser().resolve() if args.json_out else run_dir / "qa" / "identity-drift.json"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    raise SystemExit(0 if result["ok"] or args.warn_only else 1)


if __name__ == "__main__":
    main()
