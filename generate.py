import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 42
ROW_COUNT = 1_000
OUTPUT = Path(__file__).resolve().parent / "data" / "baseline.jsonl"

# Using datetime.now() here would break determinism.
BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

SLOTS = ["head", "chest", "legs", "main_hand", "off_hand"]


def generate_rows(count, seed=SEED):
    rng = random.Random(seed)

    categories = ["weapon", "armor", "consumable", "accessory"]
    rarities = ["common", "uncommon", "rare", "epic", "legendary"]

    for item_id in range(1, count + 1):
        category = rng.choice(categories)
        rarity = rng.choices(rarities, weights=[60, 25, 10, 4, 1])[0]

        # 1. Timestamp in UTC, for the local-time vs UTC semantic drift
        acquired_at = BASE_TIME + timedelta(seconds=rng.randint(0, 180 * 24 * 3600))

        # 2. Nullable field: about 20% of items are not equipped
        equipped_slot = None if rng.random() < 0.20 else rng.choice(SLOTS)

        yield {
            "item_id": item_id,
            "player_id": rng.randint(1, 250),
            "item_name": f"{category}_{item_id}",
            "category": category,
            "rarity": rarity,
            "level": rng.randint(1, 50),
            "acquired_at": acquired_at.isoformat().replace("+00:00", "Z"),
            "equipped_slot": equipped_slot,
            "stats": {
                "attack": rng.randint(0, 100),
                "defense": rng.randint(0, 100),
                "speed": rng.randint(0, 100),
            },
            "attributes": {
                "durability": rng.randint(10, 100),
                "tradeable": rng.choice([True, False]),
                "bound": rng.choice([True, False]),
            },
        }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = list(generate_rows(ROW_COUNT))

    with OUTPUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")

    print(f"Generated {len(rows):,} rows → {OUTPUT}")


if __name__ == "__main__":
    main()