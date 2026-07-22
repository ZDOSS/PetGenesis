# PetGenesis for Hermes and OpenPets

This directory contains the Hermes/OpenPets adapter for PetGenesis. It keeps the original Codex skill at the repository root intact and reuses the same deterministic Python scripts and reference files.

The adapter changes only the agent-facing workflow:

- Hermes uses its `image_generate` tool instead of Codex `$imagegen`.
- PetGenesis still creates and validates the same `1536x1872` transparent atlas.
- The finished `pet.json` and `spritesheet.webp` package is installed through OpenPets.

The installer assembles a complete local Hermes skill from this directory plus the shared root `scripts/` and `references/`. Those core files are not duplicated in Git, so the Codex and Hermes workflows cannot silently drift apart.

> This guide is also copied into the installed skill. Repository-maintenance commands such as `python .\hermes\install.py` and the development test commands must be run from a PetGenesis repository clone; the installed runtime copy intentionally omits `hermes/install.py` and `tests/`.

## Repository layout

```text
PetGenesis/
├── SKILL.md                 # Existing Codex skill
├── scripts/                 # Shared deterministic pipeline
├── references/              # Shared atlas, QA, and run documentation
└── hermes/
    ├── SKILL.md             # Hermes/OpenPets orchestration
    ├── README.md            # This guide
    └── install.py           # Assembles the user-local Hermes skill
```

## Prerequisites

- Hermes Agent with the `image_gen` toolset available.
- Python 3.10 or newer.
- Pillow with WebP support.
- Node.js/npm when using the OpenPets CLI through `npx`.
- The OpenPets desktop app for final installation and testing.

Check the local image-processing requirements from PowerShell:

```powershell
python --version
python -c "from PIL import Image, features; print(Image.__version__, features.check('webp'))"
```

The final value printed by the second command should be `True`.

## 1. Verify Hermes image generation

Run:

```powershell
hermes doctor
```

Confirm that **Tool Availability** reports `✓ image_gen`. If it does not, run `hermes tools` or `hermes setup` and configure a supported Image Generation provider, then start a fresh session.

Do not set `image_gen.provider` or `image_gen.model` when Hermes reports that those keys are unrecognized. Saving an unknown key does not establish that the active image-generation plugin reads it, and PetGenesis does not require repository-specific provider settings.

## 2. Install the repository adapter

From the PetGenesis repository root, run:

```powershell
python .\hermes\install.py
```

The default Windows destination is:

```text
%LOCALAPPDATA%\hermes\skills\creative\petgenesis
```

`HERMES_HOME` takes precedence when it is set. On macOS or Linux without `HERMES_HOME`, the default is `~/.hermes/skills/creative/petgenesis`.

The installer copies only the files required at runtime:

- `hermes/SKILL.md` as the installed `SKILL.md`;
- `hermes/README.md` as the installed `README.md`;
- shared `scripts/` and `references/`;
- `LICENSE.txt`;
- `.petgenesis-install.json`, a provenance marker used to protect updates.

It excludes caches, bytecode, tests, Git metadata, and development-only files.

Verify discovery:

```powershell
hermes skills list --source local
```

Look for `petgenesis`. Then start a fresh Hermes session with `/reset` so both the installed skill and any image-tool configuration are loaded.

### Updating an existing installation

After pulling or editing this repository, rebuild the local skill with:

```powershell
python .\hermes\install.py --force
```

Without `--force`, the installer refuses to overwrite an existing skill. Even with `--force`, it replaces only a directory containing the PetGenesis provenance marker; it refuses unmanaged folders, symbolic-link or Windows-junction destinations, and any destination that overlaps the source repository. Replacement is staged before the old directory is removed, and the moved directory is validated again before deletion, so a failed or raced copy does not overwrite unrelated content.

### Custom destination or profile

Pass an explicit skill folder when using a non-default Hermes profile or testing an installation:

```powershell
python .\hermes\install.py --destination "C:\path\to\hermes-home\skills\creative\petgenesis"
```

Use the profile's own Hermes home rather than another profile's directory unless you intentionally want to modify that profile. The destination must be outside the PetGenesis source repository.

## 3. Load and use PetGenesis

In a fresh Hermes session, load the skill:

```text
/petgenesis
```

Example request:

```text
Create a solo OpenPets pet named Pixel Otter from these reference images.
Use a soft sticker style, preserve the blue scarf and round glasses, and show
me each base and animation row for approval. Package, verify, and install the
finished pet in OpenPets.
```

Duo example:

```text
Create a two-character OpenPets pet duo named Moonlight Pair.
Subject A stays on the left and Subject B stays on the right.
Preserve both identities in every animation state, ask for approval at each
stage, then verify and install the final package in OpenPets.
```

PetGenesis writes run artifacts under the current workspace by default:

```text
petgenesis-pets/<pet-id>-<utc-timestamp>/
```

Generation is approval-gated. Hermes should show the base, duo composition when applicable, and each animation row before spending generation budget on the next normal job.

## 4. OpenPets CLI and desktop app

A global `openpets` command is optional. The npm CLI can be used without a global install:

```powershell
npx -y @open-pets/cli@latest status
npx -y @open-pets/cli@latest pets
```

The desktop app must be running before local installation. The status result should include:

```json
{
  "ok": true,
  "appRunning": true
}
```

The Hermes skill packages to a project folder, verifies it with `verify_pet_package.py --strict-clean`, and then runs the equivalent of:

```powershell
npx -y @open-pets/cli@latest install --from-folder "C:\absolute\path\to\packages\<pet-id>"
```

After installation, select the pet as the default in OpenPets Control Center. An OpenPets MCP server without a fixed `--pet` argument follows the desktop default pet.

## 5. Connect OpenPets to Hermes reactions

Check whether the MCP server already exists:

```powershell
hermes mcp list
```

If `openpets` is already enabled, do not add it again. Otherwise:

```powershell
hermes mcp add openpets --command npx --args -y @open-pets/mcp@latest
hermes mcp test openpets
```

Use `/reload-mcp` or start a fresh session after changing MCP configuration.

The bundled Hermes `petdex` skill is separate: it installs Hermes mascot selections and does not generate PetGenesis atlases or install local OpenPets packages.

## Troubleshooting

### Hermes warned that `image_gen.*` is unrecognized

Do not rely on the saved unknown key. Configure image generation through `hermes tools` or `hermes setup` instead. `hermes doctor` reporting `✓ image_gen` confirms that the tool is available; it does not prove that an unrecognized provider or model key is active.

### `image_generate` is missing in the current conversation

Tool availability is fixed when a session starts. Run `/reset` after configuring image generation.

### `petgenesis` does not appear in the skill list

Run the installer from the repository root, then check:

```powershell
python .\hermes\install.py --force
hermes skills list --source local
```

Start a fresh session after successful discovery.

If `--force` reports that the destination is not managed by this installer, do not delete or overwrite it automatically. Inspect the existing folder and choose a different `--destination`, or remove it yourself only after confirming it is safe to replace.

### `openpets` is not recognized

Use the npm form instead:

```powershell
npx -y @open-pets/cli@latest status
```

### OpenPets installation fails

Confirm the desktop app is running, then check the exact package folder:

```powershell
npx -y @open-pets/cli@latest status
python .\scripts\verify_pet_package.py "C:\absolute\path\to\package" --strict-clean
```

A clean package contains only `pet.json` and `spritesheet.webp`.

## Development and verification

Run the adapter tests without installing pytest permanently:

```powershell
uv run --with pytest python .\scripts\run_tests.py .\tests\test_hermes_install.py -q
```

Run the full PetGenesis test suite:

```powershell
uv run --with pytest python .\scripts\run_tests.py -q
```

Validate the checked-in Hermes skill frontmatter and an assembled installation before releasing changes. Never commit credentials, Hermes OAuth files, provider keys, or user-local configuration to this directory.
