"""Schema validation plus continuity rules for a pilot pack.

No network, no credentials. Uses `jsonschema` when installed; otherwise a
small built-in checker covering the subset of keywords the schemas use.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "schemas"


class ValidationError(Exception):
    pass


def load_json(p: Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- schema check
def _fallback_check(schema, data, path="$"):
    """Minimal JSON-Schema subset checker (type, required, enum, const, pattern,
    properties, additionalProperties, items, minimum, maximum, minLength,
    minItems, anyOf). Returns list of error strings."""
    errs = []
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int,
             "number": (int, float), "boolean": bool, "null": type(None)}
    if "anyOf" in schema:
        if not any(not _fallback_check(s, data, path) for s in schema["anyOf"]):
            errs.append(f"{path}: no anyOf branch matched")
        return errs
    if "const" in schema and data != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errs.append(f"{path}: {data!r} not in {schema['enum']}")
    if t:
        ok = isinstance(data, types[t]) and not (t in ("integer", "number") and isinstance(data, bool))
        if not ok:
            errs.append(f"{path}: expected {t}")
            return errs
    if isinstance(data, str):
        if "pattern" in schema and not re.search(schema["pattern"], data):
            errs.append(f"{path}: does not match {schema['pattern']}")
        if len(data) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than minLength")
    if isinstance(data, (int, float)) and not isinstance(data, bool):
        if "minimum" in schema and data < schema["minimum"]:
            errs.append(f"{path}: below minimum")
        if "maximum" in schema and data > schema["maximum"]:
            errs.append(f"{path}: above maximum")
    if isinstance(data, dict):
        for r in schema.get("required", []):
            if r not in data:
                errs.append(f"{path}: missing required '{r}'")
        props = schema.get("properties", {})
        for k, v in data.items():
            if k in props:
                errs += _fallback_check(props[k], v, f"{path}.{k}")
            elif "additionalProperties" in schema:
                ap = schema["additionalProperties"]
                if ap is False:
                    errs.append(f"{path}: unexpected property '{k}'")
                elif isinstance(ap, dict):
                    errs += _fallback_check(ap, v, f"{path}.{k}")
    if isinstance(data, list):
        if len(data) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than minItems")
        if "items" in schema:
            for i, it in enumerate(data):
                errs += _fallback_check(schema["items"], it, f"{path}[{i}]")
    return errs


def check_schema(name: str, data) -> list[str]:
    schema = load_json(SCHEMAS / f"{name}.schema.json")
    try:
        import jsonschema  # type: ignore
        v = jsonschema.Draft202012Validator(schema)
        return [f"$.{'.'.join(str(p) for p in e.path)}: {e.message}" for e in v.iter_errors(data)]
    except ImportError:
        return _fallback_check(schema, data)


# ----------------------------------------------------------- continuity rules
def continuity_errors(project, characters, scene, shots, prompts) -> list[str]:
    errs = []
    char_ids = {c["id"] for c in characters}
    props = {p["prop_id"]: p for p in scene["prop_inventory"]}
    ordered = sorted(shots, key=lambda s: s["ordinal"])
    ids = [s["id"] for s in ordered]
    if len(ids) != len(set(ids)):
        errs.append("duplicate shot ids")
    for s in ordered:
        sid = s["id"]
        if s["scene_id"] != scene["id"]:
            errs.append(f"{sid}: scene_id {s['scene_id']} != {scene['id']}")
        for c in s["character_ids"]:
            if c not in char_ids:
                errs.append(f"{sid}: unknown character {c}")
        for d in s["dialogue"]:
            if d["speaker"] not in s["character_ids"]:
                errs.append(f"{sid}: speaker {d['speaker']} not visible in shot")
        for c in s["character_ids"]:
            if c not in s["screen_positions"] or c not in s["eyelines"]:
                errs.append(f"{sid}: {c} lacks screen position or eyeline")
        # 180-degree axis: left character never looks left, right never looks right
        L, R = scene["axis_180"]["left_character"], scene["axis_180"]["right_character"]
        if s["screen_positions"].get(L) == "right" or s["screen_positions"].get(R) == "left":
            errs.append(f"{sid}: screen positions cross the 180-degree axis")
        if s["eyelines"].get(L) in ("left", "offscreen_left"):
            errs.append(f"{sid}: {L} eyeline crosses the axis")
        if s["eyelines"].get(R) in ("right", "offscreen_right"):
            errs.append(f"{sid}: {R} eyeline crosses the axis")
        for pid, st in s.get("prop_state", {}).items():
            if pid not in props:
                errs.append(f"{sid}: unknown prop {pid}")
            elif st["count_visible"] > props[pid]["count"]:
                errs.append(f"{sid}: {pid} count_visible exceeds inventory")
        for dep in s["dependencies"]:
            if dep not in ids:
                errs.append(f"{sid}: dependency {dep} missing")
            elif ids.index(dep) >= ids.index(sid):
                errs.append(f"{sid}: dependency {dep} is not earlier")
        if s["duration_requested_s"]["max"] < s["duration_requested_s"]["min"]:
            errs.append(f"{sid}: duration max < min")
        # Prompt must exist and contain the exact dialogue verbatim
        p = prompts.get(sid)
        if not p or "structured" not in p:
            errs.append(f"{sid}: no structured prompt")
        else:
            for d in s["dialogue"]:
                if f'"{d["text"]}"' not in p["structured"]:
                    errs.append(f"{sid}: structured prompt lacks verbatim line {d['text']!r}")
    total_min = sum(s["duration_requested_s"]["min"] for s in ordered)
    total_max = sum(s["duration_requested_s"]["max"] for s in ordered)
    pr = project["intended_duration_s"]
    if total_max < pr["min"] or total_min > pr["max"]:
        errs.append(f"shot durations {total_min}-{total_max}s cannot satisfy project {pr['min']}-{pr['max']}s")
    # key prop ownership chain: a single key that changes holder only in a later shot
    key_holders = [(s["id"], s.get("prop_state", {}).get("KEY01", {}).get("holder")) for s in ordered]
    seen = [h for _, h in key_holders if h]
    if seen and seen != sorted(seen, key=lambda h: seen.index(h)):
        errs.append("key holder sequence is not monotonic")
    return errs


def validate_pack(pack_dir: Path) -> dict:
    """Returns {'ok': bool, 'errors': [...], 'pack': {...}}"""
    pack_dir = Path(pack_dir)
    errors: list[str] = []
    files = {}
    for name in ("project", "characters", "scene", "shots", "prompts"):
        p = pack_dir / f"{name}.json"
        if not p.exists():
            errors.append(f"missing {p.name}")
            continue
        try:
            files[name] = load_json(p)
        except json.JSONDecodeError as e:
            errors.append(f"{p.name}: invalid JSON ({e})")
    if errors:
        return {"ok": False, "errors": errors, "pack": files}
    errors += [f"project: {e}" for e in check_schema("project", files["project"])]
    for c in files["characters"]:
        errors += [f"character {c.get('id')}: {e}" for e in check_schema("character", c)]
    errors += [f"scene: {e}" for e in check_schema("scene", files["scene"])]
    for s in files["shots"]:
        errors += [f"shot {s.get('id')}: {e}" for e in check_schema("shot", s)]
    if not errors:
        errors += continuity_errors(files["project"], files["characters"], files["scene"], files["shots"], files["prompts"])
    return {"ok": not errors, "errors": errors, "pack": files}
