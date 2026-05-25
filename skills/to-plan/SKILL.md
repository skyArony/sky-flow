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
4. 执行 Scope Check：多个独立子系统不要硬塞进一个 standalone plan；拆成多个 plan，或升级 parent / child plan。
5. 选择 plan shape：默认 standalone；只有超大、多独立交付域或需要多轮反馈后再细化时，才 parent / child。
6. 写入或更新 plan frontmatter、正文轻量模板和 `goal` 完成契约；未完成 plan 位于 `${SKY_FLOW_ROOT}/plan/`，已完成 plan 归档到 `${SKY_FLOW_ROOT}/plan/done/`。
7. 自检 plan，确保能进入 `to-task` / `to-implement`，或明确停在 blocker。
8. 创建或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Plan Shape

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
   - Outcome:
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

## Handoff Rules

- `Ready for to-task: yes`：plan 已有稳定 goal、scope、milestones、阶段级串行 / 并行意图和 task handoff，可拆 task DAG。
- `Ready for to-implement: yes`：plan 已有关联 task，且下一批可执行 task 的依赖、状态、并行批次和验证意图清楚。
- 如果没有 task，但工作足够小且明确不需要 task DAG，可以标记 `Ready for to-implement: yes`，并在 `Execution Notes` 说明 no-task execution reason。
- 对执行模型只写必须知道的边界；完整主代理 / 子代理分工、fork、fan-in 和状态回写规则交给 `to-implement`。

## 推荐关系

`to-plan` 只做计划层，遇到相邻领域时写推荐，不强制跳转：

- plan ready 且需要拆 task DAG：推荐 `to-task`。
- plan 已有关联 task，下一批可执行任务清楚：推荐 `to-implement`。
- 目标、scope、外部契约、数据口径、业务行为或 requirements 不稳定：推荐回 `to-spec`。
- 当前阶段无法推进、等待外部依赖或人类决策：推荐 `to-backlog`。
- 计划需要人类验收 gate、sign-off 或反馈轮次：推荐后续由 `to-acceptance` 承接。
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
- Placeholder scan：不得出现无意义的 `TBD`、`TODO`、`handle edge cases`、`add appropriate validation` 等空泛计划语言；允许 `[NEEDS CLARIFICATION: ...]`，但必须标明是否 blocking。
- Scope check：输入是否仍适合单个 standalone plan；如已覆盖多个独立子系统，应拆分或升级 parent / child plan。
- Parallelism check：是否把可并行阶段和 lane 表达清楚；不要把无真实依赖的工作串行化。
- Handoff check：`Ready for to-task` / `Ready for to-implement` 是否与 tasks、milestones、blockers 一致。
- Recovery check：下一轮能否只读本 plan 恢复 current phase、next action、blockers 和 last validated state。
- Boundary check：是否提前写入 task DAG、implementation details、命令清单、dispatch packet 或 commit 粒度。
