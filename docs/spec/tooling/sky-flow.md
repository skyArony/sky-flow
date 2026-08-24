---
id: sky-flow
artifact_type: spec
status: completed
---

# Sky Flow 工作流套件

最后更新：2026-08-25

## Intent

- Problem: 大型 spec 直接进入 runtime 时，阶段边界、逐层人类评审和长期交付恢复缺少合适载体；不同 durable document 也需要按自身语义独立演进。
- Outcome: Sky Flow 保持 runtime-first，并增加显式 `to-milestone` 作为滚动式交付分解层；durable documents 由 owning Skill 自己定义，core 只维护 authority 与 routing。
- Audience: 使用、维护或扩展 Sky Flow 的 Agent、开发者与需要跨会话推进大型交付的人类协作者。

## Context

### Confirmed Facts

- runtime 能动态拆解工作、调整顺序与并行、运行验证并完成 fan-in；代码级执行图不需要长期文件化。
- spec 适合保存长期设计、规范性决定、成功边界和目标级 Progress，但不适合承载层层展开的阶段 delivery tree。
- thin plan 适合保存跨会话 implementation context，但不拥有独立 goal、阶段评审或人类验收。
- 大型系统设计会随前序结果逐步清晰；一次性展开完整计划会产生过期节点、虚假依赖和维护成本。
- 人类希望先批准当前层，再选择一个或多个节点继续细化，直到形成边界清楚、可独立验收的 executable leaf。
- 文档类型之间的必要字段、状态与路径差异明显；中央 schema 的统一限制会阻碍新能力并制造无业务价值的校验工作。
- Claude 与 Codex 的 Skill 发现模型不同，现有 installer 仍解决真实安装与安全清理问题，应与 durable-document 模型解耦。

### Constraints

- 简单、一次性和可低成本重建的工作不创建 milestone 或 thin plan。
- spec 始终是外部语义、数据语义、authority、acceptance 和长期架构的真相源。
- milestone 不保存代码步骤、文件清单、命令、owner、Agent lane 或 task DAG。
- 每层 milestone 和 executable leaf 都保持人类意图边界；清楚指令可以同时授权相邻 checkpoint，不要求形式化重复批准。
- 并行只持久化真实硬依赖，实际并发由 runtime 判断共享 contract 与写冲突。
- 安全、权限、不可逆操作和生产变更审批不因文档模型简化而降低。

## Scope

### In Scope

- spec-direct、milestone-guided 与 optional thin-plan 三条执行路径。
- 逐层 milestone tree、executable leaf、人类评审、完成汇总、stale 子树和完成后压缩归档。
- Skill-owned durable-document contract。
- issue、acceptance、backlog、handoff 的真实协作边界。
- Skill routing、安装发现、copy-mode freshness 与 retired symlink 安全清理。
- 以行为场景为主的 Skill eval。

### Out of Scope

- 项目专属业务规则、基础设施凭据和部署命令。
- task / step registry、全局 owner graph、固定并行 lane 或 fan-in 文件化。
- 中央 artifact 类型注册、共享 frontmatter schema、统一状态枚举和全库 referential integrity。
- 为文档标题、字段顺序或模板措辞编写脆弱测试。

## Core Model

```text
显式可选 $to-align
  ↓ 稳定结论
spec（规范性设计 + readiness + Progress）
  ├─ 直接执行 / pick-goal → native runtime
  └─ 显式 $to-milestone
       ↓ 只创建当前直接子层
       human review
       ↓ 选择 approved frontier
       branch 再细化一层 / executable leaf
       ↓ implementation authorized by human intent
       embedded eli5 HTML → verified local URL
       to-implement
         ├─ runtime-only
         └─ optional thin plan（跨会话 implementation working set）

实现产生的 durable decisions / outcomes / evidence → spec
阶段 delivery state / human acceptance → milestone，并向父节点汇总
已关闭 subtree → milestone archive summary（代码 / spec 保持最终真相源）
```

## Durable Document Model

Sky Flow 不维护中央 artifact registry。每个 owning Skill 定义自己文档的：

- 创建条件与目录。
- 必要 metadata 与正文语义。
- 状态转换与停止条件。
- source / parent 关系何时需要检查。
- Self-Review、恢复和收口方式。

`artifact_type`、`status`、`source_id` 等现有 metadata 可以继续使用，但只由 owning Skill 解释：

- 没有全局 type whitelist。
- 没有所有文档必须共享的 status enum。
- 没有全局 id / filename、固定目录或 reserved-field 规则。
- source / parent 关系只在 owning Skill 的真实读取路径中检查。
- 没有每次 durable write 后强制执行文档 lint 的固定流程。

机械检查只在真实、重复故障证明收益成立时，由 owning Skill 增加窄范围 helper；默认依靠语义 Self-Review、真实读取路径和项目自身 Markdown / link 检查。

## Spec Contract

Spec 保存长期设计真相与目标级恢复：

- Intent、Context、Scope。
- Acceptance Scenarios 与可测试 Requirements。
- 稳定 Decisions、Verification Intent 和必要 Execution Constraints。
- Implementation Readiness 与真实 Open Questions。
- Progress：稳定 checkpoint、semantic outcomes、目标级 next、blocker、evidence 和 residual risk。

Spec 不保存代码步骤、逐文件 diff、命令、runtime 调度或 milestone 的完整树。Milestone 产生长期决定时先提升到 spec，再继续依赖该决定的节点。

## Milestone Contract

`to-milestone` 只在用户显式调用时进入。source spec 必须稳定到足以判断阶段 outcome、边界和验收；不满足时回 `to-spec`。

### Rolling-Wave Elaboration

- 首次只创建一级 milestone。
- 人类批准当前层后，才选择一个或多个节点继续。
- 每次只创建选中节点的直接子层，不创建孙级 placeholder。
- 直接子节点共同覆盖父级 required outcome，且不引入 source spec 之外的新 scope。
- 选择节点时重新读取最新 spec、仓库事实、兄弟节点结果和硬依赖。

### Executable Leaf

叶子满足：

- 单一连贯 outcome，可作为一个 runtime goal。
- 能独立验证与接受。
- 没有开放的规范性人类决策。
- 边界、硬依赖和共享 contract 清楚。
- Acceptance、核心行为测试、风险相关单元测试意图、其他 evidence 和人类验收入口明确。

叶子大小不按工时、文件、commit 或步骤数量判断。无法独立验收表示仍需细化；拆分后没有独立 outcome 表示过细。

### Intent-Aware Alignment

以下边界由人类拥有最终意图：

- 一级划分。
- 每个 branch 的直接子层。
- executable leaf 的定义与验收合同。
- 会改变 scope、外部行为、关键风险或执行授权的 runtime 方向。
- 当前叶子的 ELI5 Web 讲解必须在实现前交付，但已有实施授权时不重复等待继续指令。
- 实现后的最终验收。

一个清楚指令可以关闭多个相邻 checkpoint；“可以，让子代理实现，你来验收”同时授权实施、指定分工并委托该 leaf 的 acceptance authority。只有高影响选择仍未解决、授权范围不清、需要扩大 scope / 权限或与 spec 冲突时才追问。普通 Agent plan、状态字段更新和重复陈述不构成新 gate。

Leaf 默认在 Agent evidence 完成且人类通过后 `completed`；人类也可以明确把某个 leaf 的验收委托给未承担实现的 Agent。Parent 默认按 required children 汇总；只有存在子节点无法覆盖的整体行为、体验或风险接受时才增加父级 gate。

完成且没有 active descendant 的节点可以归档。归档前先把长期规范性结论和残余风险提升到 spec，再将 subtree 移出 active tree，并压缩为 outcome、spec coverage、验收证据索引和残余风险摘要。Archive 不保存当前实现细节：代码是实现真相源，spec 是规范性真相源。

每个 executable leaf 获得实施授权后、任何实现动作开始前，必须调用内嵌 `eli5` 生成 repo 外临时 HTML 图解，并通过本地静态 Web server 提供经实际访问验证的 URL。已有实施授权时，交付 URL 后直接进入 `to-implement`；只有人类要求先看后决定，或图解暴露实质问题时才暂停。页面只解释该 leaf 的问题、变化、流程、可见结果和主要风险，不保存代码计划，也不成为 durable document。

### Parallelism And Staleness

- 只记录硬依赖；不维护 `parallel_with`。
- 无未完成硬依赖表示具备并行资格，runtime 仍检查共享写与 contract。
- 规范性变化先写回 spec，只把受影响节点标记 stale。
- completed 节点是否 reopen 属于人类决定；相邻增强不自动推翻历史完成结论。

详细目录与文档合同由 `skills/to-milestone/references/milestone-docs.md` 维护。

## Thin Plan Contract

Thin plan 是 optional implementation working set：

- 只有跨会话、compaction、昂贵上下文重建或具体 checkpoint 恢复价值成立时才 materialize。
- source 仍是 ready spec。由 executable milestone 派生时，Current Slice 引用 milestone id，但 milestone 不成为 plan authority。
- 保存 Current Slice、Code Context、Approach、局部可逆 Decisions、Progress 和 Verification。
- 不保存 spec 副本、milestone tree、task graph、owner、dependency、parallel lane、Agent / tool 流水或完整 diff。
- 完成时把 durable decisions、semantic outcomes、evidence 和 residual risk 提升到 spec，再压缩或删除 working set。

## Other Durable Boundaries

- Issue：值得长期保留的问题、证据、机会或 unresolved finding。
- Acceptance：Agent 无法自证且需要 durable、多轮或跨会话保存的人类 gate；一次性确认留在对话。
- Backlog：工作长期退出当前活动队列，记录 blocker 与恢复条件。
- Handoff：未提交 diff、终端、临时环境和其他易失接力状态；不复制长期 Progress。

这些文档正文自包含到足以恢复其责任边界；source metadata 只在提高发现性时使用。

## Runtime Execution

`to-implement` 接收 ready spec、spec-derived goal、approved executable milestone 派生的 runtime goal，或 active thin plan locator：

- runtime 自主选择探索、实现、工具、checklist、调度和普通验证组合。
- 只有 authority、重大 scope、外部契约、不可逆操作或真实人类 gate 无法安全裁决时才询问人类。
- 普通测试、typecheck、lint、build、真实路径和 diff sanity 直接完成。
- 专门 review、review loop、consolidation、knowledge、second opinion、多 Agent 和 durable acceptance 只在用户显式调用或 source constraint 要求时进入。

## Active Skill Suite

| Skill | Responsibility |
| --- | --- |
| `sky-flow` | 入口、路由与 durable-document 边界 |
| `to-align` | 显式多轮预编码对齐 |
| `to-spec` | 规范性设计、readiness 与 Progress |
| `to-milestone` | 逐层交付树、leaf gate、人类验收与状态汇总 |
| `eli5` | Sky Flow 内嵌的 leaf HTML 图解能力，不依赖外部 Skill 安装 |
| `pick-goal` | 从 spec 只读派生 runtime goal |
| `to-implement` | runtime-first execution 与 optional thin plan |
| `to-issue` / `to-debug` | 问题证据、诊断与事故回归 |
| `to-review` / `to-review-loop` | 显式审查与复审 |
| `to-acceptance` | durable human gate |
| `to-backlog` / `to-handoff` | 长期等待与易失接力 |
| `to-commit` | scoped stage / commit 与项目验证 |
| `to-consolidation` / `to-knowledge` | 显式收敛与通用知识 |

`to-infra` 是 project-provided adapter slot。

## Installation

- Claude 安装 suite entry 与 callable child links。
- Codex 只安装 suite entry，并发现 nested children。
- copy-mode 比较完整 managed subtree。
- retired Skill 不参与 active discovery；installer 只自动清理可证明属于当前 checkout 的旧 symlink。
- durable-document 类型不参与安装注册，新增 owning Skill 无需扩充 artifact schema。

## Acceptance Scenarios

1. 简单工作绕过 milestone 与 thin plan，直接 runtime 执行。
2. 首次 `$to-milestone` 只创建一级文档，等待人类批准，不生成未来目录。
3. 人类只批准一个 branch 时，只细化该节点的直接子层，其他分支保持不动。
4. executable leaf 的验收与测试意图明确、且人类已授权实施后才编码；普通 runtime plan 不额外要求批准。
5. 无硬依赖的多个 leaf 可被提议为并行 frontier，实际并发由 runtime 根据共享写决定。
6. Spec 变化只让受影响子树 stale，不重建无关 milestone。
7. 测试和构建通过但人类未验收时，leaf 保持 active，不自行 completed。
8. 长周期实现按需 materialize thin plan；简单或连续工作保持 runtime-only。
9. 新 owning Skill 可以独立定义自己的 metadata、状态与 Self-Review。
10. Installer 发现 `to-milestone`，并能安全识别 retired `validate-flow` 安装。
11. 已验收 subtree 可以压缩归档；归档不保留实施期细节，也不与代码或 spec 竞争真相源。
12. 每个 leaf 执行前都有独立 ELI5 HTML 页面和经验证的可打开地址；已有实施授权时不重复请求继续。
13. “可以，让子代理实现，你来验收”直接进入 ELI5 preflight 和实施，不再要求 runtime-plan 批准，并由主 Agent 独立验收。

## Requirements

- R1: Spec 必须保持规范性 authority，milestone 和 thin plan 不得覆盖它。
- R2: `to-milestone` 必须 explicit-only，并且每次只展开一层。
- R3: 每层切分、leaf contract、实施授权和最终 acceptance authority 必须能从人类意图确定；一个清楚指令可以覆盖多个相邻 checkpoint，不得机械重复确认。
- R4: Milestone 文档不得包含代码步骤、文件清单、命令或 runtime 拓扑。
- R5: 只有硬依赖持久化；并行资格与实际并发必须分离。
- R6: 规范性变化必须先进入 spec，并只使受影响 milestone stale。
- R7: Thin plan 必须保持 plan-on-demand，并继续 source-link spec。
- R8: Durable documents 必须由 owning Skill 定义，不得恢复中央 type/status/field/path registry。
- R9: Sky Flow active surface 只暴露由具体工作流拥有的语义检查。
- R10: Skill eval 必须保护可观察 workflow 行为，不绑定标题和字段顺序。
- R11: Installer 必须继续匹配 Claude / Codex discovery，并安全处理 retired installs。
- R12: 只有 completed 且无 active descendant 的 milestone 可以归档；归档前必须提升长期事实到 spec，并压缩掉实施期细节。
- R13: 每个 executable leaf 必须在实现前调用 Sky Flow 内嵌 `eli5`，启动并验证本地 Web 页面，提供 URL；只有实施尚未授权或人类要求 review-before-run 时才等待继续指令。

## Decisions

- 决策: 引入 explicit-only `to-milestone`，采用 rolling-wave elaboration 与 executable leaf。
  - 理由: 大型交付需要跨会话阶段边界和逐层人类 gate，但不需要预先写死代码执行图。
- 决策: Durable document contract 归 owning Skill，Sky Flow core 只维护 authority 与路由。
  - 理由: 不同文档的真实字段和生命周期不同，开放协议能减少全局耦合与无效校验。
- 决策: Milestone 只保存 hard dependency，实际并行属于 runtime。
  - 理由: 硬 gate 具有长期语义，完整并行关系容易随探索漂移。
- 决策: Runtime plan 不持久化到 milestone；跨会话 implementation context 继续使用 thin plan。
  - 理由: 阶段方向、当前代码步骤和恢复工作集有不同稳定性与维护周期。
- 决策: 安装管理保持独立。
  - 理由: 跨客户端发现和安全 symlink ownership 是真实机器边界，与 durable-document schema 无关。

## Verification Intent

- `to-milestone` Skill 与 reference 通过 skill structure validation。
- `to-milestone`、`to-spec`、`to-align`、`to-implement` eval JSON 可解析。
- behavior eval 覆盖一级创建、单 branch 深化、leaf gate、并行、stale 子树和人类验收。
- installer list 能发现 `to-milestone`，且 explicit invocation policy 测试包含它。
- retired install 测试覆盖旧 `validate-flow` symlink 的安全识别。
- active Skill tree 只包含 owning-Skill Self-Review 与真实路径检查。
- 安装管理回归与 Skill quick validation 通过。

## Implementation Readiness

- Ready: yes
- Blocking Questions: none

## Progress

- Checkpoint: `to-milestone` 与 open durable-document 模型已落地并完成验证。
- Completed:
  - 用户已批准逐层填充、目录树、leaf gate、并行硬依赖、人类验收和父级汇总模型。
  - 用户已批准删除中央 artifact schema / validator，并保留独立安装管理。
  - 新 Skill、reference、behavior eval、routing、installer 与项目文档已经同步。
  - Skill quick validation、8 个 installer 单元测试、全部 eval JSON 解析和 changed-test audit 已通过。
- Next: 等待用户审阅实际工作流体验；后续调整由 `$to-milestone` 自己的行为反馈驱动。
- Blockers:
  - none
- Last verified:
  - 2026-08-25：`python3 -m unittest scripts.test_skill_manager`，8 tests passed。
  - 2026-08-25：skill-creator `quick_validate.py skills/to-milestone`，passed。
  - 2026-08-25：所有 `evals/*/cases.json` 解析通过；项目 `pnpm run test:audit --changed` 通过。
