import sqlite3
from pathlib import Path

DB_DIR = Path("results") / "dbs"
def counts(path):
    con = sqlite3.connect(path)
    rows = con.execute(
        "SELECT rarity, COUNT(*) FROM inventory GROUP BY rarity"
    ).fetchall()
    con.close()
    return dict(rows)

before = counts(DB_DIR / "baseline.db")
after = counts(DB_DIR / "new_enum_value.db")

for r in sorted(set(before) | set(after)):
    print(r, before.get(r, 0), "->", after.get(r, 0))