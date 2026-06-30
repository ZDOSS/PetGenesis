import argparse
import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "inspect_frames.py"


def load_inspect():
    spec = importlib.util.spec_from_file_location("inspect_frames", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_frame(path: Path, left_color=(20, 80, 220), right_color=(240, 210, 30)):
    image = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((30, 60, 78, 150), fill=(*left_color, 255))
    draw.rectangle((118, 60, 166, 150), fill=(*right_color, 255))
    image.save(path)


def args():
    return argparse.Namespace(
        require_components=False,
        allow_stable_slots=True,
        edge_margin=2,
        edge_pixel_threshold=24,
        chroma_adjacent_threshold=150.0,
        chroma_adjacent_pixel_threshold=800,
        min_used_pixels=400,
        small_outlier_ratio=0.35,
        large_outlier_ratio=2.75,
        subject_count=2,
    )


def test_duo_expected_subjects_pass_when_left_and_right_regions_are_occupied(tmp_path):
    inspect = load_inspect()
    frames_root = tmp_path / "frames"
    idle = frames_root / "idle"
    idle.mkdir(parents=True)
    for index in range(6):
        make_frame(idle / f"{index:02d}.png")
    row = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "stable-slots", "subject_count": 2}},
        None,
        args(),
    )
    assert row["expected_subjects"]["ok"] is True
    assert row["expected_subjects"]["subjects"]["a"]["present_frames"] == 6
    assert row["expected_subjects"]["subjects"]["b"]["present_frames"] == 6


def test_duo_expected_subjects_fails_when_right_region_is_empty(tmp_path):
    inspect = load_inspect()
    frames_root = tmp_path / "frames"
    idle = frames_root / "idle"
    idle.mkdir(parents=True)
    for index in range(6):
        make_frame(idle / f"{index:02d}.png", right_color=(0, 0, 0))
        image = Image.open(idle / f"{index:02d}.png").convert("RGBA")
        for x in range(96, 192):
            for y in range(0, 208):
                image.putpixel((x, y), (0, 0, 0, 0))
        image.save(idle / f"{index:02d}.png")
    row = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "stable-slots", "subject_count": 2}},
        None,
        args(),
    )
    assert row["expected_subjects"]["ok"] is False
    assert any("subject b missing" in error for error in row["errors"])
