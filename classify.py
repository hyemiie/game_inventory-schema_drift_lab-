import sqlite3


def load_rows(db_path):
    """Return (rows keyed by item_id, total row count including duplicates)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM inventory").fetchall()
        return {r["item_id"]: dict(r) for r in rows}, len(rows)
    finally:
        conn.close()


def classify(result, baseline_db, drifted_db, drift_fields=()):
    if result["status"] == "error":
        error_text = result["error"].lower()
        names_cause = any(f.lower() in error_text for f in drift_fields)
        return {
            "label": "failed_loudly" if names_cause else "failed_confusingly",
            "rows_affected": None,
            "loss_cells": 0,
            "corrupt_cells": 0,
            "extra_rows": 0,
        }

    base, _ = load_rows(baseline_db)
    drift, drift_total = load_rows(drifted_db)

    loss = corrupt = 0
    affected = set()

    for item_id, baseline_row in base.items():
        drifted_row = drift.get(item_id)

        if drifted_row is None:
            loss += 1
            affected.add(item_id)
            continue

        for column, baseline_value in baseline_row.items():
            drifted_value = drifted_row.get(column)
            if drifted_value == baseline_value:
                continue

            affected.add(item_id)
            if drifted_value is None and baseline_value is not None:
                loss += 1
            else:
                corrupt += 1

    # Rows that shouldn't exist includning new ids, plus duplicates collapsed by the dict
    extra = len(set(drift) - set(base)) + (drift_total - len(drift))

    if corrupt or extra:
        label = "passed_with_corruption"
    elif loss:
        label = "passed_with_data_loss"
    else:
        label = "passed_clean"

    return {
        "label": label,
        "rows_affected": len(affected),
        "loss_cells": loss,
        "corrupt_cells": corrupt,
        "extra_rows": extra,
    }