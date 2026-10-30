# Evidence schema

## `cases.csv`

Required columns:

- `case_id`: stable, nonempty, unique identifier;
- `source_nodeid`: nonempty, unique pytest node ID.

Keep every collected parameter column. The final file must contain 1–20 user-selected rows.

## Profile `manifest.json`

Required structure:

```json
{
  "schema_version": 1,
  "run_id": "baseline-001",
  "kind": "baseline",
  "timestamp_utc": "2026-01-01T00:00:00Z",
  "operator": "operator-name",
  "backend": "ascendc",
  "source": {
    "operator_repo": "/path/to/TileKernels-Nightly",
    "operator_commit": "full-or-short-commit",
    "framework_repo": "/path/to/tilelang-deepseek",
    "framework_commit": "full-or-short-commit"
  },
  "device": {
    "full_soc": "Ascend950PR...",
    "npu_arch": 3510,
    "device_id": "0"
  },
  "environment": {
    "cann": "version",
    "tilelang": "version-or-commit",
    "ptoas": "version"
  },
  "measurement": {
    "boundary": "kernel",
    "warmup": 10,
    "repeat": 100,
    "concurrency": 1,
    "command": "reproducible command"
  },
  "cases_csv": "../../case_selection/cases.csv"
}
```

Use `kind=baseline` for the accepted baseline and `kind=candidate` for an iteration. Add `candidate_id` and `hypothesis` to candidate manifests.

## Profile `summary.csv`

Required columns:

- `case_id`
- `kernel_name`
- `latency_us`
- `status`

Use `status=pass` only when the row maps to the target case and kernel and the aggregate is valid. Optional metric columns may include bandwidth, pipe utilization, cache, synchronization, or launch counts. Preserve metric units in column names.

## Precision summary

Use one row per selected case with:

- `case_id`, `status`, `atol`, `rtol`;
- observed error metrics supported by the repository test;
- command and result artifact path.

## Candidate comparison

For each case record baseline latency, candidate latency, percentage change, and status. Positive `improvement_pct` means faster:

`improvement_pct = (baseline_us - candidate_us) / baseline_us * 100`

Also report geometric-mean speedup across valid positive latencies and the worst regression. Never hide individual cases behind the aggregate.
