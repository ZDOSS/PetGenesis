import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script(script_name: str):
    module_path = ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_inspect_frames_parse_states_accepts_row_subset():
    inspect = load_script("inspect_frames.py")
    assert inspect.parse_states("idle,review") == ["idle", "review"]
    assert inspect.parse_states("all")[0] == "idle"
    with pytest.raises(SystemExit):
        inspect.parse_states("idle,unknown")


def test_render_previews_parse_states_accepts_row_subset():
    previews = load_script("render_animation_previews.py")
    assert previews.parse_states("running-right") == ["running-right"]
    assert previews.parse_states("all")[0] == "idle"
    with pytest.raises(SystemExit):
        previews.parse_states("")
