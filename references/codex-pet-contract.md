# Codex Pet Contract

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

The app loads custom pets from the folder name under `${CODEX_HOME:-$HOME/.codex}/pets/`.
