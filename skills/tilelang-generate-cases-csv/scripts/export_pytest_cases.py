#!/usr/bin/env python3
"""Collect pytest parameters without running tests and export CSV candidates."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import sys
import tempfile
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Any

import pytest


METADATA_COLUMNS = (
    "selected",
    "case_id",
    "test_name",
    "source_nodeid",
    "collection_markers",
    "operator_file",
    "pytest_file",
    "tk_test_level_env",
)


class CaseCollector:
    """Capture collected pytest items after parametrization has been expanded."""

    def __init__(self) -> None:
        self.items: list[pytest.Item] = []

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.items = list(session.items)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator-file", required=True, type=Path, help="Target operator source file used as provenance.")
    parser.add_argument("--pytest-file", required=True, type=Path, help="Pytest file that generates the cases.")
    parser.add_argument("--output", required=True, type=Path, help="Output candidates CSV path.")
    parser.add_argument("--project-root", type=Path, help="Project root used as cwd and import root.")
    parser.add_argument(
        "--selector",
        action="append",
        default=[],
        help="Test function selector, for example test_cast_back. Repeat to select multiple tests.",
    )
    parser.add_argument(
        "--test-level",
        type=int,
        choices=(0, 1, 2),
        default=2,
        help="TK_TEST_LEVEL used during collection. Default: 2 (full).",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Additional pytest collection argument. Repeat as needed; use --pytest-arg=VALUE for values beginning with '-'.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing output file.")
    return parser.parse_args()


def find_project_root(pytest_file: Path) -> Path:
    markers = ("pyproject.toml", "setup.cfg", "setup.py", ".git")
    for parent in (pytest_file.parent, *pytest_file.parents):
        if any((parent / marker).exists() for marker in markers):
            return parent
    return pytest_file.parent


def flatten_mapping(prefix: str, value: dict[Any, Any], output: dict[str, Any]) -> None:
    for raw_key, nested_value in value.items():
        key = str(raw_key)
        nested_key = f"{prefix}.{key}" if prefix else key
        if isinstance(nested_value, dict):
            flatten_mapping(nested_key, nested_value, output)
        else:
            output[nested_key] = nested_value


def extract_parameters(item: pytest.Item) -> dict[str, Any]:
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return {}

    extracted: dict[str, Any] = {}
    for name, value in callspec.params.items():
        if name == "params" and isinstance(value, dict):
            current: dict[str, Any] = {}
            flatten_mapping("", value, current)
        elif isinstance(value, dict):
            current = {}
            flatten_mapping(name, value, current)
        else:
            current = {name: value}

        for key, current_value in current.items():
            safe_key = f"param.{key}" if key in METADATA_COLUMNS else key
            if safe_key in extracted:
                raise ValueError(f"Parameter column collision in {item.nodeid}: {safe_key}")
            extracted[safe_key] = current_value
    return extracted


def normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return normalize_value(value.value)
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): normalize_value(nested) for key, nested in value.items()}
    return str(value)


def serialize_value(value: Any) -> str:
    normalized = normalize_value(value)
    if normalized is None:
        return "null"
    if isinstance(normalized, bool):
        return "true" if normalized else "false"
    if isinstance(normalized, (list, dict)):
        return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(normalized)


def build_pytest_targets(pytest_file: Path, selectors: list[str]) -> list[str]:
    if not selectors:
        return [str(pytest_file)]
    targets = []
    for selector in selectors:
        normalized = selector.strip()
        if not normalized:
            raise ValueError("Empty --selector is not allowed")
        targets.append(f"{pytest_file}::{normalized.lstrip(':')}")
    return targets


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
    operator_file = args.operator_file.resolve()
    pytest_file = args.pytest_file.resolve()
    if not operator_file.is_file():
        raise FileNotFoundError(f"Operator file does not exist: {operator_file}")
    if not pytest_file.is_file():
        raise FileNotFoundError(f"Pytest file does not exist: {pytest_file}")

    project_root = (args.project_root or find_project_root(pytest_file)).resolve()
    if not project_root.is_dir():
        raise NotADirectoryError(f"Project root does not exist: {project_root}")

    os.environ["TK_TEST_LEVEL"] = str(args.test_level)
    os.environ.setdefault("TILELANG_PRINT_ON_COMPILATION", "0")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(project_root))

    collector = CaseCollector()
    pytest_targets = build_pytest_targets(pytest_file, args.selector)
    pytest_args = [
        "--collect-only",
        "-q",
        "--disable-warnings",
        "-p",
        "no:cacheprovider",
        *args.pytest_arg,
        *pytest_targets,
    ]

    original_cwd = Path.cwd()
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    try:
        os.chdir(project_root)
        with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
            exit_code = pytest.main(pytest_args, plugins=[collector])
    finally:
        os.chdir(original_cwd)

    if exit_code != pytest.ExitCode.OK:
        details = "\n".join(part for part in (captured_stdout.getvalue(), captured_stderr.getvalue()) if part.strip())
        raise RuntimeError(f"pytest collection failed with exit code {int(exit_code)}\n{details}")
    if not collector.items:
        raise RuntimeError("pytest collection succeeded but produced no test items")

    parameter_columns: list[str] = []
    parameter_column_set: set[str] = set()
    extracted_items: list[tuple[pytest.Item, dict[str, Any]]] = []
    for item in collector.items:
        params = extract_parameters(item)
        extracted_items.append((item, params))
        for column in params:
            if column not in parameter_column_set:
                parameter_column_set.add(column)
                parameter_columns.append(column)

    rows: list[dict[str, str]] = []
    test_counts: Counter[str] = Counter()
    case_id_to_nodeid: dict[str, str] = {}
    seen_nodeids: set[str] = set()
    for item, params in extracted_items:
        if item.nodeid in seen_nodeids:
            raise ValueError(f"Duplicate pytest nodeid collected: {item.nodeid}")
        seen_nodeids.add(item.nodeid)
        case_id = f"case_{hashlib.sha256(item.nodeid.encode('utf-8')).hexdigest()[:16]}"
        collision_nodeid = case_id_to_nodeid.get(case_id)
        if collision_nodeid is not None and collision_nodeid != item.nodeid:
            raise ValueError(f"case_id hash collision between {collision_nodeid} and {item.nodeid}")
        case_id_to_nodeid[case_id] = item.nodeid

        test_name = getattr(item, "originalname", None) or item.name.split("[", 1)[0]
        test_counts[test_name] += 1
        row = {
            "selected": "",
            "case_id": case_id,
            "test_name": test_name,
            "source_nodeid": item.nodeid,
            "collection_markers": ";".join(sorted({marker.name for marker in item.iter_markers()})),
            "operator_file": str(operator_file),
            "pytest_file": str(pytest_file),
            "tk_test_level_env": str(args.test_level),
        }
        row.update({key: serialize_value(value) for key, value in params.items()})
        rows.append(row)

    output = args.output.resolve()
    write_csv_atomic(output, [*METADATA_COLUMNS, *parameter_columns], rows, args.force)

    print(f"Exported {len(rows)} collected pytest cases to {output}")
    for test_name, count in sorted(test_counts.items()):
        print(f"  {test_name}: {count}")
    print("No tests or kernels were executed; pytest ran in collection-only mode.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileExistsError, FileNotFoundError, NotADirectoryError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
