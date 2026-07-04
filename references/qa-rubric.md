# QA Rubric

Do not accept an atlas until all checks pass.

## Geometry

- Exact `1536x1872` dimensions.
- 8 columns x 9 rows.
- Each frame fits inside its `192x208` cell.
- Unused cells are transparent.
- Fully transparent atlas pixels do not retain non-zero RGB residue after export.
- `qa/review.json` has no errors.
- `frames/frames-manifest.json` records component extraction for production rows unless `stable-slots` was intentionally chosen to preserve row-level playback stability after visual inspection.

## Character Consistency

- Same silhouette and proportions across every row.
- Same face and expression language.
- Same style, material, palette, lighting, and prop design.
- No frame introduces a new unintended character or object.

## Duo QA

- Both subjects appear in every used cell of every row.
- Subject A remains left and Subject B remains right unless the user explicitly approved another composition.
- Each subject preserves its own silhouette, face, palette, material, markings, and props.
- Subjects may touch, but they must not fuse into one unreadable silhouette.
- In `generated` mode, duo `running-left` must be generated, not mirrored from `running-right`.
- `qa/review.json` should include `expected_subjects` for duo runs; treat it as a pre-filter and still perform contact-sheet and GIF visual QA.

## Pet-Safe Style

- Art reads as a Codex app pet, not a scene, app icon, logo sheet, or standalone illustration.
- Silhouette is compact and clear enough to read inside a `192x208` cell.
- The chosen style is consistent across every row, including edge treatment, material, lighting, and palette.
- Pixel, plush, clay, sticker, flat vector, 3D toy, painterly mascot, ink, and brand-inspired styles are all acceptable when readable at pet size.
- No tiny accessories, texture detail, logo detail, or text that disappears or becomes noisy at pet size.

## Animation Completeness

- Each row uses the exact expected number of frames.
- The first and last frames can loop without an obvious pop.
- Directional rows read as the intended direction.
- Mirrored directional rows preserve temporal frame order rather than reversing the cadence.
- State-specific actions are recognizable at pet size.
- Poses are generated animation variants, not repeated copies of the same source image.
- Preview GIFs do not show unintended size popping, extraction-induced baseline jumps, or wrong directional facing.
- In explicit `micro` or `hybrid` mode, derived rows may have simpler motion, but every state still needs a readable semantic difference at pet size.

## App Fitness

- First idle frame works as a static reduced-motion pet.
- The `idle` row should be calm and low-distraction; reject it if it reads as waving, walking, running, jumping, talking, working, reviewing, reacting dramatically, changing props, or making large pose/silhouette changes.
- No important detail is too small to read.
- No frame is clipped by the cell.
- Failed/review/waiting states are distinct from ordinary idle.
- Contact sheets must show whole sprite poses inside cells, not cropped tiles from a larger reference image.
- Contact sheets must not be accepted if every used frame is just the reference image with small geometric transforms.
- Used cells must not have white or opaque rectangular backgrounds unless the pet intentionally fills the whole cell and the user accepts that tradeoff.
- The chroma key must be visually absent from the character. If extraction removes character regions, choose a different key and regenerate the affected base/rows.
- Contact sheets must not show edge slivers or partial neighboring sprites inside cells.
- Contact sheets must not show darker/lighter versions of the chroma key as shadows, dust, smears, glows, landing marks, or motion effects. These are background extraction failures and should trigger row repair.
- If `qa/review.json` reports edge pixels, sparse frames, size outliers, or slot-extraction fallback, inspect the row visually and repair it when the issue is visible.
- If `qa/review.json` reports chroma-adjacent non-transparent pixels, repair the row unless those pixels are an intentional character color and the selected key was manually accepted.
- If preview GIFs show size popping even though the generated strip itself had stable scale and placement, rerun extraction with `stable-slots` before regenerating the row.
- If previews show wrong facing direction, reversed cadence, non-alternating gait, or an effectively static idle loop, repair or regenerate the affected row.

## Repair Policy

Repair the smallest failing scope first:

1. Single bad frame.
2. One row.
3. Full atlas regeneration only when identity or layout is broadly broken.

The normal production path should regenerate only the affected row and copy the selected replacement into the same decoded output path unless the base character is wrong.

## Package Readiness

- `final/validation.json` reports `ok: true`.
- `qa/review.json` reports `ok: true`.
- `qa/contact-sheet.png` exists and has been visually checked.
- Every expected `qa/previews/*.gif` file exists and has been visually checked.
- `imagegen-jobs.json` has no pending, rejected, or repair-needed jobs unless a cleaned run is explicitly being packaged with `--allow-cleaned-run`.
- The finished package passes `scripts/verify_pet_package.py`; use `--strict-clean` for catalog submissions.
