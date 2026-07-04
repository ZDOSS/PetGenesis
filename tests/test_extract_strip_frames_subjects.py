import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw


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


def test_chroma_removal_preserves_internal_key_leakage():
    extract = load_extract()
    image = Image.new("RGBA", (64, 64), (0, 255, 0, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 52, 52), fill=(20, 80, 220, 255))
    draw.rectangle((28, 28, 36, 36), fill=(0, 255, 0, 255))

    cleaned = extract.remove_chroma_background(image, (0, 255, 0), 8.0)

    assert cleaned.getpixel((0, 0))[3] == 0
    assert cleaned.getpixel((20, 20)) == (20, 80, 220, 255)
    assert cleaned.getpixel((32, 32)) == (0, 255, 0, 255)
