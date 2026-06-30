import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "extract_strip_frames.py"


def load_extract():
    spec = importlib.util.spec_from_file_location("extract_strip_frames", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_singleton_default_extraction_remains_auto():
    extract = load_extract()
    assert extract.resolve_extraction_method("auto", 1) == "auto"


def test_duo_auto_extraction_resolves_to_stable_slots():
    extract = load_extract()
    assert extract.resolve_extraction_method("auto", 2) == "stable-slots"


def test_explicit_component_method_is_respected_for_duo():
    extract = load_extract()
    assert extract.resolve_extraction_method("components", 2) == "components"
