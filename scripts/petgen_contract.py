"""Shared PetGenesis atlas and runtime contract constants."""

from __future__ import annotations

from pathlib import Path


CELL_WIDTH = 192
CELL_HEIGHT = 208
ATLAS_COLUMNS = 8
ATLAS_ROWS = 9
ATLAS_WIDTH = CELL_WIDTH * ATLAS_COLUMNS
ATLAS_HEIGHT = CELL_HEIGHT * ATLAS_ROWS

FRAME_COUNTS = {
    "idle": 6,
    "running-right": 8,
    "running-left": 8,
    "waving": 4,
    "jumping": 5,
    "failed": 8,
    "waiting": 6,
    "running": 6,
    "review": 6,
}

EXPECTED_STATES = tuple(FRAME_COUNTS)


def expected_preview_paths(run_dir: Path) -> list[Path]:
    return [run_dir / "qa" / "previews" / f"{state}.gif" for state in EXPECTED_STATES]
