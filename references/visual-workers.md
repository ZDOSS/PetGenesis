# Visual Workers

Read this file before using lightweight workers/subagents for PetGenesis image generation or final visual QA.

## Contents

- Activation and model choice
- Parent responsibilities
- Worker responsibilities
- Base worker prompt
- Row worker prompt
- Final visual QA prompt

## Activation And Model Choice

Use lightweight subagents for image-heavy work when the user explicitly authorizes worker/subagent mode or the current Codex environment has been configured for this PetGenesis workflow. This bounds each `$imagegen` rollout to one selected image, keeps contact-sheet vision payloads out of the parent thread, and reduces cost while preserving the full 9-state app contract.

If the user has not allowed subagents, or the intent on subagent use is vague, ask for permission to spawn lightweight visual workers. If the user declines or does not authorize worker mode, run the same sequence in the parent thread and keep outputs concise. This permission is separate from parallelization; still run visual jobs sequentially unless the user explicitly asks for parallel generation.

Prefer a smaller capable model for brand discovery, since it returns a compact research brief rather than doing orchestration. Prefer a smaller capable model for visual workers, such as `gpt-5.4-mini` with medium reasoning, when model override is available. Use the parent/default model only for orchestration or when a smaller worker model is unavailable.

When worker mode is authorized, keep at most one generation worker active at once by default. Use parallel workers only when the user explicitly asks for parallel generation. Run final visual QA as a single worker after deterministic image processing. Close workers after their result has been consumed.

## Parent Responsibilities

- run the brand discovery worker before preparation when the user provides a bare brand/product/company/prospect name
- prepare the run and use `petgen_jobs.py next` to inspect ready jobs
- assign the base job, row jobs, and final contact-sheet QA to lightweight workers
- record selected worker outputs with `petgen_jobs.py selected`, show the relevant preview, then record approval/rejection/repair with `petgen_jobs.py`
- let `petgen_jobs.py selected` create `references/canonical-base.png` from the selected singleton base output, or `references/canonical-base-a.png` and `references/canonical-base-b.png` from selected duo base outputs
- run the approved singleton `running-left` mirror derivation when appropriate; never mirror duo `running-left`
- run deterministic image processing, packaging, repair regeneration, and cleanup

## Worker Responsibilities

Base worker:

- handle only the `base` job
- read `prompts/base-pet.md` and use any listed reference images
- use `$imagegen` only
- honor any compact brand inspiration line in the prompt as broad visual/personality guidance, without copying logos, readable marks, UI screenshots, slogans, or text
- return only `selected_source=/absolute/path/to/selected-output.png` and `qa_note=<one sentence>`

Row worker:

- handle exactly one row job
- read the row prompt and use all listed input images
- use `$imagegen` only; do not draw, edit, tile, or synthesize sprites locally
- perform a quick visual sanity check for frame count, identity, chroma background, spacing, clipping, and detached effects
- enforce the row prompt's transparency and effects rules, including no detached effects, no wave marks for `waving`, no speed lines or dust for directional running rows, no literal foot-running for the non-directional `running` row, and only attached opaque sprite-like tears/smoke/stars when allowed by the state prompt
- return only `selected_source=/absolute/path/to/selected-output.png` and `qa_note=<one sentence>`

Final visual QA worker:

- inspect `qa/contact-sheet.png` plus the row GIFs under `qa/previews/`, with `qa/review.json` and `final/validation.json` as text context when useful
- verify all 9 rows match the Codex app state contract and the same pet identity
- return a compact result: `visual_qa=pass` or `visual_qa=fail`, plus row-specific repair notes when failing
- do not edit files, queue repairs, package, or clean up

## Base Worker Prompt

```text
Generate the PetGenesis base image.

Run dir: <absolute run dir>
Job id: base
Prompt file: <absolute base prompt file>
Input images:
- <absolute path> - <role>

Use $imagegen only. Read the base prompt and attach every listed input image. If the prompt contains brand inspiration, use it only as broad mascot-safe guidance; do not copy logos, readable marks, UI screenshots, slogans, or text. Before returning, visually check that the result is one centered full-body pet on a flat chroma background, with no text, scenery, shadows, or detached effects.

Do not edit manifests, copy into decoded, record selected/approved job state, generate rows, run image-processing scripts, repair, package, or open unrelated files.
Do not include Markdown image previews, base64, or extra attachments in the final response.

Return exactly:
selected_source=/absolute/path/to/selected-output.png
qa_note=<one sentence>
```

## Row Worker Prompt

```text
Generate one PetGenesis row.

Run dir: <absolute run dir>
Row id: <row-id>
Prompt file: <absolute prompt file>
Retry prompt file: <absolute retry prompt file>
Input images:
- <absolute path> - <role>
- <absolute path> - <role>

Use $imagegen only. Read the row prompt and attach every listed input image. If imagegen returns Bad Request, retry once with the retry prompt and the same input images.

Before returning, visually check: exact frame count, same pet identity as canonical base, flat chroma background, complete separated unclipped poses, and no detached effects or guide marks. The prompt's transparency and effects rules are mandatory: no detached effects, no wave marks for `waving`, no speed lines or dust for directional running rows, no literal foot-running for the non-directional `running` row, and only attached opaque sprite-like tears/smoke/stars when allowed by the state prompt.

Do not edit manifests, copy into decoded, record selected/approved job state, mirror rows, run image-processing scripts, repair, package, or open unrelated files.
Do not include Markdown image previews, base64, or extra attachments in the final response.

Return exactly:
selected_source=/absolute/path/to/selected-output.png
qa_note=<one sentence>
```

## Final Visual QA Worker Prompt

```text
Visually QA one finalized PetGenesis contact sheet.

Run dir: <absolute run dir>
Contact sheet: <absolute run dir>/qa/contact-sheet.png
Preview dir: <absolute run dir>/qa/previews
Review JSON: <absolute run dir>/qa/review.json
Validation JSON: <absolute run dir>/final/validation.json

Inspect the contact sheet and the preview GIFs visually. Confirm the same pet identity, style, palette, silhouette, face, proportions, and props across all rows:
0 idle, 1 running-right, 2 running-left, 3 waving, 4 jumping, 5 failed, 6 waiting, 7 running, 8 review.

Fail rows with identity drift, missing/blank frames, copied guide marks, white/nontransparent backgrounds, cropped bodies, slot overlap, detached effects, shadows/glows/smears/dust, chroma-key artifacts, motion that does not match the row state, unintended size popping, wrong facing direction, reversed or non-alternating gait, or idle loops that are effectively static.

Do not edit files, queue repairs, package, clean up, or inspect unrelated files.

Return exactly:
visual_qa=pass|fail
qa_note=<one sentence summary>
repair_rows=<comma-separated row ids, or none>
repair_notes=<short row-specific notes, or none>
```
