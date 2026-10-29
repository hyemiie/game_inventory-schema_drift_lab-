import json
from pathlib import Path

from classify import classify
from detector import SCHEMA_DIFF
from drifts import ALL_DRIFTS, apply_drift
from pipeline import run_pipeline
from pydantic_detectors import PYDANTIC_LOOSE, PYDANTIC_STRICT
from statistical_detectors import STATISTICAL

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "data" / "baseline.jsonl"
DB_DIR = ROOT / "results" / "dbs"
DB_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED = json.loads((ROOT / "results" / "expected.json").read_text())
DETECTORS = [SCHEMA_DIFF, PYDANTIC_LOOSE, PYDANTIC_STRICT, STATISTICAL]

baseline_db = DB_DIR / "baseline.db"
baseline_result = run_pipeline(BASELINE, db_path=str(baseline_db))
if baseline_result["status"] != "ok":
    raise SystemExit(f"Baseline run failed: {baseline_result['error']}")

rows = []   

for drift in ALL_DRIFTS:
    dst = ROOT / "data" / "drifted" / f"{drift.name}.jsonl"
    drifted_db = DB_DIR / f"{drift.name}.db"

    apply_drift(drift, BASELINE, dst)
    result = run_pipeline(dst, db_path=str(drifted_db))
    outcome = classify(result, baseline_db, drifted_db, drift.fields)

    print(f"\n=== {drift.name} ===")
    print(f"outcome: {outcome['label']} (rows affected: {outcome['rows_affected']})")

    detected = {}
    for det in DETECTORS:
        d = det.check(str(BASELINE), str(dst))
        detected[det.name] = d["detected"]
        print(f"  {det.name}: {'DETECTED' if d['detected'] else 'missed'} | {d['message'][:110]}")

    error = result.get("error")
    if error:
        print("  pipeline error:", error)
    else:
        for k, v in result["metrics"].items():
            if v != EXPECTED[k]:
                print(f"  metric {k}: {str(EXPECTED[k])[:50]} -> {str(v)[:50]}")

    rows.append((drift, outcome, detected, error))


names = [d.name for d in DETECTORS]
lines = [
    "## Results matrix",
    "",
    "| Drift | Outcome | Rows affected | " + " | ".join(names) + " |",
    "|---|---|---|" + "---|" * len(names),
]

for drift, outcome, detected, _ in rows:
    affected = outcome["rows_affected"] if outcome["rows_affected"] is not None else "-"
    cells = " | ".join("✅" if detected[n] else "❌" for n in names)
    lines.append(f"| {drift.name} | {outcome['label']} | {affected} | {cells} |")

totals = " | ".join(f"{sum(r[2][n] for r in rows)}/{len(rows)}" for n in names)
lines.append(f"| **Total caught** | | | {totals} |")

lines += ["", "## Pipeline errors", "", "| Drift | Label | Error |", "|---|---|---|"]
for drift, outcome, _, error in rows:
    if error:
        lines.append(f"| {drift.name} | {outcome['label']} | `{error}` |")

lines += ["", "## Caught by only one detector", ""]
for drift, _, detected, _ in rows:
    catchers = [n for n in names if detected[n]]
    if len(catchers) == 1:
        lines.append(f"- **{drift.name}**: only {catchers[0]}")
    elif not catchers:
        lines.append(f"- **{drift.name}**: no detector")

(ROOT / "results" / "matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\nWrote results/matrix.md")