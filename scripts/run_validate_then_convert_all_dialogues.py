#!/usr/bin/env python3
"""
Run v4 validator then modules-canonical converter for every lesson JSON under Dialogues/.

- Validates first (phase-based v4 envelope).
- Converts only if validation passes.
- Logs ONLY failures (validation failures, conversion errors, write errors, JSON parse errors).

By default writes output to:
  Converted Dialogues/<dialogue folder> Out/<lesson_XX.json>
to match the existing naming style (e.g. Converted Dialogues/dialogue 1 Out/).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Import existing scripts as libraries (no subprocess noise).
from convert_v4_to_modules_canonical import convert_v4_document
from validate_lesson_v4_format import validate_lesson_v4


def iter_lesson_jsons(dialogues_root: Path) -> list[Path]:
    out: list[Path] = []
    for d in sorted([p for p in dialogues_root.iterdir() if p.is_dir()]):
        out.extend(sorted(d.glob("lesson_*.json")))
    return out


def out_dialogue_dir(output_root: Path, dialogue_dirname: str) -> Path:
    # Naming style: "dialogue 1" -> "dialogue 1 Out"
    return output_root / f"{dialogue_dirname} Out"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--dialogues-root",
        type=Path,
        default=Path("Dialogues"),
        help="Folder containing dialogue subfolders (default: Dialogues)",
    )
    ap.add_argument(
        "--output-root",
        type=Path,
        default=Path("Converted Dialogues"),
        help="Where to write converted lessons (default: Converted Dialogues)",
    )
    ap.add_argument(
        "--no-strict-order",
        action="store_true",
        help="Do not require phase_order_config.selected_order to exactly match v4",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write converted files; still validates and reports failures",
    )
    args = ap.parse_args()

    dialogues_root: Path = args.dialogues_root
    output_root: Path = args.output_root

    if not dialogues_root.exists():
        print(f"[ERROR] dialogues root not found: {dialogues_root}", file=sys.stderr)
        return 2

    lessons = iter_lesson_jsons(dialogues_root)
    if not lessons:
        print(f"[ERROR] no lesson_*.json found under: {dialogues_root}", file=sys.stderr)
        return 2

    strict = not args.no_strict_order
    failed = 0

    for src in lessons:
        # Read/parse JSON
        try:
            raw: dict[str, Any] = json.loads(src.read_text(encoding="utf-8"))
        except Exception as e:
            failed += 1
            print(f"[FAIL][JSON] {src}: {e}")
            continue

        # Validate
        issues = validate_lesson_v4(raw, strict_phase_order=strict)
        if issues:
            failed += 1
            print(f"[FAIL][VALIDATE] {src}")
            for issue in issues:
                print(f"  - {issue}")
            continue

        # Convert
        try:
            converted = convert_v4_document(raw, source_path=str(src.resolve()))
        except Exception as e:
            failed += 1
            print(f"[FAIL][CONVERT] {src}: {e}")
            continue

        # Write output (match existing Converted Dialogues naming style)
        if args.dry_run:
            continue

        try:
            # src.parent is: Dialogues/<dialogue N>
            dialogue_dirname = src.parent.name
            dest_dir = out_dialogue_dir(output_root, dialogue_dirname)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            dest.write_text(
                json.dumps(converted, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception as e:
            failed += 1
            print(f"[FAIL][WRITE] {src} -> {dest if 'dest' in locals() else '(unknown)'}: {e}")
            continue

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

