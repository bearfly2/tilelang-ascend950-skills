# Stage contracts

Each stage consumes only accepted outputs from the preceding stages. Mark a stage `PASS`, `FAIL`, or `BLOCKED`; never use `DONE` for an unverified stage.

## S0 — Facts

Inputs:

- operator and framework repository paths;
- intended operator and target pytest file;
- runtime host or remote execution endpoint.

Exit contract:

- Ascend950PR/DT and NpuArch 3510 detector evidence;
- repository branches and commits;
- imported TileLang path/version and PTOAS/CANN versions;
- backend, measurement boundary, warmup, repeat, concurrency, and precision thresholds;
- `TASK.md` containing all facts and unresolved assumptions.

## S1 — Cases

Inputs: source/test mapping accepted in S0.

Exit contract:

- complete `cases_candidates.csv` from pytest collection;
- explicit user selection of 1–20 rows;
- validated `cases.csv` with stable IDs and source node IDs;
- coverage statement for shape, dtype, tail, semantic path, and dispatch path;
- zero selected cases that skip the target kernel without explicit exclusion rationale.

Pause after candidate export until the user selects cases.

## S2 — Design

Inputs: accepted task facts and final cases.

Exit contract:

- mathematical semantics and Golden reference;
- independent reference or immutable Golden manifest with source, case mapping, dtype/layout, seed or input hash, and tolerance evidence;
- dispatch and kernel branch mapping;
- tile/core mapping and memory-resource model;
- AIC/AIV, GM/UB/L1/L0, reduction/GEMM, tail, and synchronization decisions as applicable;
- supported API evidence from the imported TileLang checkout;
- test and profiling plan tied to case IDs.

## S3 — Baseline implementation and precision

Exit contract:

- reproducible build command and successful compile evidence for the selected backend (Ascend by default; PTO only when explicitly selected);
- core precision tests pass, then every selected case passes;
- baseline source commit or reversible patch;
- actual target kernel is launched for every performance case;
- precision summary maps one row to every case ID.

Do not advance when correctness is conditional, flaky, or based on a different backend.

## S4 — Baseline profiling

Exit contract:

- `baseline/profile/manifest.json` satisfies the evidence schema;
- `baseline/profile/summary.csv` has exactly one accepted aggregate row per selected case;
- raw profiler artifacts exist and can be mapped to case and kernel launch;
- all cases use identical documented measurement conditions;
- unknown metrics remain unknown rather than inferred.

## S5 — Diagnosis and plan

Exit contract:

- each case belongs to exactly one baseline bottleneck group;
- bottleneck claims cite raw or summarized evidence;
- current resource model is documented per group;
- no more than three candidates, each with hypothesis, affected cases, expected metric, implementation evidence, risk, validation, and rollback;
- candidate order is explicit.

## S6 — Candidate implementation

Exit contract:

- one primary hypothesis implemented;
- changed files and diff recorded;
- rollback point preserved;
- build and core precision pass before full validation.

## S7 — Candidate validation

Exit contract:

- all selected precision cases pass;
- profiling is repeated under baseline conditions;
- comparison accounts for every selected case and reports regressions;
- decision is `KEEP` or `REVERT` using acceptance gates;
- reverted candidates leave the accepted baseline unchanged.

Repeat S6–S7 for the next candidate only after the previous decision is complete.

## S8 — Delivery

Exit contract:

- target repository test and review rules pass;
- final source corresponds to the accepted profiling result;
- final report links facts, cases, precision, raw profiles, comparisons, rejected candidates, and remaining risks;
- rollback instructions and reproducible commands are present.
