#!/usr/bin/env python3
"""Package a finalized PetGenesis run as a Codex custom pet."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from petgen_contract import expected_preview_paths


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"required file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def rel(run_dir: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def json_ok(path: Path, label: str) -> tuple[bool, list[str]]:
    if not path.is_file():
        return False, [f"{label} not found: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"{label} is not valid JSON: {exc}"]
    if payload.get("ok") is not True:
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            return False, [f"{label} ok is not true: {', '.join(str(item) for item in errors)}"]
        return False, [f"{label} ok is not true"]
    return True, []


def manifest_jobs_all_done(run_dir: Path, allow_cleaned_run: bool) -> tuple[bool, list[str], list[str]]:
    manifest_path = run_dir / "imagegen-jobs.json"
    if not manifest_path.is_file():
        if allow_cleaned_run:
            return True, [], ["imagegen-jobs.json is absent; assuming an intentionally cleaned run"]
        return False, [f"imagegen-jobs.json not found: {manifest_path}"], []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"imagegen-jobs.json is not valid JSON: {exc}"], []
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        return False, ["imagegen-jobs.json jobs must be a list"], []
    unfinished = [
        str(job.get("id") or "<unknown>")
        for job in jobs
        if isinstance(job, dict) and str(job.get("status")) not in {"approved", "derived"}
    ]
    if unfinished:
        return False, ["visual jobs are not all approved or derived: " + ", ".join(unfinished)], []
    return True, [], []


def preflight_package(
    run_dir: Path,
    *,
    allow_unvalidated: bool = False,
    allow_cleaned_run: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    checked: dict[str, Any] = {
        "pet_request": rel(run_dir, run_dir / "pet_request.json"),
        "spritesheet": rel(run_dir, run_dir / "final" / "spritesheet.webp"),
        "validation": rel(run_dir, run_dir / "final" / "validation.json"),
        "review": rel(run_dir, run_dir / "qa" / "review.json"),
        "contact_sheet": rel(run_dir, run_dir / "qa" / "contact-sheet.png"),
        "previews": [rel(run_dir, path) for path in expected_preview_paths(run_dir)],
        "manifest": rel(run_dir, run_dir / "imagegen-jobs.json"),
    }

    if not (run_dir / "pet_request.json").is_file():
        errors.append(f"pet_request.json not found: {run_dir / 'pet_request.json'}")
    if not (run_dir / "final" / "spritesheet.webp").is_file():
        errors.append(f"final spritesheet not found: {run_dir / 'final' / 'spritesheet.webp'}")

    validation_ok, validation_errors = json_ok(run_dir / "final" / "validation.json", "validation")
    review_ok, review_errors = json_ok(run_dir / "qa" / "review.json", "review")
    if not validation_ok:
        errors.extend(validation_errors)
    if not review_ok:
        errors.extend(review_errors)

    contact_sheet = run_dir / "qa" / "contact-sheet.png"
    if not contact_sheet.is_file():
        errors.append(f"contact sheet not found: {contact_sheet}")

    missing_previews = [path for path in expected_preview_paths(run_dir) if not path.is_file()]
    if missing_previews:
        errors.append(
            "missing preview GIFs: "
            + ", ".join(rel(run_dir, path) for path in missing_previews)
        )

    manifest_ok, manifest_errors, manifest_warnings = manifest_jobs_all_done(
        run_dir,
        allow_cleaned_run,
    )
    if not manifest_ok:
        errors.extend(manifest_errors)
    warnings.extend(manifest_warnings)

    if allow_unvalidated and errors:
        warnings.append("UNVALIDATED PACKAGE: packaging continued despite preflight errors")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked": checked,
    }


def codex_pet_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "pets"
    return Path.home().resolve() / ".codex" / "pets"


def parse_destination(raw: str, project_dir: str) -> list[tuple[str, Path]]:
    raw = raw.strip()
    if raw == "codex":
        return [("codex", codex_pet_root())]
    if raw == "project":
        if not project_dir.strip():
            raise SystemExit("--project-dir is required for --destination project")
        return [("project", Path(project_dir).expanduser().resolve())]
    if raw == "both":
        if not project_dir.strip():
            raise SystemExit("--project-dir is required for --destination both")
        return [
            ("codex", codex_pet_root()),
            ("project", Path(project_dir).expanduser().resolve()),
        ]
    if raw.startswith("project:"):
        return [("project", Path(raw.split(":", 1)[1]).expanduser().resolve())]
    if raw.startswith("both:"):
        project_path = Path(raw.split(":", 1)[1]).expanduser().resolve()
        return [("codex", codex_pet_root()), ("project", project_path)]
    raise SystemExit(
        "destination must be codex, project, both, project:<path>, or both:<path>"
    )


def package_dir(root: Path, pet_id: str) -> Path:
    return root / pet_id


def write_package(
    *,
    run_dir: Path,
    destination_root: Path,
    destination_kind: str,
    pet_id: str,
    display_name: str,
    description: str,
    spritesheet: Path,
) -> dict[str, Any]:
    target_dir = package_dir(destination_root, pet_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_spritesheet = target_dir / "spritesheet.webp"
    target_manifest = target_dir / "pet.json"
    shutil.copy2(spritesheet, target_spritesheet)
    pet_manifest = {
        "id": pet_id,
        "displayName": display_name,
        "description": description,
        "spritesheetPath": "spritesheet.webp",
    }
    target_manifest.write_text(
        json.dumps(pet_manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "kind": destination_kind,
        "package_dir": str(target_dir),
        "pet_json": str(target_manifest),
        "spritesheet": str(target_spritesheet),
        "source_run_dir": str(run_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--destination",
        default="codex",
        help="codex, project, both, project:<path>, or both:<path>.",
    )
    parser.add_argument(
        "--project-dir",
        default="",
        help="Project package root when --destination is project or both.",
    )
    parser.add_argument(
        "--allow-unvalidated",
        action="store_true",
        help="Package despite missing or failed QA artifacts; records warnings.",
    )
    parser.add_argument(
        "--allow-cleaned-run",
        action="store_true",
        help="Allow packaging when imagegen-jobs.json was intentionally removed after QA.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    request = load_json(run_dir / "pet_request.json")
    preflight = preflight_package(
        run_dir,
        allow_unvalidated=args.allow_unvalidated,
        allow_cleaned_run=args.allow_cleaned_run,
    )
    if preflight["errors"] and not args.allow_unvalidated:
        raise SystemExit("package preflight failed: " + "; ".join(preflight["errors"]))
    spritesheet = run_dir / "final" / "spritesheet.webp"
    if not spritesheet.is_file():
        raise SystemExit(f"final spritesheet not found: {spritesheet}")

    pet_id = str(request.get("pet_id") or "").strip()
    display_name = str(request.get("display_name") or pet_id).strip()
    description = str(request.get("description") or "").strip()
    if not pet_id:
        raise SystemExit("pet_request.json is missing pet_id")

    packages = [
        write_package(
            run_dir=run_dir,
            destination_root=root,
            destination_kind=kind,
            pet_id=pet_id,
            display_name=display_name,
            description=description,
            spritesheet=spritesheet,
        )
        for kind, root in parse_destination(args.destination, args.project_dir)
    ]

    qa_dir = run_dir / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "ok": preflight["ok"],
        "packaged_at": utc_now(),
        "run_dir": str(run_dir),
        "spritesheet": str(spritesheet),
        "validation": str(run_dir / "final" / "validation.json"),
        "contact_sheet": str(qa_dir / "contact-sheet.png"),
        "review": str(qa_dir / "review.json"),
        "preflight": preflight,
        "warnings": preflight["warnings"],
        "packages": packages,
    }
    (qa_dir / "run-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
