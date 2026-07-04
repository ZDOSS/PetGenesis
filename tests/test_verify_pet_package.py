import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify_pet_package.py"
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


def write_pet_json(package_dir: Path, spritesheet_path: str = "spritesheet.webp"):
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "pet.json").write_text(
        json.dumps(
            {
                "id": "blue-helper",
                "displayName": "Blue Helper",
                "description": "A helpful blue pet.",
                "spritesheetPath": spritesheet_path,
            }
        )
        + "\n",
        encoding="utf-8",
    )


def write_atlas(path: Path, *, size=(1536, 1872), blank_state: str | None = None):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for row, (state, frames) in enumerate(STATES.items()):
        if state == blank_state:
            continue
        for col in range(frames):
            left = col * CELL_WIDTH + 50
            top = row * CELL_HEIGHT + 50
            draw.rectangle((left, top, left + 20, top + 20), fill=(20, 80, 200, 255))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "WEBP", lossless=True)


def run_verify(package_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(package_dir), *extra],
        capture_output=True,
        text=True,
    )


def test_valid_package_passes(tmp_path):
    package_dir = tmp_path / "blue-helper"
    write_pet_json(package_dir)
    write_atlas(package_dir / "spritesheet.webp")

    result = run_verify(package_dir)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["checks"]["dimensions"] is True
    assert payload["checks"]["rows_nonempty"] is True


def test_missing_pet_json_fails(tmp_path):
    package_dir = tmp_path / "blue-helper"
    package_dir.mkdir()

    result = run_verify(package_dir)

    assert result.returncode == 1
    assert "pet.json not found" in result.stdout


def test_absolute_spritesheet_path_fails(tmp_path):
    package_dir = tmp_path / "blue-helper"
    absolute = tmp_path / "spritesheet.webp"
    write_pet_json(package_dir, str(absolute))
    write_atlas(absolute)

    result = run_verify(package_dir)

    assert result.returncode == 1
    assert "must be relative" in result.stdout


def test_escaping_spritesheet_path_fails(tmp_path):
    package_dir = tmp_path / "blue-helper"
    write_pet_json(package_dir, "../spritesheet.webp")
    write_atlas(tmp_path / "spritesheet.webp")

    result = run_verify(package_dir)

    assert result.returncode == 1
    assert "outside the package" in result.stdout


def test_missing_spritesheet_fails(tmp_path):
    package_dir = tmp_path / "blue-helper"
    write_pet_json(package_dir)

    result = run_verify(package_dir)

    assert result.returncode == 1
    assert "spritesheet file not found" in result.stdout


def test_wrong_dimensions_fail(tmp_path):
    package_dir = tmp_path / "blue-helper"
    write_pet_json(package_dir)
    write_atlas(package_dir / "spritesheet.webp", size=(192, 208))

    result = run_verify(package_dir)

    assert result.returncode == 1
    assert "expected 1536x1872" in result.stdout


def test_blank_required_row_fails(tmp_path):
    package_dir = tmp_path / "blue-helper"
    write_pet_json(package_dir)
    write_atlas(package_dir / "spritesheet.webp", blank_state="review")

    result = run_verify(package_dir)

    assert result.returncode == 1
    assert "review frame 00 is blank" in result.stdout


def test_strict_clean_fails_on_unexpected_file(tmp_path):
    package_dir = tmp_path / "blue-helper"
    write_pet_json(package_dir)
    write_atlas(package_dir / "spritesheet.webp")
    (package_dir / "qa.txt").write_text("debug\n", encoding="utf-8")

    result = run_verify(package_dir, "--strict-clean")

    assert result.returncode == 1
    assert "unexpected files" in result.stdout
