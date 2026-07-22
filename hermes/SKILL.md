---
name: petgenesis
description: Use when creating, repairing, validating, or packaging an OpenPets-compatible animated pet in Hermes from text, images, brand cues, or a one/two-character concept. Runs an approval-gated `image_generate` workflow and reuses PetGenesis's deterministic atlas, QA, and packaging scripts. Do not use for general illustrations, logos, scenes, or pets with more than two subjects.
version: 1.0.0
author: PetGenesis contributors
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [openpets, pets, image-generation, spritesheets, animation]
    related_skills: []
---

# PetGenesis for Hermes and OpenPets

## Overview

Create solo or two-subject animated pets with Hermes, then validate and install them in OpenPets. The generated package remains the established Codex/OpenPets format: `pet.json` plus a transparent `spritesheet.webp` using an 8-column by 9-row atlas of `192x208` cells.

This adapter changes only agent orchestration and installation:

- Hermes generates visual candidates with `image_generate`.
- PetGenesis's shared scripts still prepare prompts, track approval, extract frames, compose and validate the atlas, render QA media, and package the result.
- OpenPets installs the verified package through its CLI and running desktop app.

The shared references bundled beside this skill are the source of truth for atlas geometry, visual standards, repair policy, and deterministic commands. This file overrides any legacy runtime wording in those references: in Hermes, use `image_generate`, never Codex `$imagegen`; for final delivery, follow the OpenPets procedure below.

## When to Use

Use this skill when the user asks Hermes to:

- create a new OpenPets pet from a description or reference images;
- preserve one subject or a two-character duo across all animation states;
- repair a PetGenesis base, row, atlas, or package;
- resume an interrupted PetGenesis run;
- validate, package, or install an existing PetGenesis run in OpenPets.

Do not use it for a static mascot image, a general animation sheet with another layout, more than two subjects, or installing an existing gallery pet that does not need PetGenesis.

## Runtime Preflight

Before preparing a run, verify:

1. `hermes doctor` reports `✓ image_gen`. If it does not, configure image generation through `hermes tools` or a supported provider and start a fresh session.
2. Python 3 and Pillow with WebP support are available:

   ```bash
   python --version
   python -c "from PIL import Image, features; print(Image.__version__, features.check('webp'))"
   ```

3. The current project/workspace is writable.
4. `ffmpeg` and `ffprobe` are available only when video references are used.
5. The OpenPets desktop app is running before final installation.

Do not instruct the user to set `image_gen.provider` or `image_gen.model` when Hermes reports that those keys are unrecognized. Saving an unknown key does not prove that the active plugin reads it. Configure image generation through `hermes tools` or `hermes setup`; when `hermes doctor` reports `✓ image_gen`, use the available `image_generate` tool without adding repository-specific provider settings.

## Shared References

Load only the reference needed for the current phase:

- `references/animation-rows.md`: row order, frame counts, and state meanings.
- `references/visual-standards.md`: transparency, effects, motion, and sprite-safe rules.
- `references/brand-discovery.md`: compact brand research handoff.
- `references/runbook.md`: exact prepare, resume, processing, packaging, verification, export, and cleanup commands.
- `references/visual-workers.md`: optional sequential worker boundaries and prompts.
- `references/repair-policy.md`: retry budget and smallest-scope repair rules.
- `references/qa-rubric.md`: final visual acceptance checks.
- `references/codex-pet-contract.md`: shared Codex/OpenPets package and atlas contract.

Hermes expands `${HERMES_SKILL_DIR}` to the installed folder containing this `SKILL.md`. At the start of terminal work, initialize the runbook variable once:

```bash
SKILL_DIR="${HERMES_SKILL_DIR}"
```

Use that value whenever a shared runbook command refers to `$SKILL_DIR`.

When preparing a Hermes run, append `--generation-skill image_generate` to the shared `prepare_pet_run.py` command. This records the correct Hermes tool in `pet_request.json`, `imagegen-jobs.json`, every visual job, and the running-left fallback. The root Codex workflow omits the flag and retains its `$imagegen` default.

## Subject Counts and Animation Modes

PetGenesis supports exactly one or two subjects:

- Infer `--subject-count 1` for a solo pet.
- Infer `--subject-count 2` for a duo, pair, or two named characters. Subject A stays left and Subject B stays right by default.
- Ask one concise question only when the source could reasonably mean either one or two subjects.
- Reject three or more subjects because a `192x208` cell cannot preserve readable full-body animation for them.

Default to `--animation-mode generated`. Use `micro` or `hybrid` only when the user explicitly accepts lower animation variety to reduce generation usage. All modes still require deterministic extraction, validation, contact-sheet review, preview-GIF review, package preflight, and package verification.

## Hermes Image Generation

Use Hermes's `image_generate` tool for every normal visual job. Do not call an image API, external image CLI, local raster generator, or Codex `$imagegen` from this adapter.

For each job returned by `scripts/petgen_jobs.py next`:

1. Read its prompt file and listed input-image roles from `imagegen-jobs.json`.
2. Use the job prompt as the authoritative visual specification.
3. For a text-only base, call `image_generate` without a source image. For a grounded job, pass the canonical base or most important source as `image_url` and the remaining canonical references and layout guide as `reference_image_urls`.
4. Use `aspect_ratio="landscape"` for horizontal row strips. Select the aspect ratio that best preserves the full-body composition for base/composite jobs.
5. Treat the path returned by `image_generate` as the candidate source. Verify that the file exists before recording it.
6. Record the exact selected candidate with `petgen_jobs.py selected`, show a compact preview, and wait for user approval before approving or generating the next normal job.

Every generated row must be grounded on its listed canonical image inputs and layout guide. Do not rely on conversation memory or a text description of an image. Reject candidates that copy guide pixels, change identity, crop poses, use a non-chroma background, add detached effects, or violate the row contract.

### Optional workers

Generate in the parent session by default. Use `delegate_task` only when the user authorizes worker/subagent mode. Keep at most one visual worker active at a time unless the user explicitly requests parallel generation. Pass absolute prompt and image paths, require only a selected file path plus one QA sentence, and verify the returned file yourself before updating the manifest.

Workers cannot ask the user for approval. The parent always owns approval gates, manifest changes, deterministic processing, package installation, and final reporting.

## Run Folder and State

Keep all artifacts in one dedicated run folder. By default, `prepare_pet_run.py` creates:

```text
<current workspace>/petgenesis-pets/<pet-id>-<utc-timestamp>/
```

Do not place prompts, generated candidates, decoded rows, frames, or QA files loose in the project root. The image path returned by `image_generate` is authoritative; do not assume a provider-specific cache location and do not delete shared Hermes cache files unless the user explicitly asks for cleanup.

Create a visible four-step plan for a normal run:

1. Getting the pet ready.
2. Imagining the pet's main look.
3. Picturing the pet's poses.
4. Hatching and installing the pet.

Mark a step complete only when its actual file, approval, or installation evidence exists.

## Approval-Gated Workflow

Read `references/runbook.md` before operating on a real run. Follow this order:

1. Prepare or resume the dedicated run with `prepare_pet_run.py` or `resume_pet_run.py`.
2. Ask `petgen_jobs.py next` for the next ready job.
3. Generate that one job with `image_generate`, attaching every listed input image.
4. Record it with `petgen_jobs.py selected`; approve, reject, or mark repair only after user or visual QA review.
5. After base approval, maintain the identity ledger and refresh row prompts before generating rows.
6. For singleton runs, derive `running-left` from approved `running-right` only when mirroring is visually safe. Never mirror duo `running-left`.
7. After every required job is approved or derived, run extraction, frame inspection, identity-drift comparison, atlas composition, validation, contact-sheet generation, and GIF preview rendering.
8. Inspect the final contact sheet and every preview GIF. Repair the smallest failing scope; do not package unresolved defects.
9. Package to a user-chosen project folder, verify it, and install it in OpenPets.
10. Clean intermediate files only after final QA passes and the user does not need debugging artifacts.

Never bypass package preflight unless the user explicitly accepts an unvalidated result. Never install a package that has not passed `verify_pet_package.py --strict-clean` unless the user explicitly requests that exact exception.

## Package for OpenPets

PetGenesis's project destination already produces the OpenPets-compatible two-file folder. Package it with the shared script:

```bash
python "$SKILL_DIR/scripts/package_pet.py" \
  --run-dir "$RUN_DIR" \
  --destination project \
  --project-dir /absolute/path/to/openpets-packages
```

The command's JSON output reports the exact `package_dir`. Verify that folder before installation:

```bash
python "$SKILL_DIR/scripts/verify_pet_package.py" \
  /absolute/path/to/openpets-packages/<pet-id> \
  --strict-clean
```

Completion criterion: the package folder contains only `pet.json` and `spritesheet.webp`, its manifest uses a relative `spritesheetPath`, and strict verification succeeds.

## Install in OpenPets

Prefer a globally installed `openpets` command when present. Otherwise, with the user's permission to let npm fetch/cache the CLI, replace `openpets` in the commands below with `npx -y @open-pets/cli@latest`.

Check the running app first:

```bash
openpets status
```

Require `ok: true` and `appRunning: true`. Then install and confirm discovery:

```bash
openpets install --from-folder /absolute/path/to/openpets-packages/<pet-id>
openpets pets
openpets status
```

Completion criterion: installation succeeds and `openpets pets` lists the expected pet ID. Ask the user to choose it as the default pet in OpenPets Control Center. A Hermes OpenPets MCP server without a fixed `--pet` argument follows that desktop default.

If the OpenPets MCP server is not configured in Hermes, the user may add it once with:

```bash
hermes mcp add openpets --command npx --args -y @open-pets/mcp@latest
hermes mcp test openpets
```

MCP changes require `/reload-mcp` or a fresh session. Do not add or replace the MCP configuration when `hermes mcp list` already shows an enabled `openpets` server.

## Repair Rules

Read `references/repair-policy.md` before repairs. Regenerate the smallest complete visual scope that owns the defect. Do not paint over anatomy, identity, face, hand, prop, or continuity errors. Leave failed jobs as `repair_needed` until a new candidate passes review.

Treat all of these as blockers: identity/style drift, unresolved repair notes, failed deterministic review, missing previews, wrong row semantics, chroma leakage inside the subject, copied layout guides, detached effects, cropped poses, wrong facing, nontransparent unused cells, or package verification failure.

## Verification Checklist

Before reporting completion, verify all of the following:

- [ ] `hermes doctor` exposed `image_gen` before visual generation.
- [ ] Subject count and animation mode match the user's request.
- [ ] Every normal generated row used its canonical images and layout guide.
- [ ] Every required job is `approved` or explicitly `derived`.
- [ ] `qa/review.json` and `final/validation.json` have `ok: true`.
- [ ] Identity-drift QA passed or the user explicitly accepted each documented exception.
- [ ] Contact sheet and all nine animation previews were visually reviewed.
- [ ] `verify_pet_package.py --strict-clean` passed on the exact package folder.
- [ ] OpenPets reported a successful installation and listed the expected pet ID.
- [ ] Final response includes the run folder, package folder, installed pet ID, and any accepted exceptions.
