---
name: tilelang-generate-cases-csv
description: 从 TileLang 算子源码和对应 pytest 文件收集完整参数化测试用例，生成供用户勾选的 cases_candidates.csv，并校验、输出最多 20 行的最终 cases.csv。用于 tilelang-tuning 开始阶段把 pytest case 转换为性能调优输入。
---

# TileLang pytest cases.csv 生成

把 pytest 已定义的 case 如实转换为调优候选表。不要新增、推测或自动挑选 case；最终选择权属于用户。

## 输入与输出

必需输入：

- 目标算子源码文件，例如 `tile_kernels/quant/cast_back_asc.py`
- 关联 pytest 文件，例如 `tests/quant/test_cast_back.py`
- 项目根目录
- 输出目录；接入 `tilelang-tuning` 时使用 `{output_dir}/case_selection/`

生成：

- `cases_candidates.csv`：pytest 完整候选集，含 `selected`、由 nodeid 生成的稳定 `case_id`、pytest `source_nodeid`、测试名、collection marker、来源文件和全部参数列
- `cases.csv`：仅含用户明确选择的 1～20 个 case，供 `tilelang-tuning` 使用

`cases_candidates.csv` 不是调优输入。候选数超过 20 时，禁止把它直接重命名为 `cases.csv`，也禁止静默截取前 20 行。

## 工作流程

### 1. 确认算子与测试的调用关系

1. 读取目标算子文件，确认它实现的 kernel 或 backend factory。
2. 沿本地源码中的 import、re-export、wrapper 和设备分发关系，定位 pytest 实际调用的公开接口。
3. 读取 pytest 文件，列出直接或经数据生成函数调用这些接口的测试函数。
4. 仅选择有源码证据的测试函数。一个 backend 被多个公开接口共享时，保留所有相关测试函数；关系仍有歧义时向用户说明并请求确认，不要猜测。

将正确性测试和带 `benchmark` marker 的测试都保留在完整候选集，由 `test_name`、`collection_markers` 区分。不要在此阶段按经验去重或采样。

`collection_markers` 是当前 collection 环境最终附加的 marker，可能包含插件加入的 `skip` 等状态；它不是源码 marker 的静态副本。带 `skip` 的候选在当前环境不能直接执行，交给用户选择前须解释原因。

### 2. 检查 collection 安全性

pytest collection 会导入测试模块并执行参数生成表达式，但不会执行测试函数。先检查测试文件、`conftest.py` 和直接导入模块是否含明显的模块级写文件、删文件、联网或启动长任务行为；发现此类副作用时暂停并告知用户。

### 3. 导出完整候选表

设置 Skill 路径后执行：

```bash
CASE_SKILL_DIR=/absolute/path/to/tilelang-generate-cases-csv
python "$CASE_SKILL_DIR/scripts/export_pytest_cases.py" \
  --operator-file /absolute/path/to/operator.py \
  --pytest-file /absolute/path/to/test_operator.py \
  --project-root /absolute/path/to/project \
  --selector test_related_correctness \
  --selector test_related_benchmark \
  --test-level 2 \
  --output /absolute/path/to/output/case_selection/cases_candidates.csv
```

- 重复 `--selector` 传入第 1 步确认的所有测试函数；不传时收集 pytest 文件中的全部测试。
- 默认 `--test-level 2`，对应本项目的完整 `TK_TEST_LEVEL=2` 参数集。用户明确要求其他级别时再修改。
- 输出列 `tk_test_level_env` 只表示 collection 时设置的环境变量。测试装饰器可显式调用 `generate_test_params(0)`；这种 benchmark 行仍是 level 0 参数集，不得把环境元数据解释为该行的生成级别。
- 需要额外 collection 参数时重复传入 `--pytest-arg=VALUE`。
- 脚本默认拒绝覆盖已有文件；只有用户明确要求重生成时使用 `--force`。
- collection 失败时保留错误信息，修复项目根目录、依赖或 pytest 参数后重试。禁止根据列表推导规则手工补造缺失行。

脚本通过 pytest collection 读取最终展开后的 `callspec.params`。名为 `params` 的字典参数展开为普通 CSV 列；嵌套字典使用点号列名；list/tuple 使用 JSON 表示。

### 4. 交给用户选择

报告以下信息并暂停调优流程：

- 候选 CSV 的绝对路径
- 总 case 数和各 `test_name` 数量
- 用户操作：在需要的 1～20 行 `selected` 列填入 `yes`，其余保持为空
- 不会启动目标 kernel 的边界 case 说明；例如 `cast_back` 在 `num_tokens=0` 时直接返回，这些行属于完整正确性候选，但不适合作为 msprof 性能 case

不要替用户选择“代表性 case”。用户完成选择前，`tilelang-tuning` 不得进入 Step 0.5。

### 5. 生成最终 cases.csv

用户确认选择完成后执行：

```bash
python "$CASE_SKILL_DIR/scripts/finalize_cases.py" \
  --input /absolute/path/to/output/case_selection/cases_candidates.csv \
  --output /absolute/path/to/output/case_selection/cases.csv \
  --max-cases 20
```

该脚本强制检查：

- 至少选择 1 个、最多选择 20 个
- `--max-cases` 只能在 1～20 内收紧门禁，不能把硬上限放宽到 20 以上
- `selected` 值合法
- `case_id` 和所选 `source_nodeid` 非空且不重复
- 输出不覆盖已有文件，除非显式传入 `--force`

只有脚本成功后，才把生成的 `cases.csv` 作为 `{cases_csv}` 交给 `tilelang-tuning`。

## 可信性门禁

- 以目标仓库源码和 pytest collection 结果为唯一 case 真源。
- 不运行 pytest 测试函数，不运行精度测试、benchmark 或 kernel。
- 不把 fixture 生成的随机 tensor 内容写入 CSV；只记录 collection 阶段已确定的 shape、dtype、attrs 等参数。
- 参数只能在测试执行期动态产生、collection 无法得到时，明确报告限制并停止，不得编造。
