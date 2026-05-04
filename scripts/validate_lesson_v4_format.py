#!/usr/bin/env python3
"""
Validate that a lesson JSON matches the structural shape of new_structure_v4.json
(phase-based template: content.lesson_structure has phase_order_config + phases).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Standard four-phase flow from new_structure_v4.json
EXPECTED_TOP_KEYS = frozenset(
    {
        "title",
        "description",
        "languageId",
        "difficultyLevel",
        "estimatedDuration",
        "status",
        "category",
        "content",
    }
)

EXPECTED_CONTENT_KEYS = frozenset(
    {"lesson_metadata", "lesson_structure", "translation_metadata"}
)

EXPECTED_PHASE_ORDER = [
    "phase_1_vocabulary_anchor",
    "phase_2_grammar_engine",
    "phase_3_dialogue",
    "phase_4_sprint_exercises",
]


def _is_i18n_leaf(x: Any) -> bool:
    return (
        isinstance(x, dict)
        and "value" in x
        and "translatable" in x
        and len(x) == 2
    )


def _title_desc_shape_ok(x: Any) -> bool:
    """v4 uses { value, translatable } for title and description."""
    return _is_i18n_leaf(x)


def validate_lesson_v4(data: dict[str, Any], strict_phase_order: bool = True) -> list[str]:
    issues: list[str] = []

    if not isinstance(data, dict):
        return ["root must be a JSON object"]

    top_extra = set(data.keys()) - EXPECTED_TOP_KEYS
    top_missing = EXPECTED_TOP_KEYS - set(data.keys())
    if top_missing:
        issues.append(f"missing top-level keys: {sorted(top_missing)}")
    if top_extra:
        issues.append(f"unexpected top-level keys (v4 template has none): {sorted(top_extra)}")

    if "title" in data and not _title_desc_shape_ok(data["title"]):
        issues.append('title should be { "value": string, "translatable": bool }')
    if "description" in data and not _title_desc_shape_ok(data["description"]):
        issues.append('description should be { "value": string, "translatable": bool }')

    content = data.get("content")
    if not isinstance(content, dict):
        issues.append("content must be an object")
        return issues

    c_missing = EXPECTED_CONTENT_KEYS - set(content.keys())
    c_extra = set(content.keys()) - EXPECTED_CONTENT_KEYS
    if c_missing:
        issues.append(f"content missing keys: {sorted(c_missing)}")
    if c_extra:
        issues.append(f"content has extra keys vs v4 template: {sorted(c_extra)}")

    ls = content.get("lesson_structure")
    if not isinstance(ls, dict):
        issues.append("content.lesson_structure must be an object")
        return issues

    if "phase_order_config" not in ls:
        issues.append("content.lesson_structure missing phase_order_config")
    if "phases" not in ls:
        issues.append("content.lesson_structure missing phases")
    if "module_order_config" in ls or "modules" in ls:
        issues.append(
            "content.lesson_structure uses module_order_config/modules; "
            "this is the modules-canonical format, not v4 phases"
        )

    if isinstance(ls.get("phase_order_config"), dict):
        po = ls["phase_order_config"]
        if "ordering_strategy" not in po:
            issues.append("phase_order_config missing ordering_strategy")
        sel = po.get("selected_order")
        if not isinstance(sel, list):
            issues.append("phase_order_config.selected_order must be a list")
        elif strict_phase_order and sel != EXPECTED_PHASE_ORDER:
            issues.append(
                f"phase_order_config.selected_order must exactly match v4: {EXPECTED_PHASE_ORDER!r}, got {sel!r}"
            )
    else:
        issues.append("phase_order_config must be an object")

    phases = ls.get("phases")
    if not isinstance(phases, dict):
        issues.append("phases must be an object")
        return issues

    p_missing = set(EXPECTED_PHASE_ORDER) - set(phases.keys())
    p_extra = set(phases.keys()) - set(EXPECTED_PHASE_ORDER)
    if p_missing:
        issues.append(f"phases missing expected phase keys: {sorted(p_missing)}")
    if p_extra:
        issues.append(f"phases has unexpected extra keys: {sorted(p_extra)}")

    for pk in EXPECTED_PHASE_ORDER:
        ph = phases.get(pk)
        if not isinstance(ph, dict):
            issues.append(f"phases.{pk} must be an object")
            continue
        for key in ("phase_id", "phase_type", "position_in_lesson"):
            if key not in ph:
                issues.append(f"phases.{pk} missing {key}")

    return issues


def expand_inputs(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.glob("*.json")))
        else:
            out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Lesson JSON files or directories (each directory: all *.json inside)",
    )
    ap.add_argument(
        "--no-strict-order",
        action="store_true",
        help="Do not require selected_order to match the v4 list exactly",
    )
    args = ap.parse_args()
    inputs = expand_inputs(args.paths)

    any_fail = False
    for path in inputs:
        if not path.is_file():
            print(f"{path}: ERROR file not found", file=sys.stderr)
            any_fail = True
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{path}: INVALID JSON — {e}", file=sys.stderr)
            any_fail = True
            continue
        issues = validate_lesson_v4(data, strict_phase_order=not args.no_strict_order)
        if issues:
            any_fail = True
            print(f"{path}: FAIL")
            for i in issues:
                print(f"  - {i}")
        else:
            print(f"{path}: OK (matches new_structure_v4.json envelope + four-phase structure)")

    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
