#!/usr/bin/env python3
"""Export a clean public PetGenesis catalog submission."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from package_pet import load_json, preflight_package
from verify_pet_package import verify_package


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(value: str, *, label: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise SystemExit(f"{label} normalizes to an empty slug")
    return slug


def target_root(out_dir: Path, catalog: str, include_pets_root: bool) -> Path:
    if catalog == "awesome-codex-pet" and include_pets_root:
        return out_dir / "pets"
    return out_dir


def write_export(
    *,
    run_dir: Path,
    out_dir: Path,
    author_slug: str,
    catalog: str,
    include_pets_root: bool,
    normalize_pet_id: bool,
) -> dict[str, Any]:
    request = load_json(run_dir / "pet_request.json")
    raw_pet_id = str(request.get("pet_id") or "").strip()
    if not raw_pet_id:
        raise SystemExit("pet_request.json is missing pet_id")
    pet_slug = slugify(raw_pet_id, label="pet_id")
    author = slugify(author_slug, label="author_slug")
    package_dir = target_root(out_dir, catalog, include_pets_root) / f"{pet_slug}--{author}"
    package_dir.mkdir(parents=True, exist_ok=True)

    exported_pet_id = pet_slug if normalize_pet_id else raw_pet_id
    display_name = str(request.get("display_name") or raw_pet_id).strip()
    description = str(request.get("description") or "").strip()
    spritesheet_source = run_dir / "final" / "spritesheet.webp"
    shutil.copy2(spritesheet_source, package_dir / "spritesheet.webp")
    pet_json = {
        "id": exported_pet_id,
        "displayName": display_name,
        "description": description,
        "spritesheetPath": "spritesheet.webp",
    }
    (package_dir / "pet.json").write_text(
        json.dumps(pet_json, indent=2) + "\n",
        encoding="utf-8",
    )
    submission = {
        "petId": exported_pet_id,
        "displayName": display_name,
        "description": description,
        "authorSlug": author,
        "source": "petgenesis",
        "catalog": catalog,
        "exportedAt": utc_now(),
    }
    (package_dir / "submission.json").write_text(
        json.dumps(submission, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "package_dir": str(package_dir),
        "pet_json": str(package_dir / "pet.json"),
        "spritesheet": str(package_dir / "spritesheet.webp"),
        "submission": str(package_dir / "submission.json"),
        "folder_name": package_dir.name,
        "pet_id": exported_pet_id,
        "author_slug": author,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--author-slug", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--catalog",
        choices=["generic", "awesome-codex-pet"],
        default="generic",
    )
    parser.add_argument("--include-pets-root", action="store_true")
    parser.add_argument("--normalize-pet-id", action="store_true")
    parser.add_argument("--allow-unvalidated", action="store_true")
    parser.add_argument("--allow-cleaned-run", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    preflight = preflight_package(
        run_dir,
        allow_unvalidated=args.allow_unvalidated,
        allow_cleaned_run=args.allow_cleaned_run,
    )
    if preflight["errors"] and not args.allow_unvalidated:
        raise SystemExit("catalog export preflight failed: " + "; ".join(preflight["errors"]))

    export = write_export(
        run_dir=run_dir,
        out_dir=out_dir,
        author_slug=args.author_slug,
        catalog=args.catalog,
        include_pets_root=args.include_pets_root,
        normalize_pet_id=args.normalize_pet_id,
    )
    verification = verify_package(Path(export["package_dir"]), strict_clean=True)
    result = {
        "ok": preflight["ok"] and verification["ok"],
        "exported_at": utc_now(),
        "run_dir": str(run_dir),
        "catalog": args.catalog,
        "allow_unvalidated": args.allow_unvalidated,
        "preflight": preflight,
        "export": export,
        "verification": verification,
        "warnings": preflight["warnings"] + verification["warnings"],
        "errors": preflight["errors"] + verification["errors"],
    }
    print(json.dumps(result, indent=2))
    if verification["ok"] and (preflight["ok"] or args.allow_unvalidated):
        raise SystemExit(0)
    raise SystemExit(1)


if __name__ == "__main__":
    main()
