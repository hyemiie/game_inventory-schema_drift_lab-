import json
from collections import Counter
from pathlib import Path
from statistics import fmean

from detector import Detector

MEAN_SHIFT = 0.25      
SHARE_SHIFT = 0.05    
NULL_SHIFT = 0.05     
MAX_CATEGORIES = 10    


def flatten(obj, prefix=""):
    for key, value in obj.items():
        field = f"{prefix}{key}"
        if isinstance(value, dict):
            yield from flatten(value, field + ".")
        else:
            yield field, value


def profile(path):
    columns, n = {}, 0
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            n += 1
            for field, value in flatten(json.loads(line)):
                columns.setdefault(field, []).append(value)
    return columns, n


def is_numeric(values):
    return bool(values) and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in values
    )


def is_categorical(values):
    return (
        bool(values)
        and all(isinstance(v, str) for v in values)
        and len(set(values)) <= MAX_CATEGORIES
    )


def statistical_check(baseline_path, incoming_path):
    base, base_n = profile(baseline_path)
    inc, inc_n = profile(incoming_path)
    findings = []

    for field in sorted(set(base) & set(inc)):
        b, i = base[field], inc[field]

        null_b, null_i = b.count(None) / base_n, i.count(None) / inc_n
        if abs(null_b - null_i) > NULL_SHIFT:
            findings.append(f"{field}: null rate {null_b:.0%} -> {null_i:.0%}")

        b_vals = [v for v in b if v is not None]
        i_vals = [v for v in i if v is not None]
        if not b_vals or not i_vals:
            continue

        if is_numeric(b_vals) and is_numeric(i_vals):
            mean_b, mean_i = fmean(b_vals), fmean(i_vals)
            if mean_b != 0 and abs(mean_i - mean_b) / abs(mean_b) > MEAN_SHIFT:
                findings.append(f"{field}: mean {mean_b:.1f} -> {mean_i:.1f}")

        elif is_categorical(b_vals):
            cb, ci = Counter(b_vals), Counter(i_vals)
            for value in sorted(set(cb) | set(ci)):
                share_b = cb[value] / len(b_vals)
                share_i = ci[value] / len(i_vals)
                if abs(share_b - share_i) > SHARE_SHIFT:
                    findings.append(
                        f"{field}={value!r}: share {share_b:.0%} -> {share_i:.0%}"
                    )

    return {
        "detected": bool(findings),
        "message": "; ".join(findings) if findings else "no statistical shift",
    }


STATISTICAL = Detector(name="statistical_profile", check=statistical_check)