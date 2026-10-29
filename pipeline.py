import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def extract(input_path):
    """Read a JSONL file and yield one dict per line."""
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def transform(row):
    """
    Normalize one inventory record.

    Intentionally assumes the baseline schema is correct.
    Missing, renamed, or incompatible fields should fail naturally.
    """
    acquired_at = datetime.fromisoformat(row["acquired_at"].replace("Z", "+00:00"))

    return {
        "item_id": row["item_id"],
        "player_id": row["player_id"],
        "item_name": row["item_name"],
        "category": row["category"],
        "rarity": row["rarity"],
        "level": row["level"],
        "acquired_at": acquired_at,

        "attack": row["stats"]["attack"],
        "defense": row["stats"]["defense"],
        "speed": row["stats"]["speed"],

        "durability": row["attributes"]["durability"],
        "tradeable": row["attributes"]["tradeable"],
        "bound": row["attributes"]["bound"],

        "equipped_slot": row["equipped_slot"],
    }


def load(records, db_path=":memory:"):
    """Load transformed inventory records into SQLite."""
    conn = sqlite3.connect(db_path)

    conn.execute("DROP TABLE IF EXISTS inventory")

    conn.execute(
        """
        CREATE TABLE inventory (
            item_id       INTEGER NOT NULL,
            player_id     INTEGER,
            item_name     TEXT,
            category      TEXT,
            rarity        TEXT NOT NULL,
            level         INTEGER,
            acquired_at   TEXT NOT NULL,
            attack        INTEGER,
            defense       INTEGER,
            speed         INTEGER,
            durability    INTEGER,
            tradeable     INTEGER,
            bound         INTEGER,
            equipped_slot TEXT
        )
        """
    )

    conn.executemany(
        """
        INSERT INTO inventory (
            item_id, player_id, item_name, category, rarity, level,
            acquired_at, attack, defense, speed, durability,
            tradeable, bound, equipped_slot
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["item_id"],
                r["player_id"],
                r["item_name"],
                r["category"],
                r["rarity"],
                r["level"],
                r["acquired_at"].isoformat(),
                r["attack"],
                r["defense"],
                r["speed"],
                r["durability"],
                r["tradeable"],
                r["bound"],
                r["equipped_slot"],
            )
            for r in records
        ],
    )

    conn.commit()
    return conn


def compute_metrics(conn):
    """Run the downstream queries whose results drift can damage."""

    total_rows = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]

    null_equipped_slot = conn.execute(
        "SELECT COUNT(*) FROM inventory WHERE equipped_slot IS NULL"
    ).fetchone()[0]

    rarity_counts = {
        rarity: count
        for rarity, count in conn.execute(
            """
            SELECT rarity, COUNT(*)
            FROM inventory
            GROUP BY rarity
            ORDER BY rarity
            """
        )
    }

    avg_attack_by_category = {
        category: round(avg_attack, 2)
        for category, avg_attack in conn.execute(
            """
            SELECT category, AVG(attack)
            FROM inventory
            GROUP BY category
            ORDER BY category
            """
        )
    }

    acquired_per_day = {
        day: count
        for day, count in conn.execute(
            """
            SELECT DATE(acquired_at), COUNT(*)
            FROM inventory
            GROUP BY DATE(acquired_at)
            ORDER BY DATE(acquired_at)
            """
        )
    }

    avg_durability = conn.execute(
        "SELECT AVG(durability) FROM inventory"
    ).fetchone()[0]

    if avg_durability is not None:
        avg_durability = round(avg_durability, 2)

    return {
        "total_rows": total_rows,
        "null_equipped_slot": null_equipped_slot,
        "item_count_per_rarity": rarity_counts,
        "avg_attack_per_category": avg_attack_by_category,
        "items_acquired_per_day": acquired_per_day,
        "avg_durability": avg_durability,
    }


def run_pipeline(input_path, db_path=":memory:"):
    """
    Run the complete pipeline.

    Exceptions become outcome data instead of terminating the lab.
    """
    conn = None

    try:
        rows = extract(input_path)
        records = [transform(row) for row in rows]

        conn = load(records, db_path)
        metrics = compute_metrics(conn)

        return {"status": "ok", "metrics": metrics}

    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}

    finally:
        if conn is not None:
            conn.close()


def save_expected(result, output_path=ROOT / "results" / "expected.json"):
    """Save a successful baseline run as the known-good result."""
    if result["status"] != "ok":
        raise RuntimeError(f"Cannot save failed pipeline run: {result['error']}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8") as f:
        json.dump(result["metrics"], f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    input_path = ROOT / "data" / "baseline.jsonl"

    result = run_pipeline(input_path)

    print(json.dumps(result, indent=2, sort_keys=True))

    if result["status"] == "ok":
        save_expected(result)
        print("\nSaved known-good metrics to results/expected.json")


if __name__ == "__main__":
    main()