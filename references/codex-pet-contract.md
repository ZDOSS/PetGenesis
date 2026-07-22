# Codex and OpenPets Pet Contract

## Sprite Atlas

- Format: PNG or WebP.
- Dimensions: `1536x1872`.
- Grid: 8 columns x 9 rows.
- Cell: `192x208`.
- Background: transparent.
- Unused cells: fully transparent.

The webview animation uses CSS background positions from the fixed row and column counts. Do not add labels, gutters, borders, grid lines, shadows outside the cell, or extra frames.

## PetGenesis Subject Counts

The atlas geometry is unchanged for solo and duo pets. Subject count changes only the pixels inside each used `192x208` cell and the generation workflow that creates those pixels.

- `subject_count = 1`: one centered subject per used cell.
- `subject_count = 2`: Subject A and Subject B both appear in every used cell, with Subject A staged left and Subject B staged right by default.
- Counts greater than 2 are rejected for v1 because the cell is too small for readable full-body animated subjects.

## Local Custom Pet Package

Place files under:

```text
${CODEX_HOME:-$HOME/.codex}/pets/<pet-name>/
├── pet.json
└── spritesheet.webp
```

Manifest shape:

```json
{
  "id": "pet-name",
  "displayName": "Pet Name",
  "description": "One short sentence.",
  "spritesheetPath": "spritesheet.webp"
}
```

Codex loads custom pets from the folder name under `${CODEX_HOME:-$HOME/.codex}/pets/`.

## OpenPets Compatibility

OpenPets accepts the same two-file package and atlas geometry. Package to a normal project folder, verify it, then install the exact pet folder through the running OpenPets desktop app:

```bash
python "$SKILL_DIR/scripts/verify_pet_package.py" \
  /absolute/path/to/packages/<pet-id> \
  --strict-clean

openpets status
openpets install --from-folder /absolute/path/to/packages/<pet-id>
openpets pets
```

When no global `openpets` executable is available, use `npx -y @open-pets/cli@latest` in its place after the user permits npm to fetch/cache it. OpenPets registers the package by the `id` in `pet.json`; keep the folder name aligned with that ID for predictable local development and sharing.
