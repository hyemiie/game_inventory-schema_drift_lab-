import json

from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Detector:
    name: str
    check: Callable[[str, str], dict]   

def infer_schema(file_path):
    schema = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                walk(json.loads(line), "", schema)
    return schema


def walk(obj, prefix, schema):
    for key, value in obj.items():
        field = f"{prefix}{key}"
        if isinstance(value, dict):
            walk(value, field + ".", schema)
        else:
            schema.setdefault(field, set()).add(type(value).__name__)


def schema_diff_check(baseline_path, incoming_path):
    baseline = infer_schema(baseline_path)
    incoming = infer_schema(incoming_path)

    base_fields = set(baseline)
    incoming_fields = set(incoming)

    removed = base_fields - incoming_fields
    added = incoming_fields - base_fields
    retyped = {
        f: (baseline[f], incoming[f])
        for f in base_fields & incoming_fields
        if baseline[f] != incoming[f]
    }

    parts = []
    if removed:
        parts.append(f"removed: {sorted(removed)}")
    if added:
        parts.append(f"added: {sorted(added)}")
    for f, (before, after) in sorted(retyped.items()):
        parts.append(f"retyped {f}: {sorted(before)} -> {sorted(after)}")

    return {
        "detected": bool(parts),
        "message": "; ".join(parts) if parts else "no schema change",
    }


SCHEMA_DIFF = Detector(name="schema_snapshot_diff", check=schema_diff_check)


if __name__ == "__main__":
    for name in ["rename_rarity", "drop_equipped_slot",
                 "local_time_without_offset", "empty_equipped_slot"]:
        result = SCHEMA_DIFF.check("data/baseline.jsonl", f"data/drifted/{name}.jsonl")
        print(f"{name}: {result}")
    