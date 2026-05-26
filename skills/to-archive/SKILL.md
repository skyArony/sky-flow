---
name: to-archive
description: 'Compress completed Sky Flow plan/task execution artifacts after a plan is done; preserve only durable facts, decisions, evidence pointers, and follow-up references while clearing or retaining task files by policy.'
---

# to-archive

`to-archive` 在 Sky Flow plan 完成后压缩执行期 artifact。它不新增长期 artifact 类型；归档摘要写回 completed plan 本身，task 文件默认视为执行脚手架，只有存在审计、恢复、争议或未压缩事实价值时才继续保留。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取来源 plan、直属 tasks、关联 spec / issue / acceptance / backlog / handoff；来源可以在 `${SKY_FLOW_ROOT}/plan/` 或 `${SKY_FLOW_ROOT}/plan/done/`。
3. 检查归档前置条件：plan 已完成或即将标记完成；所有直属 task 已 `completed`，或未完成项已转入 backlog / handoff / acceptance；没有只能靠 task 详情恢复的 blocker。
4. 提取长期事实：最终 outcome、实际 scope、产物路径、验证证据、关键决策、放弃或延期事项、后续可恢复入口。
5. 更新 completed plan：保留短 `Summary`、`Archive Summary`、`Facts`、`Decision Log`、`Evidence` 和必要 follow-up；删除执行流水、过期 recovery、重复 fan-in 细节和微步骤。
6. 选择 task retention：
   - 默认 `summary-only`：清空 plan frontmatter 的 `tasks: []`，删除 `${SKY_FLOW_ROOT}/tasks/<plan-id>/`。
   - `retain-task-files`：保留 task 文件和 `plan.tasks`，并在 `Archive Summary` 说明保留原因。
7. 如果需要删除 task 文件，遵守当前 runtime 的删除审批规则；不能静默绕过 destructive command 审批。
8. 如果 plan 已完成但还在 `${SKY_FLOW_ROOT}/plan/`，移入 `${SKY_FLOW_ROOT}/plan/done/`；同步本地 TOC / artifact 引用。
9. 创建、移动、删除或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

## Retention Policy

task 文件不默认长期保存。它们的主要价值是执行期调度、并行、fan-in 和恢复；当 plan 已完成且归档摘要覆盖了事实和决策后，继续保留完整 task 通常会增加噪声。

保留 task 文件只在下面情况成立：

- 审计、合规、客户复盘或 review 需要完整执行粒度。
- plan 虽然完成，但后续 24 小时内仍可能按 task 级上下文继续衔接。
- task 中有尚未压缩进 plan 的关键事实、验证证据、争议或失败尝试。
- 存在 abandoned / deferred / blocked task，需要 backlog 或 handoff 继续指向原 task。
- 人类明确要求保留完整任务记录。

默认删除前必须确认这些信息已进入 completed plan、acceptance、backlog 或 handoff；不能把唯一事实来源删掉。

## Archive Shape

completed plan 的归档正文保持短。优先保留事实和决策，不保留执行流水。

```markdown
## Archive Summary

- Outcome:
- Actual scope:
- Durable outputs:
- Verification:
- Follow-ups:
- Task retention: summary-only / retain-task-files

## Facts

- <最终成立的事实、产物状态、验证结论或外部约束。>

## Decision Log

- <YYYY-MM-DD>: <决策>；原因：<关键依据>；影响：<后续维护要知道的结果>。

## Evidence

- <命令、报告、artifact、PR、日志或验收入口>: <结论。>
```

可以省略没有内容的 section。不要复制完整 task 正文、长日志、聊天摘要、子代理原始汇报或命令流水；只保留结论和可追溯入口。

## Compression Rules

- 事实必须可追溯到代码、artifact、验证命令、验收反馈或明确人类决策。
- 决策只记录会影响后续维护、恢复、验收或计划拆分的取舍。
- 过期 recovery 应压成 `Recovery: complete; no resume action` 或删除；仍需恢复的事项必须转入 backlog / handoff。
- 验证证据保留命令和结论即可，失败后已修复的中间失败只在能解释最终决策时保留。
- task DAG、parallel_with、depends_on、dispatch packet、owner 选择、微步骤和普通 fan-in 过程默认丢弃。

## Boundaries

- 不改变 spec 需求、plan goal 或完成口径；发现完成口径不成立时回到 `to-implement` / `to-plan`。
- 不替代 `to-acceptance`；人类验收反馈必须保存在 acceptance。
- 不替代 `to-backlog` / `to-handoff`；仍需恢复的未完成事项必须进入对应 artifact。
- 不新增 `archive` artifact 类型；压缩结果属于 completed plan 的最终形态。
- 不为了压缩而删除唯一证据；先迁移事实，再删除脚手架。

## Self-Review

- Completeness：完成事实、关键决策、验证证据和 follow-up 是否足以理解最终状态。
- Retention：如果删除 task，是否已清空 `plan.tasks` 并确保无唯一事实丢失。
- Noise：是否删除了执行流水、重复 fan-in 和微步骤。
- Recovery：未完成或延期事项是否有 backlog / handoff，而不是埋在归档摘要里。
- Validation：是否运行 `validate-flow` 并处理结构错误。
