import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "prepare_pet_run.py"


def load_prepare():
    spec = importlib.util.spec_from_file_location("prepare_pet_run", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def args(**overrides):
    data = {
        "subject_count": 1,
        "subject_name": [],
        "subject_notes": [],
        "pet_notes": "round blue helper",
        "display_name": "Blue Helper",
        "pet_id": "blue-helper",
        "style_preset": "auto",
        "style_notes": "",
        "brand_name": "",
        "brand_brief": "",
        "chroma_key": {"hex": "#00ff00", "name": "green"},
        "composition": "left-right",
        "interaction_mode": "both-act",
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def test_singleton_subject_manifest_uses_upstream_canonical_base():
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(args(subject_count=1))
    assert subjects == [
        {
            "id": "a",
            "name": "Blue Helper",
            "notes": "round blue helper",
            "canonical_base_path": "references/canonical-base.png",
        }
    ]


def test_duo_subject_manifest_uses_two_named_canonical_bases():
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(
        args(
            subject_count=2,
            subject_name=["Bolt", "Spark"],
            subject_notes=["blue bolt character", "yellow spark robot"],
        )
    )
    assert subjects == [
        {
            "id": "a",
            "name": "Bolt",
            "notes": "blue bolt character",
            "canonical_base_path": "references/canonical-base-a.png",
        },
        {
            "id": "b",
            "name": "Spark",
            "notes": "yellow spark robot",
            "canonical_base_path": "references/canonical-base-b.png",
        },
    ]


def test_subject_count_above_two_is_rejected():
    prepare = load_prepare()
    try:
        prepare.normalize_subjects(args(subject_count=3))
    except SystemExit as exc:
        assert "subject count must be 1 or 2" in str(exc)
    else:
        raise AssertionError("subject_count=3 should fail")


def test_singleton_jobs_preserve_base_job_shape(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(args(subject_count=1))
    jobs = prepare.make_jobs(tmp_path, [], subjects)
    assert jobs[0]["id"] == "base"
    assert jobs[0]["output_path"] == "decoded/base.png"
    assert "composite-staging" not in {job["id"] for job in jobs}
    running_left = next(job for job in jobs if job["id"] == "running-left")
    assert running_left["derivation_policy"]["may_derive"] is True


def test_duo_jobs_create_two_bases_composite_and_generated_running_left(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(
        args(
            subject_count=2,
            subject_name=["Bolt", "Spark"],
            subject_notes=["blue bolt character", "yellow spark robot"],
        )
    )
    jobs = prepare.make_jobs(tmp_path, [], subjects)
    ids = [job["id"] for job in jobs]
    assert ids[:3] == ["base-a", "base-b", "composite-staging"]
    running_left = next(job for job in jobs if job["id"] == "running-left")
    assert running_left["derivation_policy"]["may_derive"] is False
    assert "references/canonical-base-a.png" in running_left["identity_reference_paths"]
    assert "references/canonical-base-b.png" in running_left["identity_reference_paths"]
    assert any(
        image["path"] == "references/composition-guide.png"
        for image in running_left["input_images"]
    )


def test_duo_prompt_requires_both_subjects_and_stable_staging():
    prepare = load_prepare()
    request = args(
        subject_count=2,
        subject_name=["Bolt", "Spark"],
        subject_notes=["blue bolt character", "yellow spark robot"],
    )
    request.subjects = prepare.normalize_subjects(request)
    prompt = prepare.row_prompt(request, "idle", 0, 6, "calm")
    assert "2 subjects in EVERY frame" in prompt
    assert "Subject A (Bolt)" in prompt
    assert "Subject B (Spark)" in prompt
    assert "A left, B right" in prompt
