#!/usr/bin/env python3
"""Assemble the repository's Hermes PetGenesis adapter as a local skill."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
from pathlib import Path
from uuid import uuid4


IGNORED_NAMES = {"__pycache__", ".pytest_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
INSTALL_MARKER = ".petgenesis-install.json"
INSTALL_MARKER_DATA = {
    "installer": "PetGenesis/hermes/install.py",
    "schema_version": 1,
    "skill": "petgenesis",
}


def default_hermes_home() -> Path:
    configured = os.environ.get("HERMES_HOME", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            return (Path(local_app_data) / "hermes").resolve()
    return (Path.home() / ".hermes").resolve()


def _ignore_runtime_files(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in IGNORED_NAMES or Path(name).suffix.lower() in IGNORED_SUFFIXES
    }


def _is_windows_reparse_point(path: Path) -> bool:
    if os.name != "nt":
        return False
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _is_link_like(path: Path) -> bool:
    return path.is_symlink() or _is_windows_reparse_point(path)


def _path_exists(path: Path) -> bool:
    return path.exists() or _is_link_like(path)


def _remove_path(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif _is_windows_reparse_point(path):
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _paths_overlap(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


def _is_managed_install(destination: Path) -> bool:
    if _is_link_like(destination):
        return False
    marker = destination / INSTALL_MARKER
    if marker.is_symlink() or not marker.is_file():
        return False
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload == INSTALL_MARKER_DATA


def _check_destination(destination: Path, *, force: bool) -> None:
    if _is_link_like(destination):
        raise ValueError(
            f"destination must not be a symbolic link or junction: {destination}"
        )
    if not destination.exists():
        return
    if not force:
        raise FileExistsError(f"destination already exists: {destination}")
    if not _is_managed_install(destination):
        raise PermissionError(
            "destination is not managed by this installer; refusing to replace it: "
            f"{destination}"
        )


def install_skill(
    repo_root: Path,
    destination: Path,
    *,
    force: bool = False,
) -> dict[str, object]:
    """Assemble the Hermes adapter and shared PetGenesis core at destination."""
    repo_root = Path(repo_root).expanduser().resolve()
    requested_destination = Path(destination).expanduser()
    if _is_link_like(requested_destination):
        raise ValueError(
            "destination must not be a symbolic link or junction: "
            f"{requested_destination}"
        )
    destination = requested_destination.resolve()
    hermes_dir = repo_root / "hermes"

    required = (
        hermes_dir / "SKILL.md",
        hermes_dir / "README.md",
        repo_root / "scripts",
        repo_root / "references",
        repo_root / "LICENSE.txt",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing PetGenesis source files: " + ", ".join(missing))
    if _paths_overlap(repo_root, destination):
        raise ValueError(
            "source and destination paths overlap; choose a Hermes skill directory "
            f"outside the PetGenesis repository: {destination}"
        )
    _check_destination(destination, force=force)

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / f".{destination.name}.tmp-{uuid4().hex}"
    try:
        staging.mkdir()
        shutil.copy2(hermes_dir / "SKILL.md", staging / "SKILL.md")
        shutil.copy2(hermes_dir / "README.md", staging / "README.md")
        shutil.copy2(repo_root / "LICENSE.txt", staging / "LICENSE.txt")
        shutil.copytree(
            repo_root / "scripts",
            staging / "scripts",
            ignore=_ignore_runtime_files,
        )
        shutil.copytree(
            repo_root / "references",
            staging / "references",
            ignore=_ignore_runtime_files,
        )
        (staging / INSTALL_MARKER).write_text(
            json.dumps(INSTALL_MARKER_DATA, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _check_destination(destination, force=force)
        backup = destination.parent / f".{destination.name}.bak-{uuid4().hex}"
        if _path_exists(destination):
            destination.replace(backup)
            try:
                if not force:
                    raise FileExistsError(
                        "destination changed after validation; refusing to replace it: "
                        f"{destination}"
                    )
                if not _is_managed_install(backup):
                    raise PermissionError(
                        "destination changed after validation; the moved object is not "
                        f"managed by this installer: {destination}"
                    )
            except Exception:
                if _path_exists(backup) and not _path_exists(destination):
                    backup.replace(destination)
                raise
        try:
            staging.replace(destination)
        except Exception:
            if _path_exists(backup) and not _path_exists(destination):
                backup.replace(destination)
            raise
        else:
            if _path_exists(backup):
                if not _is_managed_install(backup):
                    raise PermissionError(
                        "backup changed after validation; refusing to remove it: "
                        f"{backup}"
                    )
                _remove_path(backup)
    finally:
        if _path_exists(staging):
            _remove_path(staging)

    file_count = sum(1 for path in destination.rglob("*") if path.is_file())
    return {
        "ok": True,
        "destination": str(destination),
        "file_count": file_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="PetGenesis repository root. Defaults to the parent of hermes/.",
    )
    parser.add_argument(
        "--destination",
        default=str(default_hermes_home() / "skills" / "creative" / "petgenesis"),
        help="Hermes skill destination folder. Defaults under HERMES_HOME.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing installation created by this installer.",
    )
    args = parser.parse_args()

    result = install_skill(
        Path(args.repo_root),
        Path(args.destination),
        force=args.force,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
