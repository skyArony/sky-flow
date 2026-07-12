---
name: to-consolidation
description: 'Consolidate a stable completed-stage diff only when the user explicitly invokes $to-consolidation. Verify that the new implementation fully owns its responsibilities, find superseded entries, fields, states, scheduling, side effects, tests, and documentation, and remove only behavior-preserving residue.'
---

# to-consolidation

## Purpose

检查稳定阶段产物是否已经由新实现完整接管职责，并清理本次变更暴露出的旧设计残留、补丁式实现和 fan-in 熵值。目标是让结果像一次成型的实现，而不只是让局部代码更短。

它不同于：

- `to-review`：判断实现是否正确、是否有回归风险。
- 架构审计：寻找当前 diff 之外的长期重构机会。
- `validate-flow`：检查 Sky Flow artifact 结构和状态。

## P0 Boundary

自动收敛必须保持行为不变。任何可能改变外部行为、错误处理、数据口径、兼容逻辑、状态机、并发顺序、持久化格式、日志 / 指标语义或用户可见结果的处理，都只能作为候选报告并先询问人类。

审计可以发现行为相关候选；不能因为它们无法自动修改就省略。遵循：**发现可以深入，自动修改必须保守。**

默认范围为当前工作区的 staged、unstaged 和 untracked changes。用户也可指定路径、模块、提交、提交区间或 source spec。只检查代码和具体产物，不检查 artifact 状态。

允许从目标 diff 向外做有界追踪：只针对 diff、source intent 或 replacement map 暴露出的精确符号、调用方、消费者和持久化边界搜索必要相邻代码；禁止无目标的全仓死代码清理。

## Load Detailed Method

以下情况必须完整读取 [references/audit-method.md](references/audit-method.md)：

- 新设计替代旧设计；
- 涉及多个入口、模块或执行阶段；
- 涉及字段、状态、缓存、队列、重试、并发或持久化；
- 大 diff、复杂 fan-in、上下文恢复；
- 用户要求收敛审计、兼容清理或分阶段计划。

小而局部的命名、wrapper、debug 或临时代码整理，可以只使用本文件。

## Workflow

1. **建立范围事实**：确认 staged、unstaged、untracked 和用户指定范围。大 diff 先用 stat / numstat 建立 change map，并按业务切片和风险分组。
2. **恢复目标意图**：从 source spec、用户确认、diff 和相邻代码提取新实现必须接管的职责。证据不足且会影响产品或数据语义时询问人类。
3. **建立 replacement map**：记录被替代的旧入口、字段、状态、缓存、调度、配置、测试口径和文档口径，以及对应新 owner。不要只依靠文本相似性推断替代关系。
4. **纵向追踪能力**：从 trigger / entry 追到 domain decision、scheduler、IO / persistence、state transition、consumer、side effects 和 observability。不能只按文件逐个扫。
5. **检查职责接管**：确认入口、数据模型、并发调度、副作用和证据口径没有新旧并存、重复 owner、重复控制或未消费结果。详细检查矩阵见 `audit-method.md`。
6. **建立删除证明**：删除或内联符号前，确认声明、生产者、消费者、持久化、外部边界、反射 / 注册、测试 / 运维引用和替代职责。证据不完整则不得自动处理。
7. **分类 finding**：分为可直接删除、可直接合并 / 内联、需要人类确认、明确保留。保留项必须说明其领域、契约、测试 seam 或观测价值。
8. **执行低风险收敛**：只处理证据充分且行为不变的目标范围问题。新增抽象排在最后；第一次文本重复通常保留清晰重复。
9. **定点复查与验证**：复查修改 hunk、真实调用链和工作区状态。运行与实际修改匹配的最小验证；无法验证时说明缺口。

同一稳定阶段最多执行一轮完整收敛。修复后只复查相关 hunk、调用链和必要验证；只有公共契约、资金 / 状态机语义、fan-in 或 scope 再次显著变化时才重开完整检查。

## Consolidation Priorities

按以下优先级判断 ROI：

1. 删除无用残留和失效入口。
2. 消除新旧职责并存、重复调度和重复并发控制。
3. 合并重复表达同一事实的字段、状态、参数和返回值候选。
4. 内联无领域价值的浅层 wrapper 和错误抽象。
5. 统一无歧义命名、注释、测试与现行文档口径。
6. 扁平化局部控制流。
7. 最后才考虑抽象稳定且语义一致的重复业务知识。

Code smell 只是调查信号。无法证明会降低目标实现的阅读成本、状态空间或维护成本时，保留现状。

## Safe Automatic Changes

可以直接处理：

- 当前目标引入且经删除证明确认无消费者的 private / compile-time-only 符号、fixture、mock、测试数据和导出。
- 已被新实现完整接管、没有持久化或外部兼容边界的旧入口和不可达分支。
- 单次纯透传且不承担领域命名、契约、测试 seam 或观测边界的 wrapper。
- 同层重复、行为等价且无顺序差异的局部组装、guard 或错误包装。
- 临时日志、probe、断点、一次性验证代码和注释掉的旧代码。
- 无歧义的旧注释、测试描述、局部命名和已失效配置。
- 目标文件内明确的局部 format / lint 问题；不得制造大面积 churn。

## Human Gate

以下情况必须先问人：

- 公共 API、DB schema / enum、迁移、外部协议、消息、Redis / 文件持久化格式或部署配置。
- 状态合并、字段统一、事实签名、错误行为、重试 / timeout / 并发顺序或副作用时机变化。
- 删除大块逻辑，或无法证明新 owner 已覆盖全部旧职责。
- helper / wrapper 有多个调用方，或承担领域命名、测试 seam、观测边界、框架注册或公共契约。
- 多个收敛方向都成立，且会影响未来维护方式。
- 修改会扩大需求边界、覆盖其他 lane 工作或触碰历史无关代码。

## Parallelism

默认由当前 Agent 完成。只有用户显式要求 delegation / subagent 时，才按不重叠业务切片或文件组拆少量只读 lane；共享核心文件只允许并行分析、串行修改。子代理只返回 findings、证据和未验证项，主会话负责 fan-in 和最终判断。

## No Goals

- 不替代正式 review、测试设计、安全审计、业务验收或架构重构。
- 不检查 Sky Flow artifact 状态；交给 `validate-flow`。
- 不清理与目标变更无关的历史死代码。
- 不因第一次重复强行 DRY，不制造 mode / flag / caller 特例抽象。
- 不把代码压成更短但更难读的 clever 写法。
- 不把主任务正常实现、行为优化或新能力包装成收敛成果。
- 不重写历史文档；历史证据需要保留时标记 superseded 并指向现行真相源。

## Output

只输出收敛专门发现或完成的熵减结果。每个 finding 必须包含位置、问题、证据、建议、行为影响、风险和验证；不能只报 smell 名称。

小范围且只有自动整理时，可以使用：

```text
### 收敛 - 已完成
1. ...

### 收敛 - 需确认
1. ...
```

深度审计使用 `audit-method.md` 中的完整输出结构，区分：建议立即收敛、只能 deprecated / 留待后续、明确保留、最小分阶段实施。没有实际 finding 时说明检查范围、职责接管结论和未验证边界，不输出空模板。
