# Sky Flow Routing

本文件是 active 子能力和触发规则的完整来源。根 `SKILL.md` 只保留入口短路径和快速路由。

## Trigger Order

1. 显式点名优先：用户点名某个 active 子能力时直接进入。
2. 自动场景触发：debug、infra、BDD 回归、testing、review、commit、consolidation、acceptance、knowledge、validate-flow，以及 ready spec execution。
3. artifact 操作前确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`；未设置时使用默认值。
4. 不需要长期 artifact、跨会话状态或专门能力的简单工作直接使用 runtime。

## Active Skills

| Skill | 触发倾向 | 进入场景 | 边界 |
| --- | --- | --- | --- |
| `to-spec` | 显式 | 长期设计、需求澄清、spec / readiness / Progress 更新 | 先对齐再写；不记录 runtime 拓扑 |
| `pick-goal` | 显式 | 从一个或多个 spec 选择、恢复、生成或启动 runtime goal | 选择只读；ready 交 `to-implement`，alignment 交 `to-spec`，blocked 不启动 |
| `to-implement` | 自动 | 用户要求执行 / 继续 ready spec 或其派生的 implementation-ready goal | 动态执行并压缩写回 Progress；不接收 alignment 或 blocked goal |
| `to-issue` | 显式 | 记录值得长期保留的问题、证据、机会或 unresolved finding | 不是执行 slice；不创建外部 tracker |
| `to-debug` | 自动 | 定位问题、复现异常、分析 root cause | infra 取证转项目 adapter；事故回归转 BDD |
| `to-infra` | 自动 | 环境、日志、数据库、缓存、Metrics、告警、部署或外部系统 | project-provided adapter |
| `to-bdd-regression` | 自动 | 真实 bug / 事故需要固化成证据驱动回归 | 复用 debug 已有证据 |
| `to-test` | 自动 | 测试策略、BDD/TDD、ROI、stable seam、替代验证 | 不替代 debug |
| `to-knowledge` | 自动 | 发现业务无关、可跨项目复用的技术知识 | 不记录项目 / 业务实现状态 |
| `to-review` | 自动 | code / artifact review 或阶段复审 | 默认只读；风险高时独立 reviewer |
| `to-review-loop` | 显式 | review-fix-rereview | 高成本；要求 final consolidation 和 verifier gate |
| `to-agent-review` | 显式 | 复盘 Agent 决策链、工具、动态调度、fan-in 和状态写回 | 默认输出报告，不自动改规则 |
| `to-acceptance` | 自动 | 真实人类验收、sign-off、补信息或风险决策 | Agent 可自证事项不进入 |
| `to-next-acceptance` | 显式 | 根据人类反馈推进下一轮 acceptance | 未提及项不默认通过 |
| `to-backlog` | 显式 | 工作长期退出当前执行队列、等待外部条件 | 短期 blocker 留在 spec Progress |
| `to-handoff` | 显式 | 易失本地状态需要换会话 / Agent 接力 | 不复制 spec Progress |
| `to-commit` | 自动 | stage、commit、message 或拆分提交 | staged artifact 先 validate-flow |
| `to-consolidation` | 自动 | 阶段完成、多 Agent fan-in 或用户要求收敛 diff | 只处理 pending diff 熵值 |
| `validate-flow` | 自动 | 创建 / 修改 artifact、稳定 Progress 写回或提交前 | 只检查轻量结构和来源 |
| `to-claude-review` | 显式 | Codex 需要 Claude Code 只读第二意见 | Codex-only bridge |

## Native Runtime Execution

ready spec 或其派生的 implementation-ready goal 由 `to-implement` 直接交给原生 runtime：

- 工作简单时主代理直接执行，不创建额外 checklist。
- 复杂工作可以使用 runtime checklist、子代理或其他原生协调能力；不预设角色、packet 或固定流水线。
- 同一文件 / 共享状态避免并发多写；交接后可以动态更换 writer。
- 只有语义级 checkpoint、outcome、blocker、evidence、risk 或 resume target 写回 spec Progress。
- scope 内 implementation strategy 由 runtime 自主调整；material goal、external behavior、contract 或 data semantics 变化时回 `to-spec`。

runtime checklist 不是 artifact，不接受 `validate-flow`，也不应被复制进 spec、handoff 或 backlog。

用户明确要求从多个 spec 中选择或生成目标时，先用 `pick-goal` 只读派生 portable runtime goal；`Progress.Next` 只是恢复入口，不是 goal 本身。若用户同时要求启动，ready goal 交给 `to-implement`，alignment goal 交给 `to-spec`，仍有 blocker 时只报告解除条件。原生 goal 创建后，执行和稳定状态写回由接收方负责。

## Real Boundary Routing

- 临时执行阻塞：写入 spec Progress `Blockers`。
- 长期延期或退出当前执行队列：`to-backlog`。
- 未提交 diff、终端、临时环境或易失证据需要接力：`to-handoff`。
- 人类 approval、真实设备 / 账号 / 环境、体验或风险接受：`to-acceptance`。
- Agent 可自行验证：直接测试 / review / consolidate，证据压缩回 spec Progress。

## Retired Skills

历史文件化执行拓扑能力保存在仓库根 `archive/skills/`，不被 active installer 发现，也不得从 routing 推荐。迁移时把长期设计、稳定状态和证据压入 spec；只把真实边界分流到 acceptance、backlog 或 handoff。
