# Acceptance gates

## Hard gates

Reject or block an iteration when any condition holds:

- the runtime device is not confirmed as supported Ascend950/NpuArch 3510;
- build or PTO compilation fails;
- any selected correctness case fails, skips unexpectedly, hangs, or uses another backend;
- the target kernel is absent or cannot be mapped to the case;
- baseline and candidate measurement conditions differ;
- a selected case is missing from either summary;
- raw evidence required to support the claimed bottleneck is absent;
- the proposed TileLang API/lowering is not verified in the imported framework source.

## Performance gates

Define numeric thresholds in `TASK.md` before looking at candidate results. At minimum specify:

- primary aggregate metric and minimum improvement;
- maximum allowed per-case regression;
- critical cases that may not regress;
- measurement noise or rerun policy;
- maximum launch-count increase if launch count matters.

Do not invent universal percentages. Use project or user thresholds. When none exist, report results without declaring acceptance and request a threshold decision.

## Decision order

1. Apply hard correctness and evidence gates.
2. Check case-set and measurement comparability.
3. Evaluate critical cases and worst regression.
4. Evaluate aggregate performance.
5. Check code complexity, maintainability, and repository review results.
6. Record `KEEP`, `REVERT`, or `BLOCKED` with evidence links.

## Final delivery gates

- all accepted iterations are reproducible from the final source;
- rejected iterations are absent from final source;
- target branch `run-tests` and `review` pass;
- `ci` passes when that Skill exists on the target branch;
- the final report contains unresolved risks and rollback instructions.

