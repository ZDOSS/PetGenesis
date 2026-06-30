# PetGenesis Design

## Status

Approved for implementation planning on 2026-06-30.

PetGenesis is a fork of OpenAI's curated `hatch-pet` skill. It keeps the Codex custom pet atlas contract and deterministic packaging pipeline, but changes the generation workflow so a user can create a two-subject animated Codex pet from one or more source materials with minimal additional direction.

## Goal

Build a separate skill named `petgenesis` in `C:\Github\PetGenesis` that creates Codex-compatible animated pets where both subjects appear together in every used animation frame.

The user should only need to provide:

- one or more source materials, such as images, a brand cue, or character art
- confirmation that the target is a two-subject pet
- optional short notes describing which two characters should be captured

If subject notes are missing, the skill should infer likely subjects from the source material and proceed only when it can do that safely. If the source material does not clearly contain or imply two subjects, the skill should ask one concise clarification before generation.

## Non-Goals

PetGenesis v1 will not attempt general `N`-subject support. The `192x208` cell is too small for three or more readable whole-body animated subjects. The CLI and skill workflow should reject explicit `--subject-count` values other than `2`. When the user asks for a duo or pair without passing a numeric flag, the skill should infer exactly two subjects.

PetGenesis will not change the Codex app webview contract. Multi-subject support exists entirely inside generated sprite pixels and metadata used by the skill pipeline.

PetGenesis will not replace the original curated `hatch-pet` skill. It should be a separate fork with trigger language focused on "duo", "pair", "two subjects", and "multi-character pet" requests so it does not cannibalize the singleton pet workflow.

## Architecture

PetGenesis will reuse the upstream Hatch Pet structure:

- `SKILL.md` for workflow, delegation, and acceptance criteria
- `scripts/prepare_pet_run.py` for run folder creation, prompts, layout guides, and `imagegen-jobs.json`
- `scripts/extract_strip_frames.py` for converting generated strips into cells
- `scripts/inspect_frames.py` for deterministic pre-QA
- `scripts/compose_atlas.py`, `validate_atlas.py`, `make_contact_sheet.py`, and `render_animation_previews.py` for atlas assembly and review artifacts
- `references/codex-pet-contract.md`, `animation-rows.md`, and `qa-rubric.md` for contract and QA instructions
- `agents/openai.yaml` for skill UI metadata

The major rewrite is the generation graph. Instead of one canonical base pet followed by row strips, PetGenesis creates:

1. canonical base image for subject A
2. canonical base image for subject B
3. one composite staging reference showing A left and B right together in a single cell
4. all nine row-strip jobs grounded on both canonical bases, the composite staging reference, and the deterministic layout guide

The final atlas shape remains unchanged: `1536x1872`, 8 columns, 9 rows, `192x208` cells, transparent background, and transparent unused cells.

## Workflow

### Input Preparation

`prepare_pet_run.py` should accept exactly two subjects.

Planned arguments:

- `--subject-count 2`
- repeatable `--subject-name`
- repeatable `--subject-notes`
- `--composition left-right`, with left-right as the v1 default and primary supported layout
- `--interaction-mode both-act` by default, with selected states allowed to use one-acts-other-reacts language in prompts

The manifest should preserve source material and subject interpretation:

```json
{
  "subject_count": 2,
  "subjects": [
    {
      "id": "a",
      "name": "Subject A",
      "notes": "short identity description",
      "canonical_base_path": "references/canonical-base-a.png"
    },
    {
      "id": "b",
      "name": "Subject B",
      "notes": "short identity description",
      "canonical_base_path": "references/canonical-base-b.png"
    }
  ],
  "composition": "left-right",
  "interaction_mode": "both-act"
}
```

### Image Generation

All visual generation continues to go through `$imagegen`; PetGenesis should not call image APIs directly.

Base jobs generate one subject at a time. Each base job should be a clean, centered, single-subject reference on a removable chroma background.

The composite staging job uses the selected subject bases as inputs and generates one image of both subjects together. This image is not an animation row. It exists to establish relative scale, left/right position, gap, baseline, and the visual relationship between the subjects.

Each row-strip prompt must require:

- both subjects present in every frame
- subject A remains on the left and subject B remains on the right
- each subject's identity, palette, silhouette, material, face, props, and markings stay independently consistent with its own canonical base
- subjects may interact or touch, but must not fuse into a single unreadable silhouette
- no labels, text, frame numbers, scenery, shadows, detached effects, guide marks, or extra sprites

### Running Left

The upstream Hatch Pet workflow may derive `running-left` by mirroring `running-right` when visually safe. PetGenesis should not mirror `running-left` for duo runs. Mirroring would swap the staged left/right subjects and break the intended composition.

PetGenesis should always generate `running-left` as a normal grounded `$imagegen` row job. It may still use `running-right` as a gait reference, but the output must preserve subject A left and subject B right.

## Deterministic Processing

`compose_atlas.py`, `validate_atlas.py`, `make_contact_sheet.py`, and `render_animation_previews.py` can remain mostly unchanged because they operate on atlas geometry rather than subject count.

`extract_strip_frames.py` should default duo runs to `stable-slots`. Component extraction is risky because interacting subjects can touch and become one connected component. Slot-based extraction is less clever but more predictable for duo rows.

`inspect_frames.py` should add approximate two-subject checks:

- partition each cell into left and right staging regions
- compare each region against the expected canonical base palette and occupied area
- flag missing, clipped, swapped, empty, or obviously drifted subjects
- write an `expected_subjects` block to `qa/review.json`

This deterministic QA is a pre-filter, not a complete identity verifier. The final contact sheet and GIF previews remain authoritative for subtle identity drift.

## Interaction Defaults

The default mode is `both-act`, with row-specific wording:

- `idle`: both idle with subtle breathing or blinking
- `running-right`: both travel right while preserving A-left/B-right staging
- `running-left`: both travel left while preserving A-left/B-right staging
- `waving`: both wave, or A waves while B reacts when visually better
- `jumping`: both jump with slight stagger, or one jumps while the other reacts when visually better
- `failed`: both deflated, or one deflated while the other comforts when visually better
- `waiting`: both expectant
- `running`: both focused on active task work, not foot-running
- `review`: both inspecting or thinking

## Documentation

Because this repository is intended for future AI agents as well as users, meaningful code changes must update:

- `AI.md` with implementation logic, pipeline decisions, and any non-obvious behavior
- `Readme.md` with user-facing behavior, setup, usage, and feature status while preserving the author's voice once one exists

The first implementation pass should create both files if they are not present.

## Acceptance Criteria

PetGenesis is ready when:

- the skill installs or runs as `petgenesis`
- the skill trigger language clearly targets duo/two-subject pet generation
- the workflow requires exactly two subjects for v1
- `prepare_pet_run.py` creates two canonical base jobs, one composite staging job, and all row-strip jobs with both identity references attached
- every row prompt requires both subjects in every frame with stable A-left/B-right staging
- `running-left` is generated, not mirrored
- duo extraction defaults to `stable-slots`
- `qa/review.json` includes two-subject checks
- the final atlas still passes the unchanged Codex pet contract
- final review artifacts include contact sheet and GIF previews suitable for visual QA
- `AI.md` and `Readme.md` are current with the implemented behavior

## Risks

The highest risk is model-side identity drift across roughly fifty used frames. Per-subject canonical bases and the composite staging reference reduce this risk but do not eliminate it.

The second risk is cramped staging. This is why v1 is intentionally two-subject only and uses compact/chibi whole-body staging.

The third risk is false confidence from deterministic QA. Region and palette checks can catch gross failures but cannot prove that subtle details stayed correct. Visual QA remains required.

## Recommended Build Order

1. Import the upstream Hatch Pet skill into `C:\Github\PetGenesis`.
2. Rename metadata and skill trigger language to `petgenesis`.
3. Update `prepare_pet_run.py` for two-subject manifests, prompts, layout guides, and job graph.
4. Add composite staging generation.
5. Disable mirror derivation for duo `running-left`.
6. Change extraction defaults for duo runs to `stable-slots`.
7. Extend deterministic inspection with `expected_subjects`.
8. Rewrite `SKILL.md` and `references/qa-rubric.md` around the duo workflow.
9. Create or update `AI.md` and `Readme.md`.
10. Run static validation and script-level smoke tests before any real `$imagegen` run.
