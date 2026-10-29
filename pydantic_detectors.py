import json
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, ValidationError, Field

from detector import Detector


class Stats(BaseModel):
    attack: int
    defense: int
    speed: int


class Attributes(BaseModel):
    durability: int
    tradeable: bool
    bound: bool


class LooseItem(BaseModel):
    item_id: int
    player_id: int
    item_name: str
    category: str
    rarity: Literal["common", "uncommon", "rare", "epic", "legendary"]
    level: int

    # Intentionally loose
    acquired_at: str
    equipped_slot: str | None

    stats: Stats
    attributes: Attributes



class StrictItem(BaseModel):
    model_config = ConfigDict(extra="forbid")  

    item_id: int
    player_id: int
    item_name: str
    category: str
    rarity: Literal["common", "uncommon", "rare", "epic", "legendary"]
    level: int

    acquired_at: AwareDatetime

    equipped_slot: Literal["head", "chest", "legs", "main_hand", "off_hand"] | None

    stats: Stats
    attributes: Attributes



def read_rows(path):
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def check_model(path, model):
    failures = 0
    first_error = None

    for row_number, row in enumerate(read_rows(path), start=1):
        try:
            model(**row)
        except ValidationError as exc:
            failures += 1
            if first_error is None:
                err = exc.errors()[0]
                field = ".".join(str(p) for p in err["loc"])
                first_error = f"row {row_number}: {field}: {err['msg']}"

    if failures:
        message = f"{failures} validation failure(s); first: {first_error}"
    else:
        message = "0 validation failures"

    return {"detected": failures > 0, "failures": failures, "message": message}


def check_loose(baseline_path, incoming_path):
    return check_model(incoming_path, LooseItem)


def check_strict(baseline_path, incoming_path):
    return check_model(incoming_path, StrictItem)


PYDANTIC_LOOSE = Detector(name="pydantic_loose", check=check_loose)
PYDANTIC_STRICT = Detector(name="pydantic_strict", check=check_strict)