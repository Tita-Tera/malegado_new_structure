#!/usr/bin/env python3
"""
Fix content.lesson_metadata.lesson_config.lesson_number for lessons already written under
Converted Dialogues/* Out/lesson_XX.json.

Rule:
  actual_lesson_number = (dialogue_number - 1) * 15 + within_dialogue_lesson_number

Example:
  Converted Dialogues/dialogue 2 Out/lesson_01.json -> lesson_number = 16

Updates ONLY that field; leaves everything else unchanged.
Logs ONLY mismatches or problems (missing keys, parse errors, write errors).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_RE_OUT_DIR = re.compile(r"^dialogue\s+(?P<d>\d+)\s+Out$", re.IGNORECASE)
_RE_LESSON_FILE = re.compile(r"^lesson_(?P<n>\d{2})\.json$", re.IGNORECASE)


def compute_expected(dialogue_n: int, within_n: int) -> int:
    return (dialogue_n - 1) * 15 + within_n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--converted-root",
        type=Path,
        default=Path("Converted Dialogues"),
        help="Root folder containing '<dialogue N> Out' subfolders (default: Converted Dialogues)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Do not write; just report mismatches")
    args = ap.parse_args()

    root: Path = args.converted_root
    if not root.exists():
        print(f"[ERROR] not found: {root}", file=sys.stderr)
        return 2

    out_dirs = [p for p in sorted(root.iterdir()) if p.is_dir()]
    changed = 0
    failed = 0

    for d in out_dirs:
        m = _RE_OUT_DIR.match(d.name)
        if not m:
            continue
        dialogue_n = int(m.group("d"))

        for f in sorted(d.glob("lesson_*.json")):
            m2 = _RE_LESSON_FILE.match(f.name)
            if not m2:
                continue
            within_n = int(m2.group("n"))
            expected = compute_expected(dialogue_n, within_n)

            try:
                data: dict[str, Any] = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                failed += 1
                print(f"[FAIL][JSON] {f}: {e}")
                continue

            try:
                lc = (
                    data["content"]["lesson_metadata"]["lesson_config"]
                    if isinstance(data.get("content"), dict)
                    else None
                )
            except Exception:
                lc = None

            if not isinstance(lc, dict):
                failed += 1
                print(f"[FAIL][SHAPE] {f}: missing content.lesson_metadata.lesson_config")
                continue

            current = lc.get("lesson_number")
            if current == expected:
                continue

            changed += 1
            print(f"[FIX] {f}: lesson_number {current!r} -> {expected}")
            if args.dry_run:
                continue

            lc["lesson_number"] = expected
            data["content"]["lesson_metadata"]["lesson_config"] = lc
            try:
                f.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except Exception as e:
                failed += 1
                print(f"[FAIL][WRITE] {f}: {e}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

