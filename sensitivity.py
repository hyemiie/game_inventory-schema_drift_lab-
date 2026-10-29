from pathlib import Path

from drifts import Drift, apply_drift
from statistical_detectors import STATISTICAL

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "data" / "baseline.jsonl"


def make_durability_drift(factor):
    def apply(row):
        row["attributes"]["durability"] = round(row["attributes"]["durability"] * factor)
        return row
    return Drift(f"durability_x{factor}", f"durability scaled by {factor}", apply)


for factor in [1.05, 1.1, 1.2, 1.3, 1.5, 2, 10]:
    drift = make_durability_drift(factor)
    dst = ROOT / "data" / "drifted" / f"{drift.name}.jsonl"
    apply_drift(drift, BASELINE, dst)
    result = STATISTICAL.check(str(BASELINE), str(dst))
    print(f"x{factor}: {'DETECTED' if result['detected'] else 'missed'} | {result['message']}")