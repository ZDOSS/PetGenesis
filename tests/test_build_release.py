import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "build_release.py"


def load_release():
    spec = importlib.util.spec_from_file_location("build_release", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_release_archive_excludes_caches_and_development_docs(tmp_path):
    release = load_release()
    skill_dir = tmp_path / "PetGenesis-master"
    write(skill_dir / "SKILL.md", "---\nname: petgenesis\ndescription: test\n---\n")
    write(skill_dir / "scripts" / "prepare_pet_run.py", "print('ok')\n")
    write(skill_dir / "scripts" / "verify_pet_package.py", "print('ok')\n")
    write(skill_dir / "scripts" / "export_catalog_submission.py", "print('ok')\n")
    write(skill_dir / "scripts" / "petgen_identity.py", "print('ok')\n")
    write(skill_dir / "scripts" / "derive_micro_animation_rows.py", "print('ok')\n")
    write(skill_dir / "tests" / "test_prepare.py", "def test_ok(): pass\n")
    write(skill_dir / ".pytest_cache" / "README.md", "cache\n")
    write(skill_dir / "scripts" / "__pycache__" / "prepare_pet_run.pyc", "cache\n")
    write(skill_dir / "docs" / "superpowers" / "planning.md", "dev notes\n")
    output = tmp_path / "release.zip"

    result = release.build_archive(skill_dir, output, "petgenesis")

    assert result["ok"] is True
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
    assert "petgenesis/SKILL.md" in names
    assert "petgenesis/scripts/prepare_pet_run.py" in names
    assert "petgenesis/scripts/verify_pet_package.py" in names
    assert "petgenesis/scripts/export_catalog_submission.py" in names
    assert "petgenesis/scripts/petgen_identity.py" in names
    assert "petgenesis/scripts/derive_micro_animation_rows.py" in names
    assert "petgenesis/tests/test_prepare.py" in names
    assert not any(".pytest_cache" in name for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(name.startswith("petgenesis/docs/superpowers/") for name in names)


def test_release_file_iterator_excludes_dist_output(tmp_path):
    release = load_release()
    skill_dir = tmp_path / "skill"
    write(skill_dir / "SKILL.md")
    write(skill_dir / "dist" / "petgenesis.zip")
    write(skill_dir / "output" / "debug.png")
    write(skill_dir / "petgenesis-pets" / "run" / "decoded.png")
    write(skill_dir / "generated_images" / "image.png")

    files = [path.as_posix() for path in release.iter_release_files(skill_dir)]

    assert files == ["SKILL.md"]


def test_cli_default_output_uses_workspace_release_folder(tmp_path):
    skill_dir = tmp_path / "skill"
    write(skill_dir / "SKILL.md", "---\nname: petgenesis\ndescription: test\n---\n")

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--skill-dir", str(skill_dir)],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    expected = tmp_path / "petgenesis-releases" / "petgenesis.zip"
    assert Path(payload["archive"]) == expected
    assert expected.is_file()
