#!/usr/bin/env python3
"""Validate user selections in a candidate CSV and write the final cases.csv."""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from pathlib import Path


TRUE_VALUES = {"1", "true", "yes", "y", "x", "selected"}
FALSE_VALUES = {"", "0", "false", "no", "n"}
REQUIRED_COLUMNS = {"selected", "case_id", "source_nodeid"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Candidate CSV containing the selected column.")
    parser.add_argument("--output", required=True, type=Path, help="Final cases.csv path.")
    parser.add_argument("--max-cases", type=int, default=20, help="Maximum selected cases. Default: 20.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output file.")
    return parser.parse_args()


def is_selected(raw_value: str, row_number: int) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    accepted = ", ".join(sorted(TRUE_VALUES | FALSE_VALUES))
    raise ValueError(f"Unknown selected value at CSV row {row_number}: {raw_value!r}. Accepted values: {accepted}")


def write_csv_atomic(output: Path, fieldnames: list[str], rows: list[dict[str, str]], force: bool) -> None:
    if output.exists() and not force:
        raise FileExistsError(f"Output already exists; pass --force to replace it: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=output.parent, delete=False) as handle:
            temp_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)
        temp_path.replace(output)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def main() -> int:
    args = parse_args()
    if not 1 <= args.max_cases <= 20:
        raise ValueError("--max-cases must be between 1 and the hard limit of 20")

    input_path = args.input.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Candidate CSV does not exist: {input_path}")

    with input_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Candidate CSV has no header")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Candidate CSV contains duplicate column names")
        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise ValueError(f"Candidate CSV is missing required columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    if not rows:
        raise ValueError("Candidate CSV contains no cases")
    for row_number, row in enumerate(rows, start=2):
        if None in row:
            raise ValueError(f"Candidate CSV row {row_number} has more values than the header")
        missing_values = [name for name, value in row.items() if value is None]
        if missing_values:
            raise ValueError(
                f"Candidate CSV row {row_number} has fewer values than the header; missing: {', '.join(missing_values)}"
            )

    all_case_ids = [row["case_id"].strip() for row in rows]
    if any(not case_id for case_id in all_case_ids):
        raise ValueError("Every candidate row must have a non-empty case_id")
    if len(all_case_ids) != len(set(all_case_ids)):
        raise ValueError("Candidate CSV contains duplicate case_id values")

    selected_rows = [row for row_number, row in enumerate(rows, start=2) if is_selected(row["selected"], row_number)]
    if not selected_rows:
        raise ValueError("No cases selected. Mark 1-20 rows in the selected column with yes")
    if len(selected_rows) > args.max_cases:
        raise ValueError(f"Selected {len(selected_rows)} cases, exceeding the limit of {args.max_cases}")

    selected_nodeids = [row["source_nodeid"].strip() for row in selected_rows]
    if any(not nodeid for nodeid in selected_nodeids):
        raise ValueError("Every selected row must have a non-empty source_nodeid")
    if len(selected_nodeids) != len(set(selected_nodeids)):
        raise ValueError("Selected cases contain duplicate source_nodeid values")

    output_fieldnames = [name for name in reader.fieldnames if name != "selected"]
    output_rows = [{key: value for key, value in row.items() if key != "selected"} for row in selected_rows]
    output_path = args.output.resolve()
    if output_path == input_path:
        raise ValueError("Final output must differ from the candidate CSV path")
    write_csv_atomic(output_path, output_fieldnames, output_rows, args.force)

    print(f"Wrote {len(output_rows)} selected cases to {output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
