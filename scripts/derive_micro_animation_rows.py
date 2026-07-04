#!/usr/bin/env python3
"""Derive subtle PetGenesis animation rows from a canonical base or composite."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from extract_strip_frames import parse_hex_color, remove_chroma_background
from petgen_contract import CELL_HEIGHT, CELL_WIDTH, EXPECTED_STATES, FRAME_COUNTS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_chroma_key(run_dir: Path) -> tuple[int, int, int]:
    request = load_optional_json(run_dir / "pet_request.json")
    chroma = request.get("chroma_key")
    if isinstance(chroma, dict) and isinstance(chroma.get("hex"), str):
        return parse_hex_color(chroma["hex"])
    return parse_hex_color("#00FF00")


def resolve_source(run_dir: Path, raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = run_dir / path
    path = path.resolve()
    if not path.is_file():
        raise SystemExit(f"source image not found: {path}")
    return path


def relative_to_run(run_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def parse_states(raw: str) -> list[str]:
    if raw.strip().lower() == "all":
        return list(EXPECTED_STATES)
    states = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = sorted(set(states) - set(EXPECTED_STATES))
    if unknown:
        raise SystemExit(f"unknown state(s): {', '.join(unknown)}")
    return states


def source_sprite(source: Path, chroma_key: tuple[int, int, int]) -> Image.Image:
    with Image.open(source) as opened:
        cleaned = remove_chroma_background(opened, chroma_key, 96.0)
    bbox = cleaned.getbbox()
    cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    if bbox is None:
        return cell
    sprite = cleaned.crop(bbox)
    max_width = CELL_WIDTH - 18
    max_height = CELL_HEIGHT - 18
    scale = min(max_width / sprite.width, max_height / sprite.height, 1.0)
    if scale != 1.0:
        sprite = sprite.resize(
            (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))),
            Image.Resampling.LANCZOS,
        )
    left = (CELL_WIDTH - sprite.width) // 2
    top = (CELL_HEIGHT - sprite.height) // 2
    cell.alpha_composite(sprite, (left, top))
    return cell


def motion(state: str, index: int, count: int, subject_count: int) -> dict[str, float | bool]:
    phase = (index / max(1, count - 1)) * math.tau
    if state == "idle":
        return {"dx": 0, "dy": round(math.sin(phase) * 2), "scale": 1.0, "angle": 0, "mirror": False}
    if state == "running-right":
        return {"dx": round(math.sin(phase) * 5), "dy": round(math.cos(phase) * 2), "scale": 1.0, "angle": 0, "mirror": False}
    if state == "running-left":
        return {"dx": -round(math.sin(phase) * 5), "dy": round(math.cos(phase) * 2), "scale": 1.0, "angle": 0, "mirror": subject_count == 1}
    if state == "waving":
        return {"dx": 0, "dy": 0, "scale": 1.0, "angle": math.sin(phase) * 5, "mirror": False}
    if state == "jumping":
        offsets = [8, 0, -12, -4, 6]
        return {"dx": 0, "dy": offsets[index % len(offsets)], "scale": 1.0, "angle": 0, "mirror": False}
    if state == "failed":
        return {"dx": 0, "dy": 7, "scale": 0.97, "angle": -4 + index % 2, "mirror": False}
    if state == "waiting":
        return {"dx": round(math.sin(phase) * 2), "dy": round(math.cos(phase) * 2), "scale": 1.0, "angle": 0, "mirror": False}
    if state == "running":
        return {"dx": round(math.sin(phase) * 3), "dy": round(math.cos(phase) * 3), "scale": 1.0, "angle": math.sin(phase) * 2, "mirror": False}
    if state == "review":
        return {"dx": 0, "dy": round(math.sin(phase) * 1), "scale": 1.0, "angle": math.sin(phase) * 3, "mirror": False}
    return {"dx": 0, "dy": 0, "scale": 1.0, "angle": 0, "mirror": False}


def transform_sprite(sprite_cell: Image.Image, movement: dict[str, float | bool]) -> Image.Image:
    bbox = sprite_cell.getbbox()
    if bbox is None:
        return Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    sprite = sprite_cell.crop(bbox)
    if movement.get("mirror"):
        sprite = ImageOps.mirror(sprite)
    scale = float(movement.get("scale", 1.0))
    if scale != 1.0:
        sprite = sprite.resize(
            (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))),
            Image.Resampling.LANCZOS,
        )
    angle = float(movement.get("angle", 0.0))
    if angle:
        sprite = sprite.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (0, 0, 0, 0))
    left = (CELL_WIDTH - sprite.width) // 2 + int(movement.get("dx", 0))
    top = (CELL_HEIGHT - sprite.height) // 2 + int(movement.get("dy", 0))
    cell.paste(sprite, (left, top), sprite)
    return cell


def derive_state_strip(
    sprite: Image.Image,
    state: str,
    chroma_key: tuple[int, int, int],
    subject_count: int,
) -> Image.Image:
    frames = FRAME_COUNTS[state]
    strip = Image.new("RGBA", (CELL_WIDTH * frames, CELL_HEIGHT), (*chroma_key, 255))
    for index in range(frames):
        cell = Image.new("RGBA", (CELL_WIDTH, CELL_HEIGHT), (*chroma_key, 255))
        animated = transform_sprite(sprite, motion(state, index, frames, subject_count))
        cell.paste(animated, (0, 0), animated)
        strip.alpha_composite(cell, (index * CELL_WIDTH, 0))
    return strip


def update_manifest(
    run_dir: Path,
    states: list[str],
    source: Path,
    *,
    overwrite: bool,
) -> bool:
    manifest_path = run_dir / "imagegen-jobs.json"
    if not manifest_path.is_file():
        return False
    manifest = load_optional_json(manifest_path)
    job_list = manifest.setdefault("jobs", [])
    if not isinstance(job_list, list):
        raise SystemExit("imagegen-jobs.json jobs must be a list")
    by_id = {
        str(job.get("id")): job
        for job in job_list
        if isinstance(job, dict)
    }
    timestamp = utc_now()
    for state in states:
        output = run_dir / "decoded" / f"{state}.png"
        if not output.is_file():
            continue
        existing = by_id.get(state)
        if existing and existing.get("status") == "approved" and not overwrite:
            continue
        job = existing if existing is not None else {"id": state}
        job.update(
            {
                "kind": "row-strip-derived",
                "status": "derived",
                "output_path": f"decoded/{state}.png",
                "depends_on": [],
                "generation_skill": "deterministic",
                "derivation_source": relative_to_run(run_dir, source),
                "derived_at": timestamp,
                "approval": {
                    "required": False,
                    "status": "approved",
                    "approved_at": timestamp,
                    "note": "derived by derive_micro_animation_rows.py",
                },
            }
        )
        if existing is None:
            job_list.append(job)
    row_derivation = manifest.setdefault("row_derivation", {})
    if isinstance(row_derivation, dict):
        all_rows_exist = all((run_dir / "decoded" / f"{state}.png").is_file() for state in EXPECTED_STATES)
        row_derivation["status"] = "derived" if all_rows_exist else "partial"
        row_derivation["source"] = relative_to_run(run_dir, source)
        row_derivation["derived_at"] = timestamp
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--subject-count", type=int, default=0)
    parser.add_argument("--states", default="all")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    source = resolve_source(run_dir, args.source)
    request = load_optional_json(run_dir / "pet_request.json")
    subject_count = args.subject_count or int(request.get("subject_count") or 1)
    if subject_count not in {1, 2}:
        raise SystemExit("subject count must be 1 or 2")
    states = parse_states(args.states)
    chroma_key = load_chroma_key(run_dir)
    sprite = source_sprite(source, chroma_key)
    decoded = run_dir / "decoded"
    decoded.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []
    for state in states:
        output = decoded / f"{state}.png"
        if output.is_file() and not args.overwrite:
            skipped.append(state)
            continue
        derive_state_strip(sprite, state, chroma_key, subject_count).save(output)
        written.append(state)
    manifest_updated = update_manifest(run_dir, states, source, overwrite=args.overwrite)
    print(
        json.dumps(
            {
                "ok": True,
                "run_dir": str(run_dir),
                "source": str(source),
                "subject_count": subject_count,
                "written_states": written,
                "skipped_states": skipped,
                "manifest_updated": manifest_updated,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
