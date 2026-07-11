---
name: sky-flow
description: 'Lightweight artifact-based workflow suite centered on durable specs, compact Progress snapshots, and native execution. Use when the user explicitly asks for Sky Flow or a to-* workflow, or when executing an existing Sky Flow spec or artifact. Do not invoke for ordinary one-off coding, testing, review, or commit work unless a Sky Flow capability is named.'
---

# Sky Flow

Sky Flow 是轻量、spec-direct 的工作流套件。长期设计、稳定约束、实现就绪状态、关键进度和验证证据集中在 `spec`；执行拆解、工具、顺序、owner、并行与子代理调度交给原生 runtime。

简单查询、局部修改和一次性工作直接执行。只有需要长期设计、跨会话恢复、真实人类 gate、长期阻塞、易失交接或可复用知识时才创建对应 artifact。

## Quick Path

1. 用户点名 Sky Flow 或子能力时进入；否则先判断是否真的需要长期 artifact。
2. artifact 根目录 `SKY_FLOW_ROOT` 默认 `docs`，语言 `SKY_FLOW_LANG` 默认跟随用户。
3. 用户显式调用 `$to-spec` 时维护长期设计和需求对齐：先做底座对齐与决策归属，再沿决策前沿关闭实质问题，用就绪证明判断能否实施。
4. ready spec 直接交 `to-implement`；只有用户显式调用 `$pick-goal` 时才从一个或多个 spec 选择 / 恢复并派生 goal。
5. 普通测试、测试 ROI、静态检查和 diff sanity 由 runtime 直接判断与完成；重型 review、consolidation、知识沉淀和持久化验收只在用户显式调用时进入。
6. 创建或修改 file-backed artifact 后运行 `validate-flow`；项目本地 TOC 有要求时同步维护。

## Core Model

```text
spec（长期设计 + 就绪状态 + Progress）
  ↓ 可选 pick-goal（只读选择与目标投影）
ready spec / implementation-ready goal
  ↓
native runtime execution
  ↓ 直接运行与风险匹配的确定性验证
spec Progress 写回

显式可选：$to-review / $to-review-loop / $to-consolidation / 其他重型能力
```

当前 file-backed artifact 只有：

- `spec`：长期设计、稳定约束、就绪状态与 Progress。
- `issue`：值得理解和长期保留的问题、证据或机会。
- `acceptance`：Agent 无法自证的真实人类 gate。
- `backlog`：工作退出活动队列后的长期等待与恢复条件。
- `handoff`：未提交 diff、临时环境等易失接力状态。

所有 artifact 文件 stem 等于 frontmatter `id`，关系默认只保存单向 `source_type` / `source_id`。通用状态为 `draft`、`not_started`、`in_progress`、`completed`、`abandoned`。

## Invariants

- spec 是默认设计与进度真相源；`Progress` 是覆盖更新的高可读语义快照，不是流水账。
- Progress 只保存已成立的能力 / 行为、关键决策、可信证据、真实 blocker、残余风险和下一恢复目标。
- 不记录具体代码行号、逐文件 diff、完整命令、tool call、子代理过程、owner、依赖边、并行批次或微步骤；需要定位时可引用稳定模块、类、函数、接口或测试套件。
- 同一文件或共享状态避免并发多写；完成交接后可动态更换 writer，主会话负责 fan-in。
- 设计与外部行为变化时暂停实现并建议 `$to-spec`；实现策略由 runtime 自主调整。
- artifact 结构问题交 `validate-flow`；普通代码风险、测试 ROI、stable seam、验证组合和 diff sanity 由 runtime 直接处理。专门 review、diff 收敛和持久化 acceptance 只有用户显式调用时才进入对应 Skill；durable constraint 由 runtime 使用最小充分路径满足，不隐式加载重型 Skill。

## Quick Routing

| 场景 | 子能力 |
| --- | --- |
| 长期设计、需求澄清、spec / Progress | `$to-spec` |
| 选择、恢复或启动 spec-derived goal | `$pick-goal` |
| 执行 ready spec / goal | `to-implement` |
| 问题证据 / 排障 / 事故回归 | `$to-issue` / `to-debug` |
| 测试 / review / 收敛 | `native runtime` / `$to-review` / `$to-consolidation` |
| 人类 gate / 长期等待 / 易失接力 | `$to-acceptance` / `$to-backlog` / `$to-handoff` |
| commit / artifact 校验 / 通用知识 | `to-commit` / `validate-flow` / `$to-knowledge` |

完整触发和边界只维护在 `references/routing.md`；进入子能力时读取对应 `skills/<name>/SKILL.md`。安装与依赖见 `references/dependencies.md`，设计真相源见 `docs/spec/tooling/sky-flow.md`。

历史 plan/task/step 执行拓扑与已被 native runtime 吸收的测试工作流归档在 `archive/skills/`，不属于 active skill 或安装范围。迁移时把长期设计与稳定进度压入 spec，只把真实边界分流到 acceptance、backlog 或 handoff。
