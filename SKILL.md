---
name: petgenesis
description: Create Codex custom pet spritesheets from text, images, brand cues, or one/two character concepts. Use for solo or two-subject duo pet runs that need base art, animation row strips, QA previews, validation, and pet.json packaging. Do not use for general image art, logos, scenes, or pets with more than two subjects.
---

# PetGenesis

## Overview

Create a Codex-compatible animated pet from a concept, brand cue, company/prospect name, one or more reference images, or any combination of those inputs. This workflow keeps the deterministic Hatch Pet pipeline for atlas geometry, validation, visual QA, and packaging, while preserving one-subject pet generation and adding a two-subject duo workflow.

User-facing inputs are minimal. If the user omits a pet name, infer one from the concept, brand, company, or reference filenames; if that is not possible, choose a short friendly name. If the user omits a description, infer one from the concept or references. If the user omits reference images, generate the base pet from text first, then use that base as the canonical reference for every animation row.

## Detailed References

Load these first-level references only when entering the matching phase:

- `references/animation-rows.md`: atlas row/frame contract and state meanings.
- `references/visual-standards.md`: transparency, effects, and state-specific visual rules for generation and QA.
- `references/brand-discovery.md`: official-source brand research worker and compact handoff format.
- `references/runbook.md`: command recipes for prepare, resume, job control, processing, packaging, verification, export, and cleanup.
- `references/visual-workers.md`: lightweight worker responsibilities and exact worker prompts.
- `references/repair-policy.md`: repair taxonomy, retry budget, and defect-specific repair rules.
- `references/qa-rubric.md`: final contact-sheet, GIF, and atlas acceptance checks.
- `references/codex-pet-contract.md`: Codex custom-pet package contract.

## Requirements Preflight

Before preparing a run, verify the local environment has the required pieces. If something is missing, tell the user exactly what is missing and ask before installing software or switching workflows.

- Python 3 with Pillow and WebP support for deterministic sprite processing.
- `$imagegen` available for all visual generation.
- `ffmpeg`/`ffprobe` when the user provides video references or asks to sample motion from video.
- Write access to the current workspace/project root.
- Optional: `jq` when manually inspecting JSON from a shell. PetGenesis scripts own normal manifest and packaging updates.
- Optional: `pytest` when validating PetGenesis' bundled tests. In this ACL-restricted skill folder, run tests through `scripts/run_tests.py` so pytest does not write bytecode or cache files.

Useful checks:

```bash
python --version
python -c "from PIL import Image, features; print(Image.__version__, features.check('webp'))"
ffmpeg -version
ffprobe -version
```

If a user provides only still images, `ffmpeg` is not required for the pet run.

Validate bundled tests with this skill directory as `SKILL_DIR`:

```bash
python "$SKILL_DIR/scripts/run_tests.py"
```

Build a clean installable archive only when releasing or sharing the skill:

```bash
python "$SKILL_DIR/scripts/build_release.py"
```

The release archive uses `petgenesis/` as its top-level folder and excludes caches, virtual environments, `dist/`, `output/`, and development planning notes under `docs/superpowers/`.
By default, the archive is written to `./petgenesis-releases/petgenesis.zip` in the current workspace so installed skill folders do not need to be writable.

## Subject Counts

PetGenesis supports `subject_count` 1 or 2.

- Use `--subject-count 1` for normal solo pets. Preserve the Hatch Pet workflow: one canonical base, then row strips.
- Use `--subject-count 2` for duo pets. Generate one canonical base per subject, then one composite staging reference, then row strips grounded on both bases and the composition guide.
- Reject requests for more than two subjects. Explain that the `192x208` cell cannot preserve readable full-body animation for three or more subjects.
- If the user asks for a solo pet, infer `--subject-count 1`. If the user asks for a duo, pair, couple, or two characters, infer `--subject-count 2`. If the count is unclear and source material could plausibly contain one or two subjects, ask one concise clarification.

## Animation Modes

Default to `--animation-mode generated` for production-quality pets. This mode generates every semantic row through `$imagegen`, except explicitly approved singleton `running-left` mirror derivation.

Use `--animation-mode micro` or `--animation-mode hybrid` only when the user explicitly accepts a lower-fidelity, budget-saving path. `micro` derives all rows from the approved canonical source. `hybrid` generates key rows (`idle`, `running-right`, `failed`) and derives the remaining rows. These modes must still pass extraction, validation, contact-sheet review, preview-GIF review, package preflight, and package verification.

## Generation Delegation

Use `$imagegen` for all normal visual generation.

Before generating base art, row strips, or repair rows, load and follow the installed image generation skill:

```text
${CODEX_HOME:-$HOME/.codex}/skills/.system/imagegen/SKILL.md
```

Do not call the Image API, image CLI, or any other image-generation path directly. Let `$imagegen` choose its own built-in-first path and fallback rules. If `$imagegen` says a fallback requires confirmation, ask the user before continuing.

When invoking `$imagegen`, pass the generated pet prompt as the authoritative visual spec. Pet prompts should stay concise, state-specific, sprite-production oriented, and grounded in the listed input images. Keep longer policy and QA rules in this skill and the deterministic review scripts rather than expanding them into every image prompt. Do not wrap prompts in the generic `$imagegen` shared prompt schema.

Use this skill's scripts for deterministic image work only: preparing layout guides and prompts, recording selected and approved visual jobs, mirroring approved singleton `running-left`, deriving explicit micro/hybrid rows, extracting frames, validating rows, composing the final atlas, creating contact-sheet plus motion-preview QA media, packaging, verifying packages, and exporting clean catalog submissions. Duo `running-left` must be generated in `generated` mode, not mirrored, so Subject A stays left and Subject B stays right.

## Storage Controls

The built-in `$imagegen` path stores generated PNG bytes in the rollout that invokes it, even when it also writes a file under `${CODEX_HOME:-$HOME/.codex}/generated_images`. Deleting files later reduces filesystem use, but it does not shrink an already-written rollout. Keep image generation isolated and bounded:

- Use one lightweight generation worker per visual job. Do not batch multiple base/row jobs into the same worker.
- Default to one visual generation job at a time so the user can approve or stop before more image budget is spent. Only run multiple visual workers in parallel when the user explicitly asks for parallel generation.
- Workers must return only `selected_source=...` and `qa_note=...`; they must not include Markdown image previews, base64, or extra visual attachments in their final response.
- The parent must not open every generated PNG visually. Use worker QA for each job and inspect only the final contact sheet.
- After copying the selected generated output into `decoded/`, remove the selected original from `${CODEX_HOME:-$HOME/.codex}/generated_images` when it lives there, then remove its now-empty generation directory if possible.
- For storage-sensitive full runs, ask the user whether to use the `$imagegen` CLI fallback when available. That path requires local API credentials and explicit user confirmation, but it can avoid built-in image payloads being embedded in rollout events.

## Run Folder And Save Location

Keep all run artifacts inside one dedicated run folder. By default, `prepare_pet_run.py` creates that folder under the current workspace/project root:

```text
<current workspace>/petgenesis-pets/<pet-id>-<utc-timestamp>/
```

Do not create loose prompt, decoded, frame, QA, or final files directly in the project root. If the user supplies `--output-dir`, use a dedicated run folder path, not the root itself.

Before final packaging, ask where the finished pet should be saved. Offer these choices in plain language:

- Codex custom pet folder: `${CODEX_HOME:-$HOME/.codex}/pets/<pet-id>/` so Codex can load it.
- A user-chosen folder in the current project/workspace for easy browsing or sharing.
- Both locations.

Never hard-code machine-specific folders. Resolve locations from the active workspace, `CODEX_HOME`, `$HOME`, or the user-provided destination.

## Brand Discovery

For brand/product/company/prospect requests without a concrete avatar description or reference image, read `references/brand-discovery.md` before preparing the run. Run the discovery worker, save the markdown brief, and pass only its compact handoff fields to `prepare_pet_run.py`. Skip discovery when the user already provides concrete mascot art, avatar direction, or reference images unless they explicitly ask for research.

For a singleton pet run in `generated` mode, expect up to 10 visual generation jobs: 1 base pet plus 9 row-strip jobs. For a duo pet run in `generated` mode, expect up to 12 visual generation jobs: 2 base subjects, 1 composite staging reference, and 9 row-strip jobs. The Codex app contract currently uses all 9 states: `idle`, `running-right`, `running-left`, `waving`, `jumping`, `failed`, `waiting`, `running`, and `review`. The default deterministic visual derivation is singleton `running-left`, which may be produced by mirroring `running-right` only after `running-right` has been generated, visually inspected, and explicitly approved as safe to mirror. Duo `running-left` is always generated as a normal grounded `$imagegen` row in `generated` mode. Micro and hybrid modes are explicit lower-fidelity exceptions described above.

After selecting a visual output, the parent agent records it with `scripts/petgen_jobs.py selected`, which copies that exact image into the job's output path and moves the job to `selected`/`awaiting_approval`. After the user approves it, run `scripts/petgen_jobs.py approve`. Do not treat a selected image as approved just because it was copied into the run. Do not write ad hoc helper scripts that populate row outputs. The only row-output creation outside `$imagegen` must use this skill's bundled, explicitly gated derivation scripts.

Only the base job may be prompt-only. Every row-strip job generated through `$imagegen` must use the input images listed in `imagegen-jobs.json`, including the canonical base reference created after the selected base output is copied. Treat any row generation without attached grounding images as invalid.

For built-in `$imagegen` paths that rely on conversation-visible images rather than explicit file parameters, load the row's canonical base, layout guide, and any critical detail references in the same worker context immediately before generation, then identify each visible image by role in the prompt. Do not rely on "the most recently shown image", memory of earlier previews, or text-only descriptions as row grounding. If the selected `$imagegen` path cannot make the required row inputs visible to the generation job, stop and switch to a supported grounded workflow instead of producing an ungrounded row.

## Pet-Safe Styles

Default style is `auto`: infer the pet's style from the user's prompt and references, then preserve that style across every row. If the user names a style, honor it. Supported style presets include `pixel`, `plush`, `clay`, `sticker`, `flat-vector`, `3d-toy`, `painterly`, `brand-inspired`, and `auto`.

Any style is acceptable when it remains pet-safe:

- compact whole-body silhouette readable inside a `192x208` cell
- consistent face, proportions, material, palette, and props across all rows
- clean removable chroma-key background
- details large enough to read at pet size
- no text, labels, UI, or readable logos unless the user explicitly provides approved reference art and asks for them

Non-pixel styles are first-class. Plush, clay, sticker, vector, 3D toy, painterly mascot, ink, and brand-inspired looks should be accepted when they satisfy the atlas and readability constraints.

## Transparency And Effects

Before generating or visually reviewing row strips, read `references/visual-standards.md`. Keep the main invariant simple: every generated pixel must either belong to the sprite or be cleanly removable chroma-key background, and effects must be attached, opaque, state-relevant, non-chroma-key, and readable inside one frame slot.

The deterministic raster pipeline removes only chroma-key pixels connected to the source strip background. Treat chroma-key pixels inside the pet body, accessories, props, face, or effects as a generation failure, not simple cleanup.

## Visible Progress Plan

For every pet run, keep a visible checklist so the user can see where the work is up to. Create the checklist before starting, keep one step active at a time, and update it as each step finishes.

Use this checklist for a normal pet run, replacing `<Pet>` with the pet's name or `your pet`:

1. Getting `<Pet>` ready.
2. Imagining `<Pet>`'s main look.
3. Picturing `<Pet>`'s poses.
4. Hatching `<Pet>`.

What each step means:

- `Getting <Pet> ready.` Choose or confirm the pet name, description, source images, style preset, style notes, and working folder. For bare brand/product/company requests, first run the brand discovery worker and capture the compact brand brief, source URLs, and avatar seed.
- `Imagining <Pet>'s main look.` Generate the pet's main reference image. This becomes the visual source of truth.
- `Picturing <Pet>'s poses.` Generate pose rows through lightweight workers, starting with `idle` and `running-right` to confirm identity and gait. Only mirror singleton `running-left` if `running-right` clearly works when flipped. Never mirror duo `running-left`.
- `Hatching <Pet>.` Turn the approved poses into final pet files, review the contact sheet, previews, and validation results, fix any broken parts, save `pet.json` and `spritesheet.webp`, then report the output paths.

Only mark a step complete when the real file, image, or decision exists. If this is a repair run, start from the first relevant step instead of restarting the whole checklist.

## Approval-Gated Generation

Use approval checkpoints by default. The goal is to catch style, identity, and composition problems early and avoid spending more generation budget after the user is unhappy.

- Generate one visual job at a time unless the user explicitly asks for parallel generation.
- After a singleton base, show a compact preview and ask for approval before generating rows.
- After base approval, record a compact identity ledger for every canonical side-dependent or tiny detail: character-relative side, viewer-relative appearance in the approved base, visible side, pet-scale simplification, markings/decorations, and avoidances. Update this ledger whenever the user adds or corrects a canonical feature.
- For duo pets, generate and show Subject A base, Subject B base, and the composite staging reference as separate approval checkpoints before generating rows.
- Generate one animation row at a time. After each row is copied into `decoded/`, create or show a compact row preview/contact sheet and ask for approval before starting the next row.
- If the user dislikes a base, composite, or row, repair that smallest scope before continuing.
- Do not run deterministic atlas composition and packaging until every required row has user approval.
- If the user explicitly permits batching or asks to optimize for speed, the agent may parallelize independent jobs, but it must still show completed outputs and stop when the user rejects an output.

## Identity Ledger And Critical Details

Maintain the run-local identity ledger that `prepare_pet_run.py` creates at `references/identity-ledger.json`. Use it for features that are easy to misplace or overdraw: earrings, rings, scars, hair markings, props, eye details, hand-held objects, side-specific accessories, and tiny symbols. Keep it concise and update it when the approved identity changes.

For each critical detail, record:

- canonical description and approved source image or crop
- character-relative side and viewer-relative appearance in common poses
- visibility rule, such as palm side versus back-of-hand side
- pet-scale rendering rule, including when to simplify or omit decoration
- hard avoidances, such as no duplicate marks, no wrong hand, no wrong finger, no cross on the hidden side
- QA evidence required before promotion, such as source-scale and pet-scale crops

When the user adds a new canonical detail after rows already exist, stop and decide whether earlier rows must be regenerated, explicitly exempted, or deferred. Do not silently retrofit a new identity detail across finished rows with tiny local marks.

For prompts that mention hands, ears, eyes, direction, or accessories, define both character side and viewer side. If a hand or finger matters, prefer visual relationships over labels alone: thumb side, top/bottom visible finger, central long finger, palm side, back-of-hand side, and the exact approved crop. If the detail still cannot read clearly in a `192x208` cell, simplify it intentionally or choose a pose where it is readable.

## Default Workflow

Read `references/runbook.md` before preparing, resuming, processing, packaging, or cleaning up a real run. The normal order is:

1. Prepare or resume a dedicated run folder with `prepare_pet_run.py` or `resume_pet_run.py`.
2. Use `petgen_jobs.py next` to find the next ready visual job. Default manifests expose one normal job at a time.
3. Generate visual jobs approval-gated with `$imagegen`, using every input image listed in `imagegen-jobs.json`.
4. Record selected outputs with `petgen_jobs.py selected`; approve, reject, or mark repair only after user or visual-QA review.
5. For singleton runs only, derive `running-left` from approved `running-right` when mirroring is visually safe. Never mirror duo `running-left`. For explicit micro/hybrid runs, use `derive_micro_animation_rows.py` only after required base/composite or key rows are approved.
6. After every required job is approved or derived, run extraction, inspection, atlas composition, validation, contact-sheet generation, and GIF preview rendering.
7. Inspect final contact sheet and preview GIFs with the QA rubric and a visual QA worker when worker mode is authorized.
8. Ask where to save the finished pet, then package with `package_pet.py` to the Codex pet folder, a project folder, or both. Do not bypass package preflight unless the user explicitly accepts an unvalidated package.
9. Verify packaged output with `verify_pet_package.py` before treating it as install-ready or catalog-ready.
10. Clean intermediate artifacts only after final QA passes and the user does not need debug files.

Use the runbook's exact commands for row-scoped previews, `stable-slots` recovery, duo palette-region warnings, package destinations, and cleanup.

## Lightweight Visual Workers

Use lightweight workers only when the user authorizes worker/subagent mode or the current Codex environment has been configured for this PetGenesis workflow. Read `references/visual-workers.md` before spawning any brand discovery, base, row, or final visual QA worker. Run visual workers sequentially unless the user explicitly approves parallel generation.

## Subagent Delegation

If the user has not allowed subagents, or the intent on subagent use is vague, ask for permission to spawn lightweight visual workers. The parent agent still owns manifests, deterministic scripts, packaging, cleanup, and user approval gates. Workers return only the exact fields described in `references/visual-workers.md`.

## Repair Workflow

When frame inspection, final visual QA, or the user rejects a job, read `references/repair-policy.md` before repairing. Repair the smallest complete scope that owns the defect, leave known-bad jobs as `repair_needed`, and do not package while unresolved repair notes remain.

## Rules

- Keep `$imagegen` as the primary generation layer.
- For brand/product/company/prospect requests without a concrete avatar description or reference image, run brand discovery before base generation and pass only the compact brief into the run.
- Use `$imagegen` as the only visual generation layer. Do not invoke image APIs, image CLIs, local raster generators, or one-off generation scripts from this skill.
- Keep reference images attached/visible for `$imagegen` whenever the chosen path supports references.
- For every row-strip generation, verify before generation that the canonical base and layout guide are actually attached or visible to the generation context. Do not generate rows from text-only references to prior conversation images.
- Attach the row's `references/layout-guides/<state>.png` image to every row-strip job as a layout-only guide, and do not accept outputs that copy guide pixels.
- Use lightweight visual workers for base generation, row-strip visual generation, and final contact-sheet QA only when the user authorizes worker/subagent mode; the parent owns manifest updates, deterministic image scripts, packaging, and cleanup.
- Generate every normal visual job with `$imagegen`: singleton base or duo bases, duo composite staging, and all row strips that are not explicitly approved singleton `running-left` mirror derivations or explicit micro/hybrid derived rows.
- Treat only the base job as eligible for prompt-only generation; every row job must attach its listed grounding images.
- Generate `running-right` before deciding whether singleton `running-left` can be mirrored.
- When singleton `running-left` is mirrored, preserve frame order and timing semantics; derive it through the deterministic script instead of mirroring an entire strip wholesale.
- Never mirror duo `running-left`; generate it through `$imagegen`.
- In `generated` mode, do not derive or reuse `waiting`, `running`, `failed`, `review`, `jumping`, or `waving` from another state; each has distinct app semantics and must be generated as its own row.
- Never substitute locally drawn, tiled, transformed, or code-generated row strips for missing `$imagegen` outputs. The only deterministic row-creation exceptions are `derive_running_left_from_running_right.py` under its singleton mirror gate and `derive_micro_animation_rows.py` for explicit micro/hybrid runs.
- Record a visual job as `selected` only after its selected output has been copied into the configured output path by `petgen_jobs.py selected`.
- Record a visual job as `approved` only after the user or final visual QA approves it. Do not approve it if any note says the row still needs repair or the user has not approved the relevant repair.
- Do not rely on generated images for exact atlas geometry; use this skill's deterministic image scripts.
- Use the chroma key stored in `pet_request.json`; do not force a fixed green screen.
- Keep the pet's silhouette, face, materials, palette, style, and props consistent across all rows.
- Use the identity ledger for side-dependent or tiny details, and update prompts and QA when the ledger changes.
- For structural defects, redraw/regenerate the smallest complete structural scope. Do not use paint-over patches to hide anatomy, face, finger, mouth, or prop-continuity errors.
- After repeated same-class repair failures, stop to diagnose and redesign instead of continuing the same fix pattern.
- Treat visual identity or style drift as a blocker even when `qa/review.json` and `final/validation.json` have no errors.
- Treat a contact sheet that shows cropped references, repeated tiles, white cell backgrounds, or non-sprite fragments as failed.
- Treat preview GIFs that show extraction-induced size popping, reversed directional timing, wrong facing direction, or inert idle loops as failed.
- Treat row previews that show source-level horizontal sliding in non-directional rows as failed, even if the individual frames look acceptable.
- Treat row candidates with visibly thicker/cruder linework or lower-fidelity style than the canonical base as failed identity drift.
- Treat chroma-key leakage inside the pet body, hands, face, clothing, props, or accessories as failed structural generation, not simple background cleanup.
- Treat forbidden detached effects, chroma-key-adjacent artifacts, shadows, glows, smears, dust, landing marks, wave marks, speed lines, or motion trails as failed rows.
- Treat wrong-side accessories, duplicated tiny markings, prop hand-switching, pasted-on mouths, or ambiguous hand/finger details as failed rows unless the user explicitly accepts them.
- Treat `qa/review.json` errors as blockers. Warnings require visual review.

## Acceptance Criteria

- Final atlas is PNG or WebP, `1536x1872`, transparent-capable, and based on `192x208` cells.
- Used cells are non-empty and unused cells are fully transparent.
- Atlas follows the row/frame counts in `references/animation-rows.md`.
- Contact sheet and per-row motion previews have been produced and inspected by a lightweight visual QA worker.
- `qa/review.json` has no errors.
- `final/validation.json` has `ok: true`.
- Row-by-row review confirms the animation cycles are complete enough for the Codex app.
- Motion previews do not show unintended size popping, reversed directional cadence, or wrong row semantics.
- Critical side-dependent or tiny identity details have source-scale and pet-scale QA crops when they are visible in the row.
- No row is approved while unresolved repair notes remain.
- Non-pixel styles are accepted when readable at pet size and consistent across rows.
- `${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/pet.json` and `${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/spritesheet.webp` are staged together for custom pets.
- Package preflight passes before normal packaging, including contact sheet, preview GIFs, validation, review, and job manifest status.
- `verify_pet_package.py` passes on the finished package before install-ready or catalog-ready delivery.
