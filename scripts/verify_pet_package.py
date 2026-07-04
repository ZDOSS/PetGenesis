#!/usr/bin/env python3
"""Verify a packaged Codex pet folder from the install/runtime perspective."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

from petgen_contract import (
    ATLAS_HEIGHT,
    ATLAS_WIDTH,
    CELL_HEIGHT,
    CELL_WIDTH,
    EXPECTED_STATES,
    FRAME_COUNTS,
)


def load_pet_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"pet.json not found: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"pet.json is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append("pet.json must contain a JSON object")
        return {}
    return payload


def resolves_inside(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def visible_pixels(image: Image.Image) -> bool:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    return bool(alpha.getbbox())


def row_cells_nonempty(image: Image.Image, errors: list[str]) -> bool:
    ok = True
    rgba = image.convert("RGBA")
    for row_index, state in enumerate(EXPECTED_STATES):
        for col in range(FRAME_COUNTS[state]):
            cell = rgba.crop(
                (
                    col * CELL_WIDTH,
                    row_index * CELL_HEIGHT,
                    (col + 1) * CELL_WIDTH,
                    (row_index + 1) * CELL_HEIGHT,
                )
            )
            if not visible_pixels(cell):
                errors.append(f"{state} frame {col:02d} is blank")
                ok = False
    return ok


def path_style_warnings(package_dir: Path, spritesheet_path_raw: str) -> list[str]:
    warnings: list[str] = []
    package_text = str(package_dir)
    if "/mnt/" in package_text and ":" in package_text:
        warnings.append("package path appears to mix WSL and Windows path styles")
    if "\\" in spritesheet_path_raw and "/" in spritesheet_path_raw:
        warnings.append("spritesheetPath mixes slash styles")
    return warnings


def verify_package(package_dir: Path, *, strict_clean: bool = False) -> dict[str, Any]:
    package_dir = package_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {
        "pet_json": False,
        "spritesheet_path_relative": False,
        "spritesheet_resolves_inside": False,
        "spritesheet_exists": False,
        "spritesheet_readable": False,
        "dimensions": False,
        "cell_size": False,
        "alpha_capable": False,
        "rows_nonempty": False,
        "strict_clean": not strict_clean,
    }

    pet_json_path = package_dir / "pet.json"
    pet_json = load_pet_json(pet_json_path, errors)
    checks["pet_json"] = bool(pet_json)

    pet_id = str(pet_json.get("id") or "").strip()
    if pet_json and not pet_id:
        errors.append("pet.json is missing id")

    spritesheet_raw = str(pet_json.get("spritesheetPath") or "").strip()
    if pet_json and not spritesheet_raw:
        errors.append("pet.json is missing spritesheetPath")

    spritesheet_path = package_dir / "spritesheet.webp"
    if spritesheet_raw:
        raw_path = Path(spritesheet_raw)
        if raw_path.is_absolute():
            errors.append("spritesheetPath must be relative, not absolute")
        else:
            checks["spritesheet_path_relative"] = True
        candidate = (package_dir / raw_path).resolve()
        if resolves_inside(package_dir, candidate):
            checks["spritesheet_resolves_inside"] = True
            spritesheet_path = candidate
        else:
            errors.append("spritesheetPath resolves outside the package folder")
        warnings.extend(path_style_warnings(package_dir, spritesheet_raw))

    if spritesheet_path.is_file():
        checks["spritesheet_exists"] = True
    else:
        errors.append(f"spritesheet file not found: {spritesheet_path}")

    if checks["spritesheet_exists"]:
        try:
            with Image.open(spritesheet_path) as opened:
                opened.load()
                checks["spritesheet_readable"] = True
                checks["dimensions"] = opened.size == (ATLAS_WIDTH, ATLAS_HEIGHT)
                if not checks["dimensions"]:
                    errors.append(
                        f"spritesheet dimensions are {opened.size[0]}x{opened.size[1]}, expected {ATLAS_WIDTH}x{ATLAS_HEIGHT}"
                    )
                checks["cell_size"] = (
                    opened.size[0] // 8 == CELL_WIDTH and opened.size[1] // 9 == CELL_HEIGHT
                )
                checks["alpha_capable"] = opened.mode in {"RGBA", "LA"} or (
                    opened.mode == "P" and "transparency" in opened.info
                )
                if not checks["alpha_capable"]:
                    errors.append(f"spritesheet mode does not preserve alpha: {opened.mode}")
                if checks["dimensions"]:
                    checks["rows_nonempty"] = row_cells_nonempty(opened, errors)
        except Exception as exc:  # Pillow raises several image-specific exceptions.
            errors.append(f"spritesheet is not readable by Pillow: {exc}")

    if strict_clean:
        allowed = {"pet.json", "spritesheet.webp", "submission.json"}
        unexpected = sorted(
            path.name for path in package_dir.iterdir() if path.is_file() and path.name not in allowed
        )
        checks["strict_clean"] = not unexpected
        if unexpected:
            errors.append("unexpected files in strict-clean package: " + ", ".join(unexpected))

    return {
        "ok": not errors,
        "package_dir": str(package_dir),
        "pet_json": str(pet_json_path),
        "spritesheet": str(spritesheet_path),
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_dir")
    parser.add_argument("--strict-clean", action="store_true")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    result = verify_package(Path(args.package_dir), strict_clean=args.strict_clean)
    if args.json_out.strip():
        out_path = Path(args.json_out).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
