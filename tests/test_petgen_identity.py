import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "petgen_identity.py"


def write_request(run_dir: Path, subject_count: int = 1):
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "pet_id": "blue-helper",
        "display_name": "Blue Helper",
        "description": "A helpful blue pet.",
        "subject_count": subject_count,
    }
    if subject_count == 2:
        payload["subjects"] = [
            {
                "id": "a",
                "name": "Subject A",
                "notes": "blue helper",
                "canonical_base_path": "references/canonical-base-a.png",
            },
            {
                "id": "b",
                "name": "Subject B",
                "notes": "yellow helper",
                "canonical_base_path": "references/canonical-base-b.png",
            },
        ]
    (run_dir / "pet_request.json").write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def run_identity(run_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args, "--run-dir", str(run_dir)],
        capture_output=True,
        text=True,
    )


def read_ledger(run_dir: Path):
    return json.loads((run_dir / "references" / "identity-ledger.json").read_text(encoding="utf-8"))


def test_show_initializes_missing_solo_ledger(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir, subject_count=1)

    result = run_identity(run_dir, "show")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["changed"] is True
    ledger = payload["ledger"]
    assert ledger["subject_count"] == 1
    assert ledger["subjects"][0]["id"] == "a"
    assert ledger["subjects"][0]["canonical_base"] == "references/canonical-base.png"


def test_show_initializes_missing_duo_ledger(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir, subject_count=2)

    result = run_identity(run_dir, "show")

    assert result.returncode == 0, result.stderr
    ledger = json.loads(result.stdout)["ledger"]
    assert [subject["id"] for subject in ledger["subjects"]] == ["a", "b"]
    assert ledger["subjects"][1]["canonical_base"] == "references/canonical-base-b.png"


def test_add_detail_is_idempotent(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir)

    first = run_identity(run_dir, "add-detail", "--subject", "a", "--detail", "blue triangular ears")
    second = run_identity(run_dir, "add-detail", "--subject", "solo", "--detail", "blue triangular ears")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert json.loads(first.stdout)["changed"] is True
    assert json.loads(second.stdout)["changed"] is False
    details = read_ledger(run_dir)["subjects"][0]["critical_details"]
    assert details == ["blue triangular ears"]


def test_remove_detail(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir)
    run_identity(run_dir, "add-detail", "--subject", "a", "--detail", "blue triangular ears")

    result = run_identity(run_dir, "remove-detail", "--subject", "a", "--detail", "blue triangular ears")

    assert result.returncode == 0, result.stderr
    assert read_ledger(run_dir)["subjects"][0]["critical_details"] == []


def test_rejects_subject_b_for_solo_run(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir)

    result = run_identity(run_dir, "add-detail", "--subject", "b", "--detail", "wrong")

    assert result.returncode == 1
    assert "solo runs accept" in result.stderr


def test_preserves_unknown_existing_ledger_fields(tmp_path):
    run_dir = tmp_path / "run"
    write_request(run_dir)
    ledger_path = run_dir / "references" / "identity-ledger.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "subject_count": 1,
                "custom_field": {"keep": True},
                "subjects": [
                    {
                        "id": "a",
                        "canonical_base": "references/canonical-base.png",
                        "critical_details": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_identity(run_dir, "set-face", "--subject", "a", "--value", "dot eyes")

    assert result.returncode == 0, result.stderr
    ledger = read_ledger(run_dir)
    assert ledger["custom_field"] == {"keep": True}
    assert ledger["subjects"][0]["face"] == "dot eyes"


def test_fails_without_pet_request(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = run_identity(run_dir, "show")

    assert result.returncode == 1
    assert "pet_request.json not found" in result.stderr
