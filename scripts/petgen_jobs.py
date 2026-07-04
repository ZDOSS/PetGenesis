#!/usr/bin/env python3
"""Manage PetGenesis image-generation job state and approval gates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVED_STATUSES = {"approved", "derived"}
APPROVABLE_STATUSES = {"selected", "derived", "approved"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_manifest(run_dir: Path) -> tuple[Path, dict[str, Any]]:
    path = run_dir / "imagegen-jobs.json"
    if not path.is_file():
        raise SystemExit(f"job manifest not found: {path}")
    return path, json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def jobs(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    value = manifest.get("jobs")
    if not isinstance(value, list):
        raise SystemExit("invalid imagegen-jobs.json: jobs must be a list")
    return [job for job in value if isinstance(job, dict)]


def find_job(manifest: dict[str, Any], job_id: str) -> dict[str, Any]:
    for job in jobs(manifest):
        if job.get("id") == job_id:
            return job
    raise SystemExit(f"unknown job id: {job_id}")


def approval(job: dict[str, Any]) -> dict[str, Any]:
    value = job.get("approval")
    if not isinstance(value, dict):
        value = {
            "required": bool(job.get("approval_required_after", False)),
            "status": "not_requested",
            "approved_at": None,
            "note": None,
        }
        job["approval"] = value
    return value


def is_approved(job: dict[str, Any]) -> bool:
    if job.get("status") in APPROVED_STATUSES:
        return True
    job_approval = job.get("approval")
    if isinstance(job_approval, dict):
        return job_approval.get("status") == "approved"
    return job.get("status") == "complete"


def required_materialized_paths(run_dir: Path, job: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for key in ("output_path", "canonical_base_path"):
        raw = job.get(key)
        if isinstance(raw, str) and raw:
            paths.append(run_path(run_dir, raw))
    return paths


def missing_materialized_paths(run_dir: Path, job: dict[str, Any]) -> list[Path]:
    return [path for path in required_materialized_paths(run_dir, job) if not path.is_file()]


def relative_run_paths(run_dir: Path, paths: list[Path]) -> list[str]:
    result: list[str] = []
    resolved_run = run_dir.resolve()
    for path in paths:
        try:
            result.append(path.resolve().relative_to(resolved_run).as_posix())
        except ValueError:
            result.append(str(path))
    return result


def dependency_ids(job: dict[str, Any]) -> list[str]:
    value = job.get("depends_on", [])
    if not isinstance(value, list):
        raise SystemExit(f"invalid depends_on for {job.get('id')}: expected a list")
    return [str(item) for item in value]


def blocked_dependencies(manifest: dict[str, Any], run_dir: Path) -> list[dict[str, Any]]:
    by_id = {str(job.get("id")): job for job in jobs(manifest)}
    blocked: list[dict[str, Any]] = []
    for job in jobs(manifest):
        if job.get("status") != "pending":
            continue
        for dependency in dependency_ids(job):
            if dependency not in by_id:
                raise SystemExit(f"{job.get('id')} depends on unknown job: {dependency}")
            dependency_job = by_id[dependency]
            if not is_approved(dependency_job):
                continue
            missing = missing_materialized_paths(run_dir, dependency_job)
            if missing:
                blocked.append(
                    {
                        "job_id": dependency,
                        "blocking_dependent": job.get("id"),
                        "missing_paths": relative_run_paths(run_dir, missing),
                    }
                )
    return blocked


def ready_jobs(manifest: dict[str, Any], run_dir: Path | None = None) -> list[dict[str, Any]]:
    by_id = {str(job.get("id")): job for job in jobs(manifest)}
    ready: list[dict[str, Any]] = []
    for job in jobs(manifest):
        if job.get("status") != "pending":
            continue
        dependencies_ok = True
        for dependency in dependency_ids(job):
            if dependency not in by_id:
                raise SystemExit(f"{job.get('id')} depends on unknown job: {dependency}")
            dependency_job = by_id[dependency]
            if not is_approved(dependency_job):
                dependencies_ok = False
                break
            if run_dir is not None and missing_materialized_paths(run_dir, dependency_job):
                dependencies_ok = False
                break
        if dependencies_ok:
            ready.append(job)
    return ready


def run_path(run_dir: Path, relative_path: str) -> Path:
    path = (run_dir / relative_path).resolve()
    try:
        path.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise SystemExit(f"path escapes run directory: {relative_path}") from exc
    return path


def generated_images_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser().resolve() / "generated_images"
    return Path.home().resolve() / ".codex" / "generated_images"


def cleanup_generated_source(source: Path) -> bool:
    root = generated_images_root()
    try:
        source.relative_to(root)
    except ValueError:
        return False
    if source.is_file():
        source.unlink()
        try:
            source.parent.rmdir()
        except OSError:
            pass
        return True
    return False


def copy_selected_source(
    run_dir: Path,
    job: dict[str, Any],
    source: Path,
) -> tuple[Path, Path | None]:
    output_path_raw = job.get("output_path")
    if not isinstance(output_path_raw, str) or not output_path_raw:
        raise SystemExit(f"{job.get('id')} has no output_path")
    output_path = run_path(run_dir, output_path_raw)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != output_path.resolve():
        shutil.copy2(source, output_path)

    canonical_path: Path | None = None
    canonical_raw = job.get("canonical_base_path")
    if isinstance(canonical_raw, str) and canonical_raw:
        canonical_path = run_path(run_dir, canonical_raw)
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.resolve() != canonical_path.resolve():
            shutil.copy2(output_path, canonical_path)
    return output_path, canonical_path


def command_next(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    _path, manifest = load_manifest(run_dir)
    ready = ready_jobs(manifest, run_dir)
    return {
        "ok": True,
        "ready_jobs": [
            {
                "id": job.get("id"),
                "kind": job.get("kind"),
                "prompt_file": job.get("prompt_file"),
                "retry_prompt_file": job.get("retry_prompt_file"),
                "input_images": job.get("input_images", []),
                "output_path": job.get("output_path"),
            }
            for job in ready
        ],
        "blocked_dependencies": blocked_dependencies(manifest, run_dir),
    }


def command_selected(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path, manifest = load_manifest(run_dir)
    job = find_job(manifest, args.job_id)
    if job.get("status") not in {"pending", "repair_needed", "rejected", "selected"}:
        raise SystemExit(f"{args.job_id} is not selectable from status {job.get('status')}")
    source = Path(args.source).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"selected source not found: {source}")

    output_path, canonical_path = copy_selected_source(run_dir, job, source)
    timestamp = utc_now()
    job["status"] = "selected"
    job["selected_source"] = str(source)
    job["source_path"] = str(source)
    job["selected_at"] = timestamp
    job["qa_note"] = args.qa_note.strip()
    job.pop("last_error", None)
    job.pop("repair_reason", None)

    job_approval = approval(job)
    if job_approval.get("required", False):
        job_approval["status"] = "awaiting_approval"
        job_approval["requested_at"] = timestamp
        job_approval["note"] = args.qa_note.strip() or None
    else:
        job["status"] = "approved"
        job["completed_at"] = timestamp
        job_approval["status"] = "approved"
        job_approval["approved_at"] = timestamp
        job_approval["note"] = args.qa_note.strip() or None

    cleaned_source = False
    if not args.keep_source and source.resolve() != output_path.resolve():
        cleaned_source = cleanup_generated_source(source)

    save_manifest(manifest_path, manifest)
    return {
        "ok": True,
        "job_id": args.job_id,
        "status": job["status"],
        "output_path": str(output_path),
        "canonical_base_path": str(canonical_path) if canonical_path else None,
        "approval_status": approval(job).get("status"),
        "cleaned_generated_source": cleaned_source,
    }


def command_approve(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path, manifest = load_manifest(run_dir)
    job = find_job(manifest, args.job_id)
    warnings: list[str] = []
    status = str(job.get("status"))
    force = bool(getattr(args, "force", False) or args.allow_missing_output)
    if status not in APPROVABLE_STATUSES and not force:
        raise SystemExit(
            f"cannot approve {args.job_id} from status {status}; select or derive it first"
        )
    if args.allow_missing_output:
        warnings.append("--allow-missing-output is deprecated; use --force for explicit bypasses")
    if force and status not in APPROVABLE_STATUSES:
        warnings.append(f"forced approval from status {status}")

    missing_paths = missing_materialized_paths(run_dir, job)
    if missing_paths and not force:
        missing = ", ".join(relative_run_paths(run_dir, missing_paths))
        raise SystemExit(f"cannot approve {args.job_id}; required files are missing: {missing}")
    if missing_paths and force:
        warnings.append(
            "forced approval with missing required files: "
            + ", ".join(relative_run_paths(run_dir, missing_paths))
        )

    timestamp = utc_now()
    job["status"] = "approved"
    job["completed_at"] = timestamp
    if warnings:
        job.setdefault("warnings", [])
        if isinstance(job["warnings"], list):
            job["warnings"].extend(warnings)
    job_approval = approval(job)
    job_approval["status"] = "approved"
    job_approval["approved_at"] = timestamp
    job_approval["note"] = args.note.strip() or None
    save_manifest(manifest_path, manifest)
    return {
        "ok": True,
        "job_id": args.job_id,
        "status": "approved",
        "ready_jobs": [job.get("id") for job in ready_jobs(manifest, run_dir)],
        "blocked_dependencies": blocked_dependencies(manifest, run_dir),
        "warnings": warnings,
    }


def command_reject(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path, manifest = load_manifest(run_dir)
    job = find_job(manifest, args.job_id)
    timestamp = utc_now()
    job["status"] = "rejected"
    job["rejected_at"] = timestamp
    job["last_error"] = args.note.strip()
    job_approval = approval(job)
    job_approval["status"] = "rejected"
    job_approval["note"] = args.note.strip() or None
    save_manifest(manifest_path, manifest)
    return {"ok": True, "job_id": args.job_id, "status": "rejected"}


def command_repair(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    manifest_path, manifest = load_manifest(run_dir)
    job = find_job(manifest, args.job_id)
    timestamp = utc_now()
    job["status"] = "repair_needed"
    job["repair_needed_at"] = timestamp
    job["repair_reason"] = args.note.strip()
    job_approval = approval(job)
    job_approval["status"] = "repair_needed"
    job_approval["note"] = args.note.strip() or None
    save_manifest(manifest_path, manifest)
    return {"ok": True, "job_id": args.job_id, "status": "repair_needed"}


def command_summary(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser().resolve()
    _path, manifest = load_manifest(run_dir)
    counts = Counter(str(job.get("status")) for job in jobs(manifest))
    return {
        "ok": True,
        "counts": dict(sorted(counts.items())),
        "ready_jobs": [job.get("id") for job in ready_jobs(manifest, run_dir)],
        "blocked_dependencies": blocked_dependencies(manifest, run_dir),
        "jobs": [
            {
                "id": job.get("id"),
                "kind": job.get("kind"),
                "status": job.get("status"),
                "approval_status": approval(job).get("status"),
                "depends_on": job.get("depends_on", []),
            }
            for job in jobs(manifest)
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="List jobs whose dependencies are approved.")
    next_parser.add_argument("--run-dir", required=True)
    next_parser.set_defaults(func=command_next)

    selected_parser = subparsers.add_parser("selected", help="Copy a selected image into the run and await approval.")
    selected_parser.add_argument("--run-dir", required=True)
    selected_parser.add_argument("--job-id", required=True)
    selected_parser.add_argument("--source", required=True)
    selected_parser.add_argument("--qa-note", default="")
    selected_parser.add_argument("--keep-source", action="store_true")
    selected_parser.set_defaults(func=command_selected)

    approve_parser = subparsers.add_parser("approve", help="Approve a selected or derived job.")
    approve_parser.add_argument("--run-dir", required=True)
    approve_parser.add_argument("--job-id", required=True)
    approve_parser.add_argument("--note", default="")
    approve_parser.add_argument("--allow-missing-output", action="store_true")
    approve_parser.add_argument(
        "--force",
        action="store_true",
        help="Force approval despite unsafe state or missing files; records warnings.",
    )
    approve_parser.set_defaults(func=command_approve)

    reject_parser = subparsers.add_parser("reject", help="Reject a selected job.")
    reject_parser.add_argument("--run-dir", required=True)
    reject_parser.add_argument("--job-id", required=True)
    reject_parser.add_argument("--note", required=True)
    reject_parser.set_defaults(func=command_reject)

    repair_parser = subparsers.add_parser("repair", help="Mark a job as needing repair.")
    repair_parser.add_argument("--run-dir", required=True)
    repair_parser.add_argument("--job-id", required=True)
    repair_parser.add_argument("--note", required=True)
    repair_parser.set_defaults(func=command_repair)

    summary_parser = subparsers.add_parser("summary", help="Summarize job and approval state.")
    summary_parser.add_argument("--run-dir", required=True)
    summary_parser.set_defaults(func=command_summary)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    print(json.dumps(args.func(args), indent=2))


if __name__ == "__main__":
    main()
