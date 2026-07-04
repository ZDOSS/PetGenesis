import argparse
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "petgen_jobs.py"


def load_jobs():
    spec = importlib.util.spec_from_file_location("petgen_jobs", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_manifest(run_dir: Path):
    manifest = {
        "schema_version": 2,
        "jobs": [
            {
                "id": "base",
                "kind": "base-pet",
                "status": "pending",
                "output_path": "decoded/base.png",
                "depends_on": [],
                "canonical_base_path": "references/canonical-base.png",
                "approval_required_after": True,
                "approval": {
                    "required": True,
                    "status": "not_requested",
                    "approved_at": None,
                    "note": None,
                },
            },
            {
                "id": "idle",
                "kind": "row-strip",
                "status": "pending",
                "output_path": "decoded/idle.png",
                "depends_on": ["base"],
                "approval_required_after": True,
                "approval": {
                    "required": True,
                    "status": "not_requested",
                    "approved_at": None,
                    "note": None,
                },
            },
        ],
    }
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def test_selected_then_approved_job_unlocks_dependents(tmp_path):
    jobs = load_jobs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_manifest(run_dir)
    source = tmp_path / "generated.png"
    Image.new("RGBA", (32, 32), (10, 20, 30, 255)).save(source)

    next_result = jobs.command_next(argparse.Namespace(run_dir=str(run_dir)))
    assert [job["id"] for job in next_result["ready_jobs"]] == ["base"]

    selected_result = jobs.command_selected(
        argparse.Namespace(
            run_dir=str(run_dir),
            job_id="base",
            source=str(source),
            qa_note="looks usable",
            keep_source=True,
        )
    )
    assert selected_result["status"] == "selected"
    assert (run_dir / "decoded" / "base.png").is_file()
    assert (run_dir / "references" / "canonical-base.png").is_file()

    next_result = jobs.command_next(argparse.Namespace(run_dir=str(run_dir)))
    assert next_result["ready_jobs"] == []

    approve_result = jobs.command_approve(
        argparse.Namespace(
            run_dir=str(run_dir),
            job_id="base",
            note="approved by user",
            allow_missing_output=False,
            force=False,
        )
    )
    assert approve_result["status"] == "approved"
    assert approve_result["ready_jobs"] == ["idle"]

    manifest = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))
    base = manifest["jobs"][0]
    assert base["approval"]["status"] == "approved"
    assert base["status"] == "approved"


def test_repair_status_blocks_dependents(tmp_path):
    jobs = load_jobs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_manifest(run_dir)

    result = jobs.command_repair(
        argparse.Namespace(
            run_dir=str(run_dir),
            job_id="base",
            note="identity drift",
        )
    )
    assert result["status"] == "repair_needed"
    next_result = jobs.command_next(argparse.Namespace(run_dir=str(run_dir)))
    assert next_result["ready_jobs"] == []


def test_cannot_approve_pending_job_just_because_output_exists(tmp_path):
    jobs = load_jobs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_manifest(run_dir)
    (run_dir / "decoded").mkdir()
    Image.new("RGBA", (32, 32), (10, 20, 30, 255)).save(run_dir / "decoded" / "base.png")

    with pytest.raises(SystemExit, match="select or derive"):
        jobs.command_approve(
            argparse.Namespace(
                run_dir=str(run_dir),
                job_id="base",
                note="should not work",
                allow_missing_output=False,
                force=False,
            )
        )

    manifest = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))
    assert manifest["jobs"][0]["status"] == "pending"
    next_result = jobs.command_next(argparse.Namespace(run_dir=str(run_dir)))
    assert [job["id"] for job in next_result["ready_jobs"]] == ["base"]


def test_cannot_approve_selected_canonical_job_when_canonical_copy_is_missing(tmp_path):
    jobs = load_jobs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_manifest(run_dir)
    manifest = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))
    manifest["jobs"][0]["status"] = "selected"
    manifest["jobs"][0]["approval"]["status"] = "awaiting_approval"
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "decoded").mkdir()
    Image.new("RGBA", (32, 32), (10, 20, 30, 255)).save(run_dir / "decoded" / "base.png")

    with pytest.raises(SystemExit, match="canonical-base.png"):
        jobs.command_approve(
            argparse.Namespace(
                run_dir=str(run_dir),
                job_id="base",
                note="should not work",
                allow_missing_output=False,
                force=False,
            )
        )

    next_result = jobs.command_next(argparse.Namespace(run_dir=str(run_dir)))
    assert next_result["ready_jobs"] == []


def test_approved_dependency_missing_file_blocks_next(tmp_path):
    jobs = load_jobs()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_manifest(run_dir)
    manifest = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))
    manifest["jobs"][0]["status"] = "approved"
    manifest["jobs"][0]["approval"]["status"] = "approved"
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "decoded").mkdir()
    Image.new("RGBA", (32, 32), (10, 20, 30, 255)).save(run_dir / "decoded" / "base.png")

    next_result = jobs.command_next(argparse.Namespace(run_dir=str(run_dir)))
    assert next_result["ready_jobs"] == []
    assert next_result["blocked_dependencies"] == [
        {
            "job_id": "base",
            "blocking_dependent": "idle",
            "missing_paths": ["references/canonical-base.png"],
        }
    ]

    summary = jobs.command_summary(argparse.Namespace(run_dir=str(run_dir)))
    assert summary["blocked_dependencies"] == next_result["blocked_dependencies"]
