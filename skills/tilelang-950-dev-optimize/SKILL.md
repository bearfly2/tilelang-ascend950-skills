---
name: tilelang-950-dev-optimize
description: Orchestrate evidence-gated development and performance optimization of TileLang operators for Ascend950 with the Ascend backend as the default and PTO as an explicit optional backend. Use when Codex must design, implement, test, profile, diagnose, optimize, review, or deliver an operator on Ascend950, especially when work spans cases.csv selection, precision gates, msprof evidence, bottleneck attribution, single-variable optimization iterations, and regression acceptance.
---

# Ascend950 TileLang development and optimization

Coordinate existing Skills. Do not duplicate their API knowledge, templates, profiling commands, or repository test rules.

## Backend policy

Use the TileLang Ascend backend by default: `{backend}=ascendc` and
`TILELANG_DEFAULT_TARGET=ascend`. Use PTO only when the user explicitly requests
it or when a task records an explicit PTO comparison, setting
`{backend}=pto` and `TILELANG_DEFAULT_TARGET=pto` for the entire comparable run.
Never silently switch, fall back, or compare results across backends. The kernel
and test source must remain backend-neutral; select the backend only in the
launch environment.

## Reference and Golden input contract

Before S2 design, prefer an executable independent reference over precomputed
Golden tensors. The reference must not call the TileLang DUT, reuse its lowered
IR, or share implementation-specific helper code. It must define every
substantive output, dtype conversion/rounding point, layout rule, and supported
edge behavior used by the selected cases.

Accept either of these forms:

- **Reference function (preferred):** a reviewable CPU/PyTorch or authoritative
  framework implementation, with deterministic input generation and a fixed
  seed. Record its source path, version/commit, device, and invocation.
- **Golden tensors:** paired input/output files plus a manifest containing
  `case_id`, shape, dtype, layout/stride, attributes, serialization format,
  seed or input hash, and comparison tolerance. Golden data is immutable test
  evidence, not a substitute for an undocumented contract.

For either form, provide the public signature, all inputs and outputs, valid
shape/dtype/range constraints, attributes (including quantization scales and
zero-points), tolerance (`rtol`/`atol` or exact comparison), and expected
error/gradient/state behavior when applicable. If no executable reference or
Golden data is available, stop before S2 implementation and request the
mathematical contract and authoritative source; do not fabricate expected
outputs from the DUT.

## Establish the target

1. Load `ascendc-env-check` and run its architecture detector on the machine that will execute the kernel.
2. Require detector evidence containing an Ascend950PR or Ascend950DT full SoC and `npu_arch=3510`.
3. Load `npu-arch` with platform `Ascend950` and record the returned capability evidence.
4. Stop if detection fails, conflicts, or reports another platform. A user-stated target does not replace runtime evidence.
5. When development is local and execution is remote, record both environments and collect device evidence on the remote host.

Read [skill-routing.md](references/skill-routing.md) before invoking another Skill. Use the listed source precedence when duplicate names exist.

## Create the task workspace

Use `optimization/<operator>/` under the target operator repository. Never write operator outputs into a Skill or CANNBot source directory.

Read [output-layout.md](references/output-layout.md) and create only the artifacts required for the active stage. Record:

- operator source, public API, dispatch/build entry, pytest file, target branch, and commit;
- imported TileLang source path and commit, PTOAS/CANN versions, backend selection, and device evidence;
- precision thresholds, performance metric, warmup/repeat/concurrency settings, and regression limits.

## Execute the state machine

Read [stage-contracts.md](references/stage-contracts.md). Execute stages in order and require each exit contract before advancing.

1. **S0 — Facts:** freeze repositories, environment, backend, device, and comparison conditions.
2. **S1 — Cases:** load `tilelang-generate-cases-csv`; export the full pytest-derived candidate set, pause for user selection, then finalize 1–20 cases. Load `tilelang-op-test-design` with platform `Ascend950` to assess coverage and acceptance.
3. **S2 — Design:** load `tilelang-op-design` with platform `Ascend950`. Use repository-local `tilelang-ascend`, `tilelang-layout`, or other framework Skills only when the task changes or depends on framework semantics.
4. **S3 — Implement and establish precision:** load `tilelang-op-develop` with platform `Ascend950` and the selected backend (Ascend by default); then use the target repository's own `run-tests` instructions. Produce a reproducible, precision-passing baseline before profiling.
5. **S4 — Baseline profiling:** load `tilelang-op-profiling` with platform `Ascend950` and the selected backend. Load `ops-profiling` only for call-boundary identification, unusual launch chains, explicit cross-backend comparison, or evidence not covered by the TileLang-specific Skill.
6. **S5 — Diagnose and plan:** load `tilelang-perf-optimize` after all selected cases have latency and available profiling evidence. Use `tilelang-perf-optimization` with platform `Ascend950` for the CANNBot end-to-end optimization workflow, applying only rules directly evidenced for the selected backend. Produce at most three falsifiable, reversible candidates.
7. **S6 — Implement one candidate:** use `tilelang-op-develop` plus the Ascend950 performance reference selected in [skill-routing.md](references/skill-routing.md). Load `tilelang-scalar-optimization` only for proven scalar-heavy paths.
8. **S7 — Revalidate:** rerun compile, core precision, all selected precision cases, and identical-condition profiling. Keep or revert the candidate using [acceptance-gates.md](references/acceptance-gates.md).
9. **S8 — Deliver:** load `tilelang-review` with platform `Ascend950`; then follow the target repository's `review`, `run-tests`, and `ci` Skills when present. Produce the final evidence-linked report.

## Enforce iteration discipline

- Change one primary performance hypothesis per iteration.
- Preserve an explicit rollback point before modifying code.
- Do not infer a bottleneck from latency alone. Label it unknown when metrics are insufficient.
- Do not compare runs with different device, versions, cases, warmup, repeat, concurrency, backend, or measurement boundary.
- Do not optimize a case that fails precision or does not launch the target kernel.
- Account for every selected case in baseline, candidate, and final tables.
- Report regressions even when aggregate performance improves.
- Revert an iteration that fails a hard gate; do not stack another optimization on an invalid result.

## Validate artifacts

Use the scripts in `scripts/` from PowerShell:

```powershell
./scripts/Validate-Cases.ps1 -CasesCsv <path/to/cases.csv>
./scripts/Validate-ProfileArtifacts.ps1 -RunDir <baseline/profile> -CasesCsv <path/to/cases.csv> -Backend ascendc
./scripts/Compare-ProfileRuns.ps1 -BaselineSummary <baseline/summary.csv> -CandidateSummary <candidate/summary.csv> -OutputJson <comparison.json>
./scripts/Validate-Delivery.ps1 -TaskRoot <optimization/operator>
```

Read [evidence-schema.md](references/evidence-schema.md) before generating manifests or summaries. Scripts validate structure and arithmetic; they do not decide whether an optimization is technically sound.

## Stop conditions

Stop the current stage and report the missing evidence when:

- Ascend950/NpuArch evidence is missing or contradictory;
- source, test, dispatch, or case mapping is ambiguous;
- the user has not selected final cases;
- the baseline does not compile or pass precision;
- profiling cannot be mapped to every selected case and actual kernel;
- a proposed API or template cannot be verified against the imported TileLang source;
- comparison conditions differ and cannot be reproduced.
