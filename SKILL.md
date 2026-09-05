---
name: sky-flow
description: 'Lightweight runtime-first workflow suite for durable specs, progressively elaborated milestones, optional implementation working memory, and real collaboration boundaries. Use when the user explicitly asks for Sky Flow or a to-* workflow, or when executing an existing Sky Flow document.'
---

# Sky Flow

Sky Flow 是轻量、runtime-first 的工作流套件。长期设计、稳定约束和目标级进度集中在 spec；大型交付可以显式使用 `to-milestone` 逐层展开；复杂长周期实现只有在恢复价值成立时才由 `to-implement` 维护 thin plan。执行步骤、工具、owner、并行和 fan-in 仍交给原生 runtime。

Sky Flow 使用 Skill-owned durable documents，而不是中央 artifact schema。每个 owning Skill 只定义自己真正需要的目录、字段、状态和生命周期；`artifact_type` 等 metadata 可以帮助识别文档，但不进入全局白名单、统一状态机或关系图。

## Quick Path

1. 用户点名 Sky Flow 或子能力时进入；其他工作默认使用 native runtime，不强制阶段拆分、多 Agent 或多模型。
2. 文档根目录 `SKY_FLOW_ROOT` 默认 `docs`，语言 `SKY_FLOW_LANG` 默认跟随用户。
3. 持续多轮关闭实质需求决策时显式使用 `$to-align`；长期设计、readiness 与 spec Progress 使用 `$to-spec`。
4. 只有用户明确选择 milestone 流程时才使用 `to-milestone`，按其合同展开、讲解和验收；已有选择在继续或恢复同一流程时有效。
5. ready spec 或 active thin plan locator 由 `to-implement` 交给 runtime；只有用户已选择 milestone 流程时才应用 executable leaf 的额外检查。
6. 普通测试、静态检查、build、真实路径和 diff sanity 由 runtime 直接完成；专门 review、consolidation、知识沉淀和 durable acceptance 只在用户显式调用时进入。

## Core Model

```text
显式可选 $to-align
  ↓ 稳定结论
spec（长期设计 + readiness + Progress）
  ├─ 直接执行 / pick-goal → native runtime
  └─ 显式 $to-milestone → 逐层 milestone tree
                              ↓ approved executable leaf
                         runtime plan → to-implement
                                          ├─ runtime-only
                                          └─ optional thin plan
  ↓
durable decisions / outcomes / evidence 回写 spec
milestone delivery status 与人类验收回写当前节点并向上汇总；关闭后压缩归档
```

真实协作边界按需使用独立文档：

- `issue`：值得长期保留的问题、证据或机会。
- `acceptance`：Agent 无法自证且需要跨会话、多轮或可审计的人类 gate。
- `backlog`：工作退出活动队列后的长期等待与恢复条件。
- `handoff`：未提交 diff、临时环境等易失接力状态。

这些名称是 active capability 的文档约定，不是封闭 artifact 枚举。

## Invariants

- spec 是设计、外部行为、数据语义、authority、acceptance 和长期架构的规范性真相源。
- milestone 只保存阶段 outcome、层级、硬依赖、定义成熟度、评审、交付状态和完成证据；代码细节留给 runtime。
- thin plan 只保存有恢复价值的 implementation working set，不成为 readiness gate、task graph 或 milestone source。
- 规范性变化先提升到 spec；受影响 milestone 变为 stale，未受影响分支保持不动。
- 已验收且无 active descendant 的 milestone 可压缩到 archive；代码与 spec 分别保持实现和规范性真相源。
- 同一文件或共享状态避免并发多写；完成交接后可动态更换 writer。
- 人类 gate、权限、不可逆操作和未验证风险不能由 Agent 自行清除。
- 各 owning Skill 通过语义 Self-Review 和真实使用点检查自身文档；没有中央 schema、全库关系扫描或强制文档 validator。

## Quick Routing

| 场景 | 子能力 |
| --- | --- |
| 正式编码前持续多轮需求对齐 | `$to-align`（稳定结论交 `$to-spec`） |
| 长期设计、readiness、spec / Progress | `$to-spec` |
| 独立讲解当前主题 / 可视化理解 | `$show-me`（无需 spec 或 milestone） |
| 大型 spec 的逐层交付分解 | `$to-milestone` |
| 选择、恢复或启动 spec-derived goal | `$pick-goal` |
| 执行 ready spec / goal / executable milestone | `to-implement` |
| 问题证据 / 排障 / 事故回归 | `$to-issue` / `to-debug` |
| 测试 / review / 收敛 | `native runtime` / `$to-review` / `$to-consolidation` |
| 人类 gate / 长期等待 / 易失接力 | `$to-acceptance` / `$to-backlog` / `$to-handoff` |
| commit / 通用知识 | `to-commit` / `$to-knowledge` |

完整触发和边界只维护在 `references/routing.md`；进入子能力时读取对应 `skills/<name>/SKILL.md`。安装与依赖见 `references/dependencies.md`，设计真相源见 `docs/spec/tooling/sky-flow.md`。

历史 plan/task/step 执行拓扑和已退役工作流位于 `archive/skills/`，不属于 active Skill 或安装范围。当前 milestone 是阶段交付树，thin plan 是实现恢复工作集，两者都不恢复 task registry、owner graph 或固定 Agent lane。
