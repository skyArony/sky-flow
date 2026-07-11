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
| `to-implement` | 自动 | 用户要求执行 / 继续 ready spec 或其派生的 implementation-ready goal | 动态执行并压缩写回 Progress；不接收 alignment 或 blocked goal |
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
| `validate-flow` | 自动 | 创建 / 修改 artifact、稳定 Progress 写回或提交前 | 只检查轻量结构和来源 |
| `to-claude-review` | 显式 `$` | 用户要求 Claude Code 第二意见或供应商独立复审 | Codex-only bridge |

## Native Runtime Execution

ready spec 或其派生的 implementation-ready goal 由 `to-implement` 直接交给原生 runtime：

- 工作简单时主代理直接执行，不创建额外 checklist。
- 复杂工作可以使用 runtime checklist；只有用户显式要求多 Agent，或 spec 明确要求独立评估时才派发子代理，不预设角色、packet 或固定流水线。
- 多消费者或上下文容易失真时，可在 runtime 内一次投影`目标 / 成功边界 / 关键约束 / 相关契约 / 当前事实`并复用；它不是 artifact 或固定 packet。
- 同一文件 / 共享状态避免并发多写；交接后可以动态更换 writer。
- 测试 ROI、stable seam、验证模式和普通测试实现由 runtime 按风险决定；真实事故的回归固化留在 `to-debug`，`Given / When / Then` 只是可选表达方式。
- 只有语义级 checkpoint、outcome、blocker、evidence、risk 或 resume target 写回 spec Progress。
- scope 内 implementation strategy 由 runtime 自主调整；material goal、external behavior、contract 或 data semantics 变化时暂停实现并建议 `$to-spec`。

runtime checklist 不是 artifact，不接受 `validate-flow`，也不应被复制进 spec、handoff 或 backlog。

用户显式调用 `$pick-goal` 时，只读派生 portable runtime goal；`Progress.Next` 只是恢复入口，不是 goal 本身。若用户同时要求启动，ready goal 交给 `to-implement`，alignment goal 交给 `to-spec`，仍有 blocker 时只报告解除条件。原生 goal 创建后，执行和稳定状态写回由接收方负责。

## Real Boundary Routing

- 临时执行阻塞：写入 spec Progress `Blockers`。
- 长期延期或退出当前执行队列：用户明确要求记录时使用 `$to-backlog`。
- 未提交 diff、终端、临时环境或易失证据需要接力：用户明确要求交接时使用 `$to-handoff`。
- 人类 approval、真实设备 / 账号 / 环境、体验或风险接受：先在对话停止并询问；只有用户显式要求 durable gate 时使用 `$to-acceptance`。
- Agent 可自行验证：直接运行测试、静态检查、build、真实路径检查和 diff sanity，证据压缩回 spec Progress；不要为此自动进入 review / consolidation Skill。

## Retired Skills

历史文件化执行拓扑与已被 native runtime / `to-debug` 吸收的测试工作流保存在仓库根 `archive/skills/`，不被 active installer 发现，也不得从 routing 推荐。迁移时把长期设计、稳定状态和证据压入 spec；只把真实边界分流到 acceptance、backlog 或 handoff。
