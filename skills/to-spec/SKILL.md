---
name: to-spec
description: 'Align, create, and maintain the durable Sky Flow spec that carries design truth, implementation readiness, execution constraints, and a compact Progress recovery snapshot. Use for long-lived design, requirement clarification, spec updates, or design changes discovered during implementation.'
---

# to-spec

`to-spec` 先做人类对齐，再在确认后创建或更新 Sky Flow `spec`。spec 是长期设计真相源，也是文件化执行状态的唯一默认载体；ready 后由 `to-implement` 直接执行，不再生成中间执行 artifact。

简单、一次性、无需长期设计沉淀的工作直接使用 runtime，不应为了流程完整感创建 spec。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言。
2. 判断当前是 `alignment-only` 还是 `artifact-write`：用户仍在 brainstorm、问“怎么看”或设计分叉未收敛时，只做对话对齐；用户确认设计或明确要求写入时再修改 spec。
3. 只读校准相关 docs、代码、schema、issue、现有 spec、近期变更和用户目标。
4. 收敛 problem、outcome、audience、scope、non-goals、requirements、acceptance scenarios、decisions 和 verification intent。
5. 对真实分叉给出 2-3 个互斥方案、取舍和推荐；没有真实分叉时不要机械凑选项。
6. 写入或更新 spec，并判断 `Implementation Readiness`。
7. 如果 spec 已 ready，初始化或刷新 `Progress`，让 `Next` 指向下一轮目标级恢复入口，而不是具体代码动作。
8. 创建或修改 spec 后运行 `validate-flow`，请用户 review；只有用户确认或明确要求继续时才进入 `to-implement`。

## Alignment Contract

首要交付物是共享理解，不是文件。

- 能从仓库确认的事实不要问用户。
- 用户陈述与代码、docs 或既有契约冲突时，指出证据和影响，再确认口径。
- 不把初始解法直接写成最终 requirement；先确认它解决的真实问题。
- 阻塞设计的问题一次只问一个高价值问题；非阻塞问题进入 `Open Questions`。
- 不用完整模板掩盖未知；不确定内容使用 `[NEEDS CLARIFICATION: ...]`。
- 如果一个 spec 覆盖多个可以独立演进的系统或互不共享成功标准的目标，拆成多个 spec；不要引入文件化执行层承载过大 scope。

最小对齐门禁：

1. Context：仓库事实与用户目标没有未解释冲突。
2. Intent：problem、outcome、audience、success 和 non-goals 足够清楚。
3. Design：关键行为、边界、契约 / 数据影响和真实取舍已被展示并接受。
4. Readiness：没有会改变架构方向、业务行为、数据口径、外部契约或验收标准的 blocking question。

未通过时保持 `draft` 和 `Ready: no`；不要让执行层替 spec 猜设计。

## Ground Facts And Intent

对齐时建立四类工作视图：

- `Confirmed Facts`：来自代码、docs、schema、证据或已确认讨论。
- `Unknowns`：仓库无法确认且会影响行为、边界或验证的问题。
- `Conflicts`：用户描述、docs、代码或历史决策互相矛盾的地方。
- `Terms`：容易混用或需要 canonical term 的概念。

然后追到设计根部：

- 为什么现在要做，现状哪里失效。
- 什么可观察结果表示成功，什么表示失败。
- 谁会读、实现、维护或验收。
- 哪些兼容、权限、数据、运维和外部契约必须保护。
- 哪些诱人的扩展明确不做。

复杂设计至少用正常路径、边界路径和反例路径各检查一次。场景关注用户可见行为、业务不变量和系统边界，不写 mock、私有 helper 或调用顺序。

## Writing Rules

- spec 是长期设计与稳定执行状态的真相源，不是代码步骤、命令清单或子代理调度记录。
- requirements 必须可测试、无歧义；做不到就保留明确缺口。
- acceptance scenarios 保护行为、不变量或外部契约。
- `Execution Constraints` 只在确有 no-touch、人类 gate、不可逆操作、独立 review、安全 / 兼容约束时添加；不要为了模板完整感制造约束。
- `Progress` 是覆盖更新的恢复快照，不是 append-only 流水。
- Progress 只保存语义结果和稳定恢复信息；不记录具体代码行号、逐文件 diff、完整命令过程、tool call 或子代理过程。必要时可以引用关键模块、类、函数、接口或测试套件名称。
- runtime owner、依赖、并行批次、子代理消息和微步骤不进入 spec。
- 设计变化更新 Requirements / Decisions；实现结果、证据、blocker 和下一步更新 Progress。

## Spec Template

只保留有价值的 section；可选 section 不适用时直接省略。

```markdown
---
id: <spec-id>
artifact_type: spec
status: draft
---

# <Spec Title>

最后更新：<YYYY-MM-DD>

## Intent

- Problem:
- Outcome:
- Audience:

## Context

- Confirmed Facts:
- Constraints:
- Source Notes:

## Scope

### In Scope

- <覆盖内容>

### Out of Scope

- <明确不做>

## Acceptance Scenarios

1. <场景>
   - Given <初始状态>
   - When <行为>
   - Then <可观察结果>

## Requirements

- R1: <可测试要求>
- R?: [NEEDS CLARIFICATION: <具体缺口>]

## Decisions

- Decision: <选择>
  - Why: <理由>
  - Alternatives: <放弃方向及原因>

## Verification Intent

- Must Protect:
- Suggested Evidence:

## Execution Constraints

仅在确有约束时保留。

- No Touch:
- Required Human Gates:
- Independent Review:
- Irreversible / External Actions:
- Stop Conditions:

## Open Questions

- <非阻塞或阻塞问题及影响>

## Implementation Readiness

- Ready: yes / no
- Blocking Questions: <none 或具体问题>
- Notes: <执行前必须知道但不属于设计 requirement 的稳定说明>

## Progress

- Checkpoint: <当前已经成立的稳定状态>
- Completed:
  - <完成的语义结果及必要证据>
- Next: <下一轮优先推进的目标级恢复入口>
- Blockers:
  - <none，或阻塞原因与恢复条件>
- Last verified:
  - <YYYY-MM-DD；验证入口、结论和残余风险>
```

常见可选 section：

- `Glossary`：关键术语容易混用时。
- `Compatibility / Migration`：涉及旧行为、数据或协议演进时。
- `Security / Privacy`：涉及权限、敏感数据、审计或合规时。
- `Operational Notes`：涉及部署、监控、回滚或 SLO 时。
- `External Contracts`：涉及第三方 API、WS、文件格式或平台协议时。
- `Risks`：有明确高影响风险且不能自然放入 constraints 时。

## Progress Rules

`Progress` 只回答恢复执行所需的五个问题：

- `Checkpoint`：当前已经稳定成立什么。
- `Completed`：哪些能力、行为或稳定结果已经成立，证据在哪里。
- `Next`：下一轮优先推进的目标级恢复入口是什么；不是代码微任务。
- `Blockers`：为什么不能继续，什么条件解除。
- `Last verified`：最近一次验证何时完成、结论和残余风险是什么。

规则：

- `draft` spec 可以只写设计对齐状态；ready 时必须让 `Next` 可执行。
- `not_started` 表示设计已确认但尚未开始。
- `in_progress` 表示正在执行；短期阻塞仍保持该状态并写入 Blockers。
- `completed` 只在整个 scope、验证和必要人类 gate 都结束后使用。
- 完成时压缩旧 checkpoint 和过程记录，只保留 final outcome、关键 evidence、residual risk 和 follow-up。
- 不记录执行时间线、具体代码行号、逐文件变更、完整命令过程、tool call、子代理身份 / 消息或调度过程。
- 必要定位优先使用稳定模块、类、函数、公开接口或测试套件名称；新写回必须合并或替换过期内容，不持续追加。
- 工作长期延期或退出当前执行队列时，转 `to-backlog`；易失本地接力状态才转 `to-handoff`。

## Implementation Readiness

`Ready: yes` 只表示执行层不需要重新决定“到底要什么”。至少满足：

- Intent、Scope、Requirements 和 Acceptance Scenarios 互相一致。
- 关键设计选择已确认。
- 没有 blocking `[NEEDS CLARIFICATION: ...]`。
- Verification Intent 足以判断完成。
- 必要 Execution Constraints 已表达。
- Progress `Next` 是清楚的目标级恢复入口。

不满足时写 `Ready: no`，继续对齐；不要创建中间文件来代替澄清。

## 推荐关系

- ready spec 需要执行或继续：`to-implement`。
- 需要从一个或多个 spec 选择、恢复或生成 portable runtime goal：`pick-goal`。
- 尚未进入设计、只需记录问题和证据：`to-issue`。
- bug、异常或 root cause：`to-debug`。
- 测试策略、BDD 场景或验证 ROI：`to-test`。
- 真正人类 gate：`to-acceptance`。
- 工作长期退出当前执行队列：`to-backlog`。
- 易失状态跨会话接力：`to-handoff`。

## Self-Review

- Placeholder：是否还有无意义空 section、TBD 或伪完整内容。
- Consistency：Intent、Scope、Requirements、Decisions、Readiness 是否一致。
- Scope：是否大到应拆成多个 spec。
- Language：关键术语是否清楚。
- Requirements：每条是否可测试、无歧义。
- Scenarios：是否保护行为而非实现细节。
- Constraints：是否只保留真实约束，没有预设 runtime 调度。
- Progress：是否是紧凑语义快照，Next 是否保持目标级，证据是否可追溯且没有代码行 / 命令 / Agent 流水。
- Leakage：是否写入代码步骤、命令或子代理拓扑。

## User Review Gate

创建或更新 spec 后，请用户 review 设计与执行口径。确认后才进入 `to-implement`；用户要求修改时更新 spec、重新 self-review，并运行 `validate-flow`。
