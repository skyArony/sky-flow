---
name: to-task
description: 'Create or update Sky Flow task artifacts from a task-ready plan; define task DAG, task type, dependencies, parallelism, ownership, write scope, no-touch, verification intent, output contract, and optional task-level steps without executing the tasks.'
---

# to-task

`to-task` 生成或更新 Sky Flow `task` artifacts。默认路径是从 `task_ready` plan 拆出 plan-scoped task DAG；也可以在目标比日常对话复杂、需要可恢复状态和验证意图、但尚不值得创建 plan 时，从当前会话创建 standalone task。

plan-scoped task 把 plan 的 milestones 拆成可执行 task DAG：task 类型、依赖、并行关系、ownership、write scope、no-touch、verification intent、output contract、delegation policy 和可选 steps。standalone task 是单一执行单元，不绑定 plan、不建 peer task DAG，不作为长期 plan 的替代品。

task 一般由子代理承接，也可以由当前主会话或新会话主代理承接；owner 是执行时选择，不是 task 的固定身份。`to-task` 不执行 task、不派发子代理、不做 fan-in；它负责把能并行的 task 尽量定义为并行，把必须串行的 task 写清依赖，让 `to-implement` 可以高效执行。

task 是执行期调度和恢复结构，不默认作为永久历史。plan-scoped task 完成时只更新 `status: completed`，仍留在 `tasks/<plan-id>/`；plan 完成后由 `to-archive` 使用 summary-only 把 task 中值得长期保留的事实、关键决策、踩坑和证据入口压缩回 completed plan，并清理 task 目录。plan-scoped task 不捞回；后续修复追加新 task，或在旧 task 已清理后重新拆 task DAG。

拆 task 时要把代码产出和文档 / artifact 更新作为可并行 lane 优先建模。只要写集不冲突，implementation task、documentation task、verification evidence 写回和 acceptance 草稿不应被无故串行化；如果同一个 artifact 需要写入，必须指定 single writer，其余代理只回报事实或 patch 建议。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 选择 task role：
   - `plan_scoped`：输入是 task-ready plan，需要拆 task DAG 或维护既有 task。
   - `standalone`：输入是当前会话或轻量工作请求，目标单一、可由 Agent 独立完成、需要留痕但不需要 plan。
3. plan-scoped 路径：读取输入 plan；如果是 parent plan，切换到当前可执行 child plan。parent plan 不直接拆 task。确认 plan 是 `planning_depth: task_ready`；如果还是 outline，回到 `to-plan` 先细化。
4. standalone 路径：从当前会话提取目标、scope、allowed write scope、no-touch、验证意图、恢复入口和停止条件；如果出现多个 peer task、milestone、长期验收 gate、父子拆分或需求口径不稳定，回到 `to-plan`。
5. 读取关联 spec / issue / existing tasks，建立 task 边界、依赖、并行候选、串行 gate 和验证意图。
6. 先过 Agent-Executable Gate：只有 Agent 可以独立执行、判断完成并回传证据的工作才创建 task；真实设备、真实账号、外部环境、人工审批、人工体验判断或缺少权限的验证项转入 `to-acceptance`，不要创建 task。
7. 创建或更新 artifact：
   - plan-scoped：`tasks/<plan-id>/<task-id>.md`，完成时仍留在该目录，只改 `status`；维护 plan frontmatter 的 `tasks` 列表，并在 plan 正文保留 task topology 摘要。
   - standalone：`tasks/standalone/<task-id>.md`，不写 `plan`，不更新任何 plan `tasks`。
8. 自检 task：plan-scoped 检查 DAG、依赖、反向依赖和并行关系；standalone 检查 goal、scope、恢复入口、verification intent 和是否仍然不需要升级为 plan。
9. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Task Boundaries

task 应是不大不小的执行单元：

- 小到能由一个 owner 独立理解、执行、验证和汇报。
- 大到不是 2-5 分钟的微步骤；微步骤只在 task 内部作为 optional `Steps`。
- 每个 task 有明确产物、验证意图和完成条件。
- 每个 task 必须能由 Agent 独立完成并判断完成；如果完成条件依赖人类操作、真实设备、真实账号、外部网络 / 环境、审批结论或人工体验判断，不创建 task，改为创建或更新 acceptance。
- 每个 task 一般优先评估 worker / explorer / reviewer / verifier 等子代理承接；如果 task 由当前主会话或新会话主代理承接，也必须写清 owner、scope、verification 和 fan-in 责任。
- 每个 task 只能有一个 write owner；共享核心文件、公共契约、DB schema、部署配置默认 single writer。

如果 milestone 仍然包含多个独立子系统，不要硬拆 task；回到 `to-plan` 拆 child plan 或多个 plan。

standalone task 额外要求：

- 只表达一个可恢复工作单元，不表达 peer task DAG。
- 必须写 `task_role: standalone` 和 `goal`，因为没有 parent plan 提供目标契约。
- `depends_on`、`depended_by`、`parallel_with` 保持空数组；如果需要多个本地 task 依赖、并行或 fan-in，升级为 plan。
- 可以用 `external_depends_on` 记录外部 artifact / task 前置条件，但不能把它变成隐藏 mini-plan。
- 完成后由 `to-implement` 按 completed plan 的标准精简自身正文并移入 `tasks/standalone/done/`；不经过 plan `to-archive` 压缩。

## Agent-Executable Gate

`to-task` 只生成 Agent 可完成的执行单元。一个候选 task 必须同时满足：

- Agent 拿到当前仓库、允许的工具和必要上下文后，可以自己执行主要动作。
- Agent 可以判断 pass / fail，而不是等待人类、客户、Boss、真实设备或外部账号给结论。
- 完成证据可以由 Agent 产生或读取，例如 changed files、测试结果、构建结果、静态检查、日志 / metrics 查询结果、review finding 或已授权环境证据。
- Stop condition 是 Agent 可观测的，不是“等待人工操作完成”。

下面内容不创建 task，直接转 `to-acceptance` 或更新既有 acceptance：

- 真实手机、浏览器 profile、员工客户端、客户账号、外部平台、权限系统或人工体验判断。
- 需要人类批准的 push / deploy / rollout / 生产或测试环境操作。
- Agent 没有权限、入口或凭据的端到端环境验证。
- 需要人类提供截图、操作结果、业务口径、验收结论或 sign-off 的阶段 gate。

Agent 可以完成的预检、证据整理或验收文档草稿不要伪装成人工验证 task。它们应优先并入前置 implementation / verification task 的 `Validation Evidence`，或写入 acceptance 的证据区；只有预检本身足够独立、可由 Agent 完成且有明确产物时，才创建 Agent-executable task。

## Task Metadata

task frontmatter 使用 Sky Flow schema：

```yaml
id: 01-example-task
artifact_type: task
task_role: plan_scoped
task_type: implementation
status: draft
plan: 001-example-plan
depends_on: []
depended_by: []
parallel_with: []
external_depends_on: []
```

standalone task frontmatter：

```yaml
id: t001-example-task
artifact_type: task
task_role: standalone
task_type: exploration
status: draft
goal: Complete this standalone task with clear evidence, preserving the declared scope and no-touch boundaries. Update this task with progress, validation evidence, and recovery notes. If peer task dependencies, milestones, or human gates become necessary, stop and promote the work to a plan.
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

- `task_type: review`：推荐执行时使用 `to-review`；高风险 review task 可要求 multi-review / synthesize；如果发现 blocking finding，只输出问题和后续动作，不推荐进入 `to-review-loop`。
- `task_type: consolidation`：推荐执行时使用 `to-consolidation`；该 task 应放在阶段产物完成、fan-in 后或 diff 熵值风险较高的位置，不作为 `to-commit` 固定前置。
- `task_type: verification`，或涉及测试策略、ROI、BDD/TDD、stable seam、替代验证：推荐 `to-test`。
- 真实事故回归测试化：推荐 `to-bdd-regression`，并要求复用 `to-debug` 的 reproduction、evidence、incorrect path 和 correct path。
- 运行环境、日志、数据库、缓存、Metrics、Dashboard、告警或部署证据：推荐项目级 `to-infra`，并在 task 中写清假设、时间范围、环境和关键实体。
- 创建或修改 workflow artifact 的 task：完成后推荐 `validate-flow`。
- 执行策略、milestone 边界、plan shape 或 task handoff 需要变化：回到 `to-plan`；目标、scope、外部契约、数据口径或 requirements 变化：回到 `to-spec`。
- 已完成 plan-scoped task 后续发现问题时，不恢复旧 task。旧 task 仍在当前 plan DAG 中则追加新 task，并更新 depends_on / depended_by / parallel_with；旧 task 已被 completed plan summary-only 清理则基于 completed plan、issue 和证据重新拆 task DAG。

## Review Tasks

当 task 是 `task_type: review`，推荐执行时使用 `to-review`。`to-task` 只定义 review task 的范围和输出契约，不直接审查。

review task 至少写清：

- Review target：diff、artifact、plan/task fan-in 结果或具体文件范围。
- Review focus：实现风险、spec alignment、行为回归、测试缺口、安全 / 可靠性、artifact 表达问题中的哪些。
- Evidence input：需要读取的 spec / plan / task / validation evidence。
- Output contract：findings-first、严重度、文件 / 行号、真实 bug 风险、修复成本、影响、建议修复方向；multi-review 时要求 reviewer agreement 和 synthesize 清单；没有问题也要说明剩余风险。
- Escalation hint：何时需要 multi-review、深度 reviewer、verifier stage、`to-consolidation` 或 `validate-flow`。

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

如果 verification 的核心完成条件是人工或真实环境门控，例如“员工手机实际访问 gz-test 私有入口并确认体验 / 权限 / 账号结果”，不要创建 verification task。应创建或更新 plan 级 acceptance，把 Agent 已完成的预检证据作为支撑，把真实环境步骤和验收结论留给人类填写。

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

- plan-scoped task 才组成同一 plan 下的 DAG；standalone task 不声明本地 `depends_on` / `depended_by` / `parallel_with`。
- plan-scoped task 完成时只改 `status: completed`，不移动到 `done/` 子目录；`tasks/<plan-id>/done/` 不是合法位置。
- `depends_on` 和 `depended_by` 必须互相一致。
- `parallel_with` 只用于同一 plan 下可并行的 task；并行必须满足依赖已满足、写集不冲突、fan-in 方式清楚。
- 能并行的 task 应尽量并行表达；只有真实依赖、共享写集、明确 fan-in gate 或风险控制需要时才串行。
- 代码任务与文档任务默认并行表达：实现 worker 写代码时，documentation worker 或主会话可以同步更新 spec / plan / task / acceptance / handoff；最终状态和完成结论由主会话 fan-in 对齐。
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
- 如果 standalone task 执行前已需要多个 task、milestone、父子拆分或长期验收 gate，不要扩展 standalone task；创建 plan，并在 standalone task 记录 promoted-to-plan 关系。

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
- 每个 task 都通过 Agent-Executable Gate；人工 / 真实环境门控已转入 acceptance，而不是留在 task DAG 中阻塞完成。
- 依赖、反向依赖和并行关系一致；没有把可并行任务无故串行化。
- single writer / shared scope 风险已表达。
- nested delegation 是否允许已写清。
- 没有 blocking `[NEEDS CLARIFICATION: ...]`。
- plan `tasks` 列表与实际 task 文件一致。

ready 后推荐进入 `to-implement` 执行。

standalone task ready 的条件：

- `goal` 足以作为恢复契约，包含期望终态、证据、scope、no-touch、迭代策略和停止条件。
- allowed write scope、no-touch、owner 建议、output contract 和 verification intent 清楚。
- 不存在本地 peer task 依赖；如果需要拆多个 task 或表达 milestone，先升级为 plan。
- 通过 Agent-Executable Gate；人工 / 真实环境门控已转入 acceptance 或升级为 plan，而不是留在 standalone task 中阻塞完成。

## Self-Review

- Coverage：plan milestones 是否都映射到 task 或明确不拆。
- DAG：depends_on / depended_by / parallel_with 是否一致且无循环。
- Parallelism：是否尽量表达安全并行；代码产出和文档 / artifact 更新是否被建模为可并行 lane；串行关系是否都有真实依赖或 gate。
- Scope：每个 implementation task 是否有 allowed write scope 和 no-touch。
- Ownership：是否避免多 writer 触碰共享核心文件。
- Delegation：task owner 和 nested delegation policy 是否清楚。
- Verification：每个 task 是否有 Agent 可观察、可判断的完成条件；无法由 Agent 完成的验收是否已转入 acceptance。
- Boundary：是否提前写入 implementation code、命令清单或 commit 粒度。
