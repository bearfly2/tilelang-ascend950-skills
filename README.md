# TileLang Ascend950 Skills

面向 Ascend950PR/DT（NpuArch=3510）的 TileLang 算子开发、精度验证、profiling 与性能优化技能集合。

## 后端策略

- 默认使用 TileLang Ascend 后端：`TILELANG_DEFAULT_TARGET=ascend`
- PTO 是可选后端，仅在任务中显式指定时使用：`TILELANG_DEFAULT_TARGET=pto`
- 算子源码保持后端无关；编译、测试和 profiling 的同一轮运行必须固定同一后端。

## 工作流

1. S0：探测 SoC、NpuArch、CANN、TileLang 和设备证据。
2. S1：从 pytest 收集候选 case，用户选择后生成最终 `cases.csv`。
3. S2：建立数学语义、独立 reference/Golden、资源模型和设计报告。
4. S3：实现 Ascend950 kernel，完成全量精度基线。
5. S4：用统一条件采集 msprof/PTO 或 Ascend 后端证据。
6. S5：逐 case 归因，最多提出三个可验证优化候选。
7. S6-S7：一次只实施一个候选，精度和同条件性能回归后决定 KEEP/REVERT。
8. S8：代码审查、测试、CI 和证据归档。

详细入口见 `skills/tilelang-950-dev-optimize/SKILL.md`，Ascend950 编排规则见 `workflows/Ascend950/workflow.md`。

## 目录

- `skills/`：可加载的 TileLang 设计、开发、测试、profiling 和优化技能。
- `workflows/Ascend950/`：CANNBot Ascend950 工作流、角色提示和校验资源。
- `SOURCES.md`：每个技能的来源和整理说明。

本仓库不包含 NPU 凭据、远端服务器配置或用户项目代码。
