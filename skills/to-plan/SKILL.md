---
name: to-plan
description: 'Create or update Sky Flow plan artifacts from a ready spec, issue, existing plan, or current conversation; define goal, scope, plan shape, milestones, progress, recovery, and handoff to to-task or to-implement without writing implementation steps.'
---

# to-plan

`to-plan` 生成或更新 Sky Flow `plan` artifact。它把 ready spec、issue 或已确认会话目标转成可长期维护的执行计划：目标契约、范围边界、阶段、进度、恢复入口、并行 / 串行意图，以及进入 `to-task` / `to-implement` 的 handoff。

它只负责计划层。plan 应记录阶段级串行关系、可并行 lane 和 task handoff；精确 task DAG 由 `to-task` 写入 task metadata 并回填 plan 摘要。执行协调、子代理派发、fan-in、验证和状态回写由 `to-implement` 承担。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取输入来源：优先使用用户指定的 `spec` / `issue` / `plan`；否则从当前会话提取已确认目标、范围和约束。
3. 如果来自 spec，确认 `Plan Handoff` 已 ready；不 ready 时回到 `to-spec`，不替 spec 做关键设计决策。
4. 执行 Scope Check：如果只是单一可恢复工作单元、无需 milestone / task DAG / 长期验收 gate，可推荐 `to-task` 创建 standalone task；多个独立子系统不要硬塞进一个 standalone plan，拆成多个 plan，或升级 parent / child plan。
5. 选择 plan shape：默认 standalone；只有超大、多独立交付域或需要多轮反馈后再细化时，才 parent / child。
6. 写入或更新 plan frontmatter、正文轻量模板和 `goal` 完成契约；未完成 plan 位于 `${SKY_FLOW_ROOT}/plan/`，已完成 plan 归档到 `${SKY_FLOW_ROOT}/plan/done/`。
7. 如果输入是 completed plan 的捞回请求，先确认新证据是否推翻原 plan 的同一 goal / scope 完成结论；成立时把 plan 从 `plan/done/` 移回 `plan/`，把 `status: completed` 改成 `in_progress` 或 `not_started`，并写入 `Reopen Evidence` / `Reopen Reason`。后续增强、二期或相邻问题新建 plan 并引用 completed plan，不捞回旧 plan。
8. 自检 plan，确保能进入 `to-task` / `to-implement`，或明确停在 blocker。
9. 创建、移动或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Plan Shape

所有 plan shape 共享 completed 捞回规则：completed 后若同一 goal / scope 的完成结论被新证据推翻，移回 `${SKY_FLOW_ROOT}/plan/`，把 status 改为 `in_progress` 或 `not_started`，并记录 `Reopen Evidence` / `Reopen Reason`。

### Standalone

- 文件名使用 `001-xxx-xxx.md`。
- 未完成时位于 `${SKY_FLOW_ROOT}/plan/`；实现完成并设置 `status: completed` 后移入 `${SKY_FLOW_ROOT}/plan/done/`。
- `plan_role: standalone`，`planning_depth: task_ready`。
- 可绑定 `tasks`，后续由 `to-task` 生成或更新。

### Parent

- 文件名使用 `001-xxx-xxx.md`。
- 未完成时位于 `${SKY_FLOW_ROOT}/plan/`；实现完成并设置 `status: completed` 后移入 `${SKY_FLOW_ROOT}/plan/done/`。
- `plan_role: parent`，`planning_depth: outline`，`tasks: []`。
- 只写总纲、范围、阶段顺序、恢复入口和 `child_plans` 顺序。
- 不直接生成 task，不进入 `to-task`；执行时切换到当前可执行 child plan。

### Child

- 文件名使用 `001a-xxx-xxx.md`、`001b-xxx-xxx.md`，并复用 parent 的三位数字前缀。
- 未完成时位于 `${SKY_FLOW_ROOT}/plan/`；实现完成并设置 `status: completed` 后移入 `${SKY_FLOW_ROOT}/plan/done/`。
- `plan_role: child`，`parent_plan` 指向 parent。
- 初始只把第一个 child plan 写到 `planning_depth: task_ready`；后续 child plan 保持 `planning_depth: outline` 和 `tasks: []`，等前序推进反馈后再细化。

## Goal Contract

`goal` 字段只保存目标正文，不包含 `/goal` 前缀。它用于生成续跑提示，并必须写清：

- 期望终态。
- 验证证据或验收入口。
- 允许范围和禁止范围。
- 迭代策略：如何推进阶段、更新 plan 和 runtime plan。
- 阻塞停止条件：何时停止并询问人类。

## Milestone Discipline

task-ready plan 的 `Milestones` 必须把设计、测试、轻量实现、人工 gate 和复杂实现拆开表达。默认顺序是：

```text
protocol -> constraints -> abstraction_design -> bdd_test_strategy -> enabling_implementation -> design_review_gate -> core_implementation -> verification_review_consolidation
```

允许的 milestone `Kind`：

- `protocol`：明确外部协议、输入输出、事件、状态流、兼容性、调用方 / 被调用方边界。
- `constraints`：明确不变量、禁止范围、no-touch、兼容约束、性能 / 并发 / 幂等 / 迁移 / 回滚限制和停止条件。
- `abstraction_design`：明确模块边界、抽象层、ownership、数据流、扩展点、single writer 和可替换 seam；不写代码步骤。
- `bdd_test_strategy`：用 `Given / When / Then` 先写 1-3 个最高价值行为场景；如果仍有明确高价值行为，可以继续扩展，但必须标注 ROI、稳定 seam、Red / Green / Refactor、characterization 或替代验证，避免泛化铺开；普通行为测试归 `to-test`，真实事故回归才归 `to-bdd-regression`。
- `enabling_implementation`：少量正式代码体现设计方向，优先做接口、类型、协议适配壳、模块边界、测试 seam、feature flag 壳、薄 adapter、最小 fixture 或一条最小 happy-path skeleton。它是 design-bearing scaffold，不是提前实现核心逻辑；diff 必须小到人类能一次 review，且足够体现协议、约束、抽象和测试 seam。
- `design_review_gate`：hard stop。先安排 `to-consolidation` 收敛 enabling diff，再安排 `to-review` 审设计对齐，然后停下等人类明确批准；没有人类 approval，不得进入 `core_implementation`。如果人类要求调整，回到 `abstraction_design` / `bdd_test_strategy` / `enabling_implementation` 迭代后重新过 gate。
- `core_implementation`：复杂逻辑实现，包括状态机、跨模块行为、业务分支、协议适配真实落地、迁移路径、并发 / 幂等处理等；必须依赖 `design_review_gate` 的人类批准。
- `verification_review_consolidation`：最终验证、review、consolidation、validate-flow 和必要 acceptance；不夹带新功能实现，除非 review 明确要求修复。

一个 milestone 只能有一个主 `Kind`。如果同一阶段同时写协议、抽象、测试和实现，应拆成多个 milestone；如果某个 Kind 不适用，必须在 `Execution Notes` 或 milestone `Readiness Gate` 说明为什么可以跳过，而不是静默省略。中小任务可以合并低风险设计说明，但不得把 `core_implementation` 放到 `bdd_test_strategy` 或 `design_review_gate` 之前。

## Body Template

正文保持轻量。必备 section 只放 plan 层需要长期维护的信息；frontmatter 已表达的字段不要机械重复。

```markdown
# <Plan Title>

最后更新：<YYYY-MM-DD>

## Summary

<3-6 句说明本 plan 要达成什么、从哪里来、当前处于什么阶段。>

## In Scope

- <明确包含的工作>

## Out of Scope

- <明确不做的工作>

## Execution Model

- Ready for `to-task`: yes / no
- Ready for `to-implement`: yes / no
- Task topology:
  - <阶段级串行顺序、可并行 lane 或 no-task execution reason>
- Execution Notes:
  - <执行前必须知道的边界、owner 或验证意图；不写完整执行模型>

## Milestones

1. <阶段名>
   - Kind: protocol | constraints | abstraction_design | bdd_test_strategy | enabling_implementation | design_review_gate | core_implementation | verification_review_consolidation
   - Outcome:
   - Must Define:
   - Must Not Include:
   - Readiness Gate:
   - Agent / Owner:
   - Verification:
   - Handoff to `to-task`:

## Progress Log

- <YYYY-MM-DD>: <关键进展、决策、阻塞或 fan-in 结果>

## Recovery

- Resume from:
- Next action:
- Blockers:
```

可选 section：

- `Agent Lanes`：只在需要说明高层 lane 边界时使用；具体 task lane 由 `to-task` 写。
- `Dependencies / Parallelism`：写阶段级串行关系和可并行 lane；`to-task` 必须把它收敛为具体 `depends_on` / `parallel_with`。
- `Risks / Blockers`：存在真实阻塞或高影响风险时。
- `Decision Log`：有多个会影响后续维护的取舍时。
- `Validation Evidence`：已有验证结果需要长期保留时。
- `Parent / Child Plan Notes`：只有 parent / child plan 才需要。
- `Archive Summary` / `Facts` / `Evidence`：只有 completed plan 经 `to-archive` 压缩后才需要；plan 草稿和执行期不要提前写归档。
- `Reopen Evidence` / `Reopen Reason`：只有 completed plan 被捞回时才需要，说明新证据和为什么原完成结论不再成立。

## Handoff Rules

- `Ready for to-task: yes`：plan 已有稳定 goal、scope、milestones、阶段级串行 / 并行意图和 task handoff，可拆 task DAG。
- `Ready for to-task: yes` 的 milestone 必须能看出协议、约束、抽象、BDD 测试策略、enabling implementation、design review gate 和 core implementation 的顺序；若省略某类 milestone，必须写清不适用原因。
- `Ready for to-implement: yes`：plan 已有关联 task，且下一批可执行 task 的依赖、状态、并行批次和验证意图清楚。
- 如果没有 task，但工作足够小且明确不需要 task DAG，可以标记 `Ready for to-implement: yes`，并在 `Execution Notes` 说明 no-task execution reason。
- 对执行模型只写必须知道的边界；完整主代理 / 子代理分工、fork、fan-in 和状态回写规则交给 `to-implement`。

## 推荐关系

`to-plan` 只做计划层，遇到相邻领域时写推荐，不强制跳转：

- plan ready 且需要拆 task DAG：推荐 `to-task`。
- 目标比日常对话复杂但仍是单一可恢复工作单元、不需要 plan：推荐 `to-task` 创建 standalone task。
- plan 已有关联 task，下一批可执行任务清楚：推荐 `to-implement`。
- 目标、scope、外部契约、数据口径、业务行为或 requirements 不稳定：推荐回 `to-spec`。
- 当前阶段无法推进、等待外部依赖或人类决策：推荐 `to-backlog`。
- completed plan 后续发现问题：同一 goal / scope 的完成结论被推翻时按捞回规则更新；后续增强、二期或相邻问题新建 plan 并引用 completed plan。
- 计划需要人类验收 gate、sign-off 或反馈轮次：推荐后续由 `to-acceptance` 承接；`design_review_gate` 可以用 plan `Progress Log` 记录当前会话明确批准，也可以用 plan 级 acceptance 承接跨会话或多轮正式 sign-off。
- 某阶段需要 review、diff 收敛、测试策略或 artifact 校验：在 milestone / task handoff 中分别推荐 `to-review`、`to-consolidation`、`to-test` 或 `validate-flow`，但不在 plan 层替它们执行。

## Boundaries

- 不写 step-by-step implementation。
- 不以命令清单为主体。
- 不写具体代码片段、测试代码、red-green step 或 commit 粒度。
- 不拆 task-level dependency / parallel graph；交给 `to-task`。
- 不写完整子代理 dispatch packet、fork 细节、fan-in protocol；交给 `to-implement`。
- 不把中等任务拆成 parent / child plan。
- 不把 parent plan 当作 task 调度单元。
- 不一次性细化所有 child plan 的 task。
- 不把项目专属验证命令、部署限制或业务规则写入 Sky Flow core；这些由项目本地文档承载。

## Self-Review

- Spec coverage：spec 的关键 requirements / acceptance scenarios 是否至少映射到一个 milestone、task handoff 或 verification intent。
- Milestone order：task-ready plan 是否按 protocol / constraints / abstraction_design / bdd_test_strategy / enabling_implementation / design_review_gate / core_implementation / verification_review_consolidation 的工程顺序表达，或明确说明跳过原因。
- Design gate：enabling implementation 是否保持小 diff、能体现设计方向且禁止核心复杂逻辑；core implementation 是否被 human approval gate 阻断。
- Placeholder scan：不得出现无意义的 `TBD`、`TODO`、`handle edge cases`、`add appropriate validation` 等空泛计划语言；允许 `[NEEDS CLARIFICATION: ...]`，但必须标明是否 blocking。
- Scope check：输入是否仍适合单个 standalone plan；如已覆盖多个独立子系统，应拆分或升级 parent / child plan。
- Parallelism check：是否把可并行阶段和 lane 表达清楚；代码产出和文档 / artifact 更新是否默认并行，而不是无真实依赖地串行化。
- Handoff check：`Ready for to-task` / `Ready for to-implement` 是否与 tasks、milestones、blockers 一致。
- Recovery check：下一轮能否只读本 plan 恢复 current phase、next action、blockers 和 last validated state。
- Archive check：如果 plan 已 completed 且 task 已压缩，是否只保留事实、决策、证据和必要 follow-up。
- Boundary check：是否提前写入 task DAG、implementation details、命令清单、dispatch packet 或 commit 粒度。
