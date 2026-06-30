# PetGenesis

PetGenesis creates Codex-compatible animated pets from one subject or a two-subject duo. It keeps the Hatch Pet atlas contract and adds a duo workflow for paired characters.

Use `--subject-count 1` for a solo pet and `--subject-count 2` for a duo. Counts greater than 2 are rejected because each animation cell is only `192x208`.

For duo pets, PetGenesis generates each subject separately, then creates a composite staging reference before generating animation rows. This improves identity consistency while preserving the normal Codex pet atlas.

## Subject Counts

- `--subject-count 1`: solo pet, Hatch Pet-compatible workflow.
- `--subject-count 2`: duo pet, two canonical bases plus a composite staging reference.
- `--subject-count 3` or higher: rejected.
