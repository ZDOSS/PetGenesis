# AI Notes

PetGenesis is a fork of Hatch Pet. Preserve the singleton Hatch Pet workflow for `--subject-count 1`; add duo-specific behavior only when `--subject-count 2`.

Subject IDs are fixed as `a` and `b`. Singleton runs use `references/canonical-base.png`. Duo runs use `references/canonical-base-a.png`, `references/canonical-base-b.png`, and `references/composition-guide.png`.

## Job Graph

Singleton jobs keep upstream IDs: `base`, then one job per animation row. Duo jobs use `base-a`, `base-b`, `composite-staging`, then one job per animation row. Duo `running-left` is always generated and never derived by mirroring.

## Layout Guides

Singleton layout guides match Hatch Pet. Duo layout guides divide each cell into A-left and B-right safe regions while preserving atlas slot dimensions.

## Extraction

`extract_strip_frames.py --method auto` stays `auto` for singleton runs. For duo runs, `auto` resolves to `stable-slots` to avoid connected-component fusion when subjects touch.

## Inspection

Duo inspection is an approximate pre-filter. It checks left and right region occupancy for each frame and writes `expected_subjects`; visual QA remains required for subtle identity drift.
