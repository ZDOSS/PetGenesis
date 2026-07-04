import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "derive_micro_animation_rows.py"
EXTRACT = ROOT / "scripts" / "extract_strip_frames.py"
INSPECT = ROOT / "scripts" / "inspect_frames.py"
COMPOSE = ROOT / "scripts" / "compose_atlas.py"
VALIDATE = ROOT / "scripts" / "validate_atlas.py"
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


def write_request(run_dir: Path, subject_count: int = 1):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "pet_request.json").write_text(
        json.dumps(
            {
                "pet_id": "blue-helper",
                "display_name": "Blue Helper",
                "subject_count": subject_count,
                "chroma_key": {"hex": "#00FF00", "name": "green"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "imagegen-jobs.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "animation_mode": "micro",
                "row_derivation": {
                    "status": "pending",
                    "source": "references/canonical-base.png",
                    "derived_states": list(STATES),
                },
                "jobs": [
                    {
                        "id": "base",
                        "kind": "base-pet",
                        "status": "approved",
                        "output_path": "decoded/base.png",
                        "canonical_base_path": "references/canonical-base.png",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def write_source(path: Path, *, duo: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (192, 208), (0, 255, 0, 255))
    draw = ImageDraw.Draw(image)
    if duo:
        draw.rectangle((35, 70, 75, 130), fill=(20, 80, 220, 255))
        draw.rectangle((115, 70, 155, 130), fill=(240, 210, 20, 255))
    else:
        draw.rectangle((70, 60, 120, 140), fill=(20, 80, 220, 255))
    image.save(path)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def test_derive_micro_rows_creates_strips_and_manifest_entries(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir)
    write_source(run_dir / "references" / "canonical-base.png")

    result = run_script(
        str(SCRIPT_PATH),
        "--run-dir",
        str(run_dir),
        "--source",
        "references/canonical-base.png",
    )

    assert result.returncode == 0, result.stderr
    for state, frames in STATES.items():
        with Image.open(run_dir / "decoded" / f"{state}.png") as opened:
            assert opened.size == (frames * 192, 208)
    manifest = json.loads((run_dir / "imagegen-jobs.json").read_text(encoding="utf-8"))
    assert manifest["row_derivation"]["status"] == "derived"
    derived = {job["id"]: job for job in manifest["jobs"] if job["kind"] == "row-strip-derived"}
    assert set(derived) == set(STATES)
    assert derived["idle"]["status"] == "derived"


def test_derived_micro_rows_pass_deterministic_pipeline(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir)
    write_source(run_dir / "references" / "canonical-base.png")
    assert run_script(
        str(SCRIPT_PATH),
        "--run-dir",
        str(run_dir),
        "--source",
        "references/canonical-base.png",
    ).returncode == 0

    extract = run_script(
        str(EXTRACT),
        "--decoded-dir",
        str(run_dir / "decoded"),
        "--output-dir",
        str(run_dir / "frames"),
        "--states",
        "all",
        "--subject-count",
        "1",
        "--method",
        "auto",
    )
    assert extract.returncode == 0, extract.stderr
    inspect = run_script(
        str(INSPECT),
        "--frames-root",
        str(run_dir / "frames"),
        "--json-out",
        str(run_dir / "qa" / "review.json"),
        "--require-components",
    )
    assert inspect.returncode == 0, inspect.stderr
    (run_dir / "final").mkdir()
    compose = run_script(
        str(COMPOSE),
        "--frames-root",
        str(run_dir / "frames"),
        "--output",
        str(run_dir / "final" / "spritesheet.png"),
        "--webp-output",
        str(run_dir / "final" / "spritesheet.webp"),
    )
    assert compose.returncode == 0, compose.stderr
    validate = run_script(
        str(VALIDATE),
        str(run_dir / "final" / "spritesheet.webp"),
        "--json-out",
        str(run_dir / "final" / "validation.json"),
    )
    assert validate.returncode == 0, validate.stderr
    validation = json.loads((run_dir / "final" / "validation.json").read_text(encoding="utf-8"))
    assert validation["ok"] is True


def test_duo_micro_derivation_preserves_left_right_colors(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir, subject_count=2)
    source = run_dir / "references" / "composition-guide.png"
    write_source(source, duo=True)

    result = run_script(
        str(SCRIPT_PATH),
        "--run-dir",
        str(run_dir),
        "--source",
        "references/composition-guide.png",
        "--subject-count",
        "2",
        "--states",
        "idle",
    )

    assert result.returncode == 0, result.stderr
    with Image.open(run_dir / "decoded" / "idle.png") as opened:
        first_cell = opened.crop((0, 0, 192, 208)).convert("RGBA")
    assert first_cell.getpixel((55, 100))[:3] == (20, 80, 220)
    assert first_cell.getpixel((135, 100))[:3] == (240, 210, 20)
