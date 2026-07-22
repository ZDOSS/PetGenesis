# PetGenesis

PetGenesis creates Codex- and OpenPets-compatible animated pets from one subject or a two-subject duo. It is built on the `hatch-pet` Codex skill, preserving its deterministic atlas contract, visual QA, validation, and packaging workflow while adding PetGenesis-specific duo support for paired characters.

Use `--subject-count 1` for a solo pet and `--subject-count 2` for a duo. Counts greater than 2 are rejected because each animation cell is only `192x208`.

For duo pets, PetGenesis generates each subject separately, then creates a composite staging reference before generating animation rows. This improves identity consistency while preserving the normal Codex pet atlas.

## Credits

PetGenesis is based on the `hatch-pet` skill and should credit that foundation wherever it is shared. Hatch Pet provides the core Codex custom-pet pipeline for sprite atlas geometry, row extraction, transparent-background validation, QA previews, and `pet.json` packaging. PetGenesis extends that work with subject-count handling, duo composition, subject-aware row generation, and additional identity checks.

## Hermes and OpenPets

The repository includes a version-controlled Hermes adapter under [`hermes/`](hermes/README.md). It uses Hermes's `image_generate` tool, reuses the same root `scripts/` and `references/`, and installs verified packages through the running OpenPets desktop app. The existing root `SKILL.md` remains the Codex entry point.

Quick setup from PowerShell:

```powershell
hermes doctor
python .\hermes\install.py
hermes skills list --source local
```

If `hermes doctor` does not report `✓ image_gen`, configure a supported image-generation provider through `hermes tools` or `hermes setup`. Do not add unrecognized `image_gen.provider` or `image_gen.model` keys just because Hermes can save them. Start a fresh session, run `/petgenesis`, and ask for an OpenPets pet. See [`hermes/README.md`](hermes/README.md) for installation, updates, MCP setup, OpenPets CLI commands, and troubleshooting.

## Requirements

Required for normal runs:

- Python 3.10+.
- Pillow with WebP support.
- An image-generation runtime: Codex `$imagegen` for the root skill, or Hermes `image_generate` for the adapter under `hermes/`.
- Write access to the active project/workspace root.

Required for tests:

- `pytest`.

Required only when using video references:

- `ffmpeg`.
- `ffprobe`.

Optional:

- `jq` for manual JSON inspection/debugging.

Useful checks:

```bash
python --version
python -c "from PIL import Image, features; print(Image.__version__, features.check('webp'))"
python -m pytest --version
jq --version       # optional
ffmpeg -version    # video only
ffprobe -version   # video only
```

## Subject Counts

- `--subject-count 1`: solo pet, Hatch Pet-compatible workflow.
- `--subject-count 2`: duo pet, two canonical bases plus a composite staging reference.
- `--subject-count 3` or higher: rejected.

## Animation Modes

- `--animation-mode generated`: default, production-quality workflow.
- `--animation-mode micro`: derives all rows from the approved base/composite after minimal generation.
- `--animation-mode hybrid`: generates key rows and derives the rest.

Use `micro` and `hybrid` only when lower animation variety is acceptable in exchange for less image generation.

## Run Folder

By default, PetGenesis creates a dedicated run folder under the active workspace/project root:

```text
petgenesis-pets/<pet-id>-<utc-timestamp>/
```

All generated prompts, decoded strips, QA media, frames, and final files should stay inside that run folder. Do not put loose generated files directly in the project root.

## Approval Workflow

PetGenesis should show work to the user before spending more generation budget:

1. Generate one base or row at a time.
2. Show a compact preview/contact sheet.
3. Ask the user to approve, reject, or request a repair.
4. Continue only after approval.

For duo pets, approve Subject A base, Subject B base, and the composite staging reference before generating animation rows. Then approve each row before moving to the next row.

`petgen_jobs.py approve` requires a selected or derived job with its output files present. Use `--force` only for an intentional manual override.

Use `scripts/petgen_identity.py` to manage side-dependent details instead of hand-editing `references/identity-ledger.json`.

## Final Save Location

Before packaging the finished pet, ask where it should be saved:

- Codex custom pet folder: `${CODEX_HOME:-$HOME/.codex}/pets/<pet-id>/`.
- A user-chosen folder in the current project/workspace, including an OpenPets package root.
- Both.

Use the active workspace, environment variables, or the user's chosen destination. Do not hard-code machine-specific paths.

`scripts/package_pet.py` runs a preflight before normal packaging. It requires validation, review, contact sheet, preview GIFs, and an approved or derived job manifest. Use `--allow-unvalidated` only when the user explicitly accepts an unvalidated package.

Verify finished packages with:

```bash
python scripts/verify_pet_package.py /absolute/path/to/package-folder --strict-clean
```

For OpenPets, install the strictly verified package through the running desktop app:

```bash
npx -y @open-pets/cli@latest status
npx -y @open-pets/cli@latest install --from-folder /absolute/path/to/package-folder
npx -y @open-pets/cli@latest pets
```

Export clean catalog submissions with:

```bash
python scripts/export_catalog_submission.py \
  --run-dir /absolute/path/to/run \
  --author-slug <author-slug> \
  --out-dir /absolute/path/to/export-root \
  --catalog generic
```

## Prompt Starters

Solo pet:

```text
Create a solo Codex/OpenPets pet named <name> from these references.
Style: <pixel/sticker/plush/clay/flat-vector/etc>.
Must preserve: <list key colors, silhouette, face, outfit, props>.
Animation personality: <calm, energetic, mischievous, sleepy, focused>.
Avoid: <text, logos, extra props, scenery, effects, shadows>.
Final pet should be saved to: <Codex custom pet folder / OpenPets / project folder / both>.
```

Duo pet:

```text
Create a two-character Codex/OpenPets pet duo named <name>.
Subject A stays on the left: <identity details>.
Subject B stays on the right: <identity details>.
Shared style: <style and line/color guidance>.
Required interaction: <how they should relate in idle or key rows>.
Avoid: <identity drift, swapped sides, extra symbols, scenery, text>.
Final pet should be saved to: <Codex custom pet folder / OpenPets / project folder / both>.
```

Repair request:

```text
Repair only the <row/base/composite> for <pet name>.
Problem: <what looks wrong>.
Keep unchanged: <identity, colors, pose side, style, approved rows>.
Desired change: <specific correction>.
Do not regenerate approved rows unless required.
```
