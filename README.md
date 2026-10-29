# Schema Drift Lab

An experiment to see what different data-pipeline checks catch when incoming data changes.

The lab starts with 1,000 synthetic game-inventory records, breaks them in nine different ways, and runs the changed data through the same pipeline and four detectors.

The main question this lab aims to answer is **What happens when the data keeps the right shape, but its meaning changes?**

## What the pipeline does

The pipeline reads game-inventory records from JSONL, flattens the nested fields, loads them into SQLite, and calculates six metrics:

- total row count
- number of unequipped items
- item counts by rarity
- average attack by category
- items acquired per day
- average durability

The baseline is a clean run. Each drift is applied separately, and its database is compared with the baseline and labeled: failed loudly (the error names the cause), failed confusingly (it crashed, but the error doesn't mention the cause), passed with corruption (it finished, but values are wrong), or passed clean (identical to the baseline).

## The nine drifts

| Drift | Change |
|---|---|
| `rename_rarity` | Renames the `rarity` field |
| `drop_equipped_slot` | Removes `equipped_slot` |
| `stats_become_list` | Changes the `stats` object into a list |
| `add_column` | Adds a new `guild` field |
| `type_change_level` | Changes `level` from an integer to a string |
| `empty_equipped_slot` | Replaces null slots with empty strings |
| `new_enum_value` | Relabels 20 rows with a new `mythic` rarity |
| `local_time_without_offset` | Shifts timestamps to UTC+4 and removes the offset |
| `durability_scaled` | Multiplies durability values by 10 |

Some of these break the pipeline immediately. Others finish normally but produce different results, and that difference is the point of the experiment. Two of them, `add_column` and `type_change_level`, finish with a database identical to the baseline.

## The detectors

- **Schema snapshot** compares field paths and observed types with the baseline. It is good at structural changes such as missing fields and changed types.
- **Loose Pydantic model** validates records with relaxed rules and restricts `rarity` to the five expected values. Pydantic's default coercion is left on.
- **Strict Pydantic model** requires timezone-aware timestamps, restricts `rarity` and `equipped_slot` to known values, and rejects unknown top-level fields. It does **not** use Pydantic's `strict=True` mode.
- **Statistical profile** compares numeric means, category shares, and null rates with the baseline. It can catch changes that leave the schema untouched.

## Results

No detector caught everything.

| Drift | Outcome | Rows corrupted | Schema | Loose | Strict | Statistical |
|---|---|---:|:---:|:---:|:---:|:---:|
| `rename_rarity` | Failed loudly | n/a | Yes | Yes | Yes | No |
| `drop_equipped_slot` | Failed loudly | n/a | Yes | Yes | Yes | No |
| `stats_become_list` | Failed confusingly | n/a | Yes | Yes | Yes | No |
| `add_column` | Passed clean | 0 | Yes | No | Yes | No |
| `type_change_level` | Passed clean | 0 | Yes | No | No | No |
| `empty_equipped_slot` | Passed with corruption | 205 | Yes | No | Yes | Yes |
| `new_enum_value` | Passed with corruption | 20 | No | Yes | Yes | No |
| `local_time_without_offset` | Passed with corruption | 1,000 | No | No | Yes | No |
| `durability_scaled` | Passed with corruption | 1,000 | No | No | No | Yes |
| **Total caught** | | | **6 / 9** | **4 / 9** | **7 / 9** | **2 / 9** |

Three changes were caught by only one detector: the timezone change (strict model), the `level` type change (schema snapshot), and the durability scaling (statistical profile).

Detection also doesn't always mean harm. Adding an unused column was flagged even though the final database was unchanged.

## Run the lab

You need Python 3.10 or newer and Pydantic v2. SQLite comes with Python.

```bash
pip install pydantic
```

Generate the baseline data, run the pipeline, then run all nine drifts and detectors:

```bash
python generate.py
python pipeline.py
python runner.py
```

The runner compares each result with the clean baseline and prints the detector results.

## Threshold experiment

A separate experiment tests the statistical detector:

```bash
python threshold_tradeoff.py
```

It generates 200 clean datasets from different seeds (skipping the baseline's own seed, which would reproduce the baseline exactly) and tests four mean thresholds. A very small threshold catches small durability shifts, but it also flags normal variation in unrelated numeric fields. A 5% threshold raised false alarms on 23 of 200 clean files, none of them from durability. A 2% threshold raised them on 188 of 200. The category-share check has a fixed threshold, and it raised alarms on 22 of 200 clean files at every setting.

`sensitivity.py` runs larger durability shifts (1.05x up to 10x) against the same detector.

## What this lab is trying to show

A pipeline can be structurally valid and still be wrong. A schema check can tell you a field exists and has the same type. It cannot tell you the producer changed the unit of that field or what a null means.

The detectors see different parts of the problem:

**Schema checks see shape.**

**Contract validation sees the rules you explicitly wrote down.**

**Statistical checks see changes in behavior.**

None of them can infer a semantic agreement that isn't represented in the data or in a contract between producer and consumer. That is why they work better together. Of the four drifts that corrupted data, the schema snapshot caught only one, and only by side effect. The strict model and the statistical profile did the real work, and between them they covered all four.

## Project layout

```
generate.py               builds the synthetic records
pipeline.py               flatten, load into SQLite, compute metrics
drifts.py                 the nine drift definitions
runner.py                 runs every drift and detector
pydantic_detectors.py     loose and strict models
statistical_detectors.py  statistical profile
threshold_tradeoff.py     false-alarm test on 200 clean files
sensitivity.py            larger durability shifts
data/                     baseline, drifted, and clean seed files
results/dbs/              one SQLite database per drift
```

## Limitations

This is a small synthetic experiment, not a production monitoring system. The generated data is simpler and more stable than real data. The statistical detector compares against one fixed baseline, so the baseline's own sampling error carries into every comparison, and its thresholds are intentionally simple.

The goal is not to rank these tools. It is to make their blind spots easy to reproduce and inspect.
