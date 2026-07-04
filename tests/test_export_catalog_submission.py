import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "export_catalog_submission.py"
STATES = {
    "idle": 6,
    "running-right": 8,
    "running-left": 8,
    "waving": 4,
    "jumping": 5,
    "failed": 8,
    "waiting": 6,
    "running": 6,
    "review": 6,
}
CELL_WIDTH = 192
CELL_HEIGHT = 208


def write_atlas(path: Path):
    image = Image.new("RGBA", (1536, 1872), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for row, frames in enumerate(STATES.values()):
        for col in range(frames):
            left = col * CELL_WIDTH + 40
            top = row * CELL_HEIGHT + 40
            draw.rectangle((left, top, left + 24, top + 24), fill=(80, 20, 180, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "WEBP", lossless=True)


def write_run(run_dir: Path, *, complete_qa: bool = True):
    run_dir.mkdir(parents=True, exist_ok=True)
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
    write_atlas(run_dir / "final" / "spritesheet.webp")
    (run_dir / "prompts").mkdir()
    (run_dir / "prompts" / "secret.md").write_text("private prompt\n", encoding="utf-8")
    (run_dir / "references").mkdir()
    (run_dir / "references" / "identity-ledger.json").write_text("{}\n", encoding="utf-8")
    if not complete_qa:
        return
    (run_dir / "final" / "validation.json").write_text('{"ok": true, "errors": []}\n', encoding="utf-8")
    (run_dir / "qa").mkdir(exist_ok=True)
    (run_dir / "qa" / "review.json").write_text('{"ok": true, "errors": []}\n', encoding="utf-8")
    (run_dir / "qa" / "contact-sheet.png").write_bytes(b"png")
    for state in STATES:
        path = run_dir / "qa" / "previews" / f"{state}.gif"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"gif")
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps({"jobs": [{"id": "base", "status": "approved"}]}) + "\n",
        encoding="utf-8",
    )


def run_export(run_dir: Path, out_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--run-dir",
            str(run_dir),
            "--author-slug",
            "Candice Example!",
            "--out-dir",
            str(out_dir),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


def test_generic_export_creates_clean_package_and_verifies(tmp_path):
    run_dir = tmp_path / "run"
    out_dir = tmp_path / "export"
    write_run(run_dir)

    result = run_export(run_dir, out_dir)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    package_dir = out_dir / "blue-helper--candice-example"
    assert payload["ok"] is True
    assert payload["verification"]["ok"] is True
    assert sorted(path.name for path in package_dir.iterdir()) == [
        "pet.json",
        "spritesheet.webp",
        "submission.json",
    ]
    submission = json.loads((package_dir / "submission.json").read_text(encoding="utf-8"))
    assert submission["authorSlug"] == "candice-example"
    assert "run_dir" not in submission


def test_export_refuses_unvalidated_run_by_default(tmp_path):
    run_dir = tmp_path / "run"
    out_dir = tmp_path / "export"
    write_run(run_dir, complete_qa=False)

    result = run_export(run_dir, out_dir)

    assert result.returncode == 1
    assert "preflight failed" in result.stderr
    assert not out_dir.exists()


def test_export_allow_unvalidated_records_warnings(tmp_path):
    run_dir = tmp_path / "run"
    out_dir = tmp_path / "export"
    write_run(run_dir, complete_qa=False)

    result = run_export(run_dir, out_dir, "--allow-unvalidated")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert any("UNVALIDATED PACKAGE" in warning for warning in payload["warnings"])
    package_dir = out_dir / "blue-helper--candice-example"
    assert sorted(path.name for path in package_dir.iterdir()) == [
        "pet.json",
        "spritesheet.webp",
        "submission.json",
    ]


def test_awesome_catalog_can_include_pets_root(tmp_path):
    run_dir = tmp_path / "run"
    out_dir = tmp_path / "export"
    write_run(run_dir)

    result = run_export(run_dir, out_dir, "--catalog", "awesome-codex-pet", "--include-pets-root")

    assert result.returncode == 0, result.stderr
    assert (out_dir / "pets" / "blue-helper--candice-example" / "submission.json").is_file()
