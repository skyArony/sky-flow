# Sky Flow Routing

本文件是 active 子能力和触发规则的完整来源。根 `SKILL.md` 只保留入口短路径。

## Trigger Order

1. 普通工作默认直接使用 native runtime；测试、静态检查、build、diff sanity 和修复后定点验证不需要专门 Skill。
2. `to-debug`、`to-infra`、`to-commit` 和 ready execution 可按用户意图自动进入；其他长期 authoring、重型 review 和 durable collaboration 能力由用户显式调用。
3. spec 中已有的 Independent Review、Required Human Gate 或其他 durable constraint 必须满足，但只使用最小充分路径，不自动扩展成重复 gate。
4. durable document 操作前确定 `SKY_FLOW_ROOT` / `SKY_FLOW_LANG`；未设置时使用默认值。
5. 文档格式由 owning Skill 负责。Sky Flow 不运行中央 schema validator，也不维护全库 artifact graph。

## Active Skills

| Skill | 触发倾向 | 进入场景 | 边界 |
| --- | --- | --- | --- |
| `to-align` | 显式 `$` | 正式编码前持续多轮关闭实质需求、风险、兼容与验收决策 | runtime 覆盖表与停止条件；稳定结论交 `to-spec` |
| `to-spec` | 显式 `$` | 长期设计、需求澄清、spec / readiness / Progress | 规范性真相与目标级恢复，不记录执行拓扑 |
| `to-milestone` | 显式 `$` | 大型 spec 需要逐层分阶段落地、评审和人类验收 | 每次只展开一层；代码计划交 runtime |
| `pick-goal` | 显式 `$` | 从一个或多个 spec 选择、恢复、生成或启动 runtime goal | 选择只读；按 readiness 交接 |
| `to-implement` | 自动 | 执行 ready spec / goal、approved executable milestone 或 active thin plan locator | runtime-first；按恢复价值决定 thin plan |
| `to-issue` | 显式 `$` | 记录值得长期保留的问题、证据或机会 | 不是执行 slice |
| `to-debug` | 自动 | 复现异常、定位 root cause、固化真实事故回归 | infra 取证转项目 adapter |
| `to-infra` | 自动 | 环境、日志、数据库、缓存、Metrics、告警、部署或外部系统 | project-provided adapter |
| `to-knowledge` | 显式 `$` | 沉淀跨项目技术知识 | 不自动写笔记 |
| `to-review` | 显式 `$` | 专门 code / document review | 默认单 reviewer，不自动修复 |
| `to-review-loop` | 显式 `$` | review-fix-rereview | 高成本，按证据停止 |
| `to-agent-review` | 显式 `$` | 复盘 Agent 决策、工具与调度 | 默认在对话输出 |
| `to-acceptance` | 显式 `$` | durable、多轮或跨会话人类 gate | 一次性确认留在对话 |
| `to-next-acceptance` | 显式 `$` | 根据人类反馈推进下一轮 acceptance | 未提及项不默认通过 |
| `to-backlog` | 显式 `$` | 工作长期退出当前执行队列 | 短期 blocker 留在 source document |
| `to-handoff` | 显式 `$` | 易失本地状态需要换会话 / Agent 接力 | 不复制长期 Progress |
| `to-commit` | 自动 | stage、commit、message 或拆分提交 | scoped stage、项目验证与 staged sanity |
| `to-consolidation` | 显式 `$` | 对稳定 diff 做专项熵值收敛 | 普通最终检查由 runtime 完成 |
| `show-me` | 讲解请求 / 显式调用 | 独立讲解当前主题，也可供 milestone 调用 | 无需 spec、milestone 或实施授权；按主题选择最小充分图示 |
| `to-claude-review` | 显式 `$` | Claude Code 第二意见 | Codex-only bridge |

## Milestone Routing

- spec 仍缺少会改变阶段 outcome、系统边界或验收的规范性决定：回 `$to-spec`。
- 只需要实现一个清楚目标：直接 `to-implement`，不创建 milestone tree。
- 只有用户明确选择 milestone 流程时才进入 `$to-milestone`；已有选择可沿用，不因任务复杂或发现 milestone 文档而自动进入。
- 在用户已选择的 milestone 流程内，approved executable leaf 的 runtime goal 包含 milestone outcome、leaf acceptance、source spec constraints 和当前 evidence；具体步骤不持久化到 milestone。
- 实现产生长期决定：先回 `$to-spec`，再让受影响 milestone 重新评审。
- 实现完成但人类未验收：leaf 保持 active；只有需要 durable gate 且用户显式要求时才创建 acceptance document。

## Runtime Execution

ready spec、其派生 goal、approved executable milestone 或已解析回 ready source spec 的 active thin plan locator 由 `to-implement` 交给 runtime：

- 简单或低恢复成本工作直接执行。
- 复杂但当前可连续完成的工作可以只用 runtime checklist。
- 只有跨会话恢复价值超过维护成本时才 materialize thin plan。
- 默认由 native runtime 根据任务和运行时权限选择执行方式，不强制多 Agent 或多模型；显式要求的独立评估仍须保留。共享 contract、schema、部署配置和同一文档避免并发多写。
- 测试 ROI、stable seam、验证组合和 diff sanity 由 runtime 按风险决定。

## Real Boundary Routing

- 规范性设计与目标级稳定进度：spec。
- 阶段层级、hard dependency、人类逐层评审和 leaf completion：milestone。
- 当前实现代码上下文与恢复动作：optional thin plan。
- 长期退出活动队列：backlog。
- 未提交 diff、终端和临时环境：handoff。
- 跨会话、多轮或可审计的人类判断：acceptance。
- 问题、证据或机会：issue。

每类文档正文自包含到足以恢复其责任边界；来源字段只在提高发现与恢复效率时使用，不形成中央关系图。
