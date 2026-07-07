#!/usr/bin/env python3
"""Refresh PetGenesis row prompts from the current identity ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import prepare_pet_run as prepare


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"required file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def request_subject_by_id(request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    subjects = request.get("subjects")
    if not isinstance(subjects, list):
        return result
    for subject in subjects:
        if not isinstance(subject, dict):
            continue
        subject_id = str(subject.get("id") or "").lower()
        if subject_id:
            result[subject_id] = subject
    return result


def merged_subjects(request: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    request_subjects = request_subject_by_id(request)
    ledger_subjects = ledger.get("subjects")
    if not isinstance(ledger_subjects, list) or not ledger_subjects:
        ledger_subjects = list(request_subjects.values())
    subject_count = int(request.get("subject_count") or ledger.get("subject_count") or 1)
    ids = ["a"] if subject_count == 1 else ["a", "b"]
    merged: list[dict[str, Any]] = []
    for index, subject_id in enumerate(ids):
        ledger_subject = next(
            (
                item
                for item in ledger_subjects
                if isinstance(item, dict)
                and str(item.get("id") or ("a" if index == 0 else "b")).lower()
                == subject_id
            ),
            {},
        )
        request_subject = request_subjects.get(subject_id, {})
        merged.append(
            {
                **request_subject,
                **ledger_subject,
                "id": subject_id,
                "name": ledger_subject.get("name")
                or request_subject.get("name")
                or (request.get("display_name") if subject_count == 1 else f"Subject {subject_id.upper()}"),
                "notes": ledger_subject.get("identity_notes")
                or ledger_subject.get("notes")
                or request_subject.get("notes")
                or request.get("pet_notes")
                or request.get("description")
                or "",
                "canonical_base_path": ledger_subject.get("canonical_base")
                or request_subject.get("canonical_base_path")
                or ("references/canonical-base.png" if subject_count == 1 else f"references/canonical-base-{subject_id}.png"),
            }
        )
    return merged


def row_specs(request: dict[str, Any]) -> list[tuple[str, int, int, str]]:
    rows = request.get("rows")
    if not isinstance(rows, list):
        return prepare.ROWS
    result: list[tuple[str, int, int, str]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state") or "")
        if not state:
            continue
        result.append(
            (
                state,
                int(item.get("row") or 0),
                int(item.get("frames") or 1),
                str(item.get("purpose") or ""),
            )
        )
    return result or prepare.ROWS


def build_prompt_args(
    request: dict[str, Any],
    ledger: dict[str, Any],
) -> argparse.Namespace:
    chroma_key = request.get("chroma_key")
    if not isinstance(chroma_key, dict):
        chroma_key = {"hex": "#00ff00", "name": "green"}
    return argparse.Namespace(
        pet_id=str(request.get("pet_id") or "pet"),
        display_name=str(request.get("display_name") or request.get("pet_id") or "Pet"),
        pet_notes=str(request.get("pet_notes") or request.get("description") or ""),
        subject_count=int(request.get("subject_count") or ledger.get("subject_count") or 1),
        subjects=merged_subjects(request, ledger),
        style_preset=str(request.get("style_preset") or "auto"),
        style_notes=str(request.get("style_notes") or ""),
        chroma_key=chroma_key,
        composition=str(request.get("composition") or "left-right"),
        interaction_mode=str(request.get("interaction_mode") or "both-act"),
        animation_mode=str(request.get("animation_mode") or "generated"),
        forbidden=[
            str(item)
            for item in ledger.get("forbidden", [])
            if str(item).strip()
        ]
        if isinstance(ledger.get("forbidden"), list)
        else [],
    )


def refresh_prompts(run_dir: Path, requested_states: set[str] | None) -> list[str]:
    request = load_json(run_dir / "pet_request.json")
    ledger = load_json(run_dir / "references" / "identity-ledger.json")
    prompt_args = build_prompt_args(request, ledger)
    row_dir = run_dir / "prompts" / "rows"
    retry_dir = run_dir / "prompts" / "row-retries"
    row_dir.mkdir(parents=True, exist_ok=True)
    retry_dir.mkdir(parents=True, exist_ok=True)

    refreshed: list[str] = []
    for state, row, frames, purpose in row_specs(request):
        if requested_states is not None and state not in requested_states:
            continue
        (row_dir / f"{state}.md").write_text(
            prepare.row_prompt(prompt_args, state, row, frames, purpose),
            encoding="utf-8",
        )
        (retry_dir / f"{state}.md").write_text(
            prepare.retry_row_prompt(prompt_args, state, row, frames, purpose),
            encoding="utf-8",
        )
        refreshed.append(state)
    return refreshed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--states",
        nargs="*",
        help="Optional row states to refresh. Defaults to all row prompts.",
    )
    args = parser.parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    states = {state for state in (args.states or [])} or None
    refreshed = refresh_prompts(run_dir, states)
    print(
        json.dumps(
            {
                "ok": True,
                "run_dir": str(run_dir),
                "refreshed_states": refreshed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
