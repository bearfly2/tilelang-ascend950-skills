# Skill routing and provenance

Load dependencies by Skill name. Verify the source locator before execution when duplicate names exist.

| Purpose | Skill | Source precedence | Boundary |
|---|---|---|---|
| Device detection | `ascendc-env-check` | CANNBot, `.agents/skills` | Detect runtime device and CANN environment |
| Architecture capability | `npu-arch` | CANNBot, `.agents/skills` | Interpret confirmed Ascend950/3510 evidence |
| Pytest case extraction | `tilelang-generate-cases-csv` | local Codex, `.codex/skills` | Export candidates and finalize user-selected cases |
| Test design | `tilelang-op-test-design` | CANNBot, `.agents/skills`, Ascend950 branch | Coverage, ST, and acceptance design |
| Operator design | `tilelang-op-design` | CANNBot, `.agents/skills`, Ascend950 branch | Produce implementation design |
| Implementation | `tilelang-op-develop` | CANNBot, `.agents/skills`, Ascend950 branch | Implement, compile, and debug precision |
| Repository tests | `run-tests` | target repository first; global fallback second | Follow branch-specific pytest policy |
| TileLang profiling | `tilelang-op-profiling` | CANNBot, `.agents/skills`, Ascend950 branch | Standard Ascend950 collection for the selected backend (Ascend by default, PTO optional) |
| General profiling | `ops-profiling` | local Codex, `.codex/skills` | Kernel identity, call boundary, or nonstandard evidence |
| Evidence-to-plan analysis | `tilelang-perf-optimize` | local Codex, `.codex/skills` | Produce at most three candidates; do not edit code |
| End-to-end optimization | `tilelang-perf-optimization` | CANNBot, `.agents/skills`, Ascend950 branch | Execute the CANNBot optimization stage |
| Performance references | `tilelang-performance-best-practices` | prefer CANNBot `.agents/skills` router and its Ascend950 body | Query patterns and maturity for the selected backend; avoid the duplicate `.codex/skills` entry unless explicitly requested |
| Scalar hot paths | `tilelang-scalar-optimization` | local Codex, `.codex/skills` | Vectorize verified scalar-heavy logic |
| TileLang review | `tilelang-review` | CANNBot, `.agents/skills`, Ascend950 branch | Final TileLang-specific inspection |
| Repository review/CI | `review`, `ci` | target repository | Enforce the selected branch's delivery policy |

## Repository-local references

- Use `tilelang-deepseek/.agents/skills/tilelang-ascend` for Ascend programming semantics exposed by the actual framework checkout.
- Use `tilelang-deepseek/.agents/skills/tilelang-layout` when Layout/Fragment inference or conversion affects the operator.
- Use other framework repository Skills only for framework changes, not as substitutes for operator delivery stages.
- For `TileKernels-Nightly`, use the checked-out target branch's `.agents/skills`; do not borrow `ci` from another branch.

## Duplicate-name rule

Two installed Skills currently use `tilelang-performance-best-practices`. Treat the CANNBot `.agents/skills` entry as the canonical platform router for this workflow. Record the resolved source path in `TASK.md`. Stop if the runtime cannot distinguish the source rather than silently selecting one.
