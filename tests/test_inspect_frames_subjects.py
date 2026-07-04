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


def args(**overrides):
    data = {
        "require_components": False,
        "allow_stable_slots": True,
        "edge_margin": 2,
        "edge_pixel_threshold": 24,
        "chroma_adjacent_threshold": 150.0,
        "chroma_adjacent_pixel_threshold": 800,
        "min_used_pixels": 400,
        "small_outlier_ratio": 0.35,
        "large_outlier_ratio": 2.75,
        "subject_count": 2,
        "disable_duo_palette_check": False,
        "duo_palette_warning_delta": 18.0,
    }
    data.update(overrides)
    return argparse.Namespace(
        **data,
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


def test_stable_slots_require_components_needs_explicit_allowance(tmp_path):
    inspect = load_inspect()
    frames_root = tmp_path / "frames"
    idle = frames_root / "idle"
    idle.mkdir(parents=True)
    for index in range(6):
        make_frame(idle / f"{index:02d}.png")

    blocked = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "stable-slots", "subject_count": 2}},
        None,
        args(require_components=True, allow_stable_slots=False),
    )
    assert blocked["ok"] is False
    assert any("used extraction method stable-slots" in error for error in blocked["errors"])

    allowed = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "stable-slots", "subject_count": 2}},
        None,
        args(require_components=True, allow_stable_slots=True),
    )
    assert allowed["ok"] is True
    assert any("stable-slots" in warning for warning in allowed["warnings"])


def test_chroma_key_leakage_inside_sprite_fails_inspection(tmp_path):
    inspect = load_inspect()
    frames_root = tmp_path / "frames"
    idle = frames_root / "idle"
    idle.mkdir(parents=True)
    for index in range(6):
        image = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((64, 58, 128, 150), fill=(20, 80, 220, 255))
        draw.rectangle((88, 90, 104, 106), fill=(0, 255, 0, 255))
        image.save(idle / f"{index:02d}.png")

    row = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "components", "subject_count": 1}},
        (0, 255, 0),
        args(
            subject_count=1,
            chroma_adjacent_threshold=8.0,
            chroma_adjacent_pixel_threshold=0,
        ),
    )

    assert row["ok"] is False
    assert any("close to the chroma key" in error for error in row["errors"])


def write_duo_canonical_bases(run_dir: Path):
    references = run_dir / "references"
    references.mkdir(parents=True)
    Image.new("RGBA", (192, 208), (0, 255, 0, 255)).save(
        references / "unused-background.png"
    )
    base_a = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
    draw_a = ImageDraw.Draw(base_a)
    draw_a.ellipse((58, 50, 134, 158), fill=(20, 80, 220, 255))
    base_a.save(references / "canonical-base-a.png")
    base_b = Image.new("RGBA", (192, 208), (0, 0, 0, 0))
    draw_b = ImageDraw.Draw(base_b)
    draw_b.rectangle((58, 50, 134, 158), fill=(240, 210, 30, 255))
    base_b.save(references / "canonical-base-b.png")
    (references / "identity-ledger.json").write_text(
        """{
  "subject_count": 2,
  "subjects": [
    {"id": "a", "canonical_base": "references/canonical-base-a.png"},
    {"id": "b", "canonical_base": "references/canonical-base-b.png"}
  ]
}
""",
        encoding="utf-8",
    )


def test_duo_palette_region_check_stays_quiet_for_expected_sides(tmp_path):
    inspect = load_inspect()
    frames_root = tmp_path / "run" / "frames"
    write_duo_canonical_bases(frames_root.parent)
    idle = frames_root / "idle"
    idle.mkdir(parents=True)
    for index in range(6):
        make_frame(idle / f"{index:02d}.png")

    row = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "stable-slots", "subject_count": 2}},
        (0, 255, 0),
        args(),
    )

    assert row["ok"] is True
    assert row["duo_palette_regions"]["warnings"] == []


def test_duo_palette_region_check_warns_for_obvious_swaps(tmp_path):
    inspect = load_inspect()
    frames_root = tmp_path / "run" / "frames"
    write_duo_canonical_bases(frames_root.parent)
    idle = frames_root / "idle"
    idle.mkdir(parents=True)
    for index in range(6):
        make_frame(
            idle / f"{index:02d}.png",
            left_color=(240, 210, 30),
            right_color=(20, 80, 220),
        )

    row = inspect.inspect_state(
        frames_root,
        "idle",
        6,
        {"idle": {"method": "stable-slots", "subject_count": 2}},
        (0, 255, 0),
        args(),
    )

    assert row["ok"] is True
    assert any("palette regions look swapped" in warning for warning in row["warnings"])
