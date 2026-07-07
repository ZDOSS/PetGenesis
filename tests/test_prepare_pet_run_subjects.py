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
        "animation_mode": "generated",
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


def test_default_output_dir_uses_root_petgenesis_folder(monkeypatch, tmp_path):
    prepare = load_prepare()
    monkeypatch.chdir(tmp_path)
    output_dir = prepare.default_output_dir("blue-helper")
    assert output_dir.parent == tmp_path / "petgenesis-pets"
    assert output_dir.name.startswith("blue-helper-")


def test_subject_reference_parser_accepts_subject_prefix(tmp_path):
    prepare = load_prepare()
    source = tmp_path / "subject.png"
    subject_id, path = prepare.parse_subject_reference(f"A:{source}")
    assert subject_id == "a"
    assert path == source.resolve()


def test_subject_reference_parser_rejects_missing_subject(tmp_path):
    prepare = load_prepare()
    try:
        prepare.parse_subject_reference(str(tmp_path / "subject.png"))
    except SystemExit as exc:
        assert "must start with a: or b:" in str(exc)
    else:
        raise AssertionError("subject reference without subject prefix should fail")


def test_singleton_jobs_preserve_base_job_shape(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(args(subject_count=1))
    jobs = prepare.make_jobs(tmp_path, [], subjects)
    assert jobs[0]["id"] == "base"
    assert jobs[0]["output_path"] == "decoded/base.png"
    assert jobs[0]["canonical_base_path"] == "references/canonical-base.png"
    assert jobs[0]["approval_required_after"] is True
    assert jobs[0]["approval"]["status"] == "not_requested"
    assert jobs[0]["selected_source"] is None
    assert "composite-staging" not in {job["id"] for job in jobs}
    running_left = next(job for job in jobs if job["id"] == "running-left")
    running_right = next(job for job in jobs if job["id"] == "running-right")
    waving = next(job for job in jobs if job["id"] == "waving")
    assert running_right["depends_on"] == ["base", "idle"]
    assert running_left["depends_on"] == ["base", "running-right"]
    assert waving["depends_on"] == ["base", "running-left"]
    assert running_left["derivation_policy"]["may_derive"] is True
    assert running_left["approval_required_after"] is True
    assert "parallelizable_after" not in running_left


def test_micro_animation_mode_creates_only_singleton_base_job(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(args(subject_count=1))
    jobs = prepare.make_jobs(tmp_path, [], subjects, animation_mode="micro")
    assert [job["id"] for job in jobs] == ["base"]
    assert jobs[0]["kind"] == "base-pet"


def test_hybrid_animation_mode_generates_key_singleton_rows(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(args(subject_count=1))
    jobs = prepare.make_jobs(tmp_path, [], subjects, animation_mode="hybrid")
    assert [job["id"] for job in jobs] == ["base", "idle", "running-right", "failed"]
    failed = next(job for job in jobs if job["id"] == "failed")
    assert failed["depends_on"] == ["base", "running-right"]


def test_duo_reference_inputs_are_subject_scoped(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(
        args(
            subject_count=2,
            subject_name=["Bolt", "Spark"],
            subject_notes=["blue bolt character", "yellow spark robot"],
        )
    )
    copied_refs = [
        {
            "copied_path": str(tmp_path / "references" / "reference-01.png"),
            "scope": "shared",
            "subject": "",
        },
        {
            "copied_path": str(tmp_path / "references" / "subject-a-reference-01.png"),
            "scope": "subject",
            "subject": "a",
        },
        {
            "copied_path": str(tmp_path / "references" / "subject-b-reference-01.png"),
            "scope": "subject",
            "subject": "b",
        },
    ]
    jobs = prepare.make_jobs(tmp_path, copied_refs, subjects)

    base_a = next(job for job in jobs if job["id"] == "base-a")
    base_b = next(job for job in jobs if job["id"] == "base-b")
    assert [image["path"] for image in base_a["input_images"]] == [
        "references/subject-a-reference-01.png",
        "references/reference-01.png",
    ]
    assert [image["path"] for image in base_b["input_images"]] == [
        "references/subject-b-reference-01.png",
        "references/reference-01.png",
    ]

    idle = next(job for job in jobs if job["id"] == "idle")
    idle_paths = {image["path"] for image in idle["input_images"]}
    assert "references/subject-a-reference-01.png" not in idle_paths
    assert "references/subject-b-reference-01.png" not in idle_paths
    assert "references/reference-01.png" not in idle_paths
    assert "references/canonical-base-a.png" in idle_paths
    assert "references/canonical-base-b.png" in idle_paths
    assert "references/composition-guide.png" in idle_paths


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
    assert jobs[0]["approval_required_after"] is True
    assert jobs[1]["approval_required_after"] is True
    assert jobs[2]["approval_required_after"] is True
    assert jobs[0]["depends_on"] == []
    assert jobs[1]["depends_on"] == ["base-a"]
    assert jobs[0]["approval"]["required"] is True
    idle = next(job for job in jobs if job["id"] == "idle")
    running_right = next(job for job in jobs if job["id"] == "running-right")
    running_left = next(job for job in jobs if job["id"] == "running-left")
    waving = next(job for job in jobs if job["id"] == "waving")
    assert idle["depends_on"] == ["base-a", "base-b", "composite-staging"]
    assert running_right["depends_on"] == [
        "base-a",
        "base-b",
        "composite-staging",
        "idle",
    ]
    assert running_left["depends_on"] == [
        "base-a",
        "base-b",
        "composite-staging",
        "running-right",
    ]
    assert waving["depends_on"] == [
        "base-a",
        "base-b",
        "composite-staging",
        "running-left",
    ]
    assert running_left["derivation_policy"]["may_derive"] is False
    assert running_left["approval_required_after"] is True
    assert "parallelizable_after" not in running_left
    assert "references/canonical-base-a.png" in running_left["identity_reference_paths"]
    assert "references/canonical-base-b.png" in running_left["identity_reference_paths"]
    assert any(
        image["path"] == "references/composition-guide.png"
        for image in running_left["input_images"]
    )


def test_micro_animation_mode_creates_duo_bases_and_composite_only(tmp_path):
    prepare = load_prepare()
    subjects = prepare.normalize_subjects(
        args(
            subject_count=2,
            subject_name=["Bolt", "Spark"],
            subject_notes=["blue bolt character", "yellow spark robot"],
        )
    )
    jobs = prepare.make_jobs(tmp_path, [], subjects, animation_mode="micro")
    assert [job["id"] for job in jobs] == ["base-a", "base-b", "composite-staging"]


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


def test_row_prompt_includes_exact_canvas_target():
    prepare = load_prepare()
    request = args(subject_count=1)
    request.subjects = prepare.normalize_subjects(request)
    prompt = prepare.row_prompt(request, "running-right", 1, 8, "drag")
    assert "Canvas target: 1536x208 pixels for 8 frames" in prompt
    retry_prompt = prepare.retry_row_prompt(request, "idle", 0, 6, "calm")
    assert "Canvas target: 1152x208 pixels for 6 frames" in retry_prompt


def test_row_prompt_includes_identity_lock_and_critical_details():
    prepare = load_prepare()
    request = args(subject_count=1)
    request.subjects = [
        {
            "id": "a",
            "name": "Detail Keeper",
            "notes": "ornate pet with fragile markings and props",
            "canonical_base_path": "references/canonical-base.png",
            "critical_details": [
                "left cheek star marking",
                "separate lower medallion and gold wreath",
            ],
            "side_dependent_details": [
                "viewer-left blue ribbon, viewer-right red charm",
            ],
            "simplification_rules": [
                "simplify tiny markings as the same icon in the same place",
            ],
            "silhouette": "round mascot with attached base ornament",
            "face": "single smiling face with dot eyes",
        }
    ]
    request.forbidden = ["merged charms", "duplicate markings"]

    prompt = prepare.row_prompt(request, "idle", 0, 6, "calm")
    retry_prompt = prepare.retry_row_prompt(request, "idle", 0, 6, "calm")

    for text in [prompt, retry_prompt]:
        assert "Identity lock:" in text
        assert "left cheek star marking" in text
        assert "separate lower medallion and gold wreath" in text
        assert "viewer-left blue ribbon, viewer-right red charm" in text
        assert "merged charms" in text
        assert "duplicate markings" in text
        assert "do not redesign, re-symbolize" in text


def test_identity_ledger_captures_style_and_subject_contract():
    prepare = load_prepare()
    request = args(
        subject_count=2,
        subject_name=["Bolt", "Spark"],
        subject_notes=["blue bolt character", "yellow spark robot"],
    )
    request.subjects = prepare.normalize_subjects(request)
    request.style_contract = prepare.resolved_style_contract(
        request.style_preset,
        request.style_notes,
    )
    ledger = prepare.make_identity_ledger(request)
    assert ledger["subject_count"] == 2
    assert ledger["style_contract"]["preset"] == "auto"
    assert ledger["subjects"][0]["canonical_base"] == "references/canonical-base-a.png"
    assert "floating effects" in ledger["forbidden"]
