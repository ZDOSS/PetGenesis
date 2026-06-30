# PetGenesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `petgenesis` as a fork of Hatch Pet that preserves one-subject pet generation and adds a two-subject duo workflow.

**Architecture:** Import the upstream Hatch Pet skill, then add subject-count branching at the run-preparation boundary. Keep atlas composition and packaging subject-agnostic, branch generation prompts/jobs/layout guides/extraction/inspection only where subject count changes behavior.

**Tech Stack:** Python 3, Pillow, pytest, Codex skill layout, `$imagegen` delegation through skill instructions.

---

## File Structure

- `SKILL.md`: Rewrite the user-facing workflow around `subject_count` 1 or 2, with singleton preservation and duo generation steps.
- `agents/openai.yaml`: Rename UI metadata to PetGenesis and mention solo/duo support.
- `references/codex-pet-contract.md`: Keep the upstream atlas contract and add a note that one or two subjects are encoded inside each cell's pixels.
- `references/animation-rows.md`: Keep upstream row counts and add duo interaction guidance.
- `references/qa-rubric.md`: Preserve singleton QA and add duo-specific identity/staging checks.
- `scripts/prepare_pet_run.py`: Add subject-count parsing, subject manifests, singleton/duo prompt branching, duo layout guides, duo job graph, and generated composite-staging job metadata.
- `scripts/extract_strip_frames.py`: Preserve singleton default extraction and default duo runs to `stable-slots`.
- `scripts/inspect_frames.py`: Preserve upstream frame checks and add approximate duo region checks plus `expected_subjects`.
- `scripts/compose_atlas.py`, `scripts/validate_atlas.py`, `scripts/make_contact_sheet.py`, `scripts/render_animation_previews.py`: Import unchanged unless smoke tests expose path/name assumptions.
- `scripts/derive_running_left_from_running_right.py`: Import unchanged, but do not reference it for duo jobs.
- `tests/test_prepare_pet_run_subjects.py`: New tests for subject parsing, manifests, prompts, and jobs.
- `tests/test_extract_strip_frames_subjects.py`: New tests for subject-aware extraction defaults.
- `tests/test_inspect_frames_subjects.py`: New tests for duo `expected_subjects` checks.
- `AI.md`: New agent-facing implementation notes; update after meaningful code changes.
- `Readme.md`: New user-facing setup and usage notes; update after meaningful code changes.

---

### Task 1: Import Upstream Hatch Pet

**Files:**
- Create: `C:/Github/PetGenesis/SKILL.md`
- Create: `C:/Github/PetGenesis/LICENSE.txt`
- Create: `C:/Github/PetGenesis/agents/openai.yaml`
- Create: `C:/Github/PetGenesis/references/animation-rows.md`
- Create: `C:/Github/PetGenesis/references/codex-pet-contract.md`
- Create: `C:/Github/PetGenesis/references/qa-rubric.md`
- Create: all files from upstream `skills/.curated/hatch-pet/scripts/`

- [ ] **Step 1: Fetch the upstream archive**

Run:

```powershell
$zip = 'C:\tmp\openai-skills-main.zip'
$extract = 'C:\tmp\openai-skills-main'
Remove-Item -LiteralPath $zip -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $extract -Recurse -Force -ErrorAction SilentlyContinue
curl.exe -L -o $zip https://github.com/openai/skills/archive/refs/heads/main.zip
Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
```

Expected: `$extract\skills-main\skills\.curated\hatch-pet` exists.

- [ ] **Step 2: Copy the Hatch Pet skill into PetGenesis**

Run:

```powershell
$source = 'C:\tmp\openai-skills-main\skills-main\skills\.curated\hatch-pet'
$target = 'C:\Github\PetGenesis'
Copy-Item -LiteralPath "$source\SKILL.md" -Destination "$target\SKILL.md" -Force
Copy-Item -LiteralPath "$source\LICENSE.txt" -Destination "$target\LICENSE.txt" -Force
Copy-Item -LiteralPath "$source\agents" -Destination "$target\agents" -Recurse -Force
Copy-Item -LiteralPath "$source\references" -Destination "$target\references" -Recurse -Force
Copy-Item -LiteralPath "$source\scripts" -Destination "$target\scripts" -Recurse -Force
```

Expected: `C:\Github\PetGenesis\scripts\prepare_pet_run.py` exists.

- [ ] **Step 3: Commit the import**

Run:

```powershell
git -C C:\Github\PetGenesis add SKILL.md LICENSE.txt agents references scripts
git -C C:\Github\PetGenesis commit -m "Import upstream Hatch Pet skill"
```

Expected: commit succeeds.

---

### Task 2: Add Test Harness For Subject Count Behavior

**Files:**
- Create: `C:/Github/PetGenesis/tests/test_prepare_pet_run_subjects.py`
- Create: `C:/Github/PetGenesis/tests/test_extract_strip_frames_subjects.py`
- Create: `C:/Github/PetGenesis/tests/test_inspect_frames_subjects.py`

- [ ] **Step 1: Write failing tests for prepare-run subject behavior**

Create `tests/test_prepare_pet_run_subjects.py`:

```python
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
```

- [ ] **Step 2: Write failing tests for extraction defaults**

Create `tests/test_extract_strip_frames_subjects.py`:

```python
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
```

- [ ] **Step 3: Write failing tests for duo frame inspection**

Create `tests/test_inspect_frames_subjects.py`:

```python
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


def args():
    return argparse.Namespace(
        require_components=False,
        allow_stable_slots=True,
        edge_margin=2,
        edge_pixel_threshold=24,
        chroma_adjacent_threshold=150.0,
        chroma_adjacent_pixel_threshold=800,
        min_used_pixels=400,
        small_outlier_ratio=0.35,
        large_outlier_ratio=2.75,
        subject_count=2,
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
```

- [ ] **Step 4: Run tests and verify they fail**

Run:

```powershell
python -m pytest tests -q
```

Expected: failures mention missing `normalize_subjects`, `resolve_extraction_method`, and `expected_subjects`.

- [ ] **Step 5: Keep the red tests uncommitted until the first green implementation**

Run:

```powershell
git -C C:\Github\PetGenesis status --short
```

Expected: the three new test files are untracked. They will be committed with the implementation that makes the first group pass, so the repository does not intentionally capture a red checkpoint.

---

### Task 3: Implement Subject Parsing And Manifests

**Files:**
- Modify: `C:/Github/PetGenesis/scripts/prepare_pet_run.py`
- Modify: `C:/Github/PetGenesis/tests/test_prepare_pet_run_subjects.py`
- Modify: `C:/Github/PetGenesis/AI.md`
- Modify: `C:/Github/PetGenesis/Readme.md`

- [ ] **Step 1: Add subject constants and `normalize_subjects`**

In `scripts/prepare_pet_run.py`, add helpers near `CANONICAL_BASE_PATH`:

```python
SUBJECT_IDS = ("a", "b")
DUO_COMPOSITION_GUIDE_PATH = "references/composition-guide.png"


def subject_canonical_base_path(subject_count: int, subject_id: str) -> str:
    if subject_count == 1:
        return CANONICAL_BASE_PATH
    return f"references/canonical-base-{subject_id}.png"


def normalize_subjects(args: argparse.Namespace) -> list[dict[str, str]]:
    subject_count = int(getattr(args, "subject_count", 1))
    if subject_count not in {1, 2}:
        raise SystemExit("subject count must be 1 or 2")
    names = [compact(value) for value in getattr(args, "subject_name", []) if compact(value)]
    notes = [compact(value) for value in getattr(args, "subject_notes", []) if compact(value)]
    if len(names) > subject_count:
        raise SystemExit(f"received {len(names)} subject names for subject count {subject_count}")
    if len(notes) > subject_count:
        raise SystemExit(f"received {len(notes)} subject notes for subject count {subject_count}")
    subjects: list[dict[str, str]] = []
    fallback_name = compact(getattr(args, "display_name", "")) or "Subject"
    fallback_notes = compact(getattr(args, "pet_notes", "")) or "the subject shown in the reference image(s)"
    for index in range(subject_count):
        subject_id = SUBJECT_IDS[index]
        default_name = fallback_name if subject_count == 1 else f"Subject {subject_id.upper()}"
        subjects.append(
            {
                "id": subject_id,
                "name": names[index] if index < len(names) else default_name,
                "notes": notes[index] if index < len(notes) else fallback_notes,
                "canonical_base_path": subject_canonical_base_path(subject_count, subject_id),
            }
        )
    return subjects
```

- [ ] **Step 2: Add CLI arguments**

In `main()`, after `--pet-notes`, add:

```python
    parser.add_argument(
        "--subject-count",
        type=int,
        default=1,
        help="Number of subjects to preserve in the pet. PetGenesis v1 supports 1 or 2.",
    )
    parser.add_argument(
        "--subject-name",
        action="append",
        default=[],
        help="Subject display name. Pass once for solo pets or twice for duo pets.",
    )
    parser.add_argument(
        "--subject-notes",
        action="append",
        default=[],
        help="Identity notes for a subject. Pass once for solo pets or twice for duo pets.",
    )
    parser.add_argument(
        "--composition",
        default="left-right",
        choices=("left-right",),
        help="Duo subject staging. PetGenesis v1 supports left-right.",
    )
    parser.add_argument(
        "--interaction-mode",
        default="both-act",
        choices=("both-act", "one-acts-other-reacts"),
        help="Duo prompt interaction mode.",
    )
```

- [ ] **Step 3: Store subjects in the request manifest**

After existing argument normalization, set:

```python
    args.subjects = normalize_subjects(args)
```

In the `request` dictionary written to `pet_request.json`, add:

```python
        "subject_count": args.subject_count,
        "subjects": args.subjects,
        "composition": args.composition if args.subject_count == 2 else "",
        "interaction_mode": args.interaction_mode if args.subject_count == 2 else "",
```

- [ ] **Step 4: Run subject parsing tests**

Run:

```powershell
python -m pytest tests/test_prepare_pet_run_subjects.py::test_singleton_subject_manifest_uses_upstream_canonical_base tests/test_prepare_pet_run_subjects.py::test_duo_subject_manifest_uses_two_named_canonical_bases tests/test_prepare_pet_run_subjects.py::test_subject_count_above_two_is_rejected -q
```

Expected: 3 passed.

- [ ] **Step 5: Update docs for subject-count branch**

Add `AI.md` with:

```markdown
# AI Notes

PetGenesis is a fork of Hatch Pet. Preserve the singleton Hatch Pet workflow for `--subject-count 1`; add duo-specific behavior only when `--subject-count 2`.

Subject IDs are fixed as `a` and `b`. Singleton runs use `references/canonical-base.png`. Duo runs use `references/canonical-base-a.png`, `references/canonical-base-b.png`, and `references/composition-guide.png`.
```

Add `Readme.md` with:

```markdown
# PetGenesis

PetGenesis creates Codex-compatible animated pets from one subject or a two-subject duo. It keeps the Hatch Pet atlas contract and adds a duo workflow for paired characters.

Use `--subject-count 1` for a solo pet and `--subject-count 2` for a duo. Counts greater than 2 are rejected because each animation cell is only `192x208`.
```

- [ ] **Step 6: Commit subject parsing**

Run:

```powershell
git -C C:\Github\PetGenesis add scripts/prepare_pet_run.py tests/test_prepare_pet_run_subjects.py AI.md Readme.md
git -C C:\Github\PetGenesis commit -m "feat: add subject count manifest support"
```

Expected: commit succeeds.

---

### Task 4: Implement Singleton And Duo Prompt/Job Branching

**Files:**
- Modify: `C:/Github/PetGenesis/scripts/prepare_pet_run.py`
- Modify: `C:/Github/PetGenesis/tests/test_prepare_pet_run_subjects.py`
- Modify: `C:/Github/PetGenesis/AI.md`
- Modify: `C:/Github/PetGenesis/Readme.md`

- [ ] **Step 1: Add subject prompt helpers**

Add these helpers before `base_pet_prompt`:

```python
def is_duo(args: argparse.Namespace) -> bool:
    return int(getattr(args, "subject_count", 1)) == 2


def subject_identity_lines(subjects: list[dict[str, str]]) -> str:
    return "\n".join(
        f"  - Subject {subject['id'].upper()} ({subject['name']}): {subject['notes']}"
        for subject in subjects
    )


def duo_interaction_line(args: argparse.Namespace, state: str) -> str:
    if args.interaction_mode == "one-acts-other-reacts" and state in {"waving", "jumping", "failed"}:
        return "Interaction: Subject A performs the main action while Subject B visibly reacts, while both remain present."
    return "Interaction: both subjects participate in the state action with readable coordinated motion."
```

- [ ] **Step 2: Branch `base_pet_prompt` for a selected subject**

Change `base_pet_prompt` signature to:

```python
def base_pet_prompt(args: argparse.Namespace, subject: dict[str, str] | None = None) -> str:
```

Inside the function, use:

```python
    if subject is not None:
        pet_notes = subject["notes"]
        display_name = subject["name"]
    else:
        pet_notes = args.pet_notes or "the pet shown in the reference image(s)"
        display_name = args.display_name
```

Change the first prompt line to use `display_name`.

- [ ] **Step 3: Branch row prompts**

At the top of `row_prompt`, before the singleton return, add:

```python
    if is_duo(args):
        subjects = args.subjects
        style_contract = resolved_style_contract(args.style_preset, args.style_notes)
        chroma_key = args.chroma_key["hex"]
        chroma_name = args.chroma_key["name"]
        state_prompt = STATE_PROMPTS[state]
        state_requirements = "\n".join(f"- {line}" for line in STATE_REQUIREMENTS[state])
        identities = subject_identity_lines(subjects)
        interaction = duo_interaction_line(args, state)
        return f"""Create one horizontal animation strip for Codex pet `{args.pet_id}`, state `{state}`.

Use the attached canonical bases for per-subject identity. Use the attached composition guide for A-left/B-right staging, relative scale, gap, and baseline. Use the attached layout guide only for slot count, spacing, centering, and padding; do not draw the guide.

Output exactly {frames} full-body frames in one left-to-right row on flat pure {chroma_name} {chroma_key}. Treat the row as {frames} invisible equal-width slots: both complete subjects inside every slot, evenly spaced, with no overlap across slots, clipping, empty slots, labels, or borders.

Identity: 2 subjects in EVERY frame, all present, never cropped or omitted. Per-subject identity must match the matching canonical base:
{identities}
Preserve each subject's silhouette, face, proportions, markings, palette, material, style, and props independently.
Staging: left-right composition - Subject A left, Subject B right, fixed positions every frame, stable relative scale and gap. Subjects may touch for an interaction but must not merge into one silhouette.
Style: {style_contract}
Animation continuity: keep apparent subject scale and baseline stable within the row unless the state itself intentionally changes vertical position, such as `jumping`.

State action: {state_prompt}
{interaction}

State requirements:
{state_requirements}

Clean extraction: crisp opaque edges, safe padding, no scenery, text, guide marks, checkerboard, shadows, glows, motion blur, speed lines, dust, detached effects, stray pixels, or chroma-key colors inside either subject."""
```

Apply the same duo branch pattern to `retry_row_prompt`.

- [ ] **Step 4: Branch `make_jobs`**

Change the signature to:

```python
def make_jobs(run_dir: Path, copied_refs: list[dict[str, object]], subjects: list[dict[str, str]] | None = None) -> list[dict[str, object]]:
```

Set:

```python
    subjects = subjects or normalize_subjects(argparse.Namespace(subject_count=1, subject_name=[], subject_notes=[]))
    subject_count = len(subjects)
```

Keep the existing singleton branch when `subject_count == 1`. Add a duo branch that creates `base-a`, `base-b`, `composite-staging`, then rows. Duo row jobs must include:

```python
"identity_reference_paths": [subject["canonical_base_path"] for subject in subjects],
"derivation_policy": {"may_derive": False, "reason": "duo running-left must preserve A-left/B-right staging"},
```

Each duo row `input_images` must include copied references, layout guide, both canonical bases, `references/composition-guide.png`, and `decoded/running-right.png` only for `running-left`.

- [ ] **Step 5: Write base and row prompts for all jobs**

Where prompts are written in `main()`, write one base prompt per subject:

```python
    for subject in args.subjects:
        if args.subject_count == 1:
            prompt_path = run_dir / "prompts" / "base-pet.md"
        else:
            prompt_path = run_dir / "prompts" / f"base-{subject['id']}.md"
        prompt_path.write_text(base_pet_prompt(args, subject), encoding="utf-8")
```

Write `prompts/composite-staging.md` for duo runs with text requiring both selected bases in one 192x208 staging cell.

- [ ] **Step 6: Run prepare-run job tests**

Run:

```powershell
python -m pytest tests/test_prepare_pet_run_subjects.py -q
```

Expected: 6 passed.

- [ ] **Step 7: Update docs and commit**

Add to `AI.md`:

```markdown
## Job Graph

Singleton jobs keep upstream IDs: `base`, then one job per animation row. Duo jobs use `base-a`, `base-b`, `composite-staging`, then one job per animation row. Duo `running-left` is always generated and never derived by mirroring.
```

Add to `Readme.md`:

```markdown
For duo pets, PetGenesis generates each subject separately, then creates a composite staging reference before generating animation rows. This improves identity consistency while preserving the normal Codex pet atlas.
```

Run:

```powershell
git -C C:\Github\PetGenesis add scripts/prepare_pet_run.py tests/test_prepare_pet_run_subjects.py AI.md Readme.md
git -C C:\Github\PetGenesis commit -m "feat: branch generation jobs by subject count"
```

Expected: commit succeeds.

---

### Task 5: Implement Duo Layout Guides

**Files:**
- Modify: `C:/Github/PetGenesis/scripts/prepare_pet_run.py`
- Modify: `C:/Github/PetGenesis/AI.md`

- [ ] **Step 1: Extend layout guide functions**

Change `create_layout_guide` signature:

```python
def create_layout_guide(path: Path, state: str, frames: int, subject_count: int = 1) -> dict[str, object]:
```

For `subject_count == 1`, keep existing drawing behavior. For `subject_count == 2`, draw a vertical divider inside every frame slot, label the left safe region `A`, label the right safe region `B`, and keep the existing safe margins and slot boundaries.

- [ ] **Step 2: Pass subject count from `create_layout_guides`**

Change signature:

```python
def create_layout_guides(run_dir: Path, subject_count: int = 1) -> list[dict[str, object]]:
```

Call `create_layout_guide(path, state, frames, subject_count)` for every row.

- [ ] **Step 3: Call layout guide creation with `args.subject_count`**

In `main()`, change:

```python
    layout_guides = create_layout_guides(run_dir)
```

to:

```python
    layout_guides = create_layout_guides(run_dir, args.subject_count)
```

- [ ] **Step 4: Smoke test layout guide generation**

Run:

```powershell
python scripts/prepare_pet_run.py --pet-name Layout Solo --subject-count 1 --output-dir C:\tmp\petgenesis-layout-solo --force
python scripts/prepare_pet_run.py --pet-name Layout Duo --subject-count 2 --subject-name A --subject-name B --subject-notes blue --subject-notes yellow --output-dir C:\tmp\petgenesis-layout-duo --force
```

Expected: both commands write `references/layout-guides/idle.png`; duo `pet_request.json` has `"subject_count": 2`.

- [ ] **Step 5: Update docs and commit**

Add to `AI.md`:

```markdown
## Layout Guides

Singleton layout guides match Hatch Pet. Duo layout guides divide each cell into A-left and B-right safe regions while preserving atlas slot dimensions.
```

Run:

```powershell
git -C C:\Github\PetGenesis add scripts/prepare_pet_run.py AI.md
git -C C:\Github\PetGenesis commit -m "feat: add duo layout guides"
```

Expected: commit succeeds.

---

### Task 6: Implement Subject-Aware Extraction Defaults

**Files:**
- Modify: `C:/Github/PetGenesis/scripts/extract_strip_frames.py`
- Modify: `C:/Github/PetGenesis/tests/test_extract_strip_frames_subjects.py`
- Modify: `C:/Github/PetGenesis/AI.md`

- [ ] **Step 1: Add extraction method resolver**

In `scripts/extract_strip_frames.py`, add:

```python
def resolve_extraction_method(method: str, subject_count: int) -> str:
    if method == "auto" and subject_count > 1:
        return "stable-slots"
    return method
```

- [ ] **Step 2: Add CLI `--subject-count`**

Add parser argument:

```python
    parser.add_argument("--subject-count", type=int, default=1)
```

Before extraction, compute:

```python
    method = resolve_extraction_method(args.method, args.subject_count)
```

Use `method` instead of `args.method` in extraction decisions.

- [ ] **Step 3: Record subject count in `frames-manifest.json`**

Where manifest rows are written, add row-level and top-level subject count:

```python
"subject_count": args.subject_count,
```

- [ ] **Step 4: Run extraction tests**

Run:

```powershell
python -m pytest tests/test_extract_strip_frames_subjects.py -q
```

Expected: 3 passed.

- [ ] **Step 5: Update docs and commit**

Add to `AI.md`:

```markdown
## Extraction

`extract_strip_frames.py --method auto` stays `auto` for singleton runs. For duo runs, `auto` resolves to `stable-slots` to avoid connected-component fusion when subjects touch.
```

Run:

```powershell
git -C C:\Github\PetGenesis add scripts/extract_strip_frames.py tests/test_extract_strip_frames_subjects.py AI.md
git -C C:\Github\PetGenesis commit -m "feat: default duo extraction to stable slots"
```

Expected: commit succeeds.

---

### Task 7: Implement Duo Frame Inspection

**Files:**
- Modify: `C:/Github/PetGenesis/scripts/inspect_frames.py`
- Modify: `C:/Github/PetGenesis/tests/test_inspect_frames_subjects.py`
- Modify: `C:/Github/PetGenesis/AI.md`

- [ ] **Step 1: Add region helper**

In `scripts/inspect_frames.py`, add:

```python
def region_alpha_count(image: Image.Image, box: tuple[int, int, int, int]) -> int:
    return alpha_nonzero_count(image.crop(box).getchannel("A"))
```

- [ ] **Step 2: Add duo expected-subject inspection**

Add:

```python
def inspect_expected_subjects(frames: list[Image.Image], min_region_pixels: int) -> dict[str, object]:
    subjects = {
        "a": {"region": [0, 0, CELL_WIDTH // 2, CELL_HEIGHT], "present_frames": 0, "missing_frames": []},
        "b": {"region": [CELL_WIDTH // 2, 0, CELL_WIDTH, CELL_HEIGHT], "present_frames": 0, "missing_frames": []},
    }
    errors: list[str] = []
    for index, frame in enumerate(frames):
        for subject_id, info in subjects.items():
            count = region_alpha_count(frame, tuple(info["region"]))
            if count >= min_region_pixels:
                info["present_frames"] += 1
            else:
                info["missing_frames"].append(index)
                errors.append(f"subject {subject_id} missing or too sparse in frame {index:02d}")
    return {"ok": not errors, "subjects": subjects, "errors": errors}
```

- [ ] **Step 3: Preserve opened frames for subject checks**

In `inspect_state`, store loaded frame images in a list:

```python
    loaded_frames: list[Image.Image] = []
```

Append a copy after converting:

```python
        loaded_frames.append(frame.copy())
```

After area checks, add:

```python
    expected_subjects = None
    subject_count = int(manifest_row.get("subject_count", getattr(args, "subject_count", 1)) or 1)
    if subject_count == 2:
        expected_subjects = inspect_expected_subjects(loaded_frames[:expected_count], args.min_subject_region_pixels)
        row_errors.extend(expected_subjects["errors"])
```

Include `"expected_subjects": expected_subjects` in the return dict only when not `None`.

- [ ] **Step 4: Add CLI threshold**

Add parser argument:

```python
    parser.add_argument("--min-subject-region-pixels", type=int, default=80)
    parser.add_argument("--subject-count", type=int, default=1)
```

- [ ] **Step 5: Run inspection tests**

Run:

```powershell
python -m pytest tests/test_inspect_frames_subjects.py -q
```

Expected: 2 passed.

- [ ] **Step 6: Update docs and commit**

Add to `AI.md`:

```markdown
## Inspection

Duo inspection is an approximate pre-filter. It checks left and right region occupancy for each frame and writes `expected_subjects`; visual QA remains required for subtle identity drift.
```

Run:

```powershell
git -C C:\Github\PetGenesis add scripts/inspect_frames.py tests/test_inspect_frames_subjects.py AI.md
git -C C:\Github\PetGenesis commit -m "feat: inspect duo subject presence"
```

Expected: commit succeeds.

---

### Task 8: Rewrite Skill Instructions And References

**Files:**
- Modify: `C:/Github/PetGenesis/SKILL.md`
- Modify: `C:/Github/PetGenesis/agents/openai.yaml`
- Modify: `C:/Github/PetGenesis/references/codex-pet-contract.md`
- Modify: `C:/Github/PetGenesis/references/animation-rows.md`
- Modify: `C:/Github/PetGenesis/references/qa-rubric.md`
- Modify: `C:/Github/PetGenesis/Readme.md`
- Modify: `C:/Github/PetGenesis/AI.md`

- [ ] **Step 1: Update `SKILL.md` frontmatter**

Set:

```yaml
---
name: petgenesis
description: Create, repair, validate, visually QA, and package Codex-compatible animated pets from one subject or a two-subject duo using source material, generated images, brand cues, or visual references. Use when a user wants a solo Codex pet, a paired duo pet, two characters preserved together in every frame, or a full 8x9 animated pet atlas with transparent unused cells, QA contact sheets, motion previews, and pet.json packaging. This skill composes the installed $imagegen system skill for visual generation and uses bundled scripts for deterministic spritesheet assembly.
---
```

- [ ] **Step 2: Update workflow sections**

In `SKILL.md`, replace Hatch Pet singleton-only workflow language with:

```markdown
PetGenesis supports `subject_count` 1 or 2.

- Use `--subject-count 1` for normal solo pets. Preserve the Hatch Pet workflow: one canonical base, then row strips.
- Use `--subject-count 2` for duo pets. Generate one canonical base per subject, then one composite staging reference, then row strips grounded on both bases and the composition guide.
- Reject requests for more than two subjects. Explain that the `192x208` cell cannot preserve readable full-body animation for three or more subjects.
```

- [ ] **Step 3: Update reference docs**

Add a "PetGenesis subject counts" section to `references/codex-pet-contract.md`:

```markdown
## PetGenesis Subject Counts

The atlas geometry is unchanged for solo and duo pets. Subject count changes only the pixels inside each used `192x208` cell and the generation workflow that creates those pixels.
```

Add a "Duo interaction defaults" section to `references/animation-rows.md` with the row guidance from the design spec.

Add a "Duo QA" section to `references/qa-rubric.md`:

```markdown
## Duo QA

- Both subjects appear in every used cell of every row.
- Subject A remains left and Subject B remains right unless the user explicitly approved another composition.
- Each subject preserves its own silhouette, face, palette, material, markings, and props.
- Subjects may touch, but they must not fuse into one unreadable silhouette.
- Duo `running-left` must be generated, not mirrored from `running-right`.
```

- [ ] **Step 4: Update `agents/openai.yaml`**

Use display metadata:

```yaml
display_name: PetGenesis
short_description: Create solo or duo Codex pets with deterministic atlas packaging.
default_prompt: Create a Codex pet from my source material. Ask whether it should be one subject or a two-subject duo if that is not clear.
```

- [ ] **Step 5: Update `Readme.md` and `AI.md`**

Ensure `Readme.md` includes:

```markdown
## Subject Counts

- `--subject-count 1`: solo pet, Hatch Pet-compatible workflow.
- `--subject-count 2`: duo pet, two canonical bases plus a composite staging reference.
- `--subject-count 3` or higher: rejected.
```

Ensure `AI.md` includes:

```markdown
Do not remove singleton behavior while improving duo behavior. Any prompt, job, extraction, or QA change must state whether it applies to singleton, duo, or both.
```

- [ ] **Step 6: Commit instructions and references**

Run:

```powershell
git -C C:\Github\PetGenesis add SKILL.md agents/openai.yaml references AI.md Readme.md
git -C C:\Github\PetGenesis commit -m "docs: describe PetGenesis solo and duo workflows"
```

Expected: commit succeeds.

---

### Task 9: Run Smoke Tests And Skill Validation

**Files:**
- Modify only if smoke tests reveal a specific defect in prior tasks.

- [ ] **Step 1: Run the Python test suite**

Run:

```powershell
python -m pytest tests -q
```

Expected: all tests pass.

- [ ] **Step 2: Run singleton prepare smoke test**

Run:

```powershell
python scripts/prepare_pet_run.py --pet-name Solo Smoke --subject-count 1 --pet-notes "round blue helper" --output-dir C:\tmp\petgenesis-solo-smoke --force
```

Expected:

- `C:\tmp\petgenesis-solo-smoke\pet_request.json` contains `"subject_count": 1`
- `C:\tmp\petgenesis-solo-smoke\imagegen-jobs.json` contains job `base`
- `imagegen-jobs.json` does not contain `base-a`, `base-b`, or `composite-staging`

- [ ] **Step 3: Run duo prepare smoke test**

Run:

```powershell
python scripts/prepare_pet_run.py --pet-name Duo Smoke --subject-count 2 --subject-name Bolt --subject-name Spark --subject-notes "blue bolt character" --subject-notes "yellow spark robot" --output-dir C:\tmp\petgenesis-duo-smoke --force
```

Expected:

- `C:\tmp\petgenesis-duo-smoke\pet_request.json` contains `"subject_count": 2`
- `imagegen-jobs.json` contains `base-a`, `base-b`, and `composite-staging`
- `running-left` has `"may_derive": false`

- [ ] **Step 4: Run skill validation**

Run:

```powershell
python C:\Users\zeidd\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Github\PetGenesis
```

Expected: validation succeeds. If the script path differs, locate it under `C:\Users\zeidd\.codex\skills\.system\skill-creator\scripts` and run the same validator against `C:\Github\PetGenesis`.

- [ ] **Step 5: Commit validation fixes if needed**

If files changed:

```powershell
git -C C:\Github\PetGenesis add .
git -C C:\Github\PetGenesis commit -m "fix: pass PetGenesis smoke validation"
```

Expected: commit succeeds or no changes exist.

---

### Task 10: Final Review

**Files:**
- No planned edits unless review finds an issue.

- [ ] **Step 1: Check repo status**

Run:

```powershell
git -C C:\Github\PetGenesis status --short
```

Expected: no output.

- [ ] **Step 2: Review subject-count evidence**

Run:

```powershell
rg -n "subject_count|subject-count|composite-staging|stable-slots|expected_subjects|running-left" C:\Github\PetGenesis
```

Expected: matches show singleton and duo branching in scripts, docs, and tests.

- [ ] **Step 3: Summarize completed build**

Report:

- latest commit hash
- tests run
- singleton smoke result
- duo smoke result
- skill validation result
