# Sky Flow Routing

本文件是 active 子能力和触发规则的完整来源。根 `SKILL.md` 只保留入口短路径和快速路由。

## Trigger Order

1. 普通工作默认直接使用 native runtime；测试、静态检查、build、diff sanity 和修复后定点验证不需要专门 Skill。
2. 意图触发的核心能力只包括 ready spec execution、debug / infra、commit 和 artifact validation；用户提出相应动作时进入，不额外升级流程。
3. 显式能力必须由用户点名 `$skill`：spec 设计、goal 选择、issue / backlog / handoff 写入、review、review loop、consolidation、knowledge、agent review、Claude 第二意见，以及 file-backed acceptance。多 Agent 同样必须由用户显式要求，或由 source spec 的独立评估 constraint 授权。
4. spec 中已有的 Independent Review、Required Human Gate 或其他 durable constraint 仍必须满足，但只使用最小充分路径，不自动扩展成多 reviewer 或重复 gate。
5. artifact 操作前确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`；未设置时使用默认值。

## Active Skills

| Skill | 触发倾向 | 进入场景 | 边界 |
| --- | --- | --- | --- |
| `to-spec` | 显式 `$` | 长期设计、需求澄清、spec / readiness / Progress 更新 | 底座对齐、决策归属、决策前沿、就绪证明；不记录对齐流水或 runtime 拓扑 |
| `pick-goal` | 显式 `$` | 从一个或多个 spec 选择、恢复、生成或启动 runtime goal | 选择只读；ready 交 `to-implement`，alignment 交 `to-spec`，blocked 不启动 |
| `to-implement` | 自动 | 用户要求执行 / 继续 ready spec、implementation-ready goal，或给出 active thin plan 作为 resume locator | runtime-first；按恢复价值决定是否维护 plan；不接收 alignment 或 blocked goal |
| `to-issue` | 显式 `$` | 记录值得长期保留的问题、证据、机会或 unresolved finding | 不是执行 slice；不创建外部 tracker |
| `to-debug` | 自动 | 定位问题、复现异常、分析 root cause、固化真实事故回归 | infra 取证转项目 adapter；回归测试复用当前诊断证据，不另开工作流 |
| `to-infra` | 自动 | 环境、日志、数据库、缓存、Metrics、告警、部署或外部系统 | project-provided adapter |
| `to-knowledge` | 显式 `$` | 沉淀业务无关、可跨项目复用的技术知识 | 不自动写笔记或派发 sidecar |
| `to-review` | 显式 `$` | 用户要求专门 code / artifact review | 单 reviewer 默认；不自动修复或升级循环 |
| `to-review-loop` | 显式 `$` | review-fix-rereview | 高成本；consolidation 需单独显式调用，独立 verifier 仅补真实高风险证据缺口 |
| `to-agent-review` | 显式 `$` | 复盘 Agent 决策链、工具、动态调度、fan-in 和状态写回 | 默认在对话输出；只有明确要求才写报告 |
| `to-acceptance` | 显式 `$` | 创建 durable 人类验收 / sign-off artifact | 一次性问题直接在对话询问 |
| `to-next-acceptance` | 显式 `$` | 根据人类反馈推进下一轮 acceptance | 未提及项不默认通过 |
| `to-backlog` | 显式 `$` | 工作长期退出当前执行队列、等待外部条件 | 短期 blocker 留在 spec Progress |
| `to-handoff` | 显式 `$` | 易失本地状态需要换会话 / Agent 接力 | 不复制 spec Progress |
| `to-commit` | 自动 | stage、commit、message 或拆分提交 | staged artifact 先 validate-flow |
| `to-consolidation` | 显式 `$` | 用户要求对稳定 diff 做专门熵值收敛 | 普通最终检查由 runtime 直接完成 |
| `validate-flow` | 自动 | durable artifact 变更、thin plan 结构 / 恢复边界或提交前 | 先确定性预检，语义 pass 按风险进入 |
| `to-claude-review` | 显式 `$` | 用户要求 Claude Code 第二意见或供应商独立复审 | Codex-only bridge |

## Native Runtime Execution

ready spec、其派生的 implementation-ready goal，或已解析回 ready source spec 的 active plan locator，由 `to-implement` 交给原生 runtime：

- 简单工作直接执行；复杂但连续且低恢复成本的工作只用 runtime checklist。只有恢复价值成立时，`to-implement` 才按需或中途 materialize thin plan，具体门槛与内容边界由该 Skill 维护。
- 多消费者需要共享边界时，可复用紧凑 runtime 投影；它本身不是 artifact。多 Agent 只按用户或 source spec 的独立评估要求进入，不预设固定流水线。
- 同一文件 / 共享状态避免并发多写；交接后可以动态更换 writer。
- 测试 ROI、stable seam、验证模式和普通测试实现由 runtime 按风险决定；真实事故的回归固化留在 `to-debug`，`Given / When / Then` 只是可选表达方式。
- 目标级稳定状态写回 spec；有恢复价值的实施 working set 写回 active plan。任何改变 source spec 规范性边界的事实或决定先回 `$to-spec`。

runtime checklist 不是 artifact，也不因步骤多就复制成 plan。thin plan 不是 readiness gate 或 runtime controller。

用户显式调用 `$pick-goal` 时，只读派生 portable runtime goal；`Progress.Next` 只是恢复入口，不是 goal 本身。若用户同时要求启动，ready goal 交给 `to-implement`，alignment goal 交给 `to-spec`，仍有 blocker 时只报告解除条件。原生 goal 创建后，执行和稳定状态写回由接收方负责。

## Real Boundary Routing

- 当前 slice 的局部实施阻塞可留在 active plan；会阻塞整体 goal、涉及外部条件 / authority / durable constraint 的 blocker 写入 spec Progress，plan 只引用它。
- 实现上下文需要跨会话恢复，但仍属于同一 active workstream：由 `to-implement` 维护 thin plan；不要误用 handoff。
- 长期延期或退出当前执行队列：用户明确要求记录时使用 `$to-backlog`。
- 未提交 diff、终端、临时环境或易失证据需要接力：用户明确要求交接时使用 `$to-handoff`。
- 人类 approval、真实设备 / 账号 / 环境、体验或风险接受：先在对话停止并询问；只有用户显式要求 durable gate 时使用 `$to-acceptance`。
- Agent 可自行验证：直接运行测试、静态检查、build、真实路径检查和 diff sanity，证据压缩回 spec Progress；不要为此自动进入 review / consolidation Skill。

## Retired Skills

历史 plan/task/step 拓扑、`to-plan` / `pick-plan` / `to-task` / `to-archive` 与已被 native runtime / `to-debug` 吸收的测试工作流保存在仓库根 `archive/skills/`，不被 active installer 发现，也不得从 routing 推荐。当前 thin plan 只是 `to-implement` 的按需 working set，不恢复旧 skill 或拓扑。迁移时把长期设计、稳定状态和证据压入 spec，把仍有恢复价值的实施上下文改写成 thin plan，只把真实边界分流到 acceptance、backlog 或 handoff。
