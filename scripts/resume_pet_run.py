#!/usr/bin/env python3
"""Report the safest next step for an interrupted PetGenesis run."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import petgen_jobs
from petgen_contract import expected_preview_paths


APPROVED_STATUSES = {"approved", "derived"}
PROCESSING_OUTPUTS = [
    "frames/frames-manifest.json",
    "qa/review.json",
    "final/spritesheet.webp",
    "final/validation.json",
    "qa/contact-sheet.png",
]


def default_run_root() -> Path:
    return Path.cwd() / "petgenesis-pets"


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def as_posix_relative(path: Path, run_dir: Path) -> str:
    try:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
    except ValueError:
        return str(path)


def run_path(run_dir: Path, relative_path: str) -> Path:
    path = (run_dir / relative_path).resolve()
    try:
        path.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise SystemExit(f"path escapes run directory: {relative_path}") from exc
    return path


def job_output_path(run_dir: Path, job: dict[str, Any]) -> Path | None:
    raw_path = job.get("output_path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    return run_path(run_dir, raw_path)


def job_approval_status(job: dict[str, Any]) -> str:
    value = job.get("approval")
    if isinstance(value, dict):
        status = value.get("status")
        if isinstance(status, str) and status:
            return status
    return "not_requested"


def is_visual_job_done(job: dict[str, Any]) -> bool:
    return str(job.get("status")) in APPROVED_STATUSES


def job_generation_skill(job: dict[str, Any]) -> str:
    value = job.get("generation_skill")
    if isinstance(value, str) and value:
        return value
    return "$imagegen"


def job_summary(job: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    output_path = job_output_path(run_dir, job)
    return {
        "id": job.get("id"),
        "kind": job.get("kind"),
        "status": job.get("status"),
        "approval_status": job_approval_status(job),
        "prompt_file": job.get("prompt_file"),
        "retry_prompt_file": job.get("retry_prompt_file"),
        "output_path": as_posix_relative(output_path, run_dir) if output_path else None,
        "input_images": job.get("input_images", []),
        "generation_skill": job_generation_skill(job),
    }


def command(parts: list[str]) -> str:
    quoted: list[str] = []
    for part in parts:
        if any(char.isspace() for char in part) or '"' in part:
            quoted.append('"' + part.replace('"', '\\"') + '"')
        else:
            quoted.append(part)
    return " ".join(quoted)


def petgen_command(run_dir: Path, subcommand: str, *args: str) -> str:
    return command(
        [
            "python",
            "$SKILL_DIR/scripts/petgen_jobs.py",
            subcommand,
            "--run-dir",
            str(run_dir),
            *args,
        ]
    )


def processing_commands(run_dir: Path, subject_count: int) -> list[str]:
    stable_flag = ["--allow-stable-slots"] if subject_count == 2 else []
    return [
        command(
            [
                "python",
                "$SKILL_DIR/scripts/extract_strip_frames.py",
                "--decoded-dir",
                str(run_dir / "decoded"),
                "--output-dir",
                str(run_dir / "frames"),
                "--states",
                "all",
                "--subject-count",
                str(subject_count),
                "--method",
                "auto",
            ]
        ),
        command(
            [
                "python",
                "$SKILL_DIR/scripts/inspect_frames.py",
                "--frames-root",
                str(run_dir / "frames"),
                "--json-out",
                str(run_dir / "qa" / "review.json"),
                "--require-components",
                *stable_flag,
            ]
        ),
        command(
            [
                "python",
                "$SKILL_DIR/scripts/compose_atlas.py",
                "--frames-root",
                str(run_dir / "frames"),
                "--output",
                str(run_dir / "final" / "spritesheet.png"),
                "--webp-output",
                str(run_dir / "final" / "spritesheet.webp"),
            ]
        ),
        command(
            [
                "python",
                "$SKILL_DIR/scripts/validate_atlas.py",
                str(run_dir / "final" / "spritesheet.webp"),
                "--json-out",
                str(run_dir / "final" / "validation.json"),
            ]
        ),
        command(
            [
                "python",
                "$SKILL_DIR/scripts/make_contact_sheet.py",
                str(run_dir / "final" / "spritesheet.webp"),
                "--output",
                str(run_dir / "qa" / "contact-sheet.png"),
            ]
        ),
        command(
            [
                "python",
                "$SKILL_DIR/scripts/render_animation_previews.py",
                "--frames-root",
                str(run_dir / "frames"),
                "--output-dir",
                str(run_dir / "qa" / "previews"),
            ]
        ),
    ]


def render_preview_commands(run_dir: Path) -> list[str]:
    return [
        command(
            [
                "python",
                "$SKILL_DIR/scripts/render_animation_previews.py",
                "--frames-root",
                str(run_dir / "frames"),
                "--output-dir",
                str(run_dir / "qa" / "previews"),
            ]
        )
    ]


def derive_micro_commands(run_dir: Path, source: str, subject_count: int, states: list[str]) -> list[str]:
    parts = [
        "python",
        "$SKILL_DIR/scripts/derive_micro_animation_rows.py",
        "--run-dir",
        str(run_dir),
        "--source",
        source,
        "--subject-count",
        str(subject_count),
    ]
    if states:
        parts.extend(["--states", ",".join(states)])
    return [command(parts)]


def missing_job_outputs(
    run_dir: Path,
    jobs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for job in jobs:
        if str(job.get("status")) not in {"selected", "approved", "derived"}:
            continue
        output_path = job_output_path(run_dir, job)
        if output_path is not None and not output_path.is_file():
            missing.append(
                {
                    "job_id": str(job.get("id")),
                    "path": as_posix_relative(output_path, run_dir),
                    "reason": "job output is missing",
                }
            )
        canonical_raw = job.get("canonical_base_path")
        if isinstance(canonical_raw, str) and canonical_raw:
            canonical_path = run_path(run_dir, canonical_raw)
            if not canonical_path.is_file():
                missing.append(
                    {
                        "job_id": str(job.get("id")),
                        "path": as_posix_relative(canonical_path, run_dir),
                        "reason": "canonical base is missing",
                    }
                )
    return missing


def json_health(path: Path) -> dict[str, Any]:
    data = load_optional_json(path)
    if not data:
        return {"exists": path.is_file(), "ok": None, "errors": [], "warnings": []}
    return {
        "exists": True,
        "ok": data.get("ok"),
        "errors": data.get("errors", []),
        "warnings": data.get("warnings", []),
    }


def preview_status(run_dir: Path) -> dict[str, Any]:
    paths = expected_preview_paths(run_dir)
    missing = [path for path in paths if not path.is_file()]
    return {
        "ok": not missing,
        "missing": [as_posix_relative(path, run_dir) for path in missing],
        "paths": [as_posix_relative(path, run_dir) for path in paths],
    }


def packaged(run_dir: Path) -> bool:
    summary = load_optional_json(run_dir / "qa" / "run-summary.json")
    packages = summary.get("packages")
    return bool(summary.get("ok") and isinstance(packages, list) and packages)


def is_candidate_run_dir(path: Path) -> bool:
    return (
        path.is_dir()
        and (
            (path / "pet_request.json").is_file()
            or (path / "imagegen-jobs.json").is_file()
            or (path / "final" / "spritesheet.webp").is_file()
        )
    )


def run_matches_pet_id(run_dir: Path, pet_id: str) -> bool:
    pet_id = pet_id.strip()
    if not pet_id:
        return True
    request = load_optional_json(run_dir / "pet_request.json")
    request_pet_id = str(request.get("pet_id") or "").strip()
    return request_pet_id == pet_id or run_dir.name.startswith(f"{pet_id}-")


def discover_run_dirs(
    root: Path,
    *,
    pet_id: str = "",
    limit: int = 10,
) -> list[Path]:
    root = root.expanduser().resolve()
    if not root.exists():
        return []
    candidates = [root] if is_candidate_run_dir(root) else []
    if root.is_dir():
        candidates.extend(
            child
            for child in root.iterdir()
            if child.is_dir() and is_candidate_run_dir(child)
        )
    deduped = {candidate.resolve(): candidate.resolve() for candidate in candidates}
    filtered = [
        candidate
        for candidate in deduped.values()
        if run_matches_pet_id(candidate, pet_id)
    ]
    filtered.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    if limit > 0:
        return filtered[:limit]
    return filtered


def run_list_entry(run_dir: Path) -> dict[str, Any]:
    result = analyze_run(run_dir)
    return {
        "run_dir": result["run_dir"],
        "pet_id": result.get("pet_id"),
        "display_name": result.get("display_name"),
        "subject_count": result.get("subject_count"),
        "phase": result.get("phase"),
        "next_action": result.get("next_action", {}).get("kind"),
        "has_manifest": result.get("has_manifest"),
        "packaged": result.get("final", {}).get("packaged"),
        "updated_at": run_dir.stat().st_mtime,
    }


def list_runs(root: Path, *, pet_id: str = "", limit: int = 10) -> dict[str, Any]:
    root = root.expanduser().resolve()
    run_dirs = discover_run_dirs(root, pet_id=pet_id, limit=limit)
    return {
        "ok": True,
        "root": str(root),
        "pet_id_filter": pet_id.strip(),
        "count": len(run_dirs),
        "runs": [run_list_entry(run_dir) for run_dir in run_dirs],
    }


def analyze_latest(root: Path, *, pet_id: str = "") -> dict[str, Any]:
    root = root.expanduser().resolve()
    run_dirs = discover_run_dirs(root, pet_id=pet_id, limit=1)
    if not run_dirs:
        return {
            "ok": False,
            "root": str(root),
            "pet_id_filter": pet_id.strip(),
            "phase": "not_found",
            "next_action": action(
                "no_run_found",
                "No PetGenesis run folder was found under the requested root.",
            ),
        }
    result = analyze_run(run_dirs[0])
    result["discovery"] = {
        "root": str(root),
        "pet_id_filter": pet_id.strip(),
        "selected_latest": True,
    }
    return result


def action(
    kind: str,
    message: str,
    *,
    commands: list[str] | None = None,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"kind": kind, "message": message}
    if job is not None:
        result["job"] = job
    if commands:
        result["commands"] = commands
    return result


def analyze_run(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.expanduser().resolve()
    request = load_optional_json(run_dir / "pet_request.json")
    subject_count = int(request.get("subject_count") or 1)
    manifest_path = run_dir / "imagegen-jobs.json"
    final_spritesheet = run_dir / "final" / "spritesheet.webp"
    run_summary = run_dir / "qa" / "run-summary.json"
    previews = preview_status(run_dir)

    base_result: dict[str, Any] = {
        "ok": True,
        "run_dir": str(run_dir),
        "pet_id": request.get("pet_id"),
        "display_name": request.get("display_name"),
        "subject_count": subject_count,
        "has_manifest": manifest_path.is_file(),
        "final": {
            "spritesheet": final_spritesheet.is_file(),
            "validation": json_health(run_dir / "final" / "validation.json"),
            "review": json_health(run_dir / "qa" / "review.json"),
            "contact_sheet": (run_dir / "qa" / "contact-sheet.png").is_file(),
            "previews": previews,
            "run_summary": run_summary.is_file(),
            "packaged": packaged(run_dir),
        },
    }

    if not manifest_path.is_file():
        if final_spritesheet.is_file() and packaged(run_dir) and previews["ok"]:
            base_result["phase"] = "complete"
            base_result["next_action"] = action(
                "complete",
                "Final spritesheet and package summary are present.",
            )
            return base_result
        if final_spritesheet.is_file() and not previews["ok"]:
            base_result["phase"] = "deterministic_processing"
            base_result["next_action"] = action(
                "render_previews",
                "Final spritesheet exists but required preview GIFs are missing; render previews before packaging or completion.",
                commands=render_preview_commands(run_dir),
            )
            return base_result
        if final_spritesheet.is_file():
            base_result["phase"] = "packaging"
            base_result["next_action"] = action(
                "package",
                "Final spritesheet exists; ask where to package the pet.",
                commands=[
                    command(
                        [
                            "python",
                            "$SKILL_DIR/scripts/package_pet.py",
                            "--run-dir",
                            str(run_dir),
                            "--destination",
                            "project",
                            "--project-dir",
                            "<package-root>",
                        ]
                    )
                ],
            )
            return base_result
        base_result["ok"] = False
        base_result["phase"] = "invalid"
        base_result["next_action"] = action(
            "invalid_run",
            "No imagegen-jobs.json manifest or final spritesheet was found.",
        )
        return base_result

    _manifest_file, manifest = petgen_jobs.load_manifest(run_dir)
    job_list = petgen_jobs.jobs(manifest)
    counts = Counter(str(job.get("status")) for job in job_list)
    ready = petgen_jobs.ready_jobs(manifest, run_dir)
    missing = missing_job_outputs(run_dir, job_list)
    selected = [
        job
        for job in job_list
        if str(job.get("status")) == "selected"
        or job_approval_status(job) == "awaiting_approval"
    ]
    repair = [
        job
        for job in job_list
        if str(job.get("status")) in {"repair_needed", "rejected"}
        or job_approval_status(job) in {"repair_needed", "rejected"}
    ]
    all_done = bool(job_list) and all(is_visual_job_done(job) for job in job_list)
    animation_mode = str(manifest.get("animation_mode") or "generated")
    row_derivation = manifest.get("row_derivation")
    if not isinstance(row_derivation, dict):
        row_derivation = {}
    derived_states = [
        str(state)
        for state in row_derivation.get("derived_states", [])
        if isinstance(state, str)
    ]
    derived_missing = [
        state for state in derived_states if not (run_dir / "decoded" / f"{state}.png").is_file()
    ]
    processing_missing = [
        path for path in PROCESSING_OUTPUTS if not (run_dir / path).is_file()
    ]

    base_result.update(
        {
            "phase": "visual_generation",
            "counts": dict(sorted(counts.items())),
            "ready_jobs": [job_summary(job, run_dir) for job in ready],
            "selected_jobs": [job_summary(job, run_dir) for job in selected],
            "repair_jobs": [job_summary(job, run_dir) for job in repair],
            "missing_files": missing,
            "processing_missing": processing_missing,
            "animation_mode": animation_mode,
            "row_derivation": {
                "source": row_derivation.get("source"),
                "derived_states": derived_states,
                "missing_states": derived_missing,
            },
        }
    )

    if missing:
        base_result["phase"] = "recovery"
        base_result["next_action"] = action(
            "recover_missing_files",
            "A selected, approved, or derived job is missing an expected output. Re-select or repair the affected job before continuing.",
        )
        return base_result

    if repair:
        job = repair[0]
        job_id = str(job.get("id"))
        base_result["phase"] = "repair"
        base_result["next_action"] = action(
            "repair_job",
            f"Repair or replace `{job_id}` before continuing.",
            job=job_summary(job, run_dir),
            commands=[
                petgen_command(
                    run_dir,
                    "selected",
                    "--job-id",
                    job_id,
                    "--source",
                    "<replacement-output>",
                    "--qa-note",
                    "<repair QA note>",
                ),
                petgen_command(
                    run_dir,
                    "approve",
                    "--job-id",
                    job_id,
                    "--note",
                    "<approved repair note>",
                ),
            ],
        )
        return base_result

    if selected:
        job = selected[0]
        job_id = str(job.get("id"))
        base_result["phase"] = "approval"
        base_result["next_action"] = action(
            "await_approval",
            f"Show `{job_id}` to the user, then approve, reject, or mark repair needed.",
            job=job_summary(job, run_dir),
            commands=[
                petgen_command(
                    run_dir,
                    "approve",
                    "--job-id",
                    job_id,
                    "--note",
                    "<approved by user or visual QA>",
                ),
                petgen_command(
                    run_dir,
                    "reject",
                    "--job-id",
                    job_id,
                    "--note",
                    "<why rejected>",
                ),
                petgen_command(
                    run_dir,
                    "repair",
                    "--job-id",
                    job_id,
                    "--note",
                    "<smallest repair needed>",
                ),
            ],
        )
        return base_result

    if ready:
        job = ready[0]
        job_id = str(job.get("id"))
        generation_skill = job_generation_skill(job)
        base_result["next_action"] = action(
            "generate_job",
            f"Generate `{job_id}` with {generation_skill} using the listed prompt and input images.",
            job=job_summary(job, run_dir),
            commands=[
                petgen_command(
                    run_dir,
                    "selected",
                    "--job-id",
                    job_id,
                    "--source",
                    "<generated-output>",
                    "--qa-note",
                    "<one-sentence QA note>",
                )
            ],
        )
        return base_result

    if all_done:
        if animation_mode in {"micro", "hybrid"} and derived_missing:
            source = str(row_derivation.get("source") or ("references/composition-guide.png" if subject_count == 2 else "references/canonical-base.png"))
            base_result["phase"] = "row_derivation"
            base_result["next_action"] = action(
                "derive_micro_rows",
                "All required generated sources are approved; derive the remaining micro-animation rows before deterministic processing.",
                commands=derive_micro_commands(run_dir, source, subject_count, derived_missing),
            )
            return base_result
        review_health = json_health(run_dir / "qa" / "review.json")
        validation_health = json_health(run_dir / "final" / "validation.json")
        if review_health["errors"] or validation_health["errors"]:
            base_result["phase"] = "repair"
            base_result["next_action"] = action(
                "repair_after_processing",
                "Deterministic review or validation reported errors. Read the JSON outputs and repair the smallest affected scope.",
            )
            return base_result
        if processing_missing:
            base_result["phase"] = "deterministic_processing"
            base_result["next_action"] = action(
                "run_processing",
                "All visual jobs are approved or derived; run deterministic extraction, inspection, atlas, contact sheet, and preview scripts.",
                commands=processing_commands(run_dir, subject_count),
            )
            return base_result
        if not previews["ok"]:
            base_result["phase"] = "deterministic_processing"
            base_result["next_action"] = action(
                "render_previews",
                "Required preview GIFs are missing; render previews before packaging.",
                commands=render_preview_commands(run_dir),
            )
            return base_result
        if not packaged(run_dir):
            base_result["phase"] = "packaging"
            base_result["next_action"] = action(
                "package",
                "Final outputs exist; ask where to package the pet.",
                commands=[
                    command(
                        [
                            "python",
                            "$SKILL_DIR/scripts/package_pet.py",
                            "--run-dir",
                            str(run_dir),
                            "--destination",
                            "project",
                            "--project-dir",
                            "<package-root>",
                        ]
                    )
                ],
            )
            return base_result
        base_result["phase"] = "complete"
        base_result["next_action"] = action(
            "complete",
            "All visual jobs, deterministic outputs, and package summary are present.",
        )
        return base_result

    base_result["phase"] = "blocked"
    base_result["next_action"] = action(
        "blocked",
        "No job is ready and no selected or repair-needed job was found. Inspect dependencies and job statuses.",
        commands=[petgen_command(run_dir, "summary")],
    )
    return base_result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        default="",
        help="Specific run directory. If omitted, resume the newest discovered run.",
    )
    parser.add_argument(
        "--root",
        default="",
        help="Folder containing PetGenesis run directories. Defaults to ./petgenesis-pets.",
    )
    parser.add_argument(
        "--pet-id",
        default="",
        help="When discovering runs, only consider this pet_id or matching run folder prefix.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_runs",
        help="List recent discovered runs instead of resuming one.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum runs to list during discovery. Use 0 for all.",
    )
    parser.add_argument(
        "--write-summary",
        action="store_true",
        help="Also write qa/resume-summary.json.",
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve() if args.root else default_run_root().resolve()
    if args.list_runs:
        result = list_runs(root, pet_id=args.pet_id, limit=args.limit)
    elif args.run_dir.strip():
        result = analyze_run(Path(args.run_dir).expanduser().resolve())
    else:
        result = analyze_latest(root, pet_id=args.pet_id)

    if args.write_summary:
        run_dir_raw = result.get("run_dir")
        if isinstance(run_dir_raw, str) and run_dir_raw:
            qa_dir = Path(run_dir_raw) / "qa"
            qa_dir.mkdir(parents=True, exist_ok=True)
            (qa_dir / "resume-summary.json").write_text(
                json.dumps(result, indent=2) + "\n",
                encoding="utf-8",
            )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
