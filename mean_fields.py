from collections import Counter
from pathlib import Path
import statistical_detectors as sd

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "data" / "baseline.jsonl"
files = sorted((ROOT / "data" / "clean_seeds").glob("seed_*.jsonl"))

for t in [0.25, 0.10, 0.05, 0.02]:
    sd.MEAN_SHIFT = t
    by_field = Counter()
    any_alarm = 0
    for path in files:
        r = sd.statistical_check(str(BASELINE), str(path))
        parts = r["message"].split("; ") if r["detected"] else []
        hits = [p for p in parts if "mean" in p]
        any_alarm += bool(hits)
        for p in hits:
            by_field[p.split(":")[0]] += 1
    dur = by_field.get("attributes.durability", 0)
    print(f"threshold {t:.0%}: any numeric field {any_alarm}/{len(files)}, "
          f"durability only {dur}/{len(files)}")
    print("   by field:", dict(by_field))
