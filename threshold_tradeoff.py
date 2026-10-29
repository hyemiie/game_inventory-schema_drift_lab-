import json
from collections import Counter
from pathlib import Path

import statistical_detectors as sd
from drifts import Drift, apply_drift
from generate import generate_rows

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "data" / "baseline.jsonl"
CLEAN_DIR = ROOT / "data" / "clean_seeds"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

SEEDS = [s for s in range(1, 202) if s != 42]
THRESHOLDS = [0.25, 0.10, 0.05, 0.02]
FACTORS = [1.02, 1.05, 1.1, 1.2, 1.3]


def make_durability_drift(factor):
    def apply(row):
        row["attributes"]["durability"] = round(row["attributes"]["durability"] * factor)
        return row
    return Drift(f"durability_x{factor}", "", apply)


clean_paths = []
for seed in SEEDS:
    path = CLEAN_DIR / f"seed_{seed}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in generate_rows(1000, seed=seed):
            f.write(json.dumps(row, separators=(",", ":")) + "\n")
    clean_paths.append(path)

scaled_paths = {}
for factor in FACTORS:
    drift = make_durability_drift(factor)
    dst = ROOT / "data" / "drifted" / f"{drift.name}.jsonl"
    apply_drift(drift, BASELINE, dst)
    scaled_paths[factor] = dst

print(f"share threshold fixed at {sd.SHARE_SHIFT:.0%}, null threshold at {sd.NULL_SHIFT:.0%}\n")

for t in THRESHOLDS:
    sd.MEAN_SHIFT = t

    mean_alarms = share_alarms = 0
    share_fields = Counter()
    for path in clean_paths:
        r = sd.statistical_check(str(BASELINE), str(path))
        parts = r["message"].split("; ") if r["detected"] else []
        mean_alarms += any("mean" in p for p in parts)
        share_alarms += any("share" in p for p in parts)
        for p in parts:
            if "share" in p:
                share_fields[p.split(":")[0]] += 1

    caught = [
        x for x in FACTORS
        if any("mean" in p for p in
               sd.statistical_check(str(BASELINE), str(scaled_paths[x]))["message"].split("; "))
    ]

    n = len(clean_paths)
    print(f"mean threshold {t:.0%}: mean alarms {mean_alarms}/{n}, "
          f"share alarms {share_alarms}/{n}, durability factors caught {caught}")
    print("   share alarms by field:", dict(share_fields))
