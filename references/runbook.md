# PetGenesis Runbook

Read this file when preparing, resuming, processing, packaging, verifying, exporting, or cleaning up a real PetGenesis run. `SKILL.md` owns the high-level policy; this runbook keeps the command recipes.

## Contents

- Prepare or resume a run
- Select, approve, reject, or repair visual jobs
- Row-scoped preview checks
- Singleton `running-left` derivation
- Optional micro and hybrid row derivation
- Deterministic processing
- Packaging and cleanup
- Package verification and catalog export
- Identity ledger helper

## Prepare A Run

Set `SKILL_DIR` to the directory containing `SKILL.md`.

```bash
SKILL_DIR=/absolute/path/to/the/directory/containing/this/SKILL.md
python "$SKILL_DIR/scripts/prepare_pet_run.py" \
  --pet-name "<Name>" \
  --subject-count 1 \
  --animation-mode generated \
  --description "<one sentence>" \
  --reference /absolute/path/to/reference.png \
  --shared-reference /absolute/path/to/shared-reference.png \
  --subject-reference a:/absolute/path/to/subject-a-reference.png \
  --subject-a-reference /absolute/path/to/subject-a-reference.png \
  --subject-b-reference /absolute/path/to/subject-b-reference.png \
  --output-dir /absolute/path/to/dedicated/run-folder \
  --pet-notes "<stable pet description>" \
  --brand-discovery-file /absolute/path/to/brand-discovery.md \
  --brand-name "<optional researched brand name>" \
  --brand-brief "<optional compact researched brand cue sentence>" \
  --brand-source "https://example.com/source" \
  --style-preset auto \
  --style-notes "<optional freeform style notes>" \
  --force
```

All arguments above are optional except any flags needed to express user constraints. Use `--subject-count 1` for solo pets and `--subject-count 2` for duo pets. For text-only requests, pass the concept through `--pet-notes` and omit `--reference`; `prepare_pet_run.py` will infer a name, description, chroma key, and a dedicated output directory under `<current workspace>/petgenesis-pets/` as needed.

Use `--reference` or `--shared-reference` for images that apply to the whole pet concept. For duo pets, prefer subject-scoped references when the inputs depict different characters: pass `--subject-reference a:/absolute/path.png`, `--subject-reference b:/absolute/path.png`, or the convenience aliases `--subject-a-reference` and `--subject-b-reference`. Subject-scoped references are attached to the matching base job first; shared references are attached after them.

For brand-only requests, first read `brand-discovery.md`, save the markdown brief, then pass the brief path through `--brand-discovery-file`, `avatar_seed` through `--pet-notes`, `brand_name` through `--brand-name`, `brand_brief` through `--brand-brief`, and each source URL through repeated `--brand-source`.

Animation modes:

- `generated`: default production mode. Generates the base/composite and all semantic animation rows, except explicitly approved singleton `running-left` mirror derivation.
- `micro`: generates only the base/composite inputs, then derives all rows deterministically from the canonical source. Use only when the user accepts lower animation variety to save generation budget.
- `hybrid`: generates base/composite plus key rows (`idle`, `running-right`, `failed`) and derives the remaining rows. Use for a middle ground when the user accepts some lower-fidelity rows.

## Resume A Run

If continuing after an interruption, context reset, failed worker, or uncertain run state, inspect the run before doing anything else:

```bash
python "$SKILL_DIR/scripts/resume_pet_run.py" \
  --run-dir /absolute/path/to/run
```

If the exact run folder is unclear, discover recent runs from the current workspace first:

```bash
python "$SKILL_DIR/scripts/resume_pet_run.py" --list
python "$SKILL_DIR/scripts/resume_pet_run.py" --pet-id <pet-id>
```

Use `--root /absolute/path/to/petgenesis-pets` when the workspace root is not the current directory. With no `--run-dir`, the resume helper selects the newest discovered run, optionally filtered by `--pet-id`.

Follow `next_action.kind`: `generate_job`, `await_approval`, `repair_job`, `derive_micro_rows`, `run_processing`, `render_previews`, `package`, or `complete`. If `recover_missing_files`, `blocked`, or `blocked_dependencies` appears, resolve the listed missing files or dependency issue before generating more images.

`resume_pet_run.py` will not report a run as package-ready when expected preview GIFs are missing. Render previews before packaging.

## Job Controller

Ask for the next ready `$imagegen` jobs:

```bash
python "$SKILL_DIR/scripts/petgen_jobs.py" next \
  --run-dir /absolute/path/to/run
```

The generated manifest intentionally chains default visual jobs so `next` exposes one normal job at a time: singleton base before rows; duo Subject A before Subject B before composite staging; then row jobs in atlas order. In micro and hybrid modes, `next` exposes only the generated jobs required by that mode.

After a worker selects a generated output, copy and record it:

```bash
RUN_DIR=/absolute/path/to/run
JOB_ID=<job-id>
SOURCE=/absolute/path/to/generated-output.png
python "$SKILL_DIR/scripts/petgen_jobs.py" selected \
  --run-dir "$RUN_DIR" \
  --job-id "$JOB_ID" \
  --source "$SOURCE" \
  --qa-note "<one-sentence worker QA note>"
```

Approve, reject, or mark repair after the user or final visual QA decides:

```bash
python "$SKILL_DIR/scripts/petgen_jobs.py" approve --run-dir "$RUN_DIR" --job-id "$JOB_ID" --note "<approved by user or visual QA>"
python "$SKILL_DIR/scripts/petgen_jobs.py" reject --run-dir "$RUN_DIR" --job-id "$JOB_ID" --note "<why rejected>"
python "$SKILL_DIR/scripts/petgen_jobs.py" repair --run-dir "$RUN_DIR" --job-id "$JOB_ID" --note "<smallest repair needed>"
python "$SKILL_DIR/scripts/petgen_jobs.py" summary --run-dir "$RUN_DIR"
```

Approval is intentionally stricter than file existence. A job can be approved only from `selected`, `derived`, or `approved` status, and its materialized output and canonical copy must exist. Use `--force` only for an explicit manual override, and record the reason in `--note`. The deprecated `--allow-missing-output` flag behaves as an override but should not be used for new work.

## Row-Scoped Preview Checks

For row jobs, create a row-scoped extraction/inspection/preview when useful:

```bash
python "$SKILL_DIR/scripts/extract_strip_frames.py" \
  --decoded-dir "$RUN_DIR/decoded" \
  --output-dir "$RUN_DIR/frames" \
  --states "$JOB_ID" \
  --subject-count <1-or-2> \
  --method auto

STABLE_SLOT_FLAG=""
# For duo rows, use: STABLE_SLOT_FLAG="--allow-stable-slots"
python "$SKILL_DIR/scripts/inspect_frames.py" \
  --frames-root "$RUN_DIR/frames" \
  --json-out "$RUN_DIR/qa/review-$JOB_ID.json" \
  --states "$JOB_ID" \
  --require-components \
  $STABLE_SLOT_FLAG

python "$SKILL_DIR/scripts/render_animation_previews.py" \
  --frames-root "$RUN_DIR/frames" \
  --output-dir "$RUN_DIR/qa/previews" \
  --states "$JOB_ID"
```

## Singleton Running-Left Derivation

For singleton runs only, derive `running-left` only when it is visually safe:

```bash
python "$SKILL_DIR/scripts/derive_running_left_from_running_right.py" \
  --run-dir /absolute/path/to/run \
  --confirm-appropriate-mirror \
  --decision-note "<why mirroring preserves this pet's identity>"
```

That script mirrors each generated frame slot in place so the leftward row preserves the rightward row's temporal order. For duo runs, skip this step and generate `running-left` as a normal `$imagegen` row so Subject A stays left and Subject B stays right.

## Micro And Hybrid Row Derivation

Use this only when `pet_request.json` and `imagegen-jobs.json` were prepared with `--animation-mode micro` or `--animation-mode hybrid`, or when the user explicitly accepts converting a run to that lower-fidelity path.

```bash
python "$SKILL_DIR/scripts/derive_micro_animation_rows.py" \
  --run-dir "$RUN_DIR" \
  --source references/canonical-base.png \
  --subject-count 1
```

For duo runs, the default source is the composite staging reference:

```bash
python "$SKILL_DIR/scripts/derive_micro_animation_rows.py" \
  --run-dir "$RUN_DIR" \
  --source references/composition-guide.png \
  --subject-count 2
```

`resume_pet_run.py` reports `next_action.kind = "derive_micro_rows"` when derived rows are missing and the run uses `micro` or `hybrid`. The derivation helper writes row strips under `decoded/` and records `row-strip-derived` jobs as `derived`. In `hybrid` mode it preserves already generated key rows unless `--overwrite` is passed.

## Deterministic Processing

When all required jobs are approved or derived, run the image-processing scripts directly:

```bash
RUN_DIR=/absolute/path/to/run
mkdir -p "$RUN_DIR/final" "$RUN_DIR/qa"

python "$SKILL_DIR/scripts/extract_strip_frames.py" \
  --decoded-dir "$RUN_DIR/decoded" \
  --output-dir "$RUN_DIR/frames" \
  --states all \
  --subject-count <1-or-2> \
  --method auto

STABLE_SLOT_FLAG=""
# For duo runs, use: STABLE_SLOT_FLAG="--allow-stable-slots"
python "$SKILL_DIR/scripts/inspect_frames.py" \
  --frames-root "$RUN_DIR/frames" \
  --json-out "$RUN_DIR/qa/review.json" \
  --require-components \
  $STABLE_SLOT_FLAG

python "$SKILL_DIR/scripts/compose_atlas.py" \
  --frames-root "$RUN_DIR/frames" \
  --output "$RUN_DIR/final/spritesheet.png" \
  --webp-output "$RUN_DIR/final/spritesheet.webp"

python "$SKILL_DIR/scripts/validate_atlas.py" \
  "$RUN_DIR/final/spritesheet.webp" \
  --json-out "$RUN_DIR/final/validation.json"

python "$SKILL_DIR/scripts/make_contact_sheet.py" \
  "$RUN_DIR/final/spritesheet.webp" \
  --output "$RUN_DIR/qa/contact-sheet.png"

python "$SKILL_DIR/scripts/render_animation_previews.py" \
  --frames-root "$RUN_DIR/frames" \
  --output-dir "$RUN_DIR/qa/previews"
```

If preview GIFs show extraction-induced size popping and the original row strip had stable scale and placement, rerun extraction with row-stability mode and then rerun inspection, atlas composition, validation, contact sheet generation, and previews:

```bash
python "$SKILL_DIR/scripts/extract_strip_frames.py" \
  --decoded-dir "$RUN_DIR/decoded" \
  --output-dir "$RUN_DIR/frames" \
  --states all \
  --subject-count <1-or-2> \
  --method stable-slots

python "$SKILL_DIR/scripts/inspect_frames.py" \
  --frames-root "$RUN_DIR/frames" \
  --json-out "$RUN_DIR/qa/review.json" \
  --require-components \
  --allow-stable-slots
```

For singleton runs, use `stable-slots` as a deliberate QA-driven correction, not the default. For duo runs, `--method auto` resolves to `stable-slots` because touching subjects can fuse into one connected component. Duo inspection also performs a lightweight palette-region comparison when `references/identity-ledger.json` points to both canonical bases; treat palette-region swap messages as visual-review warnings, not automatic failures.

## Expected Output

```text
run/
  pet_request.json
  imagegen-jobs.json
  prompts/
  decoded/
  frames/frames-manifest.json
  final/spritesheet.webp
  final/validation.json
  qa/contact-sheet.png
  qa/previews/*.gif
  qa/review.json
  qa/run-summary.json
```

## Packaging

Before packaging, ask the user where the finished pet should be saved. The Codex custom-pet location is `${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/`; the user may also request a copy in a project folder or another destination.

Package to the Codex custom-pet location:

```bash
RUN_DIR=/absolute/path/to/run
python "$SKILL_DIR/scripts/package_pet.py" \
  --run-dir "$RUN_DIR" \
  --destination codex
```

Package to a user-chosen project folder:

```bash
python "$SKILL_DIR/scripts/package_pet.py" \
  --run-dir "$RUN_DIR" \
  --destination project \
  --project-dir /absolute/path/to/package-root
```

Package to both destinations with `--destination both --project-dir /absolute/path/to/package-root`. `package_pet.py` writes `pet.json`, copies `spritesheet.webp`, and updates `qa/run-summary.json`.

Packaging now runs a trust-boundary preflight. By default it requires `pet_request.json`, `final/spritesheet.webp`, `final/validation.json` with `ok: true`, `qa/review.json` with `ok: true`, `qa/contact-sheet.png`, every expected preview GIF, and an `imagegen-jobs.json` manifest whose jobs are all `approved` or `derived`. If intermediate manifests were intentionally cleaned after QA, pass `--allow-cleaned-run` and keep the remaining QA artifacts. Use `--allow-unvalidated` only when the user explicitly accepts an unvalidated package; the package summary will record warnings and `ok: false`.

## Package Verification

Verify a finished package from the install/runtime perspective:

```bash
python "$SKILL_DIR/scripts/verify_pet_package.py" \
  /absolute/path/to/package-folder \
  --strict-clean \
  --json-out /absolute/path/to/verification.json
```

The verifier checks `pet.json`, relative `spritesheetPath`, path containment, readable atlas dimensions, alpha capability, non-empty used frames, and optional strict-clean folder contents. It does not replace visual QA; it catches packaging and runtime-contract failures.

## Catalog Export

Export a clean public submission folder without prompts, references, debug frames, or QA internals:

```bash
python "$SKILL_DIR/scripts/export_catalog_submission.py" \
  --run-dir "$RUN_DIR" \
  --author-slug "<author-slug>" \
  --out-dir /absolute/path/to/export-root \
  --catalog generic
```

For an Awesome Codex Pet style layout, use:

```bash
python "$SKILL_DIR/scripts/export_catalog_submission.py" \
  --run-dir "$RUN_DIR" \
  --author-slug "<author-slug>" \
  --out-dir /absolute/path/to/export-root \
  --catalog awesome-codex-pet \
  --include-pets-root
```

The export creates `<pet-id>--<author-slug>/pet.json`, `spritesheet.webp`, and `submission.json`, then verifies the folder with `verify_pet_package.py --strict-clean`. It uses the same preflight as packaging unless `--allow-unvalidated` or `--allow-cleaned-run` is passed.

## Identity Ledger Helper

Use `petgen_identity.py` instead of hand-editing `references/identity-ledger.json`:

```bash
python "$SKILL_DIR/scripts/petgen_identity.py" show --run-dir "$RUN_DIR"
python "$SKILL_DIR/scripts/petgen_identity.py" add-detail --run-dir "$RUN_DIR" --subject a --detail "<detail>"
python "$SKILL_DIR/scripts/petgen_identity.py" add-side-detail --run-dir "$RUN_DIR" --subject a --detail "<side-dependent detail>"
python "$SKILL_DIR/scripts/petgen_identity.py" set-silhouette --run-dir "$RUN_DIR" --subject a --value "<silhouette contract>"
python "$SKILL_DIR/scripts/petgen_identity.py" set-face --run-dir "$RUN_DIR" --subject a --value "<face contract>"
python "$SKILL_DIR/scripts/petgen_identity.py" validate --run-dir "$RUN_DIR"
```

Solo runs accept `--subject a` or `--subject solo`; duo runs accept `a` and `b`. Unknown ledger fields are preserved.

## Cleanup

After final visual QA accepts the contact sheet and preview GIFs, remove intermediate run artifacts.

Keep `pet_request.json`, `final/spritesheet.webp`, `final/validation.json`, `qa/contact-sheet.png`, `qa/previews/`, `qa/review.json`, and `qa/run-summary.json`. Remove generated prompt files, layout guides, decoded row strips, extracted frames, `final/spritesheet.png`, and the imagegen job manifest only when `--allow-cleaned-run` will be used for any later package/export step. Skip cleanup when the user wants debug artifacts or the run still needs repair.
