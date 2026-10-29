import json
import sys
from pydantic import Field, ValidationError
from pydantic_detectors import Attributes, StrictItem


class RangedAttributes(Attributes):
    durability: int = Field(ge=10, le=100)


class StrictWithRange(StrictItem):
    attributes: RangedAttributes


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


baseline = {r["item_id"]: r for r in load(sys.argv[1])}
drifted = load(sys.argv[2])

flagged = 0
missed_originals = set()
for row in drifted:
    try:
        StrictWithRange(**row)
    except ValidationError:
        flagged += 1
    else:
        missed_originals.add(baseline[row["item_id"]]["attributes"]["durability"])

print(f"{flagged} of {len(drifted)} flagged")
print("original durability of rows that passed:", sorted(missed_originals))