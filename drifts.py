import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Drift:
    name: str
    description: str
    apply: Callable[[dict], dict]
    fields: tuple = ()  


def rename_rarity(row):
    row["rarity_tier"] = row.pop("rarity")
    return row


def drop_equipped_slot(row):
    row.pop("equipped_slot")
    return row


def add_column(row):
    row["guild"] = "none"
    return row


def type_change_level(row):
    row["level"] = str(row["level"])
    return row


def new_enum_value(row):
    if row["item_id"] % 50 == 0:        
        row["rarity"] = "mythic"
    return row


def stats_become_list(row):
    s = row["stats"]
    row["stats"] = [s["attack"], s["defense"], s["speed"]]
    return row


def durability_scaled(row):
    row["attributes"]["durability"] *= 10   
    return row  


def local_time_without_offset(row):
    timestamp = row["acquired_at"]
    if not timestamp.endswith("Z"):
        raise ValueError(f"Expected UTC timestamp ending in Z, got: {timestamp!r}")

    utc_time = datetime.fromisoformat(timestamp.removesuffix("Z") + "+00:00")
    local_time = utc_time + timedelta(hours=4)
    row["acquired_at"] = local_time.replace(tzinfo=None).isoformat()
    return row


def empty_equipped_slot(row):
    if row["equipped_slot"] is None:
        row["equipped_slot"] = ""
    return row



RENAME_RARITY = Drift("rename_rarity", "rarity renamed to rarity_tier",
                      rename_rarity, fields=("rarity",))

DROP_EQUIPPED_SLOT = Drift("drop_equipped_slot", "equipped_slot removed from every record",
                           drop_equipped_slot, fields=("equipped_slot",))

LOCAL_TIME = Drift("local_time_without_offset",
                   "acquired_at shifted to UTC+04:00 wall time, offset removed",
                   local_time_without_offset, fields=("acquired_at",))

EMPTY_EQUIPPED_SLOT = Drift("empty_equipped_slot", "null equipped_slot replaced by empty string",
                            empty_equipped_slot, fields=("equipped_slot",))

ADD_COLUMN = Drift("add_column", "new field guild added to every record",
                   add_column, fields=("guild",))

TYPE_CHANGE_LEVEL = Drift("type_change_level", "level changed from int to string",
                          type_change_level, fields=("level",))

NEW_ENUM_VALUE = Drift("new_enum_value", "rarity gains 'mythic' on 20 rows",
                       new_enum_value, fields=("rarity",))

STATS_BECOME_LIST = Drift("stats_become_list", "stats object replaced by an array",
                          stats_become_list, fields=("stats",))

DURABILITY_SCALED = Drift("durability_scaled", "durability multiplied by 10 (new meaning)",
                          durability_scaled, fields=("durability",))

ALL_DRIFTS = [
    RENAME_RARITY, DROP_EQUIPPED_SLOT, LOCAL_TIME, EMPTY_EQUIPPED_SLOT,
    ADD_COLUMN, TYPE_CHANGE_LEVEL, NEW_ENUM_VALUE, STATS_BECOME_LIST,
    DURABILITY_SCALED,
]



def apply_drift(drift, src, dst):
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with src.open("r", encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            row = drift.apply(json.loads(line))
            fout.write(json.dumps(row, separators=(",", ":")) + "\n")