import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "package_pet.py"
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


def write_request(run_dir: Path):
    (run_dir / "pet_request.json").write_text(
        json.dumps(
            {
                "pet_id": "blue-helper",
                "display_name": "Blue Helper",
                "description": "A helpful blue pet.",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def write_complete_qa(run_dir: Path):
    final_dir = run_dir / "final"
    qa_dir = run_dir / "qa"
    previews_dir = qa_dir / "previews"
    final_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)
    (final_dir / "spritesheet.webp").write_bytes(b"webp")
    (final_dir / "validation.json").write_text('{"ok": true, "errors": []}\n', encoding="utf-8")
    (qa_dir / "review.json").write_text('{"ok": true, "errors": []}\n', encoding="utf-8")
    (qa_dir / "contact-sheet.png").write_bytes(b"png")
    for state in STATES:
        (previews_dir / f"{state}.gif").write_bytes(b"gif")
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps(
            {
                "jobs": [
                    {"id": "base", "kind": "base-pet", "status": "approved"},
                    {"id": "idle", "kind": "row-strip", "status": "approved"},
                    {"id": "running-left", "kind": "row-strip", "status": "derived"},
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )


def run_package(run_dir: Path, project_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--run-dir",
            str(run_dir),
            "--destination",
            "project",
            "--project-dir",
            str(project_dir),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def test_package_pet_writes_project_package_and_run_summary(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    write_complete_qa(run_dir)
    project_dir = tmp_path / "packages"

    result = run_package(run_dir, project_dir)

    assert result.returncode == 0, result.stderr

    package_dir = project_dir / "blue-helper"
    manifest = json.loads((package_dir / "pet.json").read_text(encoding="utf-8"))
    assert manifest == {
        "id": "blue-helper",
        "displayName": "Blue Helper",
        "description": "A helpful blue pet.",
        "spritesheetPath": "spritesheet.webp",
    }
    assert (package_dir / "spritesheet.webp").read_bytes() == b"webp"

    summary = json.loads((run_dir / "qa" / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["ok"] is True
    assert summary["preflight"]["ok"] is True
    assert summary["packages"][0]["kind"] == "project"
    assert summary["packages"][0]["package_dir"] == str(package_dir)


def test_package_fails_without_validation(tmp_path):
    run_dir = tmp_path / "run"
    (run_dir / "final").mkdir(parents=True)
    write_request(run_dir)
    (run_dir / "final" / "spritesheet.webp").write_bytes(b"webp")
    project_dir = tmp_path / "packages"

    result = run_package(run_dir, project_dir)

    assert result.returncode != 0
    assert "validation" in result.stderr
    assert not project_dir.exists()


def test_package_fails_when_validation_not_ok(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    write_complete_qa(run_dir)
    (run_dir / "final" / "validation.json").write_text(
        json.dumps({"ok": False, "errors": ["bad dimensions"]}) + "\n",
        encoding="utf-8",
    )
    project_dir = tmp_path / "packages"

    result = run_package(run_dir, project_dir)

    assert result.returncode != 0
    assert "bad dimensions" in result.stderr


def test_package_fails_when_previews_are_missing(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    write_request(run_dir)
    write_complete_qa(run_dir)
    (run_dir / "qa" / "previews" / "review.gif").unlink()
    project_dir = tmp_path / "packages"

    result = run_package(run_dir, project_dir)

    assert result.returncode != 0
    assert "qa/previews/review.gif" in result.stderr


def test_allow_unvalidated_packages_but_records_warnings(tmp_path):
    run_dir = tmp_path / "run"
    (run_dir / "final").mkdir(parents=True)
    write_request(run_dir)
    (run_dir / "final" / "spritesheet.webp").write_bytes(b"webp")
    project_dir = tmp_path / "packages"

    result = run_package(run_dir, project_dir, "--allow-unvalidated")

    assert result.returncode == 0, result.stderr
    package_dir = project_dir / "blue-helper"
    assert (package_dir / "pet.json").is_file()
    payload = json.loads(result.stdout)
    summary = json.loads((run_dir / "qa" / "run-summary.json").read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert summary["ok"] is False
    assert any("UNVALIDATED PACKAGE" in warning for warning in summary["warnings"])
