#!/usr/bin/env python3
"""
Convert a new_structure_v4.json-style lesson (phase_order_config + phases, i18n leaves)
into modules-canonical shape (module_order_config + modules, plain strings),
preserving all semantic field values.

phase_2_grammar_engine is split into:
  - module_2_functional_grammar  — pro_tip → grammar_points; modifiers → grammar_engine_modifiers
  - module_3_sentence_building   — sentence_building[] (same content as in the grammar phase)

See new_structure_v4_2_2_modules_canonical.json for the target envelope.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MODULE_ORDER = [
    "module_1_core_vocabulary",
    "module_2_functional_grammar",
    "module_3_sentence_building",
    "module_dialogue_practice",
    "module_sprint_exercises",
]

DEFAULT_SB_PROMPT_SOURCE = "Put the words in the correct order:"
DEFAULT_SB_PROMPT_TARGET = "[TRANSLATE]"
DEFAULT_SB_EXERCISE_TYPE = "Drag-and-Drop Sentence Builder"


def is_i18n_leaf(x: Any) -> bool:
    return isinstance(x, dict) and "value" in x and "translatable" in x and len(x) == 2


def unwrap_value(x: Any) -> Any:
    """Turn {value, translatable} leaves into plain JSON values recursively."""
    if is_i18n_leaf(x):
        return unwrap_value(x["value"])
    if isinstance(x, dict):
        return {k: unwrap_value(v) for k, v in x.items()}
    if isinstance(x, list):
        return [unwrap_value(v) for v in x]
    return x


def unwrap_str(x: Any, default: str = "") -> str:
    u = unwrap_value(x)
    if u is None:
        return default
    if isinstance(u, str):
        return u
    return json.dumps(u, ensure_ascii=False)


def lesson_metadata_to_plain(meta: dict[str, Any]) -> dict[str, Any]:
    return unwrap_value(meta)


def pro_tip_to_grammar_points(pro_tip: dict[str, Any]) -> list[dict[str, Any]]:
    if not pro_tip:
        return []
    examples_out: list[dict[str, Any]] = []
    raw_examples = pro_tip.get("examples")
    if isinstance(raw_examples, list):
        for ex in raw_examples:
            if not isinstance(ex, dict):
                continue
            u = unwrap_value(ex)
            text_src = u.get("text_source") or u.get("source_text") or ""
            examples_out.append(
                {
                    "example_id": u.get("example_id", "ex_001"),
                    "text_source": text_src,
                    "text_target": u.get("text_target", "[TRANSLATE]"),
                    "register": u.get("register", "neutral"),
                    "usage_note_source": u.get("usage_note_source", ""),
                    "usage_note_target": u.get("usage_note_target", "[TRANSLATE]"),
                    "audio_normal": u.get("audio_normal", "[GENERATE]"),
                    "audio_slow": u.get("audio_slow", "[GENERATE]"),
                }
            )
    src = pro_tip.get("examples_source") or []
    tgt = pro_tip.get("examples_target") or []
    if isinstance(src, list) and src and not examples_out:
        for i, s in enumerate(src):
            examples_out.append(
                {
                    "example_id": f"ex_legacy_{i + 1}",
                    "text_source": unwrap_str(s),
                    "text_target": tgt[i] if isinstance(tgt, list) and i < len(tgt) else "[TRANSLATE]",
                    "register": "neutral",
                    "usage_note_source": "",
                    "usage_note_target": "[TRANSLATE]",
                    "audio_normal": "[GENERATE]",
                    "audio_slow": "[GENERATE]",
                }
            )

    gp = {
        "grammar_id": pro_tip.get("tip_id", "gram_001"),
        "concept_source": unwrap_str(pro_tip.get("concept_source")),
        "concept_target": pro_tip.get("concept_target", "[TRANSLATE]"),
        "explanation_source": unwrap_str(pro_tip.get("explanation_source")),
        "explanation_target": pro_tip.get("explanation_target", "[TRANSLATE]"),
        "focus_type": pro_tip.get("focus_type", "variations"),
        "examples": examples_out,
    }
    return [gp]


def modifiers_to_engine_modifiers(modifiers: Any) -> list[dict[str, Any]]:
    if not isinstance(modifiers, list):
        return []
    out: list[dict[str, Any]] = []
    for m in modifiers:
        if not isinstance(m, dict):
            continue
        u = unwrap_value(m)
        item = {
            "modifier_id": u.get("modifier_id", "mod_001"),
            "modifier_source": u.get("modifier_source", ""),
            "modifier_target": u.get("modifier_target", "[TRANSLATE]"),
            "example_source": u.get("example_source", ""),
            "example_target": u.get("example_target", "[TRANSLATE]"),
            "explanation_source": u.get("explanation_source", ""),
            "explanation_target": u.get("explanation_target", "[TRANSLATE]"),
            "audio_normal": u.get("audio_normal", "[GENERATE]"),
            "audio_slow": u.get("audio_slow", "[GENERATE]"),
        }
        out.append(item)
    return out


def related_word_to_vocab_item(rw: dict[str, Any], phrase_id: int) -> dict[str, Any]:
    u = unwrap_value(rw)
    wid = u.get("word_id") or f"rel_{phrase_id}"
    tooltip_src = u.get("meaning_source") or ""
    tooltip_tgt = u.get("meaning_target", "[TRANSLATE]")
    if u.get("linguistic_info"):
        li = u["linguistic_info"]
    else:
        li = {
            "tooltip_source": tooltip_src,
            "tooltip_target": tooltip_tgt,
            "pronunciation_guide": u.get("pronunciation_guide", "[GENERATE_FOR_TARGET]"),
        }
    media = u.get("media") or {"image_url": "", "audio_normal": "[GENERATE]", "audio_slow": "[GENERATE]"}
    return {
        "vocab_id": wid,
        "phrase_id": phrase_id,
        "source_text": u.get("source_text", ""),
        "target_text": u.get("target_text", "[TRANSLATE]"),
        "part_of_speech": u.get("part_of_speech", ""),
        "frequency_rank": phrase_id,
        "difficulty": u.get("difficulty", 1),
        "context": u.get("context") or {},
        "linguistic_info": li,
        "media": media,
        "exercises": {
            "exercise_selection_strategy": u.get("exercises", {}).get("exercise_selection_strategy", "sequential")
            if isinstance(u.get("exercises"), dict)
            else "sequential",
            "selected_exercises": u.get("exercises", {}).get("selected_exercises", [])
            if isinstance(u.get("exercises"), dict)
            else [],
        },
    }


def core_phrase_to_vocab_item(core: dict[str, Any]) -> dict[str, Any]:
    u = unwrap_value(core)
    vid = u.get("phrase_id") or u.get("vocab_id") or "core_001"
    phrase_id = 1
    li = u.get("linguistic_info") or {}
    media = u.get("media") or {"image_url": "", "audio_normal": "[GENERATE]", "audio_slow": "[GENERATE]"}
    return {
        "vocab_id": vid,
        "phrase_id": phrase_id,
        "source_text": u.get("source_text", ""),
        "target_text": u.get("target_text", "[TRANSLATE]"),
        "part_of_speech": u.get("part_of_speech", ""),
        "frequency_rank": 1,
        "difficulty": u.get("difficulty", 1),
        "context": u.get("context") or {},
        "linguistic_info": li,
        "media": media,
        "exercises": {
            "exercise_selection_strategy": "sequential",
            "selected_exercises": [],
        },
    }


def convert_phase_1_vocab(p1: dict[str, Any]) -> dict[str, Any]:
    core = p1.get("core_phrase") or {}
    items: list[dict[str, Any]] = [core_phrase_to_vocab_item(core)]
    rel = p1.get("related_words") or []
    if isinstance(rel, list):
        for i, rw in enumerate(rel, start=2):
            if isinstance(rw, dict):
                items.append(related_word_to_vocab_item(rw, i))

    core_plain = unwrap_value(core)
    core_src = ""
    if isinstance(core_plain, dict):
        core_src = core_plain.get("source_text") or ""

    lr_in = p1.get("listen_repeat") or {}
    lr = unwrap_value(lr_in)
    if isinstance(lr, dict) and isinstance(lr.get("audio_stimulus"), dict):
        ast = lr["audio_stimulus"]
        if "text_to_speak_target" not in ast and core_src:
            ast = {**ast, "text_to_speak_target": core_src}
        lr = {**lr, "audio_stimulus": ast}

    qm = unwrap_value(p1.get("quick_match") or {})

    return {
        "module_id": "module_1",
        "module_name": unwrap_str(p1.get("phase_name"), "Vocabulary Anchor"),
        "module_code": "VOCAB",
        "position_in_lesson": int(p1.get("position_in_lesson", 1)),
        "enabled": p1.get("enabled", True),
        "required": p1.get("required", True),
        "estimated_duration_seconds": p1.get("estimated_duration_seconds", 60),
        "title_source": unwrap_str(p1.get("title_source")),
        "title_target": p1.get("title_target", "[TRANSLATE]"),
        "module_type": "Vocabulary",
        "vocabulary_items": items,
        "vocabulary_anchor_listen_repeat": lr,
        "vocabulary_anchor_quick_match": qm,
    }


def convert_phase_2_split(
    p2: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    pro_tip = p2.get("pro_tip") or {}
    sentence_building = p2.get("sentence_building") or []

    grammar_points = pro_tip_to_grammar_points(pro_tip if isinstance(pro_tip, dict) else {})
    grammar_mods = modifiers_to_engine_modifiers(
        p2.get("grammar_engine_modifiers") if p2.get("grammar_engine_modifiers") is not None else p2.get("modifiers")
    )

    mod2 = {
        "module_id": "module_2",
        "module_name": unwrap_str(p2.get("phase_name"), "Grammar Engine"),
        "module_code": p2.get("phase_code", "GRAMMAR"),
        "position_in_lesson": int(p2.get("position_in_lesson", 2)),
        "enabled": p2.get("enabled", True),
        "required": p2.get("required", True),
        "estimated_duration_seconds": p2.get("estimated_duration_seconds", 45),
        "title_source": unwrap_str(p2.get("title_source")),
        "title_target": p2.get("title_target", "[TRANSLATE]"),
        "module_type": "Grammar",
        "grammar_points": grammar_points,
        "grammar_engine_modifiers": grammar_mods,
    }

    sb_exercises: list[dict[str, Any]] = []
    if isinstance(sentence_building, list):
        for ex in sentence_building:
            if not isinstance(ex, dict):
                continue
            u = unwrap_value(ex)
            if "exercise_type" not in u:
                u["exercise_type"] = DEFAULT_SB_EXERCISE_TYPE
            if "prompt_source" not in u:
                u["prompt_source"] = DEFAULT_SB_PROMPT_SOURCE
            if "prompt_target" not in u:
                u["prompt_target"] = DEFAULT_SB_PROMPT_TARGET
            hints_plain = u.get("hints")
            if hints_plain is not None:
                if "hints_source" not in u:
                    u["hints_source"] = hints_plain
                if "hints_target" not in u:
                    u["hints_target"] = "[TRANSLATE]"
            sb_exercises.append(u)

    mod3 = {
        "module_id": "module_3",
        "module_name": "Sentence Building",
        "module_code": "SENTENCE",
        "position_in_lesson": 3,
        "enabled": p2.get("enabled", True),
        "required": p2.get("required", True),
        "estimated_duration_seconds": max(
            60,
            int(p2.get("estimated_duration_seconds") or 0) if sb_exercises else 60,
        ),
        "title_source": "Build sentences",
        "title_target": "[TRANSLATE]",
        "module_type": "SentenceBuilding",
        "exercises": sb_exercises,
    }

    return mod2, mod3


def convert_phase_3_dialogue(p3: dict[str, Any]) -> dict[str, Any]:
    setting = unwrap_str(p3.get("setting"))
    context = unwrap_str(p3.get("context"))
    turns_in = p3.get("dialogue") or []
    turns_out: list[dict[str, Any]] = []
    if isinstance(turns_in, list):
        for t in turns_in:
            if not isinstance(t, dict):
                continue
            u = unwrap_value(t)
            if "text_source" in u and isinstance(u["text_source"], str):
                pass
            if u.get("audio_file") and not u.get("audio_normal"):
                u.setdefault("audio_normal", u["audio_file"])
            u.setdefault("audio_slow", "[GENERATE]")
            turns_out.append(u)

    return {
        "module_id": "module_dialogue_practice",
        "module_name": unwrap_str(p3.get("phase_name"), "Dialogue Practice"),
        "module_code": p3.get("phase_code", "DIALOGUE"),
        "position_in_lesson": int(p3.get("position_in_lesson", 4)),
        "enabled": p3.get("enabled", True),
        "required": p3.get("required", True),
        "estimated_duration_seconds": p3.get("estimated_duration_seconds", 90),
        "title_source": unwrap_str(p3.get("title_source")),
        "title_target": p3.get("title_target", "[TRANSLATE]"),
        "module_type": "Conversations",
        "setting_source": setting,
        "setting_target": "[TRANSLATE]",
        "context_source": context,
        "context_target": "[TRANSLATE]",
        "setting": setting,
        "context": context,
        "dialogue": turns_out,
    }


def convert_phase_4_sprint(p4: dict[str, Any]) -> dict[str, Any]:
    base = unwrap_value({k: v for k, v in p4.items() if k not in ("phase_id", "phase_name", "phase_code", "phase_type")})
    base["module_id"] = "module_sprint_exercises"
    base["module_name"] = unwrap_str(p4.get("phase_name"), "Sprint & review")
    base["module_code"] = p4.get("phase_code", "SPRINT")
    base["module_type"] = "Review"
    base["position_in_lesson"] = int(p4.get("position_in_lesson", 5))
    for old in ("phase_id", "phase_name", "phase_code", "phase_type"):
        base.pop(old, None)
    return base


def convert_v4_document(doc: dict[str, Any], source_path: str | None = None) -> dict[str, Any]:
    content = doc.get("content") or {}
    phases = (content.get("lesson_structure") or {}).get("phases") or {}
    if not isinstance(phases, dict):
        raise ValueError("Invalid lesson: content.lesson_structure.phases missing")

    p1 = phases.get("phase_1_vocabulary_anchor") or {}
    p2 = phases.get("phase_2_grammar_engine") or {}
    p3 = phases.get("phase_3_dialogue") or {}
    p4 = phases.get("phase_4_sprint_exercises") or {}

    m1 = convert_phase_1_vocab(p1 if isinstance(p1, dict) else {})
    m2, m3 = convert_phase_2_split(p2 if isinstance(p2, dict) else {})
    m4 = convert_phase_3_dialogue(p3 if isinstance(p3, dict) else {})
    m5 = convert_phase_4_sprint(p4 if isinstance(p4, dict) else {})

    po = (content.get("lesson_structure") or {}).get("phase_order_config") or {}
    ordering = po.get("ordering_strategy", "standard")

    new_ls = {
        "module_order_config": {
            "ordering_strategy": ordering,
            "selected_order": list(MODULE_ORDER),
        },
        "modules": {
            "module_1_core_vocabulary": m1,
            "module_2_functional_grammar": m2,
            "module_3_sentence_building": m3,
            "module_dialogue_practice": m4,
            "module_sprint_exercises": m5,
        },
    }

    meta_plain = lesson_metadata_to_plain(content.get("lesson_metadata") or {})

    out_content = {
        "lesson_metadata": meta_plain,
        "lesson_structure": new_ls,
        "translation_metadata": unwrap_value(content.get("translation_metadata") or {}),
    }

    lesson_id = ""
    if isinstance(meta_plain, dict):
        lesson_id = str(meta_plain.get("lesson_id", ""))

    out: dict[str, Any] = {
        "title": unwrap_str(doc.get("title")),
        "description": unwrap_str(doc.get("description")),
        "languageId": doc.get("languageId", ""),
        "difficultyLevel": doc.get("difficultyLevel", "BEGINNER"),
        "estimatedDuration": doc.get("estimatedDuration", 5),
        "status": doc.get("status", "DRAFT"),
        "category": doc.get("category", "home"),
        "content": out_content,
        "metadata": {
            "lessonType": "malegado",
            "uploadSchema": "modules_canonical_v1",
            "convertedFrom": "new_structure_v4_phases",
            "sourcePath": source_path or "",
            "sourceLessonId": lesson_id,
        },
    }
    return out


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
        "inputs",
        nargs="+",
        type=Path,
        help="Lesson JSON files or directories (*.json); phases-based v4 lessons only",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file when exactly one input is given (default: stdout)",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        help="Write each converted file here using the same basename as the source",
    )
    args = ap.parse_args()
    inputs = expand_inputs(args.inputs)

    if len(inputs) > 1 and args.output:
        print("Use --output-dir with multiple inputs, not -o/--output", file=sys.stderr)
        return 1
    if len(inputs) > 1 and not args.output_dir:
        print("Multiple inputs require --output-dir", file=sys.stderr)
        return 1

    out_dir = args.output_dir
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    rc = 0
    for inp in inputs:
        if not inp.is_file():
            print(f"Not found: {inp}", file=sys.stderr)
            rc = 1
            continue
        try:
            raw = json.loads(inp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"{inp}: invalid JSON — {e}", file=sys.stderr)
            rc = 1
            continue
        try:
            converted = convert_v4_document(raw, source_path=str(inp.resolve()))
        except ValueError as e:
            print(f"{inp}: {e}", file=sys.stderr)
            rc = 1
            continue

        text = json.dumps(converted, ensure_ascii=False, indent=2) + "\n"
        if out_dir is not None:
            dest = out_dir / inp.name
            dest.write_text(text, encoding="utf-8")
            print(f"{inp} -> {dest}")
        elif len(inputs) == 1 and args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
