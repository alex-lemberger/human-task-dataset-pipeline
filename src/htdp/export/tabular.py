from __future__ import annotations

SUFFIXES: tuple[str, ...] = ("x_m", "y_m", "z_m", "qw", "qx", "qy", "qz", "quality")


def motion_wide(
    rows: list[dict[str, str]],
    trackers: list[str],
) -> tuple[list[str], list[list[str]]]:
    by_tracker: dict[str, dict[str, dict[str, str]]] = {}
    for r in rows:
        by_tracker.setdefault(r["tracker_id"], {})[r["timestamp_s"]] = r
    all_ts = sorted({r["timestamp_s"] for r in rows}, key=float)
    header = ["timestamp_s"] + [f"{t}_{s}" for t in trackers for s in SUFFIXES]
    matrix: list[list[str]] = []
    for ts in all_ts:
        out_row = [ts]
        for t in trackers:
            cell = by_tracker.get(t, {}).get(ts)
            for s in SUFFIXES:
                out_row.append(cell[s] if cell is not None else "n/a")
        matrix.append(out_row)
    return header, matrix


def matrix_to_tsv(header: list[str], matrix: list[list[str]]) -> str:
    lines = ["\t".join(header)]
    lines.extend("\t".join(row) for row in matrix)
    return "\n".join(lines) + "\n"
