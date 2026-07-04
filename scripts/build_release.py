#!/usr/bin/env python3
"""Build a clean PetGenesis skill archive."""

from __future__ import annotations

import argparse
import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_EXCLUDES = (
    ".git/**",
    ".pytest_cache/**",
    ".venv/**",
    "__pycache__/**",
    "*/__pycache__/**",
    "*.pyc",
    "*.pyo",
    "dist/**",
    "output/**",
    "petgenesis-pets/**",
    "generated_images/**",
    "docs/superpowers/**",
)


def as_posix(path: Path) -> str:
    return path.as_posix()


def matches_pattern(relative_path: str, pattern: str) -> bool:
    if fnmatch.fnmatch(relative_path, pattern):
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return relative_path == prefix.rstrip("/") or relative_path.startswith(prefix)
    return False


def should_exclude(relative_path: Path, patterns: tuple[str, ...] = DEFAULT_EXCLUDES) -> bool:
    raw = as_posix(relative_path)
    return any(matches_pattern(raw, pattern) for pattern in patterns)


def iter_release_files(skill_dir: Path) -> list[Path]:
    skill_dir = skill_dir.resolve()
    files: list[Path] = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir)
        if should_exclude(relative):
            continue
        files.append(relative)
    return sorted(files, key=as_posix)


def build_archive(skill_dir: Path, output: Path, root_name: str) -> dict[str, object]:
    skill_dir = skill_dir.resolve()
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = iter_release_files(skill_dir)
    if not (skill_dir / "SKILL.md").is_file():
        raise SystemExit(f"SKILL.md not found in {skill_dir}")
    if not files:
        raise SystemExit(f"no release files found in {skill_dir}")

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for relative in files:
            archive.write(skill_dir / relative, f"{root_name}/{as_posix(relative)}")

    return {
        "ok": True,
        "archive": str(output),
        "root_name": root_name,
        "file_count": len(files),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "excluded": list(DEFAULT_EXCLUDES),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-dir",
        default=str(Path(__file__).resolve().parents[1]),
        help="Skill folder to package. Defaults to the parent of this script directory.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output .zip path. Defaults to ./petgenesis-releases/petgenesis.zip.",
    )
    parser.add_argument(
        "--root-name",
        default="petgenesis",
        help="Top-level folder name inside the archive.",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_dir).expanduser().resolve()
    output = (
        Path(args.output).expanduser().resolve()
        if args.output.strip()
        else Path.cwd() / "petgenesis-releases" / "petgenesis.zip"
    )
    result = build_archive(skill_dir, output, args.root_name.strip() or "petgenesis")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
