import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "refresh_row_prompts.py"


def write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_refresh_row_prompts_uses_current_identity_ledger(tmp_path):
    run_dir = tmp_path / "run"
    write_json(
        run_dir / "pet_request.json",
        {
            "pet_id": "detail-keeper",
            "display_name": "Detail Keeper",
            "description": "A pet with fragile symbols.",
            "subject_count": 1,
            "subjects": [
                {
                    "id": "a",
                    "name": "Detail Keeper",
                    "notes": "round pet with base markings",
                    "canonical_base_path": "references/canonical-base.png",
                }
            ],
            "rows": [
                {
                    "state": "idle",
                    "row": 0,
                    "frames": 6,
                    "purpose": "calm resting loop",
                }
            ],
            "chroma_key": {"hex": "#00ff00", "name": "green"},
            "style_preset": "auto",
            "style_notes": "",
            "pet_notes": "round pet with base markings",
        },
    )
    write_json(
        run_dir / "references" / "identity-ledger.json",
        {
            "schema_version": 1,
            "subject_count": 1,
            "subjects": [
                {
                    "id": "a",
                    "name": "Detail Keeper",
                    "canonical_base": "references/canonical-base.png",
                    "identity_notes": "round pet with base markings",
                    "critical_details": [
                        "tiny crescent charm remains separate from the collar",
                    ],
                    "side_dependent_details": [
                        "viewer-left teal ear, viewer-right orange ear",
                    ],
                    "simplification_rules": [
                        "small symbols simplify as the same icon, not a new motif",
                    ],
                    "silhouette": "round pet with two ears and a collar charm",
                    "face": "single smiling face",
                }
            ],
            "forbidden": ["merged charm", "extra ear"],
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--run-dir",
            str(run_dir),
            "--states",
            "idle",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    prompt = (run_dir / "prompts" / "rows" / "idle.md").read_text(encoding="utf-8")
    retry = (run_dir / "prompts" / "row-retries" / "idle.md").read_text(
        encoding="utf-8"
    )
    for text in [prompt, retry]:
        assert "Identity lock:" in text
        assert "tiny crescent charm remains separate from the collar" in text
        assert "viewer-left teal ear, viewer-right orange ear" in text
        assert "small symbols simplify as the same icon" in text
        assert "merged charm" in text
        assert "extra ear" in text
