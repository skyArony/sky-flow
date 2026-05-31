---
name: to-implement
description: "Execute and maintain a prepared Sky Flow plan/task artifact or task DAG only when explicitly requested or when continuing Sky Flow plan/task execution; coordinate main-agent and subagent work, context policy, verification, review, consolidation, fan-in, runtime plan updates, dynamic task adjustments, and artifact status writeback."
---

# to-implement

`to-implement` 执行 Sky Flow `plan` / `task` DAG。它是执行协调器：读取已准备好的 Sky Flow plan / task artifact，选择下一批可执行 task，决定主代理和子代理分工，管理上下文、验证、review、consolidation、fan-in、runtime plan、artifact 状态回写和必要的执行期计划调整。

它不是日常任务默认入口。只有用户显式指定 `to-implement`，或要求执行 / 继续 / 推进某个已制定的 Sky Flow plan / task artifact，或当前会话已经进入文件化 Sky Flow plan / task 的执行阶段时才触发。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取 plan、task DAG、关联 spec / issue；如果缺 task 且 plan 不是 no-task execution，回到 `to-task`。
3. 如果 runtime 是 Codex，按任务复杂度维护运行时任务清单；多 task、跨阶段、存在依赖 / fan-in / blocker 时使用内置 `update_plan`，单个直接 task 可用简短内部 checklist。
4. 检查 artifact 状态、scope、依赖和 blocker；不满足时停止，不猜。
5. 选择下一批 executable tasks：依赖满足、状态可推进、写集不冲突、fan-in 成本可控。
6. 决定 execution mode：按 ROI 选择主代理直接执行还是派 worker。多 task、fan-in、上下文隔离或独立 review 收益明确时主代理偏 coordinator；单 owner、小 task、当前上下文最完整时主代理可以直接实现。
7. 并行调度代码与文档：实现型 worker 推进代码 / 配置，文档 owner 同步更新 spec / plan / task / acceptance / handoff 等 artifact；主会话可以自己做文档 owner，也可以派 documentation worker。
8. 派发或执行 task，收集输出。
9. Fan-in：检查 changed files、task 要求、spec alignment、验证结果、artifact 更新和 blocker。
10. 必要时触发 `to-test`、`to-review`、`to-consolidation`、`to-acceptance`、`validate-flow`。
11. 维护 runtime plan；Codex 中对关键状态变化同步 task status、并行批次、fan-in、blocker 和 next action，避免为单 task 内微步骤过度打点。
12. 按执行事实更新 task status、plan progress / recovery / decision / blocker。
13. 如果实现事实要求拆分 task、调整依赖 / 并行关系或补充验证 / 收敛 task，在已确认 scope 内按 `to-task` 规则更新 artifact 并运行 `validate-flow`。
14. 到达人类验收、sign-off、争议确认或下一轮反馈节点时，调用 `to-acceptance` 创建或更新验收文档。
15. plan 到达完成态后，调用 `to-archive` 压缩 task / fan-in 执行记录，只把长期事实、关键决策和证据入口留在 completed plan。
16. 遇到关键歧义、验证反复失败、scope / contract / 数据口径变化或高风险操作时，停止并询问人类。

## Execution Model

主代理职责：

- plan owner。
- coordinator。
- fan-in reviewer。
- artifact maintainer。
- runtime plan maintainer。
- Codex `update_plan` maintainer。

常见执行形态是：主代理承接会话、维护 runtime plan 和文件化 plan 进度；task 可以由子代理承接，也可以由当前主会话或新会话主代理承接。选择 owner 时看 ROI：如果主代理掌握完整上下文、写集单一且 fan-in 成本高，可以直接实现；如果并行、隔离、专业化或独立审查收益更高，再派 worker 或“主代理替身”。

子代理策略：

- 实现型 worker / 主代理替身：优先 full-context fork。
- explorer / reviewer / docs researcher / verifier：优先最小上下文包。
- 一个子代理通常对应一个 task，或一组明确同 owner、同写集边界的并行 task。
- 子代理派发必须有正向 ROI：并行时间、上下文隔离、专业化、质量 / review 或其他明确收益需要超过 fan-in 成本。收益不明确时，主会话直接承接更好。
- 子代理不直接抢写 plan 状态；主会话显式指定 documentation worker 为某个 artifact 的 single writer 时，可以更新正文、证据或草稿状态，最终进度、决策、阻塞和恢复入口仍由主会话 fan-in 后确认。
- 文档更新可以和代码实现并行：主会话可作为文档 owner 在代码 worker 运行时同步更新 artifact，也可派 documentation worker；同一 spec / plan / task / acceptance 文件必须有 single writer，最终状态由主会话 fan-in 确认。
- 子代理状态至少能表达 `DONE`、`DONE_WITH_CONCERNS`、`NEEDS_CONTEXT`、`BLOCKED`。
- 如果 runtime 支持二级子代理，承接 task 的子代理可以在 task write scope 和 delegation policy 内继续派发二级子代理；task owner 负责二级 fan-in，再向主代理汇报最终结果。
- 如果某个 task 由主会话承接，主会话也可以继续为该 task 派发子代理；这不改变主会话对 plan 进度和 artifact 状态的最终维护责任。

## Subagent ROI

`to-implement` 是最终执行调度点，必须在选择 task owner 和并行批次时主动判断子代理 ROI。

下面任一收益明确成立，且收益超过 fan-in 成本时，可以派发子代理：

- 并行时间收益：可与当前主路径并行推进。
- 上下文隔离收益：把局部代码区、调查面或验证面隔离出去更清晰。
- 专业化收益：worker / explorer / reviewer / verifier 等角色更适合该 task。
- 质量 / review 收益：独立视角能降低 spec 偏差、实现风险或验证遗漏。
- 其他明确正向收益：能解释为什么派发比主会话直接做更好。

如果收益不成立、fan-in 成本超过收益、共享写集无法 single writer，或需要主会话直接决策高风险取舍，可以由主会话承接 task，但必须记录原因。

## Dispatch Packet

每个子代理必须拿到最小充分任务包：

- Mission。
- Source artifact：plan / task / spec 路径。
- Task text。
- Allowed write scope。
- No-touch scope。
- Context policy：full fork / minimal context。
- Delegation policy：no nested agents / nested agents allowed。
- Verification intent。
- Output contract。
- Stop condition。
- Reminder：not alone in the codebase；不要 revert 他人改动；根据已有改动调整实现。

不要把全量 plan 历史、写作者辩护或无关上下文塞给只读 reviewer / verifier。实现型 full fork 例外。

## Selecting Executable Tasks

可执行 task 必须满足：

- `status` 是 `not_started` 或明确可继续的 `in_progress`。
- `depends_on` 和 `external_depends_on` 已满足。
- 所属 parent / child plan 顺序允许执行。
- 没有 blocking `[NEEDS CLARIFICATION: ...]`。
- write scope 与同批 task 不冲突，或已有 single writer / gate。
- verification intent 清楚。
- 能由 Agent 独立执行并判断完成；如果核心完成条件依赖人类操作、真实设备 / 账号、未授权外部环境、审批或人工体验判断，不执行、不标记 completed，转 `to-acceptance` 并按 `to-task` 规则从 task DAG 中纠偏。

parent plan 不直接执行；必须切换到当前可执行 child plan。没有 task 且不是 no-task execution 时，回到 `to-task`。

## Parallelism

依赖满足、写集不冲突、上下文可隔离、fan-in 成本可控时，优先评估并行 implementation task；只有并行收益明确高于 fan-in 成本时才派发，不要为了形式并行，也不要无故串行化。

- 代码改动与文档 / artifact 更新可以并行；当稳定事实已经足够、写集不冲突且 fan-in 成本可控时，documentation worker 或主会话可以同步维护 spec、plan、task、acceptance、handoff、README 或其他交付文档。若文档依赖最终实现事实，先记录待 fan-in 项，避免过早写死。
- 并行文档更新必须遵守 single writer：同一个文件、同一个 frontmatter 状态字段、同一个 plan/task status 只能由一个 owner 写；其他代理只提交事实、证据或 patch 建议。
- 父子代理可以并行：子代理执行代码 task 时，父代理可以并行更新 runtime plan、plan progress、decision log、validation evidence 和 acceptance 草稿；如果文档更新需要代码最终事实，先写稳定事实和待 fan-in 项，最终结论在 fan-in 后落地。
- explorer / reviewer / verifier 的并行门槛可以低于 worker，但必须有明确 output contract。
- coordination task 不派给普通子代理；默认由主代理承担。
- 共享核心文件、公共 contract、数据库 schema、部署配置默认单 writer。
- task owner 的二级并行必须保持在自己的 task scope 内，不能绕过主代理维护 plan / task status。
- 强耦合、多 writer、跨多轮 review / 返工的任务不要在 `to-implement` 中硬并行；应拆小 task、串行化共享写集，或暂停并回到 `to-task` / `to-plan` 重新表达执行边界。

## Fan-in And Verification

主代理 fan-in 时至少检查：

- task 要求是否完成。
- changed files 是否在 allowed write scope 内。
- no-touch 是否被遵守。
- spec / plan alignment 是否保持。
- 验证证据是否充分。
- 是否引入新 blocker、scope creep 或未确认口径。

顺序建议：

1. Spec compliance review。
2. 需要测试策略、测试 ROI、BDD/TDD 或替代验证时，触发 `to-test`。
3. Code / artifact quality review。
4. 如果当前阶段是在关闭已选 review findings，触发 `to-review` verifier stage，并要求至少两个不同模型 verifier；只有一个供应商时使用最新模型和次新模型。
5. 必要验证。
6. 必要 `to-consolidation`。
7. 必要 `to-acceptance` 生成或更新验收文档。
8. `validate-flow` 检查 artifact/status。

不接受 “close enough” 的 spec 偏差。

## Testing Gates

执行期出现下面任一情况时，主代理应调用 `to-test` 或要求 task owner 使用 `to-test` 输出测试策略：

- task 明确要求新增或修改测试。
- 实现改变用户可见行为、系统边界、外部契约、关键状态或数据不变量。
- 需要判断测试 ROI、stable seam、Red / Green / Refactor、characterization 或替代验证。
- `to-task` 的 verification intent 不足以指导执行，需要补充行为场景或验证证据。
- fan-in 后存在“是否要补测试”或“是否可以跳过测试”的争议。

真实事故、客户反馈、日志 / 数据异常、时序问题或状态机问题需要回归固化时，转 `to-bdd-regression`；`to-test`
只处理普通测试策略和验证取舍。具体测试命令、包名和环境限制由项目本地规则决定。

## 推荐关系

`to-implement` 是执行协调器。执行中进入非本 skill 领域时，只推荐对应专门 skill，不在执行层代偿：

- 运行环境、日志、数据库、缓存、Metrics、Dashboard、告警、部署状态或外部系统证据：推荐项目级 `to-infra`；调用前写清 hypothesis、prediction、环境、时间范围和关键实体。
- 测试策略、测试 ROI、BDD/TDD、stable seam 或替代验证：推荐 `to-test`。
- 真实事故回归固化：推荐 `to-bdd-regression`。
- 普通 code / artifact review：推荐 `to-review`。
- review 输出存在 blocking finding：只输出阻塞问题、证据、影响和后续需要的人类决策或显式流程；不推荐、不自动转入 `to-review-loop`。`to-review-loop` 只能由用户显式触发。
- review synthesize 后需要人类决定修哪些 finding、延后哪些 finding 或接受哪些风险：直接在对话或 review 报告中输出 triage 清单，不创建 `acceptance` artifact。
- 阶段产物完成、fan-in 后或 task 已显式安排收敛：推荐 `to-consolidation`。
- 人类验收、sign-off、争议确认或反馈节点：推荐 `to-acceptance` / `to-next-acceptance`。
- plan 完成后需要压缩 task / fan-in 执行记录：推荐 `to-archive`。
- 创建或修改 workflow artifact：推荐 `validate-flow`。

## Acceptance Gates

`to-implement` 在执行层必须主动识别验收和确认节点。出现下面任一情况时，调用 `to-acceptance`：

- plan / task 写明需要人类验收、sign-off 或阶段 gate。
- 产物已经完成，需要把验证证据、观察结果、残余风险和确认项交给人类判断。
- fan-in 后存在非 blocking 但需要人类选择的取舍、争议或残余风险。
- 人类补充验收要求、反馈上一轮验收结果，或要求进入下一轮验收。

`to-implement` 不在聊天里替代验收文档。验收项应映射到实际产物、行为场景、验证证据或 artifact 契约；
不把 mock、私有实现路径、调用顺序或内部临时代码当作验收对象。已有 acceptance 需要推进下一轮时，由
`to-acceptance` 的子能力 `to-next-acceptance` 处理。

## Status Writeback

执行中，主代理负责更新：

- task `status`、依赖解除和 blocker。
- plan `Progress Log`、`Recovery`、`Decision Log`、`Validation Evidence`。
- runtime plan；Codex 中用 `update_plan` tool 维护。
- 必要时 backlog / handoff / acceptance；验收文档由 `to-acceptance` 创建或更新。

写回规则：

- task 完成且验证通过：标记 completed。
- task 产出有问题但可修：保持 in_progress，记录 blocker / next action。
- task 阻塞：记录 blocked 信息；当前 schema 无 blocked status 时保持 in_progress 或 draft，并在正文写清 blocker。
- task 本身无法由 Agent 完成：不要标记 completed；把人工 / 真实环境验收项转入 acceptance，并更新 plan/task 以移除或改写该不可执行 task。
- plan 完成时，所有直属 task 必须 completed，并设置 `completed_at`。
- plan 设置为 `status: completed` 后，必须从 `${SKY_FLOW_ROOT}/plan/` 移入 `${SKY_FLOW_ROOT}/plan/done/`，并同步本地 docs TOC / artifact 引用；完成 plan 仍保留原 `id` 和文件名。
- completed plan 应进入 `to-archive`：默认把 task 事实、关键决策和验证证据压缩进 plan 正文，清空 `plan.tasks` 并删除该 plan 的 task 目录；如果存在审计、恢复或人类要求，保留 task 文件并在归档摘要写清原因。

## Dynamic Plan Maintenance

`to-implement` 参考 `to-plan` 的计划层约束，负责在执行期维护两层状态：

- runtime plan：当前会话的执行投影，可以更细、更临时，用来追踪正在执行的 task、并行批次、fan-in 和验证 checkpoint；Codex runtime 必须使用内置 `update_plan` tool 维护。
- file artifacts：长期真相源，只记录稳定进度、task status、依赖变化、关键决策、blocker、验证证据和恢复入口。

下游动态调整不能和上游定义冲突。执行中发现计划和现实不匹配时，先分类再更新：

- status-only：只更新 runtime plan、task status、`Progress Log`、`Recovery` 或 blocker。
- task topology：在原 goal / scope 内拆分过大的 task、补充遗漏 task、调整 `depends_on` / `parallel_with`、增加 review / verification / consolidation task；按 `to-task` 规则更新 artifact。
- plan maintenance：补充 milestone 进度、task handoff、validation evidence、decision log 或恢复入口；保持 `goal` 和 scope 不变。
- strategy update：执行策略、milestone 边界、plan shape、scope 分解或 task handoff 需要变化时，暂停执行并调用 `to-plan` 更新 plan。
- design update：目标、scope、外部契约、数据口径、业务行为或 requirements 需要变化时，暂停执行并调用 `to-spec` 更新 spec。

动态调整规则：

- 主代理可以根据执行事实维护 plan / task 状态和 task DAG；子代理只能提出调整建议，不直接改 plan。
- runtime plan 更新要及时但不过度；在 Codex 中，选择下一批 task、开始 / 完成一组可见 task、fan-in、发现 blocker 或调整 task DAG 后，应调用 `update_plan`。单个 task 内部的微步骤、短暂探测或不会改变对外状态的局部切换，不必每次调用。file artifact 只写稳定事实，不记录每个微步骤。
- 拆分或新增 task 后，按 `to-task` 规则同步更新 plan `tasks`、task dependency fields 和 runtime plan。
- 下游只做已确认 scope 内的执行期维护；任何策略或设计重决策都必须回到对应上游 skill 更新 artifact，再继续执行。
- artifact 结构变更后必须运行 `validate-flow`；如果只更新 runtime plan，不需要 artifact 校验。

## Stop Conditions

遇到下面情况停止并询问人类：

- scope 扩大或目标变化。
- 关键协议、数据口径、业务行为或外部契约不清。
- 验证失败且修复路径不唯一。
- 公共契约、数据库、部署、权限或高风险模块变更超出已确认 plan。
- 子代理之间出现写冲突或 fan-in 无法安全决策。
- 需要 destructive command、发布、删除、重命名或未授权操作。

## Boundaries

- 不在执行层重做设计；关键设计缺口回 `to-spec`。
- 不把未确认的 plan / task 重写成新方案；执行中可在已确认 scope 内维护 task DAG，结构性 task 缺口按 `to-task` 规则处理。
- 不替代 `to-review`、`to-consolidation`、`to-acceptance` 或 `validate-flow`。
- 不替代 `to-test`；测试 ROI、seam、Red / Green / Refactor 和替代验证判断交给 `to-test`。
- 不让子代理直接维护 plan。
- 不为了使用 Sky Flow 而执行日常可直接完成的任务；只有 Sky Flow plan / task artifact 执行才自动触发。
