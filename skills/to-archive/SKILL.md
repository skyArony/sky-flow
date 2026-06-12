---
name: to-archive
description: "Compress completed Sky Flow plan/task/acceptance artifacts after a plan is done; preserve durable design facts, implementation facts, acceptance conclusions, evidence pointers, and follow-up references while clearing plan-scoped task files by summary-only policy."
---

# to-archive

`to-archive` 在 Sky Flow plan 完成后压缩执行期 artifact，也定义 standalone task 完成后的自压缩规则。它不新增长期 artifact 类型；plan 归档摘要写回 completed plan 本身，plan-scoped task 文件视为执行脚手架，默认 summary-only 清理，验收通过的 acceptance 默认压缩为长期验收凭证。standalone task 没有 parent plan，完成后按 completed plan 的标准把事实和证据压缩回 task 自身并移动到 `tasks/standalone/done/`。

## Quick Path

1. 确定 runtime 配置：`SKY_FLOW_ROOT` 默认 `docs`，`SKY_FLOW_LANG` 默认跟随用户语言；不读取额外项目配置文件。
2. 读取来源 plan、直属 tasks、关联 spec / issue / acceptance / backlog / handoff；来源可以在 `${SKY_FLOW_ROOT}/plan/` 或 `${SKY_FLOW_ROOT}/plan/done/`。
3. 检查归档前置条件：plan 已完成或即将标记完成；所有直属 task 已 `completed`，或未完成项已转入 backlog / handoff / acceptance；没有只能靠 task 详情恢复的 blocker。
4. 提取长期事实并归位：
   - spec：只放长期需求、设计约束、架构决策、接口 / 数据 / 安全口径；不放执行流水。
   - completed plan：放实际实现 scope、落地产物、关键实现决策、验证证据入口、后续 follow-up 和 task retention。
   - completed acceptance：放人工验收结论、覆盖的关键场景、核心证据入口、残余风险和未授权推广边界。
5. 更新 completed plan：保留短 `Summary`、`Archive Summary`、`Facts`、`Decision Log`、`Evidence` 和必要 follow-up；删除执行流水、代码修改流水、过期 recovery、重复 fan-in 细节和微步骤。
6. 压缩全部验收通过的 acceptance：保留 artifact 和 frontmatter，把长步骤、逐项执行流水和中间排查压成 `结论`、`验收结果`、`证据入口`、`残余风险 / Follow-up`；未通过、部分通过、仍有 open feedback 或争议的 acceptance 不压缩为通过结论。
7. 执行 task retention：
   - 固定 `summary-only`：清空 plan frontmatter 的 `tasks: []`，删除 `${SKY_FLOW_ROOT}/tasks/<plan-id>/`。
   - 如果审计、合规、争议、后续衔接或人类明确要求导致不能安全删除 task 文件，先迁移事实或停下来确认；标准归档不保留完整 plan-scoped task 文件。
8. 如果需要删除 task 文件，遵守当前 runtime 的删除审批规则；不能静默绕过 destructive command 审批。
9. 如果 plan 已完成但还在 `${SKY_FLOW_ROOT}/plan/`，移入 `${SKY_FLOW_ROOT}/plan/done/`；同步本地 TOC / artifact 引用。
10. 创建、移动、删除或修改 artifact 后运行 `validate-flow`，处理结构错误后再交付。

standalone task 不走 plan 归档路径：确认 task 已完成，按 completed plan 的归档标准把执行流水压成短 `Summary`、`Facts`、`Decision Log`、`Evidence`、`Follow-ups`，设置 `status: completed`，并移入 `${SKY_FLOW_ROOT}/tasks/standalone/done/`。如果执行中已经升级为 plan，standalone task 只记录 promoted-to-plan 和恢复入口，不复制 plan 执行流水。

## Retention Policy

plan-scoped task 文件不作为长期归档形态。它们的主要价值是执行期调度、并行、fan-in 和恢复；当 plan 已完成且归档摘要覆盖了事实和决策后，长期归档面只保留 summary。

如果审计、合规、客户复盘、review、后续衔接、未完成项或人类明确要求仍需要 task 级事实，不能把唯一事实来源直接删除；先把必要事实迁移到 completed plan、acceptance、backlog、handoff 或证据入口，或停下来让人类确认。标准归档结果仍是 `Task retention: summary-only`，不保留 `plan.tasks` 和完整 plan-scoped task 文件。

默认删除前必须确认这些信息已进入 completed plan、acceptance、backlog 或 handoff；不能把唯一事实来源删掉。plan-scoped task 不做捞回；后续修复追加新 task，或在旧 task 已清理后重新拆 task DAG。

acceptance 不默认删除。验收报告是人工结论凭证，计划完成且所有验收组通过后应纳入压缩范围：删除详细验收步骤、重复证据和中间排查流水，只保留结论、关键场景覆盖、证据入口、残余风险和后续边界。

保留完整 acceptance 只在下面情况成立：

- 验收未完成、未通过、部分通过，或存在 open feedback / dispute。
- 后续验收轮次需要逐项复用原步骤、样本、截图、日志或人工说明。
- 审计、合规、客户复盘或 review 需要完整验收过程。
- acceptance 中存在尚未迁移进 spec / completed plan 的唯一事实。

## Archive Shape

completed plan 的归档正文保持短。优先保留事实和决策，不保留执行流水。

```markdown
## Archive Summary

- Outcome:
- Actual scope:
- Durable outputs:
- Verification:
- Follow-ups:
- Task retention: summary-only
- Acceptance retention: compressed / retained-full

## Facts

- <最终成立的事实、产物状态、验证结论、踩坑或外部约束。>

## Decision Log

- <YYYY-MM-DD>: <决策>；原因：<关键依据>；影响：<后续维护要知道的结果>。

## Evidence

- <命令、报告、artifact、PR、日志或验收入口>: <结论。>
```

可以省略没有内容的 section。不要复制完整 task 正文、长日志、聊天摘要、子代理原始汇报、命令流水或代码修改流水；只保留结论和可追溯入口。文件、函数、行号级改动流水默认不写，除非关键类、关键设计、关键接口、关键状态或关键词本身是后续维护的必要锚点。

completed acceptance 压缩后保持短，优先保留人类判断和验收边界，不保留完整执行步骤：

```markdown
## 结论

- 结论:
- 确认人 / 来源:
- 确认时间:
- Scope:

## 验收结果

- <关键场景>: 通过 / 未授权 / 不在本次范围。

## 证据入口

- <completed plan / commit / report / command>: <结论。>

## 残余风险 / Follow-up

- <仍需后续维护知道的风险、推广前提或边界。>
```

## Compression Rules

- 事实必须可追溯到代码、artifact、验证命令、验收反馈或明确人类决策。
- 决策只记录会影响后续维护、恢复、验收或计划拆分的取舍。
- 坑点、细节点和关键设计锚点优先保留；逐文件逐函数逐行的代码变更过程默认丢弃。
- 过期 recovery 应压成 `Recovery: complete; no resume action` 或删除；仍需恢复的事项必须转入 backlog / handoff。
- 验证证据保留命令和结论即可，失败后已修复的中间失败只在能解释最终决策时保留。
- 验收通过的 acceptance 应压缩为结论凭证；不要保留验收步骤清单、长日志、逐项 curl 输出或已被 completed plan 覆盖的实现细节。
- 如果 acceptance 里的事实属于长期设计，迁移到 spec；如果属于实际实现或发布状态，迁移到 completed plan；acceptance 只保留人类验收结论和验收边界。
- task DAG、parallel_with、depends_on、dispatch packet、owner 选择、微步骤、普通 fan-in 过程和代码修改流水默认丢弃。

## Boundaries

- 不改变 spec 需求、plan goal 或完成口径；发现完成口径不成立时回到 `to-implement` / `to-plan`。
- 不替代 `to-acceptance`；人类验收反馈必须保存在 acceptance。
- 不把未通过、部分通过、有 open feedback 或有争议的 acceptance 压成通过结论。
- 不删除 acceptance 作为人类验收凭证；只压缩内容，除非人类明确要求删除。
- 不替代 `to-backlog` / `to-handoff`；仍需恢复的未完成事项必须进入对应 artifact。
- 不新增 `archive` artifact 类型；压缩结果属于 completed plan 的最终形态。
- 不为了压缩而删除唯一证据；先迁移事实，再删除脚手架。
- 不把 plan-scoped task 当作可捞回归档；后续修复必须追加新 task 或重新进入 `to-task`。

## Self-Review

- Completeness：spec / completed plan / completed acceptance 是否足以分别理解需求设计、实现事实和验收结论。
- Placement：设计细节是否在 spec；实现细节、证据和 follow-up 是否在 plan；验收结论、关键场景和残余风险是否在 acceptance。
- Retention：是否已按 summary-only 清空 `plan.tasks`，删除 plan-scoped task 目录，并确保无唯一事实丢失。
- Acceptance：全部验收通过的 acceptance 是否已压缩；未完成或有争议的 acceptance 是否保留足够细节。
- Noise：是否删除了执行流水、重复 fan-in 和微步骤。
- Recovery：未完成或延期事项是否有 backlog / handoff，而不是埋在归档摘要里。
- Validation：是否运行 `validate-flow` 并处理结构错误。
