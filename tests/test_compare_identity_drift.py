import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare_identity_drift.py"


def load_module():
    spec = importlib.util.spec_from_file_location("compare_identity_drift", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_base(path: Path) -> None:
    image = Image.new("RGB", (192, 208), (0, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((38, 44, 154, 174), radius=8, fill=(70, 90, 180))
    draw.rectangle((78, 74, 114, 128), fill=(230, 190, 80))
    draw.ellipse((82, 84, 96, 98), fill=(20, 20, 30))
    draw.ellipse((100, 84, 114, 98), fill=(20, 20, 30))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def save_frames(run_dir: Path, frames: list[Image.Image]) -> None:
    state_dir = run_dir / "frames" / "idle"
    state_dir.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        frame.save(state_dir / f"{index:02d}.png")


def make_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run"
    make_base(run_dir / "references" / "canonical-base.png")
    (run_dir / "pet_request.json").write_text(
        json.dumps({"chroma_key": {"hex": "#00FFFF"}}),
        encoding="utf-8",
    )
    return run_dir


def run_compare(run_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--run-dir",
            str(run_dir),
            "--states",
            "idle",
            "--json-out",
            str(run_dir / "qa" / "identity-drift.json"),
            "--overlay-dir",
            str(run_dir / "qa" / "identity-drift-overlays"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def reference_frame(run_dir: Path) -> Image.Image:
    module = load_module()
    return module.normalize_reference(
        run_dir / "references" / "canonical-base.png",
        (0, 255, 255),
        80.0,
    )


def shifted_frame(source: Image.Image, dx: int, dy: int = 0) -> Image.Image:
    frame = Image.new("RGBA", source.size, (0, 0, 0, 0))
    frame.alpha_composite(source, (dx, dy))
    return frame


def recolored_frame(source: Image.Image) -> Image.Image:
    frame = source.copy()
    data = bytearray(frame.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] <= 16:
            continue
        data[index] = 210
        data[index + 1] = 45
        data[index + 2] = 45
    return Image.frombytes("RGBA", frame.size, bytes(data))


def test_compare_identity_drift_accepts_matching_idle_frames(tmp_path):
    run_dir = make_run(tmp_path)
    reference = reference_frame(run_dir)
    save_frames(run_dir, [reference.copy() for _ in range(6)])

    result = run_compare(run_dir)

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((run_dir / "qa" / "identity-drift.json").read_text())
    assert report["ok"] is True
    assert report["rows"][0]["row_motion"]["center_span_x"] == 0
    assert (run_dir / "qa" / "identity-drift-overlays" / "idle" / "00.png").is_file()


def test_compare_identity_drift_flags_idle_sliding(tmp_path):
    run_dir = make_run(tmp_path)
    reference = reference_frame(run_dir)
    save_frames(run_dir, [shifted_frame(reference, index * 4) for index in range(6)])

    result = run_compare(run_dir)

    assert result.returncode == 1
    report = json.loads((run_dir / "qa" / "identity-drift.json").read_text())
    assert report["ok"] is False
    assert any("row center slides" in error for error in report["errors"])


def test_compare_identity_drift_flags_color_identity_change(tmp_path):
    run_dir = make_run(tmp_path)
    reference = reference_frame(run_dir)
    save_frames(run_dir, [recolored_frame(reference) for _ in range(6)])

    result = run_compare(run_dir)

    assert result.returncode == 1
    report = json.loads((run_dir / "qa" / "identity-drift.json").read_text())
    assert any("mean RGB drift" in error for error in report["errors"])
