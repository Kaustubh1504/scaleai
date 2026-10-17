# 06. Keep rows with a unique id, collect errors for the rest
# Standalone: copy this file as-is. Deps: stdlib

def rows_by_id(header: list[str], rows, id_col: str, file: str, errors: list) -> list[tuple[int, dict]]:
    """Skips malformed rows, empty ids and repeat ids (first wins); skipped rows aren't "seen".
    Appends {"file", "row", "id", "error"} with malformed_row / missing_<id_col> / duplicate_<id_col>."""
    kept, seen = [], set()
    for n, values in rows:
        if len(values) != len(header):
            errors.append({"file": file, "row": n, "id": None, "error": "malformed_row"})
            continue
        row = dict(zip(header, values))
        rid = row[id_col]
        if not rid:
            errors.append({"file": file, "row": n, "id": None, "error": f"missing_{id_col}"})
            continue
        if rid in seen:
            errors.append({"file": file, "row": n, "id": rid, "error": f"duplicate_{id_col}"})
            continue
        seen.add(rid)
        kept.append((n, row))
    return kept
