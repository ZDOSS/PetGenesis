import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "hermes" / "install.py"


def load_installer():
    assert MODULE_PATH.is_file(), "hermes/install.py has not been implemented"
    spec = importlib.util.spec_from_file_location("hermes_install", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_source_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "PetGenesis"
    write(
        repo / "hermes" / "SKILL.md",
        "---\nname: petgenesis\ndescription: Hermes adapter\n---\n\n# Adapter\n",
    )
    write(repo / "hermes" / "README.md", "# Hermes setup\n")
    write(repo / "scripts" / "prepare_pet_run.py", "print('prepare')\n")
    write(repo / "scripts" / "__pycache__" / "ignored.pyc", "cache")
    write(repo / "references" / "runbook.md", "# Runbook\n")
    write(repo / "LICENSE.txt", "MIT\n")
    write(repo / "tests" / "test_not_installed.py", "def test_noop(): pass\n")
    return repo


def test_install_assembles_complete_skill_without_runtime_caches(tmp_path):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = tmp_path / "hermes-home" / "skills" / "creative" / "petgenesis"

    result = installer.install_skill(repo, destination)

    assert result["ok"] is True
    assert Path(result["destination"]) == destination.resolve()
    assert (destination / "SKILL.md").read_text(encoding="utf-8").endswith("# Adapter\n")
    assert (destination / "README.md").read_text(encoding="utf-8") == "# Hermes setup\n"
    assert (destination / "scripts" / "prepare_pet_run.py").is_file()
    assert (destination / "references" / "runbook.md").is_file()
    assert (destination / "LICENSE.txt").is_file()
    marker = json.loads(
        (destination / ".petgenesis-install.json").read_text(encoding="utf-8")
    )
    assert marker == {
        "installer": "PetGenesis/hermes/install.py",
        "schema_version": 1,
        "skill": "petgenesis",
    }
    assert not (destination / "scripts" / "__pycache__").exists()
    assert not (destination / "tests").exists()


def test_install_refuses_to_replace_unmanaged_destination(tmp_path):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = tmp_path / "skills" / "creative" / "petgenesis"
    write(destination / "stale.txt", "old installation\n")

    with pytest.raises(FileExistsError, match="destination already exists"):
        installer.install_skill(repo, destination)

    with pytest.raises(PermissionError, match="not managed by this installer"):
        installer.install_skill(repo, destination, force=True)

    assert (destination / "stale.txt").is_file()


def test_install_force_atomically_replaces_managed_skill(tmp_path):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = tmp_path / "skills" / "creative" / "petgenesis"
    installer.install_skill(repo, destination)
    write(destination / "stale.txt", "old installation\n")

    result = installer.install_skill(repo, destination, force=True)

    assert result["ok"] is True
    assert (destination / "SKILL.md").is_file()
    assert not (destination / "stale.txt").exists()


@pytest.mark.parametrize("relative_destination", [".", "..", "hermes/installed"])
def test_install_rejects_source_destination_overlap(tmp_path, relative_destination):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = (repo / relative_destination).resolve()

    with pytest.raises(ValueError, match="overlap"):
        installer.install_skill(repo, destination, force=True)


def test_install_rejects_symbolic_link_destination(tmp_path):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    target = tmp_path / "unrelated-target"
    target.mkdir()
    destination = tmp_path / "linked-skill"
    try:
        destination.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symbolic links are unavailable: {exc}")

    with pytest.raises(ValueError, match="symbolic link"):
        installer.install_skill(repo, destination, force=True)

    assert target.is_dir()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction behavior only")
def test_install_rejects_windows_junction_destination(tmp_path):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    target = tmp_path / "managed-target"
    installer.install_skill(repo, target)
    write(target / "sentinel.txt", "must survive\n")
    destination = tmp_path / "junction-skill"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"Windows junctions are unavailable: {result.stderr}")

    try:
        with pytest.raises(ValueError, match="symbolic link or junction"):
            installer.install_skill(repo, destination, force=True)
        assert (target / "sentinel.txt").is_file()
    finally:
        if destination.exists():
            destination.rmdir()


def test_force_rechecks_the_object_moved_after_validation(tmp_path, monkeypatch):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = tmp_path / "skills" / "creative" / "petgenesis"
    installer.install_skill(repo, destination)
    displaced_managed_install = tmp_path / "displaced-managed-install"
    unmanaged_victim = tmp_path / "unmanaged-victim"
    write(unmanaged_victim / "sentinel.txt", "must survive\n")
    original_check = installer._check_destination
    check_count = 0

    def swap_after_second_check(path, *, force):
        nonlocal check_count
        original_check(path, force=force)
        check_count += 1
        if check_count == 2:
            path.replace(displaced_managed_install)
            unmanaged_victim.replace(path)

    monkeypatch.setattr(installer, "_check_destination", swap_after_second_check)

    with pytest.raises(PermissionError, match="changed after validation"):
        installer.install_skill(repo, destination, force=True)

    assert (destination / "sentinel.txt").is_file()
    assert (displaced_managed_install / ".petgenesis-install.json").is_file()


def test_force_does_not_overwrite_path_created_after_backup(tmp_path, monkeypatch):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = tmp_path / "skills" / "creative" / "petgenesis"
    installer.install_skill(repo, destination)
    unmanaged_victim = tmp_path / "late-unmanaged-victim"
    write(unmanaged_victim / "sentinel.txt", "must survive\n")
    original_is_managed = installer._is_managed_install

    def insert_victim_after_backup_check(path):
        result = original_is_managed(path)
        if result and path.name.startswith(".petgenesis.bak-"):
            unmanaged_victim.replace(destination)
        return result

    monkeypatch.setattr(installer, "_is_managed_install", insert_victim_after_backup_check)

    with pytest.raises(OSError):
        installer.install_skill(repo, destination, force=True)

    assert (destination / "sentinel.txt").is_file()
    backups = list(destination.parent.glob(".petgenesis.bak-*"))
    assert len(backups) == 1
    assert (backups[0] / ".petgenesis-install.json").is_file()


def test_non_force_restores_path_created_after_final_check(tmp_path, monkeypatch):
    installer = load_installer()
    repo = make_source_repo(tmp_path)
    destination = tmp_path / "skills" / "creative" / "petgenesis"
    unmanaged_victim = tmp_path / "late-unmanaged-victim"
    write(unmanaged_victim / "sentinel.txt", "must survive\n")
    original_check = installer._check_destination
    check_count = 0

    def insert_victim_after_second_check(path, *, force):
        nonlocal check_count
        original_check(path, force=force)
        check_count += 1
        if check_count == 2:
            unmanaged_victim.replace(path)

    monkeypatch.setattr(installer, "_check_destination", insert_victim_after_second_check)

    with pytest.raises(FileExistsError, match="changed after validation"):
        installer.install_skill(repo, destination)

    assert (destination / "sentinel.txt").is_file()
    assert not list(destination.parent.glob(".petgenesis.bak-*"))
    assert not list(destination.parent.glob(".petgenesis.tmp-*"))


def test_cli_installs_to_explicit_destination(tmp_path):
    repo = make_source_repo(tmp_path)
    destination = (
        tmp_path
        / "Hermes Home With Spaces"
        / "skills"
        / "creative"
        / "petgenesis"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--repo-root",
            str(repo),
            "--destination",
            str(destination),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert Path(payload["destination"]) == destination.resolve()
    assert (destination / "SKILL.md").is_file()


def test_cli_defaults_to_petgenesis_under_hermes_home(tmp_path):
    repo = make_source_repo(tmp_path)
    hermes_home = tmp_path / "hermes-home"
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--repo-root", str(repo)],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    expected = hermes_home / "skills" / "creative" / "petgenesis"
    assert Path(payload["destination"]) == expected.resolve()
    assert (expected / "SKILL.md").is_file()


def test_checked_in_adapter_has_valid_frontmatter_and_openpets_workflow():
    content = (ROOT / "hermes" / "SKILL.md").read_text(encoding="utf-8")
    readme = (ROOT / "hermes" / "README.md").read_text(encoding="utf-8")

    assert content.startswith("---\n")
    frontmatter, body = content[4:].split("\n---\n", 1)
    assert "name: petgenesis" in frontmatter
    assert "description:" in frontmatter
    assert "version:" in frontmatter
    assert "license: MIT" in frontmatter
    assert body.strip()
    assert len(content) <= 100_000
    assert "`image_generate`" in body
    assert "${HERMES_SKILL_DIR}" in body
    assert "--generation-skill image_generate" in body
    assert "openpets install --from-folder" in body
    assert "verify_pet_package.py" in body
    assert "/petgenesis" in readme
    assert "/skill petgenesis" not in readme
    assert "hermes config set image_gen.provider" not in content
    assert "hermes config set image_gen.model" not in content
    assert "hermes config set image_gen.provider" not in readme
    assert "hermes config set image_gen.model" not in readme
    assert "must be run from a PetGenesis repository clone" in readme


def test_checked_in_adapter_assembles_with_shared_runtime_files(tmp_path):
    installer = load_installer()
    destination = tmp_path / "petgenesis"

    result = installer.install_skill(ROOT, destination)

    assert result["ok"] is True
    assert (destination / "SKILL.md").is_file()
    assert (destination / "README.md").is_file()
    assert (destination / "scripts" / "package_pet.py").is_file()
    assert (destination / "scripts" / "verify_pet_package.py").is_file()
    assert (destination / "references" / "runbook.md").is_file()
    assert not (destination / "hermes").exists()
