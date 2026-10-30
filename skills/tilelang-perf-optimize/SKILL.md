---
name: tilelang-perf-optimize
description: 为 TileKernels-Nightly 中运行在 PTO 后端的 TileLang 算子制定性能优化方案。基于源码、全部目标 case、PTO 编译结果和同口径 profiling 证据完成 case 分组、瓶颈归因、Tiling/流水候选设计、TileLang API 与模板可实施性核验，并输出最多三个可验证、可回退的优化方案。适用于性能数据采集后的方案分析，不用于直接修改算子代码或处理普通功能故障。
---

# TileLang/PTO 算子性能方案分析

本 Skill 只面向 TileLang 前端与 PTO 后端。目标是把实测瓶颈转化为可由 TileLang 代码实现和验证的方案，不维护其他编程模型的 API、代码模板或迁移规则。

## 职责边界

- 本 Skill 负责：基线证据整理、逐 case 瓶颈分析、case 分组、Tiling 与流水候选设计、方案排序和验证设计。
- `$tilelang-performance-best-practices` 负责：TileLang API、执行域、buffer、模板成熟度、PTO lowering 和实现门禁。制定方案时必须同时加载它。
- 当前 `TileKernels-Nightly` 的公开接口、`tile_kernels/**/*_asc.py` 与测试是产品事实源；实际导入的 TileLang 源码及其 `examples/ascend/`、`testing/ascend/` 是前端能力事实源。
- PTOAS 接收 TileLang lowering 的结果。底层编译器能表达某项能力，不等于 TileLang 前端已有对应 API。
- 本 Skill 不直接修改 kernel。用户要求实施时，把通过门禁的方案交给实现阶段。

## 必需输入

开始分析前确认以下信息齐全：

- 待优化的完整 TileLang kernel、dispatch/build 入口和正确性测试。
- 全部目标 case：case ID、shape、dtype、属性和公开接口约束。
- 当前代码的精度基线与 PTO 编译状态。
- 同一设备、环境、warmup、repeat 和并发设置下的逐 case kernel latency。
- 可获得的 profiling 指标或 trace；没有指标时不得虚构 bound 类型。

缺少逐 case latency、代码与 case 映射或基线不能正确运行时，先返回数据采集阶段，不输出确定性优化结论。

## 工作流

### 1. 固定事实与比较口径

1. 记录当前 commit、实际导入的 TileLang 路径、PTOAS 版本、设备和测试命令。
2. 从测试与 dispatch 还原每个 case 实际进入的 kernel 分支，不能按算子名推测。
3. 校验 profiling 中的 kernel 来自目标源码，整理全部 case 的基线 latency 与可用指标。
4. 按 [证据与瓶颈归因](references/evidence-and-diagnosis.md) 区分计算、搬运、标量/调度、并行度和 launch 开销。

### 2. 按执行路径分组

先按实际计算路径分组，再考虑 shape 大小。推荐顺序：

1. 语义路径：elementwise、broadcast、reduction、transpose/gather、GEMM、attention 或 irregular。
2. dtype 与累加精度。
3. 当前 dispatch/kernel 分支。
4. 对齐、尾块、空任务和特殊属性。
5. 实测瓶颈特征与 shape 规模。

每个 case 必须出现在且只出现在一个基线瓶颈组中。分组方法见 [Tiling 与 case 建模](references/tiling-and-cases.md)。

### 3. 建立当前实现的资源模型

对每个组写出可检查的当前值，而不是先套固定模板：

- 独立任务数、实际核数、每核任务量及负载尾差。
- tile shape、循环次数、有效元素数和 padded footprint。
- GM/UB/L1/L0 buffer 大小、buffer versions、常驻数据与安全余量。
- 每 tile 的读写字节、有效计算量、重复搬运和中间结果生命周期。
- `T.Persistent`、`T.SimdVF`、`T.SimtVF`、`T.gemm` 或归约结构的实际使用方式。

只有公式所依赖的硬件容量、对齐和 API 行为已从当前源码或已验证实现确认后，才能给出具体数值参数。

### 4. 生成并筛选候选

每个候选必须对应一个可证伪假设，例如：

- 增大或减小 tile，以降低固定开销、提高并行度或控制 buffer 压力。
- 调整任务到核的映射，减少负载不均或空核。
- 使用 `T.Persistent` 与明确的 buffer versions 改善搬算重叠。
- 在同一执行域消费中间值，减少 GM 往返或重复读取。
- 为 reduction/GEMM 保留必要的 fp32 状态，并调整分层归约或 K 维流水。
- 为对齐边界和尾块拆分 dispatch 分支，避免所有 case 承担通用路径成本。

随后加载 `$tilelang-performance-best-practices`，逐项完成以下门禁：

1. 在目标仓库同类 `_asc.py` 或实际 TileLang 源码中找到 API 和调用结构依据。
2. 复用 `$tilelang-performance-best-practices` bundled reference 时，标注真实 Python 路径及成熟度；只有 `PRODUCTION_REFERENCE` 或重新验证后的 `VERIFIED` 可作为直接复用候选。当前仓库或实际 TileLang 源码中的真实实现不要求先登记到该状态表，但仍须核验 API、lowering、精度与适用范围。
3. bundled reference 中的 `EXECUTABLE_BASELINE` 只作为正确性起点；`PARTIAL`、`DESIGN_ONLY` 或无可执行 kernel 的资料不得以模板身份进入直接实施方案。若候选另有当前仓库或实际 TileLang 源码证据，应按该直接证据独立判断，不因模板库未收录而自动降级。
4. 无法确认 lowering、布局或 API 参数时，将候选标为 `DESIGN_ONLY`，不编造 TileLang 写法。

最终最多保留三个已准入方案，状态只能是 `IMPLEMENTABLE` 或 `EXPERIMENT`。尽量让每个方案只验证一个主要假设；互斥 dispatch 分支可合并到同一方案，但必须列出分支条件。`DESIGN_ONLY` 单列为“未准入候选”，说明缺失的 API、lowering 或验证证据；仅在候选依赖 bundled reference 时说明缺失的模板证据。它不占三个方案名额，也不交给实现阶段。

### 5. 输出方案与验证顺序

按 [方案与验证](references/plan-and-validation.md) 输出：

- 基线事实表和逐 case 瓶颈表。
- 每个方案的证据、假设、具体参数、TileLang 代码改动位置、参考实现、成熟度和适用 case。
- 精度、PTO lowering、逐 case 性能比较及回退条件。
- 全部 case 覆盖清单；没有证据支持优化时明确写“暂不修改”。

## 硬性规则

- 不把经验阈值当成结论；bound 必须由本轮数据支持。
- 不遗漏慢 case、尾块 case 或当前失败 case，不用平均值掩盖单 case 退化。
- 不通过降低 reference 精度、放宽容差、减少测试或 host 侧短路获得通过。
- 不把底层 IR、编译器内部能力或设计文档写成 TileLang 前端 API。
- 不把“理论上更快”写成性能收益；只有同条件实测才报告加速比。
- 不在方案分析阶段改源码；实现、编译和实测由后续阶段完成。

## 场景

- 已有全部 case 的编译、精度和 profiling 数据：完成分支映射、瓶颈分组并输出最多三个已准入方案；`DESIGN_ONLY` 另列为未准入候选。
- 只有源码或少量 latency：输出缺失证据和采集计划，不猜测 bound、具体 tile 或加速比。
- 只有底层编译能力说明、没有当前 TileLang 表达与 lowering 依据：保留为 `DESIGN_ONLY`，不交给直接实施。
