# AI Notes

PetGenesis is a fork of Hatch Pet. Preserve the singleton Hatch Pet workflow for `--subject-count 1`; add duo-specific behavior only when `--subject-count 2`.

Subject IDs are fixed as `a` and `b`. Singleton runs use `references/canonical-base.png`. Duo runs use `references/canonical-base-a.png`, `references/canonical-base-b.png`, and `references/composition-guide.png`.

## Job Graph

Singleton jobs keep upstream IDs: `base`, then one job per animation row. Duo jobs use `base-a`, `base-b`, `composite-staging`, then one job per animation row. Duo `running-left` is always generated and never derived by mirroring.

## Run Folder

Default run folders are created under `Path.cwd() / "petgenesis-pets" / "<pet-id>-<timestamp>"`. `Path.cwd()` is the active workspace/project root for the current user. Do not replace this with a machine-specific absolute path.

## Approval Gates

The default workflow is approval-gated. Generate one visual job at a time, show it to the user, and wait for approval before starting the next visual job. This applies to bases, duo composite staging, and each animation row. Parallel generation is opt-in only when the user explicitly asks for it.

## Layout Guides

Singleton layout guides match Hatch Pet. Duo layout guides divide each cell into A-left and B-right safe regions while preserving atlas slot dimensions.

## Extraction

`extract_strip_frames.py --method auto` stays `auto` for singleton runs. For duo runs, `auto` resolves to `stable-slots` to avoid connected-component fusion when subjects touch.

## Inspection

Duo inspection is an approximate pre-filter. It checks left and right region occupancy for each frame and writes `expected_subjects`; visual QA remains required for subtle identity drift.

## Skill Instructions

Do not remove singleton behavior while improving duo behavior. Any prompt, job, extraction, or QA change must state whether it applies to singleton, duo, or both.
