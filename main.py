import csv
import json
import random
from pathlib import Path

SEED = 42
ROW_COUNT = 1_000
OUTPUT = Path("data/baseline.csv")


def generate_rows(count):
    random.seed(SEED)

    categories = [
        "weapon",
        "armor",
        "consumable",
        "accessory",
    ]

    rarities = [
        "common",
        "uncommon",
        "rare",
        "epic",
        "legendary",
    ]

    for item_id in range(1, count + 1):
        category = random.choice(categories)
        rarity = random.choice(rarities)

        yield {
            "item_id": item_id,
            "player_id": random.randint(1, 250),
            "item_name": f"{category}_{item_id}",
            "category": category,
            "rarity": rarity,
            "level": random.randint(1, 50),
            "stats": json.dumps(
                {
                    "attack": random.randint(0, 100),
                    "defense": random.randint(0, 100),
                    "speed": random.randint(0, 100),
                },
                separators=(",", ":"),
            ),
            "attributes": json.dumps(
                {
                    "durability": random.randint(10, 100),
                    "tradeable": random.choice([True, False]),
                    "bound": random.choice([True, False]),
                },
                separators=(",", ":"),
            ),
        }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    rows = list(generate_rows(ROW_COUNT))
    fieldnames = rows[0].keys()

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows):,} rows → {OUTPUT}")


if __name__ == "__main__":
    main()