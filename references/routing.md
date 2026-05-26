# Sky Flow Routing

本文件是 Sky Flow 子能力清单和触发规则的完整来源。根 `SKILL.md` 只保留入口必经短路径和快速路由，避免 Agent 每次加载重复细节。已落地为独立 skill 的顶层子能力通常放在 `skills/<name>/SKILL.md`；嵌套子能力可以放在所属能力目录下；普通 `.md` 引用文件不会被发现为 callable skill。

## 触发顺序

1. 显式点名优先：用户提到 `to-spec`、`to-plan`、`validate-flow` 等子能力时，直接进入对应能力。
2. 自动场景必须触发：debug、infra 查询 / 操作、BDD 回归固化、testing、review、commit、consolidation、acceptance、completed plan 归档压缩、validate-flow、Sky Flow plan / task execution 命中时，不等待用户再次点名。
3. Artifact 操作前先确定 runtime 配置：任何读取、创建或修改 Sky Flow artifact 的任务，都先确定 `SKY_FLOW_ROOT` 和 `SKY_FLOW_LANG`，没有环境变量时使用默认值。
4. 简单任务快速退出：不需要 workflow artifact、不需要跨会话状态、不命中自动场景时，直接使用 runtime。

## 完整触发表

| Skill                | 触发倾向 | 进入场景                                                                                               | 注意事项                                            |
| -------------------- | -------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| `to-spec`            | 显式     | 生成或更新长期留存的设计文档；系统化设计澄清。                                                         | 不强制立刻进入 plan。                               |
| `to-issue`           | 显式     | 在本地 docs issue 目录记录近期问题、现象、证据、线索或可独立认领 slice，尚不进入修复。                  | 不创建外部 tracker issue；不替代 debug 或 plan。    |
| `to-debug`           | 自动     | 定位问题、复现异常、分析 root cause。                                                                  | 调试循环入口；基础设施查询 / 操作转项目级 `to-infra`，真实事故回归转 `to-bdd-regression`。 |
| `to-infra`           | 自动     | 查询或操作基础设施、环境、日志、数据库、缓存、Metrics、Grafana、AlertManager、部署或外部系统。           | Project-provided adapter；Sky Flow core 不实现具体环境细节。 |
| `to-bdd-regression`  | 自动     | 线上 bug、客户反馈、日志 / 数据异常、时序或状态机问题需要固化为 BDD-style 回归。                         | `to-debug` 子能力；复用已有诊断信息，不重复取证。   |
| `to-test`            | 自动     | 新增 / 修改测试、写 Given / When / Then、判断测试 ROI、选择 stable seam、决定 Red / Green / Refactor 或替代验证。 | 不替代 `to-debug`；真实事故回归转 `to-bdd-regression`；项目命令由本地规则决定。 |
| `to-plan`            | 显式     | 从 spec、issue 或当前会话生成实施计划；承载目标、范围、阶段、进度、恢复入口和 handoff。                  | 普通 / 中等任务保持单 Plan；task DAG 和执行模型分别交给 `to-task` / `to-implement`。 |
| `to-task`            | 显式     | 从 plan 拆出 task、依赖、并行关系、owner、write scope、no-touch 和可选 step。                           | 必须以 task-ready plan 作为输入；不执行 task。      |
| `to-implement`       | 自动     | 执行和维护指定 Sky Flow plan / task artifact / task DAG，协调主代理、子代理、验证、fan-in、runtime plan、动态 task 调整和 artifact 状态回写。 | 日常任务不用；仅显式指定，或执行已制定 Sky Flow plan / task 时触发。 |
| `to-review`          | 自动     | 小型 review、明确 review 指令，或流程阶段需要复审。                                                    | 查代码风险，不做 artifact 校验或 diff 收敛。        |
| `to-review-loop`     | 显式     | review-fix-review 循环。                                                                               | 成本较高，必须有明确意图。                          |
| `to-agent-review`    | 显式     | Agent 决策链路、工具调用、子代理 ROI 和流程低效点复盘；常见自动场景是 runtime 自动化在固定时间点触发。 | 普通会话只在明确 Agent 复盘场景中自动触发；报告默认写入 `${SKY_FLOW_ROOT}/backlog/agent-reivew/`。 |
| `pick-plan`          | 显式     | 从未完成 plan 和近期完成 plan 中挑选下一步推荐项。                                                     | 输出推荐 plan 和可复制续跑提示。                    |
| `to-acceptance`      | 自动     | 出现需要人类验收的点，或人类补充验收点 / 验收要求。                                                    | 完成声明前必须有验证证据。                          |
| `to-next-acceptance` | 显式     | 处理已有 acceptance 的人类反馈并推进下一轮；作为 `to-acceptance` 的子能力维护。                         | 未提及项不默认通过。                                |
| `to-archive`         | 自动     | plan 完成后需要压缩 task / fan-in 执行记录，或用户要求归档、压缩、清理 completed plan。                 | 默认 summary-only；删除 task 文件前必须满足当前 runtime 审批规则。 |
| `to-backlog`         | 显式     | 当前阶段无法推进、被阻塞、延期或需要回收。                                                             | 说明阻塞原因、依赖和建议恢复时机。                  |
| `to-handoff`         | 显式     | 跨会话继续、换 Agent、保存可执行恢复状态。                                                             | 不写聊天摘要式 handoff。                            |
| `to-commit`          | 自动     | 用户要求 stage、commit、commit message 或拆分提交。                                                    | 遵守项目本地提交规范和验证要求；staged diff 含 workflow artifact 时先推荐 `validate-flow`。 |
| `to-consolidation`   | 自动     | 阶段产物完成、多 Agent fan-in 后、task 显式安排收敛或用户要求收敛 diff。                               | 只收敛当前 pending diff，不查 artifact/status；不作为 `to-commit` 固定前置。 |
| `validate-flow`      | 自动     | 创建或修改 Sky Flow artifact 后、plan 主会话 fan-in 后，或提交 workflow artifact 前。                  | 只检查 artifact 契约和状态一致性。                  |

## Runtime Plan

使用 Codex 执行 Sky Flow plan 时，`to-implement` 主会话负责把文件化 plan / task DAG 映射为 `update_plan` 任务清单，并随着 task 状态变化持续更新。

当文件化 plan 是父 Plan 时，主会话只把当前可执行子 Plan 映射为 runtime 任务清单；父 Plan 本身只提供总纲和
`child_plans` 串行顺序。

并行组使用 `[并行 n]` 标记：

```text
- task A
- [并行 1] task B-1
- [并行 1] task B-2
- task C
```

主会话负责 plan 级 coordination / fan-in 和 artifact 状态维护。若 runtime 支持二级子代理，task owner 可以在自己的 task scope 内继续派发二级子代理，但必须自行 fan-in 后把最终结果回报主会话。
