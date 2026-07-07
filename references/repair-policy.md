# Repair Policy

Read this file when frame inspection or final visual QA fails, or when a user rejects a generated base/composite/row.

## Core Rule

Repair the smallest complete scope that owns the defect. Repair the failed row, not the whole sheet, unless the defect is inherited from the canonical base or identity ledger.

## Taxonomy

- **Extraction cleanup:** cyan fringe, transparent RGB residue, isolated specks, edge despill, alpha matte cleanup, or slot extraction/baseline popping. Use deterministic scripts and local raster cleanup.
- **Semantic correction:** wrong state acting, weak motion, missing approved prop, wrong expression, or row-level prompt miss. Regenerate the row with clearer references and prompt constraints.
- **Structural redraw:** anatomy, finger identity, mouth integration, face structure, prop ownership, hand continuity, side-dependent accessory placement, or any defect where a local paint-over would fake the drawing. Redraw or regenerate the smallest complete structural scope: whole hand, whole face, whole frame, or whole row.
- **Full regeneration or redesign:** repeated failures, unreadable pet-scale detail, incompatible pose, identity drift across many frames, or a candidate that accumulates visible repair artifacts.

Do not treat structural drawing defects as pixel cleanup. Local raster edits are acceptable for extraction residue and small non-structural artifacts, but not for anatomy, mouth shapes, fingers, props, or identity placement unless the user explicitly asks for manual pixel-art editing.

## Repair Budget

After two failed repairs of the same defect class, stop and diagnose the cause before trying again. After three failed repairs, abandon that candidate and redesign the row, pose, prompt, or identity simplification. Record rejected candidates and why they were rejected.

Never approve a row or visual job while any manifest note, QA note, or user-visible concern says it still needs repair. If a row is known-bad, set or leave it as `repair_needed` with `petgen_jobs.py repair`, and do not package it.

## Identity And Detail Repairs

For identity repairs, use the canonical base image, original references, contact sheet, and exact row failure note as grounding context. Give the row worker the existing row prompt plus a compact repair note from `qa/review.json`; preserve the canonical pet identity and chosen style.

For critical tiny details, create QA crops before promotion:

- source-scale crop showing the detail in every relevant frame
- pet-scale crop showing how it reads after extraction/downscale
- full-row preview or GIF showing the detail does not drift, duplicate, or switch sides

Promote only if the crops prove placement, count, side, and simplification. If the crop shows a duplicate, hidden patch, blocky mark, or ambiguous placement, reject the candidate instead of covering it with another patch.

## Common Failure Modes

For extraction-induced motion popping, do not regenerate imagery first. If the source strip already preserves row-level scale and baseline, rerun the deterministic pipeline with `--method stable-slots`, inspect with `--allow-stable-slots`, then re-check the preview GIFs. Regenerate the row only when the original strip itself is clipped, unstable, or semantically wrong.

For row strips, inspect the raw generated strip before any extraction/downscale and reject candidates with generation-level drift or style regression. For non-directional rows such as `idle`, `waiting`, `running`, and `review`, the subject should remain centered within each source slot except for small intentional bobbing; visible horizontal sliding or a measured subject-center drift over about 5% of the source slot width is a row failure, not an extraction issue. Reject rows that only blink while the body slides.

Treat line-quality/style regression as identity drift. If a row becomes visibly thicker, cruder, blurrier, lower-detail, or less faithful to the canonical base than the approved base image, regenerate the row with stronger grounding rather than accepting it because the pose is recognizable.

Use `compare_identity_drift.py` to diagnose suspected drift before another generation attempt. Its base-vs-frame report is generic: it normalizes the approved canonical base into the pet cell, aligns it to each extracted frame, then reports silhouette overlap, color drift, alpha-area changes, local tile drift, and whole-row center sliding using state-aware motion thresholds. Treat the overlays as QA evidence, not as an automatic replacement for visual review.

Treat chroma-key color inside the sprite as structural failure. A non-flat or slightly varied chroma background can be normalized only when the key color is confined to background/edge cleanup. If cyan/green/magenta key pixels appear inside hands, face, clothing, accessories, or other pet details, reject or regenerate the row instead of relying on extraction cleanup.
