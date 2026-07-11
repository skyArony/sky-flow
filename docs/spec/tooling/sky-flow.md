---
id: sky-flow
artifact_type: spec
status: completed
---

# Sky Flow 工作流套件

最后更新：2026-07-11

## Intent

- Problem: 文件化执行层、静态依赖图和 runtime 自主调度重复表达同一件事；随着模型能够动态派发子代理、调整顺序和 fan-in，过重约束开始降低执行效率。
- Outcome: Sky Flow 只持久化长期设计与真实协作边界，默认从 ready spec 直接执行；执行拆解与分工由 runtime 动态完成。
- Audience: 使用、维护或扩展 Sky Flow 的 Agent、开发者与需要跨会话恢复状态的人类协作者。

## Context

### Confirmed Facts

- Agent runtime 已能根据当前事实动态拆解工作、选择主代理或子代理、维护临时 checklist、调整并行并完成 fan-in。
- 预先写死的文件化执行图容易在第一轮探索后失效，还要求额外维护字段、双向关系、状态和校验器。
- 长期设计、行为约束、关键决策、当前 checkpoint、blocker 和验证证据仍需要可恢复、可检索的文件化真相源。
- 人类 approval、真实设备 / 账号 / 环境、长期外部依赖和易失接力状态仍然是独立协作边界。

### Constraints

- Sky Flow 核心保持项目无关；项目命令、业务规则、部署限制和领域术语由本地文档或 adapter 承担。
- 简单工作不得为了使用流程而创建 artifact。
- 文件化状态必须紧凑，不能退化成执行流水或隐藏拓扑。
- 同一文件或共享状态避免并发多写；完成交接后可以动态更换 writer，多 Agent 输出由主会话 fan-in。

## Scope

### In Scope

- spec-direct 设计、执行、进度和恢复模型。
- 从 durable spec 只读派生 portable runtime goal 的选择边界。
- `spec`、`issue`、`acceptance`、`backlog`、`handoff` 五种 file-backed artifact。
- ready spec 的 runtime 动态执行与 Progress 写回。
- 测试、review、consolidation、验收、阻塞、交接、提交和校验边界。
- 历史文件化执行拓扑能力的归档与退出安装范围。

### Out of Scope

- 项目专属实施命令、基础设施凭据、业务状态机和团队组织规则。
- 记录子代理完整对话、微步骤、owner 分配或 runtime 并行图。
- 为 legacy 执行拓扑提供兼容创建、继续或校验入口。

## Core Model

```text
spec（长期设计 + readiness + Progress）
  ↓
可选 pick-goal（只读 goal projection）
  ↓
native runtime execution + dynamic subagents
  ↓
test / review / consolidation（按实际风险触发）
  ↓
spec Progress 写回
```

旁路 artifact 只在真实边界出现：

- 人类必须判断：`acceptance`。
- 工作长期离开当前执行队列：`backlog`。
- 未提交 diff、终端、临时环境或易失证据需要接力：`handoff`。
- 值得长期保留的问题、线索或待决策证据：`issue`。

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

### Naming And Source

- artifact 文件 stem 必须等于 frontmatter `id`。
- spec 不使用数字编号前缀。
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
- blockers 必须包含解除条件；工作长期离队时转 backlog。
- last verified 记录关键证据、结论、未验证范围和独立评估不可用降级。
- 必要定位可以使用少量稳定模块、类、函数、公开接口或测试套件名称，不使用具体代码行号。
- 不记录完整命令过程、tool call、子代理身份 / 消息、调度过程或执行时间线。
- 新写回必须合并或替换过期信息；spec 完成时压缩为 final outcome、evidence、residual risk 和 follow-up。

## Goal Projection

`pick-goal` 在用户明确要求选择、恢复或生成目标时，从 unfinished spec 只读派生 portable runtime goal：

- spec 是 durable goal source。
- Progress 是 resume cursor，`Next` 只是恢复入口。
- runtime goal 是当前会话的执行投影，不是新 artifact。
- objective 来自 spec outcome；done condition、constraints 和 evidence 来自相关 durable semantics。
- direct target 优先；未指定时做语义选择，不使用固定评分、mtime 或机械状态排序。
- 选择和投影不修改 spec。用户明确要求启动时按 readiness 交接：implementation-ready goal 进入 `to-implement`，alignment goal 进入 `to-spec`，仍有 blocker 的 goal 保持未启动。
- 原生 goal 只承载已经选定的目标；创建后 `pick-goal` 结束职责，由接收方拥有执行和稳定状态写回。

一个 coherent spec 可以随 Progress 推进连续派生多个 runtime goal，但每次只输出一个当前投影，不持久化 sibling goal graph。只有多个 outcome 彼此无关、可独立演进且不共享成功标准时才由 `to-spec` 考虑拆分；不能由 `pick-goal` 挖成隐藏 task 图。

## Native Runtime Execution

`to-implement` 直接读取 ready spec 或由它派生的 implementation-ready runtime goal。alignment goal 回 `to-spec`，仍有 blocker 的 goal 不启动。执行器只规定不可越过的目标、权限、真实 gate、并发写安全、完成证据和 Progress 边界；实现策略保持高自由度。

- 读取足以理解目标、成功标准、当前真相、constraints 和恢复入口的语义；不要求固定 section schema。
- runtime 自主选择探索、实现、工具、checklist、子代理、顺序、并行和验证组合。
- Mission 必须清楚；其他 delegation packet 字段只在相关时提供，不形成缩小版 task 模板。
- 测试、review、consolidation、acceptance 和 validation 按证据缺口与风险选用，不形成固定流水线。
- 多个修复方向或 fan-in 冲突优先继续取证和裁决；只有触及用户拥有的重大决策、权限或不可逆边界且无法安全推导时才问人。
- 只在语义 checkpoint、outcome、blocker、evidence、risk 或 resume target 稳定变化时写回 spec。

### Subagent ROI

只有明确收益高于 fan-in 成本时派发：

- 并行时间收益。
- 上下文隔离收益。
- 专业化收益。
- 独立 review / verification 收益。

共享 contract、数据库 schema、部署配置、公共入口和同一 artifact 避免并发多写；完成交接后可以动态更换 writer。

### Runtime Gates

gate 保留为不变量，不再物化成执行节点：

- spec、用户或实际风险要求独立 review 时，implementation owner 不得自行清除。
- fresh reviewer / verifier 动态派发，结论写入 Last verified。
- 独立评估不可用时记录 `independent_review: unavailable` 和残余风险。
- 人类 approval、真实设备 / 账号 / 环境、体验或风险接受进入 acceptance。
- Agent 可自行完成的 test、lint、build、静态 review 直接执行并记录证据。

## Artifact Boundaries

### Issue

issue 保存问题、证据、影响和一个有价值的下一决策。它不是实施脚本。

如果问题需要长期设计，转入或关联 spec；如果设计已经明确且工作很小，可直接 runtime 执行并在 issue 完成时写 resolution / evidence。

### Acceptance

acceptance 只承载 Agent 无法自行判断或必须由人类拍板的事项。来源优先是 spec 或 conversation，也可以来自 issue、backlog 或 handoff。

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
| `to-implement` | spec-direct runtime execution 与稳定写回 |
| `to-issue` | 本地问题与证据记录 |
| `to-debug` / `to-bdd-regression` | 诊断与真实事故回归 |
| `to-test` | 测试策略与验证 ROI |
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
- acceptance / backlog / handoff 单向 source。
- abandoned 与 backlog / 人类依据。
- ready / active / completed spec 的 Progress 存在性。
- retired artifact 或旧拓扑字段残留。

语义收口只看设计一致性、Progress 快照、真实 constraints、acceptance 价值、backlog 恢复和 handoff 易失性。Progress 必须保持语义级，排除代码行号、逐文件 diff、完整命令 / tool / Agent 过程和时间线。它不验证 runtime owner、依赖边、并行 lane 或微步骤。

## Migration And Archive

旧文件化执行拓扑是 breaking removal，不提供 active 兼容创建或继续入口。

迁移规则：

- 长期目标、scope、requirements、decisions → spec 对应 section。
- 当前 checkpoint、已完成结果、next、blocker、evidence → spec Progress。
- 人类 gate → acceptance。
- 长期延期 / 外部依赖 → backlog。
- 未提交 diff / 临时环境 / 终端状态 → handoff。

历史 Skill 保存在仓库根 `archive/skills/`，文件名使用 `SKILL.archived.md`，不位于 active `skills/` 发现范围。active routing 和安装清单不得引用它们。root copy-mode 安装必须排除 `archive` 与 `.git`；symlink 模式虽然能看到 checkout 文件树，但 archive 中没有可发现的 `SKILL.md`。

升级时，installer 只自动清理明确指向当前 checkout 的 retired symlink 或冗余 Codex child symlink。copied / foreign install 不得隐式删除，但必须让 update / doctor readiness 失败并给出显式替换路径。Claude 因不发现 nested Skill，直接安装 suite entry 和 callable children；Codex 只安装 suite entry，并通过它发现 children。doctor 对 Codex symlink 验证 suite root，对 copy-mode 逐个比较 nested `SKILL.md`，并把残留 direct child 判为待迁移状态，不得用它掩盖 stale content。

## Acceptance Scenarios

1. 简单工作不进入文件化流程。
   - Given 工作不需要长期设计、跨会话恢复或真实人类 gate
   - When 用户要求执行
   - Then Agent 直接使用 runtime，不创建 workflow artifact

2. ready spec 可以直接执行。
   - Given spec 没有 blocking question，且 Next 提供目标级恢复入口
   - When 用户要求实现或继续
   - Then `to-implement` 动态调度 runtime，并只写回稳定 Progress

3. 第一轮探索推翻初始拆解。
   - Given runtime 已形成临时工作顺序
   - When 新证据改变依赖或并行方式但不改变 spec scope
   - Then 主代理直接调整 runtime checklist，不修改文件化拓扑

4. 执行出现设计变化。
   - Given 新事实会改变 requirement、contract、data semantics 或 acceptance behavior
   - When Agent 无法在既有 spec 内安全继续
   - Then 停止执行并回 `to-spec` 对齐

5. 人类 gate 不被伪装成 Agent 自证。
   - Given 完成依赖真实设备、账号、环境、体验或风险接受
   - When Agent 到达该边界
   - Then 创建或更新 acceptance，不宣称自行通过

6. Progress 不膨胀成流水账。
   - Given 多轮执行和多个子代理完成工作
   - When 写回 spec
   - Then 只保留语义 checkpoint、outcome、目标级 next、blocker、证据和 residual risk，不记录代码行、逐文件 diff、命令 / tool / Agent 过程或时间线

7. 旧执行 artifact 被拒绝。
   - Given checked docs 仍声明 retired artifact type 或拓扑字段
   - When `validate-flow` 运行
   - Then 返回明确 migration error，不提供兼容执行路径

8. 多个 spec 可以派生一个 runtime goal。
   - Given 用户要求挑选下一目标且存在多个 unfinished spec
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

## Requirements

- R1: Sky Flow active artifact 枚举必须只包含 spec、issue、acceptance、backlog、handoff。
- R2: ready spec 必须可以直接进入 `to-implement`，无需中间文件化执行层。
- R3: runtime decomposition、owner、dependency、parallelism 和 fan-in batching 不得持久化为 workflow artifact。
- R4: spec Progress 必须是覆盖更新的恢复快照，不是 append-only 执行日志。
- R5: 人类 gate、长期阻塞和易失交接必须分别归入 acceptance、backlog、handoff。
- R6: active installer 和 routing 不得发现或推荐 archived skills。
- R7: validator 必须拒绝 retired artifact type 和旧拓扑字段，并提供迁移方向。
- R8: 独立 review、人类 approval、no-touch 和不可逆操作约束不得因删除执行图而消失。
- R9: 简单工作必须保留直接 runtime 快速路径。
- R10: 所有 active skill 必须以 spec Progress 或 runtime state 表达执行上下文，不引用旧文件化拓扑。
- R11: installer / doctor 必须显式检测 retired install residue 与 active stale copy；不能把旧拓扑指令误报为 ready。
- R12: internal-only reviewer profile 不得作为顶层 callable skill 安装。
- R13: `pick-goal` 必须只读地从 unfinished spec 派生 portable runtime goal，不创建 goal artifact、不自动执行、不恢复 task topology。
- R14: Progress 只能保存语义结果和稳定恢复信息；不得保存具体代码行、逐文件 diff、完整命令 / tool / Agent 过程或执行时间线。
- R15: `to-implement` 只硬性保护用户 intent、真实 constraints、authority、并发写安全和 completion evidence；其他执行策略必须保持为 runtime 自主选择或启发式建议。
- R16: `pick-goal` 显式启动必须按 readiness 唯一交接；它不拥有 implementation 或 alignment 执行。
- R17: installer / doctor 必须使用 target-specific discovery：Claude 要求直接 child install，Codex 通过 suite root 接受 nested child，并保持 copy-mode stale 检测。

## Decisions

- Decision: 删除文件化执行拓扑，不保留兼容创建或继续路径。
  - Why: runtime 已能动态调度；兼容层会保留原有复杂度并继续诱导重复状态。
  - Alternatives: 只把旧模型降级为可选模式；放弃，因为 active surface 仍会膨胀。
- Decision: 保留并重写 `to-implement` 为薄 spec executor。
  - Why: 它提供清晰的 spec → runtime → Progress bridge，避免把执行规则重新塞进根入口。
  - Alternatives: 完全删除执行入口；放弃，因为 ready spec 的触发与写回边界会分散到多个 Skill。
- Decision: Progress 放在 spec，采用快照而非事件流。
  - Why: 只保留恢复执行所需的最小状态，避免新建替代 artifact。
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
  - Why: ready、alignment 和 blocked 的处理边界需要明确，但持久化中间层会重新制造被删除的执行拓扑。
- Decision: installer 使用 target-specific discovery model。
  - Why: Claude 需要直接 child links；Codex 已能从 suite root 发现 nested Skills，重复链接会扩大安装面并让 doctor 与真实 runtime 状态不一致。

## Verification Intent

- Must Protect:
  - active install list 不包含 archived skills。
  - internal reviewer profile 不进入 active install list。
  - stale active copies 与无法安全删除的 retired installs 被 readiness 拒绝。
  - validator 拒绝 retired artifact 与拓扑字段。
  - current spec 自身通过 deterministic validation。
  - active docs / Skill 没有旧路由或旧 artifact lifecycle 残留。
  - `to-implement` 清楚表达动态 runtime 与 Progress 写回。
  - `pick-goal` 只读、不会创建 artifact 或把 Next 当 goal。
  - goal 显式启动按 readiness 交给 `to-implement` 或 `to-spec`；blocked goal 不启动。
  - Claude direct-child 与 Codex suite-root 的 install / doctor 判定一致，Codex copy-mode 仍能发现 stale nested Skill。
  - Progress 不包含代码行号、逐文件 / 命令 / tool / Agent 流水。
- Suggested Evidence:
  - `node --check scripts/validate_flow.ts`
  - `node scripts/validate_flow.ts docs/spec/tooling/sky-flow.md`
  - `./install.sh list --json`
  - `./install.sh --dry-run --no-deps`
  - retired artifact / topology negative fixtures
  - active tree residual keyword scan
  - pending diff review and consolidation

## Execution Constraints

- No Touch:
  - `to-claude-review` 的 permission strategy `plan` 属于 ACP 权限模式，不是 Sky Flow artifact，不能误删。
  - Agent review 测试中的 `ExitPlanMode` / `Task` 是外部 transcript 工具名，不能误删。
- Required Human Gates:
  - none；用户已明确批准 breaking removal。
- Independent Review:
  - 完成前对 pending diff 做独立 read-only review。
- Irreversible / External Actions:
  - 清理安装目录中的旧 symlink 只允许删除明确指向本仓库 retired skill path 的链接。
- Stop Conditions:
  - 发现必须保留 legacy active compatibility，或清理目标不是 repo-owned symlink 时停止询问。

## Open Questions

- none。

## Implementation Readiness

- Ready: yes
- Blocking Questions: none
- Notes: spec-direct、goal projection、semantic Progress 和 high-freedom executor 已由用户明确确认。

## Progress

- Checkpoint: spec-direct 模型已稳定；goal projection 有唯一 readiness 交接，Claude/Codex 安装判定匹配各自 discovery，Progress 只保存语义恢复状态。
- Completed:
  - plan/task/step 拓扑与旧选择 / 归档能力已退出 active surface，历史只保留不可调用 archive。
  - `pick-goal` 已成为只读 spec→runtime goal 投影；active `to-implement` 只保留目标、安全、authority、evidence 和 Progress 硬边界。
  - Progress contract 已明确排除代码行、逐文件 diff、命令 / tool / Agent 过程和时间线，同时允许少量稳定 symbol 定位。
  - issue、acceptance、backlog、handoff、validator 和 installer 边界已与 spec-direct 模型一致；旧 reviewer 顶层安装残留已清理。
  - ready、alignment、blocked goal 已分别闭合到 `to-implement`、`to-spec` 和未启动状态，不新增中间 artifact。
  - installer 已按 Claude direct-child、Codex suite-root 分流，并保留 nested copy stale 检测。
- Next: none。
- Blockers:
  - none
- Last verified:
  - 2026-07-11：artifact 与 Skill structure 校验无误，installer 和 agent-review regressions 全绿；全量 doctor 的 20 个 active Skill 均 ready，Codex 顶层只保留 suite root，retired / internal reviewer 顶层入口为 0。
