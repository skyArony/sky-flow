---
name: to-task
description: 'Create or update Sky Flow task artifacts from a task-ready plan; define task DAG, task type, dependencies, parallelism, ownership, write scope, no-touch, verification intent, output contract, and optional task-level steps without executing the tasks.'
---

# to-task

`to-task` 从 `task_ready` plan 生成或更新 Sky Flow `task` artifacts。它把 plan 的 milestones 拆成可执行 task DAG：task 类型、依赖、并行关系、ownership、write scope、no-touch、verification intent、output contract、delegation policy 和可选 steps。

task 一般由子代理承接，也可以由当前主会话或新会话主代理承接；owner 是执行时选择，不是 task 的固定身份。`to-task` 不执行 task、不派发子代理、不做 fan-in；它负责把能并行的 task 尽量定义为并行，把必须串行的 task 写清依赖，让 `to-implement` 可以高效执行。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取输入 plan；如果是 parent plan，切换到当前可执行 child plan。parent plan 不直接拆 task。
3. 确认 plan 是 `planning_depth: task_ready`；如果还是 outline，回到 `to-plan` 先细化。
4. 读取关联 spec / issue / existing tasks，建立 task 边界、依赖、并行候选、串行 gate 和验证意图。
5. 创建或更新 `tasks/<plan-id>/<task-id>.md`；维护 plan frontmatter 的 `tasks` 列表，并在 plan 正文保留 task topology 摘要。
6. 自检 task DAG：依赖、反向依赖、并行关系、single writer、no-touch、delegation policy 和 execution handoff。
7. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Task Boundaries

task 应是不大不小的执行单元：

- 小到能由一个 owner 独立理解、执行、验证和汇报。
- 大到不是 2-5 分钟的微步骤；微步骤只在 task 内部作为 optional `Steps`。
- 每个 task 有明确产物、验证意图和完成条件。
- 每个 task 一般优先评估 worker / explorer / reviewer / verifier 等子代理承接；如果 task 由当前主会话或新会话主代理承接，也必须写清 owner、scope、verification 和 fan-in 责任。
- 每个 task 只能有一个 write owner；共享核心文件、公共契约、DB schema、部署配置默认 single writer。

如果 milestone 仍然包含多个独立子系统，不要硬拆 task；回到 `to-plan` 拆 child plan 或多个 plan。

## Task Metadata

task frontmatter 使用 Sky Flow schema：

```yaml
id: 01-example-task
artifact_type: task
task_type: implementation
status: draft
plan: 001-example-plan
depends_on: []
depended_by: []
parallel_with: []
external_depends_on: []
```

`task_type` 选项：

- `exploration`：只读探索、事实校准、技术可行性调查。
- `implementation`：修改代码、文档、配置或正式产物。
- `review`：检查实现风险、spec alignment、测试缺口。
- `verification`：运行验证、整理证据、复现验收；涉及测试策略、测试 ROI、BDD/TDD 或替代验证时推荐执行时使用 `to-test`。
- `documentation`：更新长期文档或 workflow artifact。
- `coordination`：主代理协调、fan-in 或状态更新；不派给普通子代理。
- `consolidation`：阶段产物收敛，通常触发 `to-consolidation`。

## 推荐关系

`to-task` 负责把 plan 变成可执行 DAG，也负责在 task 中写清执行时推荐的专门 skill；这些推荐是 advisory，不是强制跳转：

- `task_type: review`：推荐执行时使用 `to-review`；如果发现 blocking finding，只输出问题和后续动作，不推荐进入 `to-review-loop`。
- `task_type: consolidation`：推荐执行时使用 `to-consolidation`；该 task 应放在阶段产物完成、fan-in 后或 diff 熵值风险较高的位置，不作为 `to-commit` 固定前置。
- `task_type: verification`，或涉及测试策略、ROI、BDD/TDD、stable seam、替代验证：推荐 `to-test`。
- 真实事故回归测试化：推荐 `to-bdd-regression`，并要求复用 `to-debug` 的 reproduction、evidence、incorrect path 和 correct path。
- 运行环境、日志、数据库、缓存、Metrics、Dashboard、告警或部署证据：推荐项目级 `to-infra`，并在 task 中写清假设、时间范围、环境和关键实体。
- 创建或修改 workflow artifact 的 task：完成后推荐 `validate-flow`。
- 执行策略、milestone 边界、plan shape 或 task handoff 需要变化：回到 `to-plan`；目标、scope、外部契约、数据口径或 requirements 变化：回到 `to-spec`。

## Review Tasks

当 task 是 `task_type: review`，推荐执行时使用 `to-review`。`to-task` 只定义 review task 的范围和输出契约，不直接审查。

review task 至少写清：

- Review target：diff、artifact、plan/task fan-in 结果或具体文件范围。
- Review focus：实现风险、spec alignment、行为回归、测试缺口、安全 / 可靠性、artifact 表达问题中的哪些。
- Evidence input：需要读取的 spec / plan / task / validation evidence。
- Output contract：findings-first、严重度、文件 / 行号、影响、建议修复方向；没有问题也要说明剩余风险。
- Escalation hint：何时需要深度 reviewer、`to-consolidation` 或 `validate-flow`。

不要把 review task 写成修复 task。修复属于后续 implementation task，或在用户显式要求时进入 `to-review-loop`；artifact frontmatter /
DAG/status 校验属于 `validate-flow`；pending diff 熵值收敛属于 `to-consolidation`。

## Test / Verification Tasks

当 task 是 `task_type: verification`，或 implementation task 明确要求新增 / 修改测试、写 `Given / When / Then`、判断测试 ROI、选择 stable seam、决定 Red / Green / Refactor 或替代验证，推荐执行时使用 `to-test`。

`to-task` 只定义测试 / 验证 task 的目标和边界，不替执行层选择具体项目命令。相关 task 至少写清：

- Behavior：要保护的用户可见行为、业务不变量、系统边界或外部契约。
- ROI：`P0` / `P1` / `P2` / `Skip`，以及判断理由。
- Seam：建议测试的稳定接口、层级或系统边界。
- Execution mode：Red / Green / Refactor、characterization 或 alternative verification。
- Verification evidence：期望回传的测试结果、构建结果、静态检查、review 结论或人工验收证据。
- Artifact writeback：验证结果需要回写到 plan、task、acceptance 还是只在执行报告中保留。

真实事故回归的测试化 task 应推荐 `to-bdd-regression`，并复用 `to-debug` 的 reproduction、evidence、incorrect path 和 correct path。

## Body Template

正文保持轻量。固定的是核心必要信息，不是完整标题清单；标题可以按任务形态调整，但必须能承载下面这些内容。

```markdown
# <Task Title>

## Summary

<任务目标、来源 milestone、期望产物。>

## Scope

- Allowed Write Scope:
  - <文件、目录或 artifact 范围>
- No Touch:
  - <禁止修改或只读引用范围>

## Dependencies

- Depends on:
- Can run in parallel with:
- Blocks:

## Execution Handoff

- Recommended owner: main-agent / worker / explorer / reviewer / verifier
- Context policy: full fork / minimal context / no fork
- Delegation policy: no nested agents / nested agents allowed
- Output contract:
  - <changed files / findings / validation evidence / blocker report>
- Stop condition:
  - <何时停止并回报主代理>

## Verification Intent

- <应保护的行为、不变量、证据类型>
```

核心必要信息：

- `Summary`：任务目标、来源 milestone、期望产物。
- `Scope`：allowed write scope 和 no-touch scope。
- `Dependencies`：depends on、can run in parallel with、blocks。
- `Execution Handoff`：owner、context policy、delegation policy、output contract、stop condition。
- `Verification Intent`：应保护的行为、不变量或证据类型。

常见可选 section：

- `Steps`：task 自身复杂、需要 checkpoint 或明确阶段顺序时。
- `Context Notes`：需要保留关键背景、事实来源或读取入口时。
- `Interface / Data Notes`：task 涉及契约、数据口径或外部接口时。
- `Risks / Blockers`：存在真实风险或阻塞时。
- `Decision Log`：执行中形成会影响后续维护的取舍时。
- `Fan-in Notes`：多子代理或二级子代理需要汇总时。
- `Validation Evidence`：已有验证证据需要长期保留时。

允许在模板不足以承载关键执行信息时新增自定义 section。不要为了完整感添加空 section；frontmatter 已表达的信息不要在正文机械重复。

## Dependency Rules

- `depends_on` 和 `depended_by` 必须互相一致。
- `parallel_with` 只用于同一 plan 下可并行的 task；并行必须满足依赖已满足、写集不冲突、fan-in 方式清楚。
- 能并行的 task 应尽量并行表达；只有真实依赖、共享写集、明确 fan-in gate 或风险控制需要时才串行。
- 外部 plan 依赖写入 `external_depends_on`，并说明依赖 artifact 和恢复条件。
- 不把看起来独立但会碰同一共享核心文件的 task 并行。
- coordination task 默认由主代理承担，不派给普通子代理。

## Delegation Rules

- task 一般由子代理承接，但可以由当前主会话或新会话主代理承接；`Recommended owner` 必须写执行理由，不机械默认。
- 如果 runtime 支持二级子代理，且 task 内部仍有并行时间收益、上下文隔离收益、专业化收益、质量 / review 收益或其他明确正向收益，可以把 `Delegation policy` 标为 `nested agents allowed`。
- task owner 可以在自己的 task 范围内派发二级子代理。这里的 task owner 可以是子代理，也可以是当前主会话或新会话主代理；owner 必须自行 fan-in 二级结果，并只把最终结果、验证证据、changed files 和 blocker 汇报给主会话。
- 二级子代理不直接修改 plan / task status；artifact 状态仍由主会话 fan-in 后维护。

## Upstream Boundaries

- `to-task` 可以在不改变 plan goal / scope / milestone intent 的前提下调整 task DAG。
- 如果拆 task 时发现执行策略、milestone 边界、plan shape、scope 分解或 task handoff 需要变化，回到 `to-plan` 更新 plan。
- 如果发现目标、scope、外部契约、数据口径、业务行为或 requirements 需要变化，回到 `to-spec` 更新 spec。

## Step Rules

不是所有 task 都需要 steps。只有 task 本身复杂、需要 checkpoint、或执行中需要明确阶段顺序时才加。

可以写：

- 阶段性目标。
- 验证 checkpoint。
- 依赖解除点。

不要写：

- 具体代码片段。
- 逐命令清单。
- 每 2-5 分钟一步的 implementation script。
- commit 粒度。

## Handoff To to-implement

task DAG ready 的条件：

- 每个 task 有类型、owner 建议、write scope、no-touch、verification intent 和 output contract。
- 依赖、反向依赖和并行关系一致；没有把可并行任务无故串行化。
- single writer / shared scope 风险已表达。
- nested delegation 是否允许已写清。
- 没有 blocking `[NEEDS CLARIFICATION: ...]`。
- plan `tasks` 列表与实际 task 文件一致。

ready 后推荐进入 `to-implement` 执行。

## Self-Review

- Coverage：plan milestones 是否都映射到 task 或明确不拆。
- DAG：depends_on / depended_by / parallel_with 是否一致且无循环。
- Parallelism：是否尽量表达安全并行；串行关系是否都有真实依赖或 gate。
- Scope：每个 implementation task 是否有 allowed write scope 和 no-touch。
- Ownership：是否避免多 writer 触碰共享核心文件。
- Delegation：task owner 和 nested delegation policy 是否清楚。
- Verification：每个 task 是否有可观察完成条件。
- Boundary：是否提前写入 implementation code、命令清单或 commit 粒度。
