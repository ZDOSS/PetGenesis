import importlib.util
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "resume_pet_run.py"
STATES = [
    "idle",
    "running-right",
    "running-left",
    "waving",
    "jumping",
    "failed",
    "waiting",
    "running",
    "review",
]


def load_resume():
    spec = importlib.util.spec_from_file_location("resume_pet_run", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_request(
    run_dir: Path,
    subject_count: int = 1,
    *,
    pet_id: str = "blue-helper",
    display_name: str = "Blue Helper",
):
    (run_dir / "pet_request.json").write_text(
        json.dumps(
            {
                "pet_id": pet_id,
                "display_name": display_name,
                "subject_count": subject_count,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def approval(status: str = "not_requested"):
    return {
        "required": True,
        "status": status,
        "approved_at": None,
        "note": None,
    }


def write_manifest(run_dir: Path, jobs):
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps({"schema_version": 2, "jobs": jobs}, indent=2) + "\n",
        encoding="utf-8",
    )


def base_job(status: str = "pending", approval_status: str = "not_requested"):
    return {
        "id": "base",
        "kind": "base-pet",
        "status": status,
        "prompt_file": "prompts/base-pet.md",
        "output_path": "decoded/base.png",
        "depends_on": [],
        "canonical_base_path": "references/canonical-base.png",
        "approval_required_after": True,
        "approval": approval(approval_status),
    }


def idle_job(status: str = "pending", approval_status: str = "not_requested"):
    return {
        "id": "idle",
        "kind": "row-strip",
        "status": status,
        "prompt_file": "prompts/rows/idle.md",
        "output_path": "decoded/idle.png",
        "depends_on": ["base"],
        "approval_required_after": True,
        "approval": approval(approval_status),
    }


def touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")


def write_processing_outputs(run_dir: Path):
    touch(run_dir / "frames" / "frames-manifest.json")
    touch(run_dir / "final" / "spritesheet.webp")
    (run_dir / "final" / "validation.json").write_text(
        json.dumps({"ok": True, "errors": []}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "qa").mkdir(parents=True, exist_ok=True)
    (run_dir / "qa" / "review.json").write_text(
        json.dumps({"ok": True, "errors": []}) + "\n",
        encoding="utf-8",
    )
    touch(run_dir / "qa" / "contact-sheet.png")


def write_previews(run_dir: Path):
    for state in STATES:
        touch(run_dir / "qa" / "previews" / f"{state}.gif")


def test_resume_reports_ready_job(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    write_manifest(run_dir, [base_job(), idle_job()])

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "visual_generation"
    assert result["next_action"]["kind"] == "generate_job"
    assert result["next_action"]["job"]["id"] == "base"
    assert result["ready_jobs"][0]["id"] == "base"
    assert "$imagegen" in result["next_action"]["message"]


def test_resume_reports_hermes_generation_tool(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    hermes_base = base_job()
    hermes_base["generation_skill"] = "image_generate"
    write_manifest(run_dir, [hermes_base, idle_job()])

    result = resume.analyze_run(run_dir)

    assert result["next_action"]["kind"] == "generate_job"
    assert result["next_action"]["job"]["generation_skill"] == "image_generate"
    assert "image_generate" in result["next_action"]["message"]
    assert "$imagegen" not in result["next_action"]["message"]


def test_resume_reports_selected_job_waiting_for_approval(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    selected_base = base_job("selected", "awaiting_approval")
    write_manifest(run_dir, [selected_base, idle_job()])
    touch(run_dir / "decoded" / "base.png")
    touch(run_dir / "references" / "canonical-base.png")

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "approval"
    assert result["next_action"]["kind"] == "await_approval"
    assert result["next_action"]["job"]["id"] == "base"
    assert "approve" in result["next_action"]["commands"][0]


def test_resume_blocks_on_missing_approved_output(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    approved_base = base_job("approved", "approved")
    write_manifest(run_dir, [approved_base, idle_job()])

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "recovery"
    assert result["next_action"]["kind"] == "recover_missing_files"
    assert result["missing_files"][0]["job_id"] == "base"


def test_resume_reports_processing_when_all_jobs_approved(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    approved_base = base_job("approved", "approved")
    approved_idle = idle_job("approved", "approved")
    write_manifest(run_dir, [approved_base, approved_idle])
    touch(run_dir / "decoded" / "base.png")
    touch(run_dir / "references" / "canonical-base.png")
    touch(run_dir / "decoded" / "idle.png")

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "deterministic_processing"
    assert result["next_action"]["kind"] == "run_processing"
    assert any("extract_strip_frames.py" in item for item in result["next_action"]["commands"])


def test_resume_derives_micro_rows_before_processing(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    approved_base = base_job("approved", "approved")
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "animation_mode": "micro",
                "row_derivation": {
                    "source": "references/canonical-base.png",
                    "derived_states": ["idle", "running-right"],
                },
                "jobs": [approved_base],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    touch(run_dir / "decoded" / "base.png")
    touch(run_dir / "references" / "canonical-base.png")

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "row_derivation"
    assert result["next_action"]["kind"] == "derive_micro_rows"
    assert "derive_micro_animation_rows.py" in result["next_action"]["commands"][0]


def test_resume_renders_previews_before_packaging(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    approved_base = base_job("approved", "approved")
    approved_idle = idle_job("approved", "approved")
    write_manifest(run_dir, [approved_base, approved_idle])
    touch(run_dir / "decoded" / "base.png")
    touch(run_dir / "references" / "canonical-base.png")
    touch(run_dir / "decoded" / "idle.png")
    write_processing_outputs(run_dir)

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "deterministic_processing"
    assert result["next_action"]["kind"] == "render_previews"
    assert "qa/previews/idle.gif" in result["final"]["previews"]["missing"]
    assert any("render_animation_previews.py" in item for item in result["next_action"]["commands"])


def test_resume_packages_after_previews_are_present(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    approved_base = base_job("approved", "approved")
    approved_idle = idle_job("approved", "approved")
    write_manifest(run_dir, [approved_base, approved_idle])
    touch(run_dir / "decoded" / "base.png")
    touch(run_dir / "references" / "canonical-base.png")
    touch(run_dir / "decoded" / "idle.png")
    write_processing_outputs(run_dir)
    write_previews(run_dir)

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "packaging"
    assert result["next_action"]["kind"] == "package"
    assert result["final"]["previews"]["ok"] is True


def test_resume_reports_complete_without_manifest_when_packaged(tmp_path):
    resume = load_resume()
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    touch(run_dir / "final" / "spritesheet.webp")
    (run_dir / "qa").mkdir()
    (run_dir / "qa" / "run-summary.json").write_text(
        json.dumps({"ok": True, "packages": [{"kind": "project"}]}) + "\n",
        encoding="utf-8",
    )
    write_previews(run_dir)

    result = resume.analyze_run(run_dir)

    assert result["phase"] == "complete"
    assert result["next_action"]["kind"] == "complete"


def test_discover_run_dirs_lists_newest_first(tmp_path):
    resume = load_resume()
    root = tmp_path / "petgenesis-pets"
    old_run = root / "old-run"
    new_run = root / "new-run"
    old_run.mkdir(parents=True)
    new_run.mkdir()
    write_request(old_run, pet_id="old-helper", display_name="Old Helper")
    write_manifest(old_run, [base_job()])
    write_request(new_run, pet_id="new-helper", display_name="New Helper")
    write_manifest(new_run, [base_job()])
    os.utime(old_run, (1000, 1000))
    os.utime(new_run, (2000, 2000))

    result = resume.list_runs(root)

    assert result["count"] == 2
    assert result["runs"][0]["pet_id"] == "new-helper"
    assert result["runs"][1]["pet_id"] == "old-helper"


def test_analyze_latest_filters_by_pet_id(tmp_path):
    resume = load_resume()
    root = tmp_path / "petgenesis-pets"
    other_run = root / "other-helper-20260704"
    target_run = root / "blue-helper-20260704"
    other_run.mkdir(parents=True)
    target_run.mkdir()
    write_request(other_run, pet_id="other-helper", display_name="Other Helper")
    write_manifest(other_run, [base_job()])
    write_request(target_run, pet_id="blue-helper", display_name="Blue Helper")
    write_manifest(target_run, [base_job()])
    os.utime(target_run, (1000, 1000))
    os.utime(other_run, (2000, 2000))

    result = resume.analyze_latest(root, pet_id="blue-helper")

    assert result["pet_id"] == "blue-helper"
    assert result["run_dir"] == str(target_run.resolve())
    assert result["discovery"]["selected_latest"] is True


def test_analyze_latest_reports_not_found_for_empty_root(tmp_path):
    resume = load_resume()

    result = resume.analyze_latest(tmp_path / "missing")

    assert result["ok"] is False
    assert result["phase"] == "not_found"
    assert result["next_action"]["kind"] == "no_run_found"
