---
name: sky-flow
description: 'Lightweight artifact-based workflow suite centered on durable specs, optional thin plans for long-running implementation, compact recovery snapshots, and native execution. Use when the user explicitly asks for Sky Flow or a to-* workflow, or when executing an existing Sky Flow spec or artifact. Do not invoke for ordinary one-off coding, testing, review, or commit work unless a Sky Flow capability is named.'
---

# Sky Flow

Sky Flow 是轻量、runtime-first 的工作流套件。长期设计、稳定约束、实现就绪状态、目标级进度和验证证据集中在 `spec`；复杂长周期实现需要跨会话恢复时，可由 `to-implement` 按需维护一个非规范性的 thin `plan`。执行拆解、工具、顺序、owner、依赖、并行与子代理调度仍交给原生 runtime。

简单查询、局部修改和一次性工作直接执行；复杂但能连续完成、重新推导成本低的工作也只使用 runtime checklist。只有需要长期设计、昂贵的实现恢复上下文、真实人类 gate、长期阻塞、易失交接或可复用知识时才创建对应 artifact。

## Quick Path

1. 用户点名 Sky Flow 或子能力时进入；否则先判断是否真的需要长期 artifact。
2. artifact 根目录 `SKY_FLOW_ROOT` 默认 `docs`，语言 `SKY_FLOW_LANG` 默认跟随用户。
3. 用户显式调用 `$to-align` 时，在正式编码前持续多轮关闭实质决策、控制边角 ROI，并把稳定结论交给 `to-spec`；直接维护长期设计、spec、readiness 或 Progress 时使用 `$to-spec`。
4. ready spec 直接交 `to-implement`；用户直接给出 active plan 时，把它作为 resume locator，先解析 source spec 再进入同一路径。只有用户显式调用 `$pick-goal` 时才从一个或多个 spec 选择 / 恢复并派生 goal。
5. 普通测试、测试 ROI、静态检查和 diff sanity 由 runtime 直接判断与完成；重型 review、consolidation、知识沉淀和持久化验收只在用户显式调用时进入。
6. durable artifact 变更后运行 `validate-flow`；thin plan snapshot 遵循 `to-implement` 的分层时机。项目本地 TOC 有要求时同步维护。

## Core Model

```text
显式可选 $to-align（多轮预编码对齐）
  ↓ 稳定结论
spec（长期设计 + 就绪状态 + Progress，由 to-spec 写入）
  ↓ 可选 pick-goal（只读选择与目标投影）
ready spec / implementation-ready goal
  ↓
native runtime execution ───────────────→ spec Progress（目标级语义快照）
  └─ 可选 thin plan（复杂长周期 working set）
       ↕ 当前 slice / code context / 局部 decision / Progress
       └─ 收口时提升 durable semantics 到 spec，再压缩或删除

显式可选：$to-review / $to-review-loop / $to-consolidation / 其他重型能力
```

当前 file-backed artifact 只有：

- `spec`：长期设计、稳定约束、就绪状态与 Progress。
- `plan`：复杂长周期实现的可选 working set；只保存有恢复价值的落地上下文，不是规范性真相源或执行图。
- `issue`：值得理解和长期保留的问题、证据或机会。
- `acceptance`：Agent 无法自证的真实人类 gate。
- `backlog`：工作退出活动队列后的长期等待与恢复条件。
- `handoff`：未提交 diff、临时环境等易失接力状态。

所有 artifact 文件 stem 等于 frontmatter `id`，关系默认只保存单向 `source_type` / `source_id`。通用状态枚举为 `draft`、`not_started`、`in_progress`、`completed`、`abandoned`；thin plan 没有 pre-readiness `draft` 阶段。

## Invariants

- spec 是设计与外部语义的规范性真相源；spec `Progress` 是覆盖更新的目标级语义快照，不是流水账。
- spec Progress 只保存已成立的能力 / 行为、关键决策、可信证据、真实 blocker、残余风险和下一恢复目标；不保存代码行号、逐文件 diff、完整命令或 Agent 过程。
- thin plan 只由 `to-implement` 在恢复价值成立时按需管理；简单和低恢复成本工作保持 runtime-only。plan 是非规范性 working set，不能恢复 task / step、owner / dependency / lane 等旧拓扑；详细合同只在该 Skill 的 thin-plan 参考中维护。
- plan 与 spec 冲突时 spec 胜出；任何改变 source spec 规范性边界的事实或决定必须先提升回 spec。
- 同一文件或共享状态避免并发多写；完成交接后可动态更换 writer，主会话负责 fan-in。
- 设计与外部行为变化时暂停实现；需要持续多轮关闭实质决策时建议 `$to-align`，直接更新稳定设计时建议 `$to-spec`。实现策略由 runtime 自主调整。
- artifact 结构问题交 `validate-flow`；普通代码风险、测试 ROI、stable seam、验证组合和 diff sanity 由 runtime 直接处理。专门 review、diff 收敛和持久化 acceptance 只有用户显式调用时才进入对应 Skill；durable constraint 由 runtime 使用最小充分路径满足，不隐式加载重型 Skill。

## Quick Routing

| 场景 | 子能力 |
| --- | --- |
| 正式编码前持续多轮需求对齐 | `$to-align`（稳定结论调用 `$to-spec`） |
| 长期设计、直接维护 spec / readiness / Progress | `$to-spec` |
| 选择、恢复或启动 spec-derived goal | `$pick-goal` |
| 执行 ready spec / goal，或从 active plan 恢复 | `to-implement` |
| 问题证据 / 排障 / 事故回归 | `$to-issue` / `to-debug` |
| 测试 / review / 收敛 | `native runtime` / `$to-review` / `$to-consolidation` |
| 人类 gate / 长期等待 / 易失接力 | `$to-acceptance` / `$to-backlog` / `$to-handoff` |
| commit / artifact 校验 / 通用知识 | `to-commit` / `validate-flow` / `$to-knowledge` |

完整触发和边界只维护在 `references/routing.md`；进入子能力时读取对应 `skills/<name>/SKILL.md`。安装与依赖见 `references/dependencies.md`，设计真相源见 `docs/spec/tooling/sky-flow.md`。

历史 plan/task/step 执行拓扑和 `to-plan` / `pick-plan` 等旧工作流与已被 native runtime 吸收的测试工作流归档在 `archive/skills/`，不属于 active skill 或安装范围。当前 thin plan 由 `to-implement` 按需维护，不恢复 task/step、DAG、owner、lane 或归档目录。迁移时把长期设计与稳定进度压入 spec，只把仍有恢复价值的实施 working set 改写成 thin plan，真实边界分流到 acceptance、backlog 或 handoff。
