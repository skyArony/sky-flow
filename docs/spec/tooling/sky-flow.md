---
id: sky-flow
artifact_type: spec
status: completed
---

# Sky Flow 工作流套件

最后更新：2026-07-20

## Intent

- Problem: 旧的文件化执行拓扑与 runtime 自主调度重复，但完全删除中间层后，复杂、长周期实现中跨会话仍有价值的代码事实、局部实现决策和具体恢复状态无处安放；它们既不应污染长期 spec，也不应只留在易失 runtime 中。
- Outcome: Sky Flow 保持 `runtime-first`：简单或单会话工作仍从 ready spec 直接执行；只在复杂、长周期或重新推导成本高的实现中按需物化一份非规范性 thin plan，作为跨会话 working set；执行拆解、owner、依赖、并行和 fan-in 仍由 runtime 动态完成。
- Audience: 使用、维护或扩展 Sky Flow 的 Agent、开发者与需要跨会话恢复状态的人类协作者。

## Context

### Confirmed Facts

- Agent runtime 已能根据当前事实动态拆解工作、选择主代理或子代理、维护临时 checklist、调整并行并完成 fan-in。
- Skill 使用 progressive disclosure；一旦隐式命中就会读取完整正文，因此过宽触发面会把可选能力变成日常上下文和延迟成本。
- 预先写死的文件化执行图容易在第一轮探索后失效，还要求额外维护字段、双向关系、状态和校验器。
- [GPT-5.6 prompting best practices](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#prompting-best-practices) 强调清晰结果、必要上下文、约束与验证，同时避免冲突 / 重复指令和不必要工具调用；因此这一层必须是按需 working memory，而不是固定阶段或步骤脚本。
- 长期设计、行为约束、关键决策、当前 checkpoint、blocker 和验证证据仍需要可恢复、可检索的文件化真相源。
- 复杂、长周期实现中的代码入口、模块关系、实现策略、局部决策、失败路线和具体 resume action 往往需要跨会话保留，但不具备 spec 的长期规范性。
- 人类 approval、真实设备 / 账号 / 环境、长期外部依赖和易失接力状态仍然是独立协作边界。

### Constraints

- Sky Flow 核心保持项目无关；项目命令、业务规则、部署限制和领域术语由本地文档或 adapter 承担。
- 简单工作不得为了使用流程而创建 artifact。
- plan 不是 ready spec 的必经 gate；不得仅因为存在 spec 或实现包含多个步骤就创建 plan。
- 文件化状态必须紧凑，不能退化成执行流水或隐藏拓扑。
- 同一文件或共享状态避免并发多写；完成交接后可以动态更换 writer，多 Agent 输出由主会话 fan-in。
- 简化不得删除 authority、no-touch、不可逆操作确认或确定性完成证据；减少的是重复模型 pass，不是安全与正确性边界。

## Scope

### In Scope

- spec-direct 设计、执行、进度和恢复模型。
- 从 durable spec 只读派生 portable runtime goal 的选择边界。
- `spec`、`plan`、`issue`、`acceptance`、`backlog`、`handoff` 六种 file-backed artifact。
- ready spec 的 runtime 动态执行与 Progress 写回。
- thin plan 的按需物化、快照更新、决策提升和完成收口。
- 测试、review、consolidation、验收、阻塞、交接、提交和校验边界。
- 历史文件化执行拓扑能力的归档与退出安装范围。

### Out of Scope

- 项目专属实施命令、基础设施凭据、业务状态机和团队组织规则。
- 记录子代理完整对话、微步骤、owner 分配或 runtime 并行图。
- 为 legacy plan/task/step 执行拓扑提供兼容创建、继续或校验入口。

## Core Model

```text
spec（长期设计 + readiness + Progress）
  ↓
显式可选 $pick-goal（只读 goal projection）
  ↓
ready spec / implementation-ready goal
  ├─ 简单、单会话或可低成本重建 → native runtime execution
  └─ 复杂、长周期或恢复成本高 → optional thin plan ↔ native runtime execution
  ↓
直接测试 / 静态检查 / build / 真实路径 / diff sanity
  ↓
durable semantics 提升到 spec Decisions / Progress；plan 更新或收口

显式可选：review / review-loop、consolidation、知识沉淀、第二意见、多 Agent、durable acceptance
```

旁路 artifact 只在真实边界出现：

- 人类必须判断：`acceptance`。
- 工作长期离开当前执行队列：`backlog`。
- 未提交 diff、终端、临时环境或易失证据需要接力：`handoff`。
- 值得长期保留的问题、线索或待决策证据：`issue`。

`plan` 不是真实边界 artifact，而是按需生成的实现期 working set。它可以在执行开始时创建，也可以在原本简单的工作扩大、需要跨会话恢复时中途 materialize。

## Runtime Configuration

Sky Flow 只读取 runtime 提供的环境变量：

- `SKY_FLOW_ROOT`：artifact 根目录，默认 `docs`。
- `SKY_FLOW_LANG`：artifact 与 Skill 输出语言，默认跟随用户语言；脚本默认 `简体中文`。

不解析额外项目配置文件。Codex 项目需要长期覆盖时，使用 `.codex/config.toml` 的原生环境策略：

```toml
[shell_environment_policy.set]
SKY_FLOW_ROOT = "docs"
SKY_FLOW_LANG = "简体中文"
```

## Artifact Model

### artifact_type

当前枚举：

- `spec`：长期设计、implementation readiness、稳定约束、Progress 和证据。
- `plan`：复杂、长周期实现的非规范性 working set；保存当前实现 slice、代码事实、局部策略、有价值的决策、具体恢复状态和验证入口。
- `issue`：问题、证据、机会或 unresolved finding；不是执行 slice。
- `acceptance`：真实人类 gate、反馈和 sign-off。
- `backlog`：长期阻塞、延期和恢复条件。
- `handoff`：易失跨会话 / Agent 接力状态。

普通 knowledge note 不属于 workflow artifact。

### status

通用枚举：

- `draft`：内容仍在形成或有阻塞澄清。
- `not_started`：已 ready，但执行尚未开始。
- `in_progress`：正在推进；短期阻塞也保持此状态并写入恢复条件。
- `completed`：该 artifact 的目标和必要验证 / 人类 gate 已结束。
- `abandoned`：有明确事实或人类依据不再继续，并应关联 backlog 或说明依据。

plan 没有 pre-readiness `draft` 阶段：恢复价值成立但尚未执行时使用 `not_started`，开始实施后 plan 与 source spec 都使用 `in_progress`。plan 的 `abandoned` 只表示丢弃当前 working set / approach，不代表放弃 source spec；只有 source work 真正退出 active queue 时才以 durable source 创建 backlog。

### Naming And Source

- artifact 文件 stem 必须等于 frontmatter `id`。
- spec 不使用数字编号前缀。
- plan 默认位于 `plan/<id>.md`，不使用数字排序、parent / child role 或反向绑定。
- plan 必须用单向 `source_type: spec` / `source_id: <spec-id>` 指向 ready、unfinished 规范性真相源；不允许 conversation、issue 或另一份 plan 作为来源。`in_progress` plan 要求 source spec 同样为 `in_progress`。
- 未完成 issue 位于 `issue/<id>.md`；completed issue 位于 `issue/fixed/<id>.md`。
- acceptance、backlog、handoff 使用单向 `source_type` / `source_id`；不维护反向绑定图。
- `conversation` + `current-session` 可作为没有上游 artifact 的来源，但正文必须补足上下文。

## Spec Contract

spec 至少表达：

- Intent：problem、outcome、audience。
- Context：confirmed facts、constraints、source notes。
- Scope：in / out。
- Acceptance Scenarios：关键成功、边界和反例行为。
- Requirements：可测试、无歧义。
- Decisions：选择、理由与替代方案。
- Verification Intent：必须保护什么、需要什么证据。
- Implementation Readiness：是否可以直接执行，以及 blocking questions。
- Progress：当前 checkpoint、语义结果、目标级恢复入口、blocker 和最近验证。

只有确有价值时增加 `Execution Constraints`：

- No Touch。
- Required Human Gates。
- Independent Review。
- Irreversible / External Actions。
- Stop Conditions。

不要把 runtime work items、owner、依赖、并行批次或子代理消息写进 spec。

## Design Alignment Contract

`to-spec` 不以问题数量或模板完整度衡量对齐质量，而以是否找到了决定设计成立的核心底座衡量：

- `底座对齐`确认根问题、成功边界、不变量、系统 / authority 边界、关键契约与非目标。
- `决策归属`区分仓库事实、人类决策、Agent 决策、runtime 选择和外部未知；可查事实不转问用户，边界内工程判断不误升级。
- `决策前沿`只存在于对话 / runtime，按依赖顺序关闭会改变多个下游判断的根问题；一次只问一个人类决策，并给出推荐、影响和解锁范围。
- `就绪证明`确认实现者不需要猜测产品口径、外部行为、数据语义、权限边界或验收方式。

spec 只保存稳定决策和仍真实开放的实质问题。重要决策可按需标注归属；开放问题可按需标注负责人、重要性、推荐与解锁范围。问题树、问答时间线、已关闭分支和 runtime 选择不得持久化。

复杂或高风险设计按需加载深度对齐参考；简单工作不得因此被迫创建 spec 或经历完整 grill 流程。

## Progress Contract

推荐格式：

```markdown
## Progress

- Checkpoint: <当前已经成立的稳定状态>
- Completed:
  - <完成的能力 / 行为结果及必要 evidence>
- Next: <下一轮优先推进的目标级恢复入口>
- Blockers:
  - <none，或阻塞原因与恢复条件>
- Last verified:
  - <YYYY-MM-DD；验证入口、结论和残余风险>
```

Progress 是覆盖更新的语义恢复快照：

- checkpoint 只记录稳定成立的能力、行为或状态。
- completed 记录语义结果，不记录逐步操作或逐文件改动。
- next 是目标级 resume target，不是 goal 本身或具体代码微任务。
- blockers 只保存会阻塞整体 goal、涉及外部条件 / authority / durable constraint 的目标级阻塞及解除条件；当前 slice 的局部实施 blocker 留在 active plan。工作长期离队时转 backlog。
- last verified 记录关键证据、结论、未验证范围和独立评估不可用降级。
- 必要定位可以使用少量稳定模块、类、函数、公开接口或测试套件名称，不使用具体代码行号。
- 不记录完整命令过程、tool call、子代理身份 / 消息、调度过程或执行时间线。
- 新写回必须合并或替换过期信息；spec 完成时压缩为 final outcome、evidence、residual risk 和 follow-up。

## Thin Plan Contract

plan 是可选、半持久的 implementation working set，不是 spec 与 runtime 之间的必经状态机。`to-implement` 默认直接执行；只有当 runtime-only 状态已不足以可靠恢复时，才创建或继续 active plan。

典型物化信号：

- 工作预期跨会话、跨 compaction 或明显无法在当前连续执行窗口完成。
- 实现包含多个需要独立验证的 slice，且中间事实或局部决策会影响后续 slice。
- 代码入口、模块关系、迁移顺序、失败路线或验证 seam 的重新推导成本较高。
- 工作原本由 runtime 直接开始，但执行中扩大、中断或出现必须保留的实现策略。

复杂度和时长只是判断信号，不是机械阈值。复杂但可在当前会话连续完成、且重新推导成本低的工作仍可只用 runtime checklist。简单、局部、一次性工作不创建 plan。

plan 默认形状：

```markdown
---
id: <plan-id>
artifact_type: plan
status: not_started | in_progress | completed | abandoned
source_type: spec
source_id: <spec-id>
---

# <Title>

## Current Slice
## Code Context
## Approach
## Decisions
## Progress
## Verification
```

字段与内容边界：

- `Current Slice` 只指向当前实现目标，不复制 spec 的 intent、requirements、constraints 或 acceptance。
- `Code Context` 保存下一轮不应重新探索的代码入口、模块 / symbol 关系、兼容或迁移事实；恢复时仍必须对可能漂移的事实做定点复核。
- `Approach` 保存当前可修正的实现方向和顺序理由，不绑定固定 milestone 或 step-by-step 脚本。
- `Decisions` 只保留会影响后续实现、或能防止重复踩坑的局部、可逆工程决策；任何事实或决定会改变 material scope、stable constraint、no-touch、外部行为、contract、data semantics、authority、acceptance 或长期架构时，必须先提升到 spec。
- `Progress` 使用覆盖快照，保存 Done / Active / Next / Blockers；允许模块、文件、symbol 或实现 slice 级定位，但 blocker 只限当前 slice 的局部实施问题，目标级 blocker 只引用 spec Progress。不得保存 tool call、Agent 消息、owner、依赖边、并行批次或时间流水。
- `Verification` 保存下一轮需要复用的验证入口、最近结论和未验证范围，不复制完整命令输出。

spec 是规范性真相源，plan 只是活动实现上下文；冲突时 spec 胜出。默认一份 spec 同时只保持一份 active plan；出现多份时由 validator warning 要求收敛或证明为什么 spec 不应拆分，不建立 plan graph。

用户直接提供 active plan path / id 时，它只是 resume locator：先解析并验证 source spec 的 readiness 与 lifecycle，再交给 `to-implement`；plan 不拥有独立 goal。

完成时，把已成立的长期决策提升到 spec Decisions，把语义 outcome、evidence 和 residual risk 写入 spec Progress，再将 plan 压缩为最小 completed 摘要或删除。不创建 `plan/done`、完整执行档案或 task retention 流程。

## Goal Projection

`pick-goal` 在用户明确要求选择、恢复或生成目标时，从 unfinished spec 只读派生 portable runtime goal：

- spec 是 durable goal source。
- Progress 是 resume cursor，`Next` 只是恢复入口。
- runtime goal 是当前会话的执行投影，不是新 artifact。
- objective 来自 spec outcome；done condition、constraints 和 evidence 来自相关 durable semantics。
- direct target 优先；未指定时做语义选择，不使用固定评分、mtime 或机械状态排序。
- 选择和投影不修改 spec。用户明确要求启动时按 readiness 交接：implementation-ready goal 进入 `to-implement`，alignment goal 进入 `to-spec`，仍有 blocker 的 goal 保持未启动。
- 原生 goal 只承载已经选定的目标；创建后 `pick-goal` 结束职责，由接收方拥有执行和稳定状态写回。
- 选择时如果目标 spec 存在 active thin plan，可把其路径作为 resume context 一并交给 `to-implement`；目标、成功边界和 constraints 仍只来自 spec，pick-goal 不选择、排序或继续 plan。

一个 coherent spec 可以随 Progress 推进连续派生多个 runtime goal，但每次只输出一个当前投影，不持久化 sibling goal graph。只有多个 outcome 彼此无关、可独立演进且不共享成功标准时才由 `to-spec` 考虑拆分；不能由 `pick-goal` 挖成隐藏 task 图。

## Native Runtime Execution

`to-implement` 直接读取 ready spec、由它派生的 implementation-ready runtime goal，或先把用户给出的 active plan locator 解析回 ready source spec。alignment goal 回 `to-spec`，仍有 blocker 的 goal 不启动。执行器只规定不可越过的目标、权限、真实 gate、并发写安全、完成证据和写回边界；实现策略保持高自由度。

- 读取足以理解目标、成功标准、当前真相、constraints 和恢复入口的语义；不要求固定 section schema。
- runtime 自主选择探索、实现、工具、checklist、顺序和普通验证组合；Sky Flow 不预设 lane、角色或重复 pass。
- Mission 必须清楚；其他 delegation packet 字段只在相关时提供，不形成缩小版 task 模板。
- 简单工作直接执行；复杂但可连续完成的工作可只用 runtime checklist。当恢复成本或中断风险超过维护成本时，才按 Thin Plan Contract 创建或更新 plan；无需在开工前预测所有后续复杂度。
- 只有多个消费者或上下文容易在交接中失真时，才在 runtime 内一次投影`目标 / 成功边界 / 关键约束 / 相关契约 / 当前事实`并复用；它不是固定 packet，也不代替 plan 的跨会话 working set。
- runtime 支持模型选择时，清楚、局部、可验证的工作可使用满足要求的最小模型；高歧义、高风险或最终冲突仲裁使用更强模型。
- 普通测试、测试 ROI、stable seam、静态检查、build、真实路径验证和 diff sanity 由 runtime 直接判断与执行；真实事故回归留在 `to-debug` 的同一证据循环。专门 review、review loop、consolidation、知识沉淀、第二意见、多 Agent 和 file-backed acceptance 只在用户显式调用时进入；已有 durable constraint 由 runtime 用最小充分路径满足，不隐式加载其他重型 Skill。
- 多个修复方向或 fan-in 冲突优先继续取证和裁决；只有触及用户拥有的重大决策、权限或不可逆边界且无法安全推导时才问人。
- 只在语义 checkpoint、outcome、blocker、evidence、risk 或 resume target 稳定变化时写回 spec；代码事实、局部策略和具体 resume action 只在 active plan 存在且具有恢复价值时写回 plan。

### Subagent ROI

Sky Flow 默认不要求派发子代理。只有用户显式要求多 Agent，或 source spec 明确要求独立评估时，runtime 才在授权边界内决定是否派发；派发仍要求收益高于 fan-in 成本：

- 并行时间收益。
- 上下文隔离收益。
- 专业化收益。
- 独立 review / verification 收益。

共享 contract、数据库 schema、部署配置、公共入口和同一 artifact 避免并发多写；完成交接后可以动态更换 writer。

### Runtime Gates

gate 保留为不变量，不再物化成执行节点：

- spec 或用户明确要求独立 review 时，implementation owner 不得自行清除。实际风险只能在安全 / 权限 / 资金 / 数据 / 迁移等高风险且当前证据不足时升级独立评估，不能因普通 P1 标签自动升级。
- 独立评估默认一个 fresh reviewer / verifier；只有用户明确要求，或 P0 安全边界仍存在证据冲突时才使用第二个模型 / 供应商。结论写入 Last verified。
- 独立评估不可用时记录 `independent_review: unavailable` 和残余风险。
- 人类 approval、真实设备 / 账号 / 环境、体验或风险接受先在对话中停止并询问；只有需要 durable、多轮或跨会话 gate 且用户显式调用时才创建 acceptance。
- Agent 可自行完成的 test、lint、build、静态 review 直接执行并记录证据。

### Review Efficiency

- 普通实现不自动进入 `to-review`；runtime 用测试、静态证据、真实路径和 focused diff check 完成自检。
- 用户显式调用 `$to-review` 时，默认一个 reviewer 同时给出设计 / spec 符合性和代码质量结论，并列出无法验证项。
- 只有大 diff、多 reviewer 或重复复审时才准备文件化 review context；必须引用 source spec / goal，不能只提供 diff。
- 多 reviewer 只在用户显式要求，或 source spec 的 Independent Review 明确要求多个独立结论时使用，并保持独立上下文。
- consolidation 只在用户显式调用 `$to-consolidation` 时进入；runtime 仍应直接清理自己引入的明显临时残留和无关 diff。
- finding 修复后默认由当前执行者定点验证对应 hunk、真实路径和必要测试；只有 P0、证据冲突、高风险安全 / 资金 / 权限 / 迁移且定点证据不足，或用户 / spec 明确要求时才启动一个独立 verifier。
- 只有独立 verifier 后仍存在证据冲突、P0 安全边界需要双重确认，或用户明确要求时，才使用两个模型 / 供应商。
- 没有文件变化或 confirmed finding 时不启动 verifier，由整合 review 直接给出可追溯结论。

## Artifact Boundaries

### Plan

plan 只承载 active implementation working set，必须来源于 ready spec。它可以记录文件 / 模块 / symbol 级实现上下文、当前 approach、局部 decisions、具体 progress 和验证入口，但不复制 spec，不承载人类 gate，不成为 task registry 或 runtime controller。

runtime 可以直接绕过 plan，也可以在执行中途 materialize。plan 完成不等于 spec 完成；收口前先把 durable semantics 提升到 spec。

### Issue

issue 保存问题、证据、影响和一个有价值的下一决策。它不是实施脚本。

如果问题需要长期设计，转入或关联 spec；如果设计已经明确且工作很小，可直接 runtime 执行并在 issue 完成时写 resolution / evidence。

### Acceptance

acceptance 只承载 Agent 无法自行判断或必须由人类拍板、且需要 durable / 多轮 / 跨会话记录的事项。一次性补信息或确认直接在对话处理；用户显式调用 `$to-acceptance` 后才创建 file-backed artifact。

每组保持「问题 / 需求 → 验收步骤 → 验收结论（人类填）」；Agent 可自证结果只作为简短 evidence。

### Backlog

backlog 只在工作退出当前执行队列、等待长期外部依赖、人类决定或环境条件时创建。短期阻塞写 spec Progress。

必须记录 source、blocker、depends_on、recommended_resume 和恢复后的第一动作。

### Handoff

handoff 只保存易失接力状态：未提交 diff、当前终端、临时环境、短生命周期证据和接手动作。

长期设计、稳定进度、关键决策和验证结论必须回写 spec；handoff 不复制 Progress。

## Active Skill Suite

| Skill | Responsibility |
| --- | --- |
| `sky-flow` | 入口、路由和 artifact 纪律 |
| `to-spec` | 设计对齐、readiness、constraints、Progress |
| `pick-goal` | 从 unfinished spec 只读派生 portable runtime goal，并在显式启动时按 readiness 交接 |
| `to-implement` | runtime-first execution、按需 thin plan 与 spec / plan 稳定写回 |
| `to-issue` | 本地问题与证据记录 |
| `to-debug` | 诊断与真实事故回归 |
| `to-review` / `to-review-loop` | 风险审查与显式复审循环 |
| `to-agent-review` | Agent 决策链复盘 |
| `to-consolidation` | pending diff 熵值收敛 |
| `to-acceptance` / `to-next-acceptance` | 人类 gate 与反馈轮次 |
| `to-backlog` | 长期阻塞与恢复条件 |
| `to-handoff` | 易失接力状态 |
| `to-commit` | scoped stage / commit |
| `validate-flow` | 轻量 artifact 校验 |
| `to-knowledge` | 通用技术知识 |
| `to-claude-review` | Codex 到 Claude Code 的只读 review bridge |

`to-infra` 是 project-provided adapter slot，不由 Sky Flow core 实现。

## Validation Model

确定性校验只覆盖：

- frontmatter、最小字段、枚举、id / 文件名和 root。
- issue fixed 路径规则。
- plan 不允许 `draft`，必须单向来源于 ready、unfinished spec；`in_progress` plan 的 source spec 也必须为 `in_progress`。全量扫描中的孤儿 plan 是 error，显式局部范围缺失 source 才是 warning。
- acceptance / backlog / handoff 继续使用各自单向 source，且不得以 plan 为规范性来源。
- active plan 的 Progress 存在性，以及同一 spec 多份 active plan 的收敛 warning。
- abandoned 与 backlog / 人类依据。
- ready / active / completed spec 的 Progress 存在性。
- retired task / step artifact 或 legacy plan/task topology 字段残留。

语义收口看设计一致性、spec Progress 快照、thin plan 的物化价值、blocker 分层与非规范性边界、真实 constraints、acceptance 价值、backlog 恢复和 handoff 易失性。spec Progress 必须保持语义级；plan 可使用文件 / 模块 / symbol / slice 级定位，但仍排除 tool / Agent 流水、owner、依赖边、并行 lane 和微步骤。

校验时机按成本分层：plan create、source / status、decision promotion、closure，以及 plan 即将作为恢复 / handoff / commit 输入时必须运行 deterministic precheck；有 warning 或规范性判断时做 focused semantic pass。仅覆盖 body working-set snapshot 的高频更新可批量到下一个恢复 / 提交边界，不要求每次都触发完整 validator / model pass。

## Migration And Archive

旧文件化 plan/task/step 执行拓扑仍是 breaking removal，不提供 active 兼容创建或继续入口。新 `artifact_type: plan` 只兼容 thin plan contract；恢复 artifact 名称不等于恢复旧 lifecycle 或 Skill。

迁移规则：

- 长期目标、scope、requirements、外部行为、稳定架构 decisions → spec 对应 section。
- 语义 checkpoint、已成立 outcome、目标级 next、真实 blocker、evidence → spec Progress。
- 仍在 active implementation 中有用的代码事实、局部 approach / decision、具体 progress 与 resume action → 重写为 thin plan，不保留 task graph。
- 人类 gate → acceptance。
- 长期延期 / 外部依赖 → backlog。
- 未提交 diff / 临时环境 / 终端状态 → handoff。

历史 Skill 保存在仓库根 `archive/skills/`，文件名使用 `SKILL.archived.md`，不位于 active `skills/` 发现范围。active routing 和安装清单不得引用它们。root copy-mode 安装必须排除 `archive` 与 `.git`；symlink 模式虽然能看到 checkout 文件树，但 archive 中没有可发现的 `SKILL.md`。

升级时，installer 只自动清理明确指向当前 checkout 的 retired symlink 或冗余 Codex child symlink。copied / foreign install 不得隐式删除，但必须让 update / doctor readiness 失败并给出显式替换路径。Claude 因不发现 nested Skill，直接安装 suite entry 和 callable children；Codex 只安装 suite entry，并通过它发现 children。doctor 对 Codex symlink 验证 suite root，对 copy-mode 逐个比较 managed child subtree（包括 references / scripts），并把残留 direct child 判为待迁移状态，不得用它掩盖 stale content。

## Acceptance Scenarios

1. 简单工作不进入文件化流程。
   - Given 工作不需要长期设计、跨会话恢复或真实人类 gate
   - When 用户要求执行
   - Then Agent 直接使用 runtime，不为执行创建 plan

2. ready spec 可以直接执行。
   - Given spec 没有 blocking question，且 Next 提供目标级恢复入口
   - When 用户要求实现或继续
   - Then `to-implement` 动态调度 runtime；如果工作可在当前执行窗口可靠完成，不先创建 plan

3. 第一轮探索推翻初始拆解。
   - Given runtime 已形成临时工作顺序
   - When 新证据改变依赖或并行方式但不改变 spec scope
   - Then 主代理直接调整 runtime checklist，不修改文件化拓扑

4. 执行出现设计变化。
   - Given 新事实会改变 requirement、contract、data semantics 或 acceptance behavior
   - When Agent 无法在既有 spec 内安全继续
   - Then 停止执行并建议用户显式调用 `$to-spec` 对齐，不在实现层猜设计

5. 人类 gate 不被伪装成 Agent 自证。
   - Given 完成依赖真实设备、账号、环境、体验或风险接受
   - When Agent 到达该边界
   - Then 在对话中停止并请求人类结论，不宣称自行通过；只有用户显式要求 durable gate 时才创建或更新 acceptance

6. Progress 不膨胀成流水账。
   - Given 多轮执行和多个子代理完成工作
   - When 写回 spec
   - Then 只保留语义 checkpoint、outcome、目标级 next、blocker、证据和 residual risk，不记录代码行、逐文件 diff、命令 / tool / Agent 过程或时间线

7. 旧执行 artifact 被拒绝。
   - Given checked docs 仍声明 retired artifact type 或拓扑字段
   - When `validate-flow` 运行
   - Then 返回明确 migration error，不提供兼容执行路径

8. 多个 spec 可以派生一个 runtime goal。
   - Given 用户显式调用 `$pick-goal` 且存在一个或多个 unfinished spec
   - When `pick-goal` 运行
   - Then 它按用户意图和 durable semantics 选择一个 spec，输出 portable goal，不创建 artifact、不把 Progress.Next 当 goal、不自动执行

9. 显式启动 goal 有唯一交接路径。
   - Given `pick-goal` 已派生 goal 且用户明确要求启动
   - When readiness 已判定
   - Then ready goal 交给 `to-implement`，alignment goal 交给 `to-spec`，blocked goal 只报告解除条件；`pick-goal` 不拥有后续执行

10. 安装判定匹配 runtime discovery。
   - Given Claude 需要直接 child links 而 Codex 能从 suite root 发现 nested Skills
   - When install、update 或 doctor 运行
   - Then Claude 按 Skill 直接判定，Codex 按 suite root 判定，并在 copy-mode 校验目标 child 的当前内容

11. 仓库事实不被伪装成人类问题。
   - Given 一个设计分叉可以从代码、docs、schema 或现有证据确认
   - When `to-spec` 对齐设计
   - Then Agent 自行取证并说明结论，不询问用户仓库当前如何实现

12. 决策按真实 authority 分流。
   - Given 设计同时包含产品口径、边界内工程选择和执行时细节
   - When 判断决策归属
   - Then 只把产品口径交用户，Agent 自主完成工程选择，runtime 细节不进入 spec

13. 决策前沿先关闭根问题。
   - Given 多个实质问题存在依赖关系
   - When 进行复杂 spec 对齐
   - Then 一次只问一个最靠近根部的问题，附推荐、影响和解锁范围，且不持久化问题树

14. 多消费者复用紧凑 runtime context。
   - Given 实现需要多个 reviewer 或子代理理解相同边界
   - When runtime 派发工作
   - Then 可复用目标、成功边界、关键约束、相关契约和当前事实，而不创建固定 packet 或 artifact

15. review 成本与风险匹配。
   - Given 复审没有高风险证据、fan-in 熵值或 confirmed finding
   - When review 或 review loop 收口
   - Then 不强制 final consolidation、独立 verifier 或双 verifier，并由一次整合 review 或定点验证给出结论

16. 日常实现不自动加载重型能力。
   - Given 用户要求普通实现、测试修改或修复，且 source spec 没有独立评估 constraint
   - When runtime 执行并验证结果
   - Then 直接判断测试 ROI 并运行必要测试、静态检查、build、真实路径和 diff sanity，不自动进入 `to-review`、`to-consolidation`、多 Agent 或 artifact 写入

17. 重型能力由用户主动开启。
   - Given 用户需要专门 review、review-fix-rereview、diff 收敛、知识沉淀、第二意见、多 Agent 或 durable acceptance
   - When 用户显式调用对应 `$skill`；或 source spec 已持久化独立评估 constraint
   - Then 只运行被请求的 Skill；独立评估 constraint 由 runtime 用最小充分路径满足，不隐式加载其他重型 Skill

18. 真实事故回归不另开工作流。
   - Given `to-debug` 已确认真实事故的 expected behavior、复现、incorrect path 和 correct path
   - When 存在稳定测试 seam
   - Then 用最小失败测试命中 incorrect path，修复后用同一测试验证 correct path；没有稳定 seam 时保留可重复 replay / smoke evidence 和 residual risk

19. 复杂长周期实现按需创建 plan。
   - Given ready spec 的实现预期跨会话或包含多个会相互影响的验证 slice，重新推导代码事实与局部决策成本较高
   - When `to-implement` 开始或继续执行
   - Then 它创建或读取一份 source spec 单向绑定的 thin plan，保存紧凑 working set，仍由 runtime 自主拆解与调度

20. 工作可以中途 materialize plan。
   - Given 工作开始时足够小，因而只使用 runtime checklist
   - When 新证据使实现扩大、中断或需要保留难以重建的上下文
   - Then runtime 在不重启流程、不询问人类的情况下物化 thin plan，把仍有效的 working set 压缩写入

21. plan decision 按稳定性分流。
   - Given 实现中产生一项会影响后续 slice 的工程决策
   - When 它只是已确认边界内局部、可逆的实现选择
   - Then 记入 plan；如果它改变 material scope、stable constraint、no-touch、外部行为、contract、data semantics、authority、acceptance 或长期架构，先提升到 spec 再继续

22. thin plan 不恢复旧执行拓扑。
   - Given plan 已创建并由 `validate-flow` 检查
   - When 文件包含 tasks、plan role、dependency / parallel fields、owner lanes 或 task / step artifact
   - Then validator 拒绝 legacy topology；只有 thin plan 的单向 source、snapshot Progress 和非规范性内容可以通过

23. active plan 可以作为恢复定位器。
   - Given 用户直接给出 active plan path 或 id 并要求继续
   - When 路由执行
   - Then 先解析 source spec、校验 readiness 与 lifecycle，再进入 `to-implement`；plan 不成为独立 goal 或规范性来源

24. plan 与 source spec lifecycle 保持一致。
   - Given implementation working set 的恢复价值已经成立
   - When plan 尚未开始或已经推进
   - Then plan 分别使用 `not_started` 或 `in_progress`，不创建 `draft` 阶段；`in_progress` plan 对应 `in_progress` source spec

25. plan 收口不自动收口 spec。
   - Given 当前 implementation slice 已完成，但 source spec 仍有 durable scope
   - When plan closure
   - Then durable decision / outcome / evidence / risk 先提升到 spec，plan 压缩或删除且不进入 `plan/done`；高频 body snapshot 可以批量校验，但 closure 必须完成确定性与必要语义校验

## Requirements

- R1: Sky Flow active artifact 枚举必须只包含 spec、plan、issue、acceptance、backlog、handoff。
- R2: ready spec 必须可以直接进入 `to-implement`，plan 不得成为 mandatory gate。
- R3: runtime decomposition、owner、dependency、parallelism 和 fan-in batching 不得持久化为 workflow artifact；thin plan 只保存非规范性 implementation working set。
- R4: spec Progress 必须是覆盖更新的恢复快照，不是 append-only 执行日志。
- R5: 人类 gate、长期阻塞和易失交接必须分别归入 acceptance、backlog、handoff。
- R6: active installer 和 routing 不得发现或推荐 archived skills。
- R7: validator 必须接受符合 thin contract 的 plan，拒绝 retired task / step artifact 和 legacy plan/task topology 字段，并提供迁移方向。
- R8: 独立 review、人类 approval、no-touch 和不可逆操作约束不得因删除执行图而消失。
- R9: 简单工作必须保留直接 runtime 快速路径。
- R10: 所有 active skill 必须以 spec Progress、可选 thin plan 或 runtime state 表达执行上下文，不引用旧文件化拓扑。
- R11: installer / doctor 必须显式检测 retired install residue 与 active stale copy，并比较 managed skill subtree 而不只比较 `SKILL.md`；不能把缺失 / 过期 reference 或旧拓扑指令误报为 ready。
- R12: internal-only reviewer profile 不得作为顶层 callable skill 安装。
- R13: `pick-goal` 必须只读地从 unfinished spec 派生 portable runtime goal，不创建 goal artifact、不自动执行、不恢复 task topology。
- R14: spec Progress 只能保存语义结果和稳定恢复信息；不得保存具体代码行、逐文件 diff、完整命令 / tool / Agent 过程或执行时间线。
- R15: `to-implement` 只硬性保护用户 intent、真实 constraints、authority、并发写安全和 completion evidence；其他执行策略必须保持为 runtime 自主选择或启发式建议。
- R16: `pick-goal` 显式启动必须按 readiness 唯一交接；它不拥有 implementation 或 alignment 执行。
- R17: installer / doctor 必须使用 target-specific discovery：Claude 要求直接 child install，Codex 通过 suite root 接受 nested child，并保持 copy-mode stale 检测。
- R18: `to-spec` 必须用底座对齐、决策归属、决策前沿和就绪证明识别实质决策；不能用固定问题数量替代真实对齐。
- R19: 仓库事实必须优先取证，人类只决定其 authority 范围内的产品 / 业务 / 风险 / 外部行为 / 权限 / 不可逆事项。
- R20: 问题树与问答过程只存在于对话 / runtime；spec 只保存稳定结论和仍真实开放的问题。
- R21: 多消费者 runtime context 可按需投影目标、成功边界、关键约束、相关契约和当前事实，但不得自动成为固定 packet；只有满足 thin plan 物化边界的 implementation working set 才可持久化。
- R22: 显式 `to-review` 必须默认由一个 reviewer 同时判断设计 / spec 符合性和代码质量；finding 修复默认定点验证，额外 reviewer / verifier 只在用户 / spec 明确要求或高风险证据不足时触发。
- R23: `to-spec` 必须有覆盖简单任务、仓库事实、authority、外部契约和过大 scope 的轻量回归夹具。
- R24: 重型 Skill 必须使用显式调用策略；普通实现、测试修改、修复和交付检查不得因宽泛 description 自动加载它们。
- R25: runtime 必须直接完成与风险匹配的确定性验证；显式 Skill policy 不得被误解为可以跳过 test、lint、typecheck、build、真实路径或权限 gate。
- R26: 测试 ROI、stable seam、普通测试实现与验证组合必须属于 native runtime；真实事故回归必须留在 `to-debug`，不得要求独立测试 workflow 才能完成。
- R27: `to-implement` 必须使用 `runtime-first, plan-on-demand`；简单或单会话可靠完成的工作不创建 plan，复杂长周期工作可在开始时或中途物化 plan。
- R28: plan 必须单向来源于 ready、unfinished spec，不得使用 `draft`，且 `in_progress` plan 必须对应 `in_progress` spec；plan 不得作为 acceptance、backlog 或 handoff 的规范性 source。
- R29: plan 必须使用覆盖更新的 working-set 快照，不得存储 task graph、owner、dependency、parallelism、fan-in batching、tool / Agent 过程或时间流水。
- R30: plan decision 只能承载边界内局部、可逆工程选择；会改变 material scope、stable constraint、no-touch、外部行为、contract、data semantics、authority、acceptance 或长期架构的事实 / 决策必须先提升到 spec。
- R31: plan 完成时必须先把 durable decisions、semantic outcomes、evidence 和 residual risk 提升到 spec，再压缩或删除；不恢复 `plan/done` 或 task archive。
- R32: 新 plan artifact 不得恢复 active `$to-plan`、`pick-plan`、`to-task`、`to-archive` Skill；日后只有被代表性 eval 证明的独立 authoring 需求，才可考虑新的 explicit-only 薄入口。
- R33: 必须有代表性 eval 覆盖简单工作绕过、单会话复杂工作绕过、长周期物化、中途物化、direct plan resume、decision 提升、closure 和 handoff 边界。
- R34: spec Progress 只拥有 goal-level、external、authority 或 durable-constraint blocker；plan 只拥有当前 slice 的局部实施 blocker，并引用而不复制 spec blocker。
- R35: 用户直接提供 active plan 时，routing 必须先解析和验证 source spec，再由 `to-implement` 恢复；不得把 plan 当作独立 goal。
- R36: plan create、source / status、promotion、closure 和恢复 / handoff / commit 边界必须校验；纯 body snapshot 可批量到下一个边界，避免每次更新触发完整模型 pass。

## Decisions

- Decision: 继续删除 legacy plan/task/step 执行拓扑，不保留兼容创建或继续路径。
  - Why: runtime 已能动态调度；兼容层会保留原有复杂度并继续诱导重复状态。新 thin plan 只恢复 working memory，不恢复 control topology。
  - Alternatives: 恢复旧 plan/task 作为可选模式；放弃，因为 active surface 仍会膨胀。
- Decision: 保留并重写 `to-implement` 为薄 spec executor。
  - Why: 它提供清晰的 spec → runtime → Progress bridge，避免把执行规则重新塞进根入口。
  - Alternatives: 完全删除执行入口；放弃，因为 ready spec 的触发与写回边界会分散到多个 Skill。
- Decision: Progress 放在 spec，采用快照而非事件流。
  - Why: spec 只保留长期语义恢复所需的最小状态；实现期的代码事实和具体 resume state 由可选 thin plan 承载，不再挤进 spec Progress。
- 决策: 恢复 `plan` artifact 名称，将其重新定义为非规范性、半持久 implementation working set。
  - 归属: 人类确认需求与定位，Agent 负责合同与边界设计。
  - 理由: spec Progress 明确排除实现细节，runtime checklist 不持久，handoff 又只保存易失本地状态；复杂长周期实现因此缺少可恢复中层。
  - 放弃方案: 扩容 spec Progress；放弃，因为会混合长期真相与实现期 scratch state。把它放进 handoff；放弃，因为 handoff 是本地易失接力而非默认实现记忆。
- 决策: 采用 `runtime-first, plan-on-demand`，plan 可以在执行中途 materialize。
  - 归属: 人类明确简单工作直接 runtime、复杂长周期工作才需要 plan；Agent 负责物化启发式。
  - 理由: 恢复性是真实需求，但它不应让局部、单会话工作支付 artifact 成本；中途物化避免了在开工前过度预测复杂度。
  - 放弃方案: 每个 ready spec 都预先创建 plan；放弃，因为违反简单工作快路径和 lean prompting。
- 决策: plan 没有独立 authoring / draft lifecycle，直接恢复也必须先回到 ready source spec。
  - 归属: Agent（已确认边界内）。
  - 理由: `not_started` 已能表达物化后尚未执行；额外 draft 或 plan-owned goal 会重新制造 readiness gate。
- 决策: plan 校验按结构与恢复边界分层，高频 body snapshot 允许批量。
  - 归属: Agent（已确认边界内）。
  - 理由: source / status / promotion / closure 必须确定性可靠，但每次 working-set 覆盖都启动完整模型 pass 会抵消 thin plan 的收益。
- 决策: 第一阶段不恢复 active `$to-plan`、`pick-plan`、`to-task` 或 `to-archive`。
  - 归属: Agent（已确认边界内）。
  - 理由: plan 的当前缺口是实现期存储而非独立编排能力；由 `to-implement` 按需管理能保持最小 skill / prompt surface。
- Decision: gate 以 constraint 和 evidence 表达，不以节点存在性证明。
  - Why: 保护安全不变量，同时允许 runtime 动态选择实现方式。
- Decision: archived Skill 使用 `SKILL.archived.md` 并位于根 `archive/skills/`。
  - Why: 保留历史参考，同时避免 installer 或 runtime 把它们识别为 callable capability。
- Decision: reviewer profile 使用 `PROFILE.md`，只由 `to-review` 按深度读取。
  - Why: internal policy 不是用户入口，暴露为顶层 skill 只会增加安装和路由噪音。
- Decision: 新增只读 `pick-goal`，从 spec 编译 runtime goal。
  - Why: 补足多个 spec 的选择 / 恢复入口，同时让 spec 保持 durable truth、Progress 保持 cursor，避免恢复 task artifact。
  - Alternatives: 直接恢复 `pick-plan` 或把 Progress.Next 当 goal；放弃，因为都会重建执行层。
- Decision: `to-implement` 使用 Must Preserve 与开放 guidance，而不是固定 packet、role 和流水线。
  - Why: 安全边界必须明确，但实现方法应随模型能力、上下文和证据动态调整。
- Decision: goal 启动按 readiness 交给现有能力，不新增 goal workflow 层。
  - Why: ready、alignment 和 blocked 的处理边界需要明确；thin plan 只作为 `to-implement` 的 resume context，不拥有 goal 选择或启动。
- Decision: installer 使用 target-specific discovery model。
  - Why: Claude 需要直接 child links；Codex 已能从 suite root 发现 nested Skills，重复链接会扩大安装面并让 doctor 与真实 runtime 状态不一致。copy-mode freshness 必须比较 managed subtree，确保按需 reference / script 也不会缺失或过期。
- 决策: spec 对齐采用底座对齐、决策归属、决策前沿和就绪证明。
  - 归属: 人类确认方向，Agent 负责方法设计。
  - 理由: 重点关闭会改变成功边界和关键契约的少数根决策，而不是象征性提问。
  - 放弃方案: 固定问题清单或持久化 decision graph；前者容易漏掉核心底座，后者会恢复流程负担。
- 决策: 深度 grill 指引与评估夹具按需加载，不增加顶层 callable skill。
  - 归属: Agent（已确认边界内）。
  - 理由: progressive disclosure 保持简单任务快速，同时让复杂设计具备压力检查能力。
- 决策: 复杂执行可使用一次性 runtime context 投影；只有在跨会话恢复价值成立时才物化 thin plan。
  - 归属: Agent（已确认边界内）。
  - 理由: 多消费者复用共同语义可减少重复 token 和上下文漂移；持久化成本只在可恢复性收益更高时支付。
- 决策: review 合并双维度判断；consolidation 只显式触发，verifier 只补真实高风险证据缺口。
  - 归属: Agent（已确认边界内）。
  - 理由: 保留高风险独立验证，同时移除低风险范围的固定重复 pass。
- 决策: 仍有独立价值的重型 workflow Skill 保留能力但关闭隐式调用。
  - 归属: 人类确认方向，Agent 负责具体边界。
  - 理由: progressive disclosure 只有在触发准确时才节省上下文；显式 `$skill` 让日常任务不为 review loop、consolidation、knowledge、second opinion、多 Agent 或 durable acceptance 支付固定成本。
  - 放弃方案: 删除所有重型能力；放弃，因为复杂或高风险任务仍需要可复用入口。
- 决策: 退役 `to-test` 与 `to-bdd-regression`，只把最小不变量合入 native runtime 和 `to-debug`。
  - 归属: 人类确认方向，Agent 负责迁移边界。
  - 理由: 最新 runtime 已能按风险选择测试 ROI、stable seam、Red / Green 和替代验证；事故回归若脱离 debug 证据另开流程，只会重复上下文并增加延迟。
  - 放弃方案: 继续作为显式 Skill 保留；放弃，因为它们的独特价值可以分别由一条 ROI 规则和一个 evidence-to-regression 规则完整表达。
- 决策: 普通正确性反馈由 runtime 直接完成，模型独立 pass 不替代确定性证据。
  - 归属: Agent（已确认边界内）。
  - 理由: 测试、静态检查、build、真实路径和 diff sanity 通常比重复模型审查更快、更稳定；authority 与不可逆边界仍保留。

## Verification Intent

- Must Protect:
  - active install list 不包含 archived skills。
  - internal reviewer profile 不进入 active install list。
  - stale active copies 与无法安全删除的 retired installs 被 readiness 拒绝。
  - validator 接受 source spec 单向绑定的 thin plan，拒绝 task / step artifact 与 legacy topology 字段。
  - 同一 spec 多份 active plan 产生收敛 warning，plan 来源非 spec 时确定性失败。
  - current spec 自身通过 deterministic validation。
  - active docs / Skill 没有旧路由或旧 artifact lifecycle 残留。
  - `to-implement` 清楚表达 runtime-first、plan-on-demand、中途 materialization、decision promotion 和双快照写回。
  - `pick-goal` 只读、不会创建 artifact 或把 Next 当 goal。
  - goal 显式启动按 readiness 交给 `to-implement` 或 `to-spec`；blocked goal 不启动。
  - Claude direct-child 与 Codex suite-root 的 install / doctor 判定一致，copy-mode 能发现缺失 / 过期的 nested Skill、reference 或 script。
  - Progress 不包含代码行号、逐文件 / 命令 / tool / Agent 流水。
  - thin plan 可以保存文件 / 模块 / symbol / slice 级上下文与验证入口，但不复制 spec、不存储微步骤或执行拓扑。
  - `to-spec` 能区分仓库事实、人类 / Agent 决策、runtime 选择和外部未知，并形成可解释就绪证明。
  - 深度对齐参考只按复杂度加载，评估夹具覆盖 6 类代表性案例。
  - 仍 active 的 heavy Skill 使用 `allow_implicit_invocation: false`，routing 与 description 不再自动推荐它们。
  - `to-test` 与 `to-bdd-regression` 不在 active discovery / routing；installer 能识别并清理它们指向当前 checkout 的旧直链。
  - review context 同时携带 source spec / goal 和 diff；finding 修复默认定点验证，review-loop 不再强制 consolidation、独立 verifier 或双 verifier。
  - 普通实现路径仍直接运行必要测试、静态检查、build、真实路径和 diff sanity，显式调用策略不降低验证完整性。
  - 代表性 eval 能区分简单 / 单会话绕过与复杂长周期 / 中途 materialization，并检查 spec、plan、runtime、handoff 决策分流。
- Suggested Evidence:
  - `node --check scripts/validate_flow.ts`
  - `node scripts/validate_flow.ts`
  - `python3 -m unittest scripts.test_validate_flow scripts.test_skill_manager`
  - `./install.sh list --json`
  - `./install.sh --dry-run --no-deps`
  - retired artifact / topology negative fixtures
  - thin plan positive、invalid-source、source-status、direct-resume、full / partial orphan、multiple-active 和 runtime-bypass fixtures
  - copy-mode managed subtree freshness fixtures，覆盖 nested Skill、reference 与 script
  - active tree residual keyword scan
  - `python3 skills/to-review/scripts/test_prepare_review_context.py`
  - `python3 skills/to-agent-review/scripts/test_preflight.py`
  - `python3 -m json.tool evals/to-spec/cases.json`
  - `python3 -m json.tool evals/to-implement/cases.json`
  - pending diff integrated sanity；不隐式运行 review、consolidation 或多 Agent

## Execution Constraints

- No Touch:
  - `to-claude-review` 的 permission strategy `plan` 属于 ACP 权限模式，不是 Sky Flow artifact，不能误删。
  - Agent review 测试中的 `ExitPlanMode` / `Task` 是外部 transcript 工具名，不能误删。
- Required Human Gates:
  - none；用户已明确批准以 optional thin plan 恢复复杂长周期 implementation working set，并保留简单工作 runtime 快路径。
- Independent Review:
  - 默认无；当前执行者做 focused diff review 与确定性验证。只有用户 / spec 明确要求，或高风险证据不足时才增加独立 reviewer。
- Irreversible / External Actions:
  - 清理安装目录中的旧 symlink 只允许删除明确指向本仓库 retired skill path 的链接。
- Stop Conditions:
  - 发现必须保留 legacy active compatibility，或清理目标不是 repo-owned symlink 时停止询问。

## Open Questions

- none。

## Implementation Readiness

- Ready: yes
- Blocking Questions: none
- Notes: runtime-first、plan-on-demand、中途 materialization、spec / plan 决策提升边界、goal projection、high-freedom executor 和 deterministic-first verification 已由用户明确确认。

## Progress

- Checkpoint: `runtime-first, plan-on-demand` 已完整落地；简单 / 单会话工作仍直接 runtime，复杂长周期实现可在开始时或执行中按需物化非规范性 thin plan，并从 plan 安全恢复到 source spec。
- Completed:
  - `plan` 已作为第六种 active artifact 恢复，但旧 plan/task/step 拓扑、`to-plan`、`pick-plan`、owner / dependency / lane 和 `plan/done` lifecycle 仍保持退役。
  - thin plan 的 source、status、working-set、decision / blocker 分层、direct resume、promotion 与 closure contract 已进入 schema、validator、routing、`to-implement` 和相关 artifact Skill。
  - validator 已覆盖 ready unfinished source、source lifecycle、full / partial orphan、legacy topology、active Progress 和同一 spec 多 active plan；高频 body snapshot 与恢复 / 提交边界采用分层校验。
  - installer / doctor 的 copy-mode freshness 已扩展到完整 managed subtree，可发现 nested Skill、reference 或 script 的缺失与过期。
  - 代表性 `to-implement` eval 已覆盖 runtime bypass、长周期 / 中途 materialization、direct resume、decision promotion、closure 和 handoff 分流；确定性回归已覆盖 validator 与 installer 行为。
  - active docs、routing、review / commit / handoff 边界与 archive 说明已同步，spec 始终保持规范性真相源。
- Next: none for this scope；后续只有代表性 eval 暴露误触发或恢复缺口时，再调节物化启发式，不恢复固定 plan 阶段。
- Blockers:
  - none
- Last verified:
  - 2026-07-20：validator、installer / doctor、review context、agent-review preflight、eval JSON、install dry-run、diff whitespace 与独立语义复审均通过；无已知残余阻塞。
