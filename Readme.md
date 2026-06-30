# PetGenesis

PetGenesis is a fork of OpenAI's curated Hatch Pet skill, expanded for more reliable Codex pet production from source material. It keeps the original Hatch Pet atlas contract, packaging shape, and single-subject workflow, then adds a more explicit preparation and QA layer for one-subject pets plus a two-subject duo path.

The goal is to let a user provide one or more references, say how many subjects should be preserved, and get a Codex-compatible animated pet with minimal back-and-forth. A normal solo pet still uses the Hatch-style flow: one canonical base image, state-specific row strips, deterministic frame extraction, validation, contact-sheet QA, previews, and `pet.json` packaging. Duo pets add separate canonical bases for each subject, a composite staging reference, and row prompts designed to keep both characters readable in the same `192x208` cells.

Use `--subject-count 1` for a solo pet and `--subject-count 2` for a duo. Counts greater than 2 are rejected because each animation cell is only `192x208`.

PetGenesis relies on the installed `$imagegen` skill for visual generation and keeps deterministic scripts responsible for atlas assembly, transparency cleanup, validation, contact sheets, animation previews, and final packaging. For duo pets, PetGenesis generates each subject separately, then creates a composite staging reference before generating animation rows. This improves identity consistency while preserving the normal Codex pet atlas.

## Subject Counts

- `--subject-count 1`: solo pet, Hatch Pet-compatible workflow.
- `--subject-count 2`: duo pet, two canonical bases plus a composite staging reference.
- `--subject-count 3` or higher: rejected.
