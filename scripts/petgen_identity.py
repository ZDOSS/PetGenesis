#!/usr/bin/env python3
"""Manage a PetGenesis run's identity ledger without hand-editing JSON."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEDGER_PATH = Path("references") / "identity-ledger.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"required file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def save_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def canonical_paths_from_manifest(run_dir: Path) -> dict[str, str]:
    manifest = load_optional_json(run_dir / "imagegen-jobs.json")
    result: dict[str, str] = {}
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list):
        return result
    for job in jobs:
        if not isinstance(job, dict):
            continue
        canonical = job.get("canonical_base_path")
        if not isinstance(canonical, str) or not canonical:
            continue
        job_id = str(job.get("id") or "")
        if job_id == "base":
            result["a"] = canonical
            result["solo"] = canonical
        elif job_id == "base-a":
            result["a"] = canonical
        elif job_id == "base-b":
            result["b"] = canonical
    return result


def initial_subjects(run_dir: Path, request: dict[str, Any]) -> list[dict[str, Any]]:
    subject_count = int(request.get("subject_count") or 1)
    manifest_paths = canonical_paths_from_manifest(run_dir)
    request_subjects = request.get("subjects")
    subjects: list[dict[str, Any]] = []
    if isinstance(request_subjects, list) and request_subjects:
        for index, item in enumerate(request_subjects[:subject_count]):
            if not isinstance(item, dict):
                continue
            subject_id = str(item.get("id") or ("a" if index == 0 else "b")).lower()
            subjects.append(
                {
                    "id": subject_id,
                    "name": str(item.get("name") or f"Subject {subject_id.upper()}"),
                    "canonical_base": str(
                        item.get("canonical_base")
                        or item.get("canonical_base_path")
                        or manifest_paths.get(subject_id)
                        or ("references/canonical-base.png" if subject_count == 1 else f"references/canonical-base-{subject_id}.png")
                    ),
                    "identity_notes": str(item.get("notes") or item.get("identity_notes") or ""),
                    "critical_details": [],
                    "side_dependent_details": [],
                    "simplification_rules": [
                        "Keep details pet-scale readable; simplify or omit fragile tiny details instead of duplicating or misplacing them."
                    ],
                }
            )
    if subjects:
        return subjects
    ids = ["a"] if subject_count == 1 else ["a", "b"]
    display_name = str(request.get("display_name") or request.get("pet_id") or "Subject")
    return [
        {
            "id": subject_id,
            "name": display_name if subject_count == 1 else f"Subject {subject_id.upper()}",
            "canonical_base": manifest_paths.get(subject_id)
            or ("references/canonical-base.png" if subject_count == 1 else f"references/canonical-base-{subject_id}.png"),
            "identity_notes": str(request.get("description") or ""),
            "critical_details": [],
            "side_dependent_details": [],
            "simplification_rules": [
                "Keep details pet-scale readable; simplify or omit fragile tiny details instead of duplicating or misplacing them."
            ],
        }
        for subject_id in ids
    ]


def default_ledger(run_dir: Path) -> dict[str, Any]:
    request = load_json(run_dir / "pet_request.json")
    subject_count = int(request.get("subject_count") or 1)
    return {
        "schema_version": 1,
        "subject_count": subject_count,
        "style_contract": {},
        "subjects": initial_subjects(run_dir, request),
        "forbidden": [],
        "updated_at": utc_now(),
    }


def load_or_init_ledger(run_dir: Path) -> tuple[Path, dict[str, Any], bool]:
    request_path = run_dir / "pet_request.json"
    if not request_path.is_file():
        raise SystemExit(f"pet_request.json not found: {request_path}")
    path = run_dir / LEDGER_PATH
    if path.is_file():
        ledger = load_json(path)
        if not isinstance(ledger.get("subjects"), list):
            ledger["subjects"] = initial_subjects(run_dir, load_json(request_path))
            ledger["updated_at"] = utc_now()
            save_ledger(path, ledger)
            return path, ledger, True
        return path, ledger, False
    ledger = default_ledger(run_dir)
    save_ledger(path, ledger)
    return path, ledger, True


def subjects(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    value = ledger.setdefault("subjects", [])
    if not isinstance(value, list):
        raise SystemExit("identity ledger subjects must be a list")
    return [item for item in value if isinstance(item, dict)]


def resolve_subject(ledger: dict[str, Any], requested: str) -> dict[str, Any]:
    requested = requested.lower().strip()
    subject_list = subjects(ledger)
    subject_count = int(ledger.get("subject_count") or len(subject_list) or 1)
    if subject_count == 1:
        if requested not in {"a", "solo"}:
            raise SystemExit("solo runs accept subject a or solo only")
        if not subject_list:
            raise SystemExit("identity ledger has no subjects")
        return subject_list[0]
    if requested not in {"a", "b"}:
        raise SystemExit("duo runs accept subject a or b only")
    for subject in subject_list:
        if str(subject.get("id") or "").lower() == requested:
            return subject
    raise SystemExit(f"subject {requested} not found in identity ledger")


def list_field(subject: dict[str, Any], key: str) -> list[str]:
    value = subject.setdefault(key, [])
    if not isinstance(value, list):
        raise SystemExit(f"subject field {key} must be a list")
    return [str(item) for item in value]


def add_unique(values: list[str], item: str) -> bool:
    item = item.strip()
    if not item:
        raise SystemExit("detail value cannot be empty")
    if item in values:
        return False
    values.append(item)
    return True


def remove_value(values: list[str], item: str) -> bool:
    item = item.strip()
    if item in values:
        values.remove(item)
        return True
    return False


def finish(
    path: Path,
    ledger: dict[str, Any],
    *,
    changed: bool,
    subject: str | None,
    summary: str,
    include_ledger: bool = False,
) -> dict[str, Any]:
    if changed:
        ledger["updated_at"] = utc_now()
        save_ledger(path, ledger)
    result: dict[str, Any] = {
        "ok": True,
        "ledger_path": str(path),
        "changed": changed,
        "summary": summary,
    }
    if subject is not None:
        result["subject"] = subject
    if include_ledger:
        result["ledger"] = ledger
    return result


def command_show(args: argparse.Namespace) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    return finish(path, ledger, changed=created, subject=None, summary="show identity ledger", include_ledger=True)


def command_add_detail(args: argparse.Namespace) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    subject = resolve_subject(ledger, args.subject)
    details = list_field(subject, "critical_details")
    changed = add_unique(details, args.detail)
    subject["critical_details"] = details
    return finish(path, ledger, changed=created or changed, subject=str(subject.get("id")), summary="added critical detail")


def command_remove_detail(args: argparse.Namespace) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    subject = resolve_subject(ledger, args.subject)
    details = list_field(subject, "critical_details")
    changed = remove_value(details, args.detail)
    subject["critical_details"] = details
    return finish(path, ledger, changed=created or changed, subject=str(subject.get("id")), summary="removed critical detail")


def command_set_field(args: argparse.Namespace, key: str, summary: str) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    subject = resolve_subject(ledger, args.subject)
    value = args.value.strip()
    if not value:
        raise SystemExit(f"{key} cannot be empty")
    changed = subject.get(key) != value
    subject[key] = value
    return finish(path, ledger, changed=created or changed, subject=str(subject.get("id")), summary=summary)


def command_add_side_detail(args: argparse.Namespace) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    subject = resolve_subject(ledger, args.subject)
    details = list_field(subject, "side_dependent_details")
    changed = add_unique(details, args.detail)
    subject["side_dependent_details"] = details
    return finish(path, ledger, changed=created or changed, subject=str(subject.get("id")), summary="added side-dependent detail")


def command_style_contract(args: argparse.Namespace) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    style = ledger.setdefault("style_contract", {})
    if not isinstance(style, dict):
        raise SystemExit("style_contract must be an object")
    changed = style.get("contract") != args.value.strip()
    style["contract"] = args.value.strip()
    return finish(path, ledger, changed=created or changed, subject=None, summary="set style contract")


def command_forbidden(args: argparse.Namespace, *, remove: bool) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    values = ledger.setdefault("forbidden", [])
    if not isinstance(values, list):
        raise SystemExit("forbidden must be a list")
    forbidden = [str(item) for item in values]
    changed = remove_value(forbidden, args.value) if remove else add_unique(forbidden, args.value)
    ledger["forbidden"] = forbidden
    return finish(path, ledger, changed=created or changed, subject=None, summary=("removed forbidden item" if remove else "added forbidden item"))


def command_set_canonical_base(args: argparse.Namespace) -> dict[str, Any]:
    return command_set_field(args, "canonical_base", "set canonical base")


def command_validate(args: argparse.Namespace) -> dict[str, Any]:
    path, ledger, created = load_or_init_ledger(Path(args.run_dir).expanduser().resolve())
    errors: list[str] = []
    subject_list = subjects(ledger)
    subject_count = int(ledger.get("subject_count") or len(subject_list) or 1)
    expected = {"a"} if subject_count == 1 else {"a", "b"}
    actual = {str(subject.get("id") or "").lower() for subject in subject_list}
    if not expected.issubset(actual):
        errors.append("missing expected subjects: " + ", ".join(sorted(expected - actual)))
    for subject in subject_list:
        if not subject.get("canonical_base"):
            errors.append(f"subject {subject.get('id')} is missing canonical_base")
    result = finish(path, ledger, changed=created, subject=None, summary="validated identity ledger")
    result["ok"] = not errors
    result["errors"] = errors
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show")
    show.add_argument("--run-dir", required=True)
    show.set_defaults(func=command_show)

    add = sub.add_parser("add-detail")
    add.add_argument("--run-dir", required=True)
    add.add_argument("--subject", required=True)
    add.add_argument("--detail", required=True)
    add.set_defaults(func=command_add_detail)

    remove = sub.add_parser("remove-detail")
    remove.add_argument("--run-dir", required=True)
    remove.add_argument("--subject", required=True)
    remove.add_argument("--detail", required=True)
    remove.set_defaults(func=command_remove_detail)

    silhouette = sub.add_parser("set-silhouette")
    silhouette.add_argument("--run-dir", required=True)
    silhouette.add_argument("--subject", required=True)
    silhouette.add_argument("--value", required=True)
    silhouette.set_defaults(func=lambda args: command_set_field(args, "silhouette", "set silhouette"))

    face = sub.add_parser("set-face")
    face.add_argument("--run-dir", required=True)
    face.add_argument("--subject", required=True)
    face.add_argument("--value", required=True)
    face.set_defaults(func=lambda args: command_set_field(args, "face", "set face"))

    side = sub.add_parser("add-side-detail")
    side.add_argument("--run-dir", required=True)
    side.add_argument("--subject", required=True)
    side.add_argument("--detail", required=True)
    side.set_defaults(func=command_add_side_detail)

    style = sub.add_parser("set-style-contract")
    style.add_argument("--run-dir", required=True)
    style.add_argument("--value", required=True)
    style.set_defaults(func=command_style_contract)

    add_forbidden = sub.add_parser("add-forbidden")
    add_forbidden.add_argument("--run-dir", required=True)
    add_forbidden.add_argument("--value", required=True)
    add_forbidden.set_defaults(func=lambda args: command_forbidden(args, remove=False))

    remove_forbidden = sub.add_parser("remove-forbidden")
    remove_forbidden.add_argument("--run-dir", required=True)
    remove_forbidden.add_argument("--value", required=True)
    remove_forbidden.set_defaults(func=lambda args: command_forbidden(args, remove=True))

    canonical = sub.add_parser("set-canonical-base")
    canonical.add_argument("--run-dir", required=True)
    canonical.add_argument("--subject", required=True)
    canonical.add_argument("--value", required=True)
    canonical.set_defaults(func=command_set_canonical_base)

    validate = sub.add_parser("validate")
    validate.add_argument("--run-dir", required=True)
    validate.set_defaults(func=command_validate)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
